"""
Core Agent Logic — ReAct (Reasoning + Acting) Loop
Connects to Ollama's local API and runs qwen2:7b
"""

import json
import requests
from typing import Generator
from agent.tools import TOOLS, execute_tool
from agent.prompts import SYSTEM_PROMPT


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2:7b"


def chat_with_ollama(messages: list, stream: bool = True) -> Generator[str, None, None]:
    """Send messages to Ollama and stream back the response."""
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
        response = requests.post(OLLAMA_URL, json=payload, stream=stream, timeout=120)
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
    except Exception as e:
        yield f"❌ **Error:** {str(e)}"


def build_tool_context(tools: list) -> str:
    """Format available tools into a readable context block for the model."""
    tool_descriptions = []
    for tool in tools:
        args = ", ".join(
            f"{k}: {v['type']}" for k, v in tool["parameters"]["properties"].items()
        )
        tool_descriptions.append(f"- **{tool['name']}({args})**: {tool['description']}")
    return "\n".join(tool_descriptions)


def detect_and_run_tool(response_text: str) -> tuple[str | None, str | None]:
    """
    Detect if the model wants to use a tool.
    Model should output: TOOL_CALL: tool_name({"arg": "value"})
    Returns (tool_name, tool_result) or (None, None)
    """
    if "TOOL_CALL:" not in response_text:
        return None, None

    try:
        tool_line = [l for l in response_text.split("\n") if "TOOL_CALL:" in l][0]
        tool_part = tool_line.split("TOOL_CALL:")[1].strip()

        paren_idx = tool_part.index("(")
        tool_name = tool_part[:paren_idx].strip()
        args_str = tool_part[paren_idx + 1 : tool_part.rindex(")")].strip()
        args = json.loads(args_str) if args_str else {}

        result = execute_tool(tool_name, args)
        return tool_name, result

    except Exception as e:
        return "unknown", f"Tool parsing error: {str(e)}"


class AIAgent:
    """Simple AI Agent with memory, tools, and streaming responses."""

    def __init__(self):
        self.conversation_history: list[dict] = []
        self.tool_context = build_tool_context(TOOLS)
        self.system_message = {
            "role": "system",
            "content": SYSTEM_PROMPT.format(tool_context=self.tool_context),
        }

    def reset(self):
        """Clear conversation history."""
        self.conversation_history = []

    def get_history_for_display(self) -> list[tuple[str, str]]:
        """Return history in Gradio chatbot format."""
        display = []
        i = 0
        msgs = self.conversation_history
        while i < len(msgs):
            if msgs[i]["role"] == "user":
                user_msg = msgs[i]["content"]
                assistant_msg = msgs[i + 1]["content"] if i + 1 < len(msgs) else ""
                display.append((user_msg, assistant_msg))
                i += 2
            else:
                i += 1
        return display

    def stream_response(self, user_message: str) -> Generator[str, None, None]:
        """
        Process user message and stream back response.
        Handles tool detection and multi-turn tool use.
        """
        self.conversation_history.append({"role": "user", "content": user_message})
        messages = [self.system_message] + self.conversation_history

        full_response = ""
        for chunk in chat_with_ollama(messages):
            full_response += chunk
            yield full_response

        # Check if the model wants to use a tool
        tool_name, tool_result = detect_and_run_tool(full_response)

        if tool_result:
            tool_display = f"\n\n🔧 **Tool Used:** `{tool_name}`\n```\n{tool_result}\n```\n\n"
            yield full_response + tool_display

            # Feed tool result back and get final answer
            follow_up = f"Tool result for {tool_name}:\n{tool_result}\n\nNow provide a helpful, clear answer based on this result."
            messages_with_tool = messages + [
                {"role": "assistant", "content": full_response},
                {"role": "user", "content": follow_up},
            ]

            final_response = ""
            for chunk in chat_with_ollama(messages_with_tool):
                final_response += chunk
                yield full_response + tool_display + final_response

            full_response = full_response + tool_display + final_response

        self.conversation_history.append({"role": "assistant", "content": full_response})
