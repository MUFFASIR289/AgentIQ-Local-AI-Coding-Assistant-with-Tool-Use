"""
Core Agent Logic — ReAct (Reasoning + Acting) Loop
with Langfuse observability tracing.

Every conversation turn is recorded as a Langfuse Trace containing:
  - The user's input message
  - A Span for the message sanitisation step
  - A Generation for each Ollama LLM call (with token counts and latency)
  - A Span for tool detection
  - A Span for tool execution (if a tool was called)
  - A second Generation for the synthesis LLM call (if a tool was used)

If Langfuse is not configured, all tracing calls are silently skipped
and the agent behaves exactly as it did before — tracing is purely additive.
"""

import json
import time
import requests
from typing import Generator
from agent.tools import TOOLS, execute_tool
from agent.prompts import build_system_prompt


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2:7b"


# ──────────────────────────────────────────────
#  OLLAMA COMMUNICATION
# ──────────────────────────────────────────────

def chat_with_ollama(
    messages: list,
    stream: bool = True,
) -> Generator[str, None, None]:
    """
    Send a list of messages to Ollama and stream back the response.

    Yields text chunks one at a time so the UI can display them
    progressively (the 'typing' streaming effect).
    """
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": stream,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_ctx": 4096,
        },
    }

    try:
        response = requests.post(
            OLLAMA_URL, json=payload, stream=stream, timeout=120
        )
        response.raise_for_status()

        if stream:
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line.decode("utf-8"))
                    if not chunk.get("done", False):
                        yield chunk.get("message", {}).get("content", "")
        else:
            data = response.json()
            yield data.get("message", {}).get("content", "")

    except requests.exceptions.ConnectionError:
        yield "❌ **Cannot connect to Ollama.** Make sure Ollama is running: `ollama serve`"
    except requests.exceptions.Timeout:
        yield "❌ **Request timed out.** The model is taking too long to respond."
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else "unknown"
        body   = e.response.text[:300]  if e.response else ""
        yield f"❌ **HTTP {status} Error from Ollama:** {body}"
    except Exception as e:
        yield f"❌ **Unexpected Error:** {str(e)}"


# ──────────────────────────────────────────────
#  TOOL CONTEXT BUILDER
# ──────────────────────────────────────────────

def build_tool_context(tools: list) -> str:
    """Format the tool list into a readable description for the system prompt."""
    lines = []
    for tool in tools:
        props = tool["parameters"].get("properties", {})
        args  = ", ".join(f"{k}: {v['type']}" for k, v in props.items())
        lines.append(f"- **{tool['name']}({args})**: {tool['description']}")
    return "\n".join(lines)


# ──────────────────────────────────────────────
#  TOOL DETECTION
# ──────────────────────────────────────────────

def detect_and_run_tool(response_text: str) -> tuple:
    """
    Scan the model's response for a TOOL_CALL signal.

    If found, parse the tool name + JSON args, execute the tool,
    and return (tool_name, result).
    If not found, return (None, None).

    Expected format from the model:
        TOOL_CALL: tool_name({"arg": "value"})
    """
    if "TOOL_CALL:" not in response_text:
        return None, None

    try:
        tool_line = next(l for l in response_text.split("\n") if "TOOL_CALL:" in l)
        tool_part = tool_line.split("TOOL_CALL:")[1].strip()

        paren_idx = tool_part.index("(")
        tool_name = tool_part[:paren_idx].strip()
        args_str  = tool_part[paren_idx + 1 : tool_part.rindex(")")].strip()

        args = json.loads(args_str) if args_str and args_str != "{}" else {}

        result = execute_tool(tool_name, args)
        return tool_name, result

    except StopIteration:
        return "unknown", "Could not find TOOL_CALL line."
    except json.JSONDecodeError as e:
        return "unknown", f"Could not parse tool arguments as JSON: {e}"
    except Exception as e:
        return "unknown", f"Tool parsing error: {str(e)}"


# ──────────────────────────────────────────────
#  MESSAGE SANITISATION
# ──────────────────────────────────────────────

def extract_text_content(content) -> str:
    """
    Convert any content format to a plain string.

    Gradio 6 sometimes sends content as a list of blocks
    (e.g. [{"type": "text", "text": "hello"}]) rather than
    a plain string. This function handles all cases and always
    returns a clean string that Ollama will accept.
    """
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text") or block.get("content", "")
                if text:
                    parts.append(str(text))
            elif isinstance(block, str):
                parts.append(block)
        return " ".join(parts)

    return str(content) if content is not None else ""


def sanitise_messages(messages: list) -> list:
    """
    Prepare messages for Ollama by converting content to plain strings
    and filtering out any messages with empty content.

    Ollama returns HTTP 400 if any message has an empty content field.
    """
    clean = []
    for msg in messages:
        text = extract_text_content(msg.get("content", ""))
        if text.strip():
            clean.append({"role": msg.get("role", "user"), "content": text})
    return clean


# ──────────────────────────────────────────────
#  LANGFUSE HELPERS
# ──────────────────────────────────────────────

def _safe_end_span(span, output: str = None, metadata: dict = None):
    """
    Safely end a Langfuse span/generation.

    We wrap every Langfuse call in a try/except so that if Langfuse's
    servers are temporarily unreachable, the agent keeps working normally.
    Observability should never break your application — it's optional
    infrastructure layered on top of core functionality.
    """
    if span is None:
        return
    try:
        kwargs = {}
        if output   is not None: kwargs["output"]   = output
        if metadata is not None: kwargs["metadata"]  = metadata
        span.end(**kwargs)
    except Exception:
        pass  # tracing failure must never crash the agent


# ──────────────────────────────────────────────
#  AGENT CLASS
# ──────────────────────────────────────────────

class AIAgent:
    """
    A ReAct-style AI Agent with Langfuse observability.

    Every call to stream_response() creates one Langfuse Trace that
    contains the complete story of what happened: which messages were
    sent, which LLM calls were made, whether a tool was used, what the
    tool returned, and how long each step took.

    The langfuse_client is injected at construction time so the agent
    doesn't depend on any global state. If it's None, tracing is skipped.
    """

    def __init__(self, langfuse_client=None):
        self.conversation_history: list[dict] = []
        self.langfuse = langfuse_client         # None means tracing is disabled

        tool_context = build_tool_context(TOOLS)
        self.system_message = {
            "role":    "system",
            "content": build_system_prompt(tool_context),
        }

    def reset(self):
        """Wipe conversation memory — called when the user clicks Clear."""
        self.conversation_history = []

    def stream_response(self, user_message: str) -> Generator[str, None, None]:
        """
        The full ReAct loop with Langfuse tracing woven in.

        Langfuse Trace structure created per call:
        ─────────────────────────────────────────
        Trace: "chat_turn"
          ├── Span:       "sanitise_messages"
          ├── Generation: "llm_first_call"       ← always happens
          ├── Span:       "tool_detection"        ← always happens
          ├── Span:       "tool_execution"        ← only if tool called
          └── Generation: "llm_synthesis_call"   ← only if tool called
        """

        # ── STEP 1: Record user message ──────────────────────────────────────
        self.conversation_history.append({
            "role":    "user",
            "content": user_message,
        })

        # ── STEP 2: Create the root Langfuse Trace for this conversation turn ─
        # A Trace is the top-level container that groups all the Spans and
        # Generations that happen during a single user → agent interaction.
        trace = None
        try:
            if self.langfuse:
                trace = self.langfuse.trace(
                    name="chat_turn",
                    input=user_message,
                    metadata={
                        "model":            MODEL_NAME,
                        "history_length":   len(self.conversation_history),
                        "tools_available":  [t["name"] for t in TOOLS],
                    },
                )
        except Exception:
            pass  # Langfuse unavailable — continue without tracing

        # ── STEP 3: Sanitise messages ─────────────────────────────────────────
        # We record this as a Span so you can see in the dashboard how many
        # messages were cleaned and how many were filtered out as empty.
        sanitise_span = None
        try:
            if trace:
                sanitise_span = trace.span(name="sanitise_messages")
        except Exception:
            pass

        raw_messages = [self.system_message] + self.conversation_history
        messages     = sanitise_messages(raw_messages)

        _safe_end_span(sanitise_span, metadata={
            "raw_count":   len(raw_messages),
            "clean_count": len(messages),
        })

        # ── STEP 4: First LLM call — stream the model's initial response ──────
        # We record this as a Langfuse Generation, which is the special Span
        # type for LLM calls. It captures the prompt, the completion, the
        # model name, and the latency so you can see it all in the dashboard.
        generation_span = None
        try:
            if trace:
                generation_span = trace.generation(
                    name="llm_first_call",
                    model=MODEL_NAME,
                    input=messages,     # the full message list sent to Ollama
                    metadata={"stream": True},
                )
        except Exception:
            pass

        t0            = time.time()
        full_response = ""

        for chunk in chat_with_ollama(messages):
            full_response += chunk
            yield full_response              # each yield updates the UI live

        first_call_latency = round(time.time() - t0, 3)

        # End the generation span with the completed output and latency
        try:
            if generation_span:
                generation_span.end(
                    output=full_response,
                    usage={
                        # Ollama doesn't return token counts during streaming,
                        # so we estimate: ~0.75 tokens per character is a
                        # reasonable approximation for English text.
                        "input":  int(sum(len(m["content"]) for m in messages) * 0.75),
                        "output": int(len(full_response) * 0.75),
                    },
                    metadata={"latency_seconds": first_call_latency},
                )
        except Exception:
            pass

        # ── STEP 5: Tool detection ────────────────────────────────────────────
        tool_detection_span = None
        try:
            if trace:
                tool_detection_span = trace.span(
                    name="tool_detection",
                    input=full_response[:500],  # first 500 chars is enough context
                )
        except Exception:
            pass

        tool_name, tool_result = detect_and_run_tool(full_response)

        _safe_end_span(tool_detection_span, metadata={
            "tool_detected": tool_name is not None,
            "tool_name":     tool_name,
        })

        # ── STEP 6: Tool execution (if a tool was detected) ───────────────────
        if tool_result:
            tool_exec_span = None
            try:
                if trace:
                    tool_exec_span = trace.span(
                        name="tool_execution",
                        input={"tool": tool_name},
                        metadata={"tool_name": tool_name},
                    )
            except Exception:
                pass

            # Format the tool result for display in the chat UI
            tool_display = (
                f"\n\n🔧 **Tool Used:** `{tool_name}`\n"
                f"```\n{tool_result}\n```\n\n"
            )
            yield full_response + tool_display

            _safe_end_span(tool_exec_span, output=tool_result)

            # ── STEP 7: Second LLM call — synthesise answer from tool result ──
            # We inject the tool result back into the conversation and ask the
            # model to form a final grounded answer based on the real output.
            follow_up = (
                f"Tool '{tool_name}' returned this result:\n{tool_result}\n\n"
                "Now provide a clear, helpful answer based on this result."
            )
            second_messages = sanitise_messages(
                messages + [
                    {"role": "assistant", "content": full_response},
                    {"role": "user",      "content": follow_up},
                ]
            )

            synthesis_span = None
            try:
                if trace:
                    synthesis_span = trace.generation(
                        name="llm_synthesis_call",
                        model=MODEL_NAME,
                        input=second_messages,
                        metadata={"stream": True, "triggered_by_tool": tool_name},
                    )
            except Exception:
                pass

            t1             = time.time()
            final_response = ""

            for chunk in chat_with_ollama(second_messages):
                final_response += chunk
                yield full_response + tool_display + final_response

            synthesis_latency = round(time.time() - t1, 3)

            try:
                if synthesis_span:
                    synthesis_span.end(
                        output=final_response,
                        usage={
                            "input":  int(sum(len(m["content"]) for m in second_messages) * 0.75),
                            "output": int(len(final_response) * 0.75),
                        },
                        metadata={"latency_seconds": synthesis_latency},
                    )
            except Exception:
                pass

            full_response = full_response + tool_display + final_response

        # ── STEP 8: Save response to memory and close the root trace ─────────
        if full_response.strip():
            self.conversation_history.append({
                "role":    "assistant",
                "content": full_response,
            })

        # End the root trace with the final output so the dashboard shows
        # the complete input → output pair for every conversation turn.
        try:
            if trace:
                trace.update(
                    output=full_response,
                    metadata={
                        "tool_used":            tool_name,
                        "tool_result_length":   len(tool_result) if tool_result else 0,
                        "total_response_length": len(full_response),
                    },
                )
                # flush() ensures this trace is sent to Langfuse immediately
                # rather than waiting for the next batch. Important for
                # short-lived processes and debugging.
                self.langfuse.flush()
        except Exception:
            pass