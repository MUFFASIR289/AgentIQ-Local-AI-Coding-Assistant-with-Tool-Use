"""
Core Agent Logic — ReAct (Reasoning + Acting) Loop
Connects to Ollama's local API and runs qwen2:7b
"""

import json
import requests
from typing import Generator
from agent.tools import TOOLS, execute_tool
from agent.prompts import build_system_prompt


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2:7b"


# ──────────────────────────────────────────────
#  OLLAMA COMMUNICATION
# ──────────────────────────────────────────────

def chat_with_ollama(messages: list, stream: bool = True) -> Generator[str, None, None]:
    """
    Send a list of messages to Ollama and stream back the response token by token.

    Each message must follow the format:
        {"role": "user" | "assistant" | "system", "content": "non-empty string"}

    Ollama returns HTTP 400 if any message has an empty content field,
    which is why we run sanitise_messages() before calling this function.
    """
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": stream,
        "options": {
            "temperature": 0.7,   # controls creativity (0=deterministic, 1=very random)
            "top_p": 0.9,         # nucleus sampling — only considers top 90% probability mass
            "num_ctx": 4096,      # context window size in tokens
        },
    }

    try:
        response = requests.post(
            OLLAMA_URL, json=payload, stream=stream, timeout=120
        )
        # raise_for_status() converts any 4xx/5xx HTTP response into a Python exception
        # so we can catch and display it cleanly instead of getting a confusing crash
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
        body   = e.response.text[:300] if e.response else ""
        yield f"❌ **HTTP {status} Error from Ollama:** {body}"
    except Exception as e:
        yield f"❌ **Unexpected Error:** {str(e)}"


# ──────────────────────────────────────────────
#  TOOL CONTEXT BUILDER
# ──────────────────────────────────────────────

def build_tool_context(tools: list) -> str:
    """Format the list of available tools into a readable description for the model."""
    lines = []
    for tool in tools:
        props = tool["parameters"].get("properties", {})
        args  = ", ".join(f"{k}: {v['type']}" for k, v in props.items())
        lines.append(f"- **{tool['name']}({args})**: {tool['description']}")
    return "\n".join(lines)


# ──────────────────────────────────────────────
#  TOOL DETECTION & EXECUTION
# ──────────────────────────────────────────────

def detect_and_run_tool(response_text: str) -> tuple:
    """
    Scan the model's response for a TOOL_CALL signal.

    If found, parse the tool name and JSON arguments, execute the tool,
    and return (tool_name, result).

    If not found, return (None, None) — meaning the model answered directly.

    Expected signal format from the model:
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
#  MESSAGE VALIDATION
# ──────────────────────────────────────────────

def extract_text_content(content) -> str:
    """
    Safely extract a plain string from a message's content field.

    This is necessary because Gradio 6 (and some AI APIs) can represent
    message content in multiple formats:

      1. A plain string:    "Hello, how are you?"
         — the most common format, used by Ollama and our agent

      2. A list of blocks:  [{"type": "text", "text": "Hello"}]
         — the multimodal format used by some Gradio versions and APIs
         — each block has a "type" and the actual text lives inside "text"

      3. Something else (None, int, etc.)
         — should never happen in normal usage, but we handle it anyway

    We always return a plain string so the rest of our code never has
    to think about which format it received.
    """
    if isinstance(content, str):
        # Case 1: already a plain string — most common case, just return it
        return content

    if isinstance(content, list):
        # Case 2: a list of content blocks — extract and join all text blocks
        # Each block looks like: {"type": "text", "text": "actual content"}
        parts = []
        for block in content:
            if isinstance(block, dict):
                # Try the "text" key first (multimodal block format)
                text = block.get("text") or block.get("content", "")
                if text:
                    parts.append(str(text))
            elif isinstance(block, str):
                parts.append(block)
        return " ".join(parts)

    # Case 3: something unexpected — convert to string as a fallback
    return str(content) if content is not None else ""


def sanitise_messages(messages: list) -> list:
    """
    Prepare messages for sending to Ollama by:
      1. Extracting plain string content from any format (string, list of blocks, etc.)
      2. Filtering out any messages where the content is empty after extraction

    This prevents Ollama's HTTP 400 'Bad Request' error, which it returns
    whenever any message in the array has an empty content field.
    """
    clean = []
    for msg in messages:
        raw_content = msg.get("content", "")
        # Always convert to a plain string first, regardless of original format
        text_content = extract_text_content(raw_content)

        # Only keep the message if it has actual non-whitespace content
        if text_content.strip():
            clean.append({
                "role":    msg.get("role", "user"),
                "content": text_content,   # always a clean plain string
            })
    return clean


# ──────────────────────────────────────────────
#  AGENT CLASS
# ──────────────────────────────────────────────

class AIAgent:
    """
    A ReAct-style AI Agent with persistent conversation memory and tool use.

    'ReAct' stands for Reasoning + Acting — the agent can decide to use
    a tool mid-response, observe the result, and then form a final answer
    based on that real output rather than just making something up.
    """

    def __init__(self):
        self.conversation_history: list[dict] = []

        # Build tool descriptions and inject into the system prompt
        tool_context = build_tool_context(TOOLS)
        self.system_message = {
            "role":    "system",
            "content": build_system_prompt(tool_context),
        }

    def reset(self):
        """Wipe all conversation memory — called when the user clicks Clear."""
        self.conversation_history = []

    def stream_response(self, user_message: str) -> Generator[str, None, None]:
        """
        The full ReAct loop — processes a user message and streams a response.

        Step 1: Record the user's message in conversation history.
        Step 2: Send the full history to Ollama and stream the first response.
        Step 3: Check if the response contains a TOOL_CALL signal.
        Step 4: If yes — execute the tool, show the result, make a second
                Ollama call so the model can interpret the result, stream that.
        Step 5: Save the complete final response to conversation history.
        """

        # Step 1 — add the user's message to memory
        self.conversation_history.append({
            "role":    "user",
            "content": user_message,
        })

        # Build the full message list: system prompt + entire conversation so far
        # Then sanitise to ensure every message has non-empty plain-string content
        messages = sanitise_messages([self.system_message] + self.conversation_history)

        # Step 2 — stream the model's initial response
        full_response = ""
        for chunk in chat_with_ollama(messages):
            full_response += chunk
            yield full_response  # each yield updates the UI in real time

        # Step 3 — check if the model wants to use a tool
        tool_name, tool_result = detect_and_run_tool(full_response)

        if tool_result:
            # Format the tool result as a nicely displayed block in the chat
            tool_display = (
                f"\n\n🔧 **Tool Used:** `{tool_name}`\n"
                f"```\n{tool_result}\n```\n\n"
            )
            yield full_response + tool_display

            # Step 4 — feed the tool result back to the model so it can
            # form a final answer grounded in the actual tool output
            follow_up = (
                f"Tool '{tool_name}' returned this result:\n{tool_result}\n\n"
                "Now provide a clear, helpful answer based on this result."
            )
            second_pass_messages = sanitise_messages(
                messages + [
                    {"role": "assistant", "content": full_response},
                    {"role": "user",      "content": follow_up},
                ]
            )

            final_response = ""
            for chunk in chat_with_ollama(second_pass_messages):
                final_response += chunk
                yield full_response + tool_display + final_response

            full_response = full_response + tool_display + final_response

        # Step 5 — save the complete response to memory for future context
        if full_response.strip():
            self.conversation_history.append({
                "role":    "assistant",
                "content": full_response,
            })