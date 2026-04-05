"""
Gradio UI — Clean, professional chat interface for CodeMentor AI.
Compatible with Gradio 5.x / 6.x

The build_ui() function now accepts an optional langfuse_client parameter
which it passes through to the AIAgent. This is called "dependency injection"
— rather than the UI creating its own Langfuse connection, it receives one
from main.py that was already initialised and health-checked at startup.
"""

import gradio as gr
from agent.agent import AIAgent


# ──────────────────────────────────────────────
#  EVENT HANDLER FUNCTIONS
# ──────────────────────────────────────────────

def handle_send(message: str, history: list):
    """
    Called the instant the user hits Send or presses Enter.
    Appends the user message + an empty assistant placeholder to history,
    and clears the text input so the UI feels responsive immediately.
    """
    if not message.strip():
        return history, ""
    history = history + [
        {"role": "user",      "content": message},
        {"role": "assistant", "content": ""},
    ]
    return history, ""


def make_bot_respond(agent: AIAgent):
    """
    Returns a bot_respond generator function that is bound to a specific
    agent instance. We use a factory function here (a function that returns
    a function) because Gradio's event system needs a plain callable, but
    we also need the function to have access to the agent object.
    This pattern is called a closure.
    """
    def bot_respond(history: list):
        if not history or history[-1]["role"] != "assistant":
            yield history
            return

        user_message = history[-2]["content"]

        for partial_response in agent.stream_response(user_message):
            history[-1]["content"] = partial_response
            yield history

    return bot_respond


def make_clear(agent: AIAgent):
    """Returns a clear function bound to a specific agent instance."""
    def clear_chat():
        agent.reset()
        return [], ""
    return clear_chat


# ──────────────────────────────────────────────
#  EXAMPLE PROMPTS
# ──────────────────────────────────────────────

EXAMPLES = [
    "Explain how neural networks work like I'm 16 years old",
    "Write a Python function to find all prime numbers up to N",
    "What's the difference between a list and a tuple in Python?",
    "How does gradient descent work? Show me with code",
    "Build a simple REST API with Flask — step by step",
    "What is RAG (Retrieval-Augmented Generation) and why is it useful?",
    "Explain Big O notation with real examples",
    "Run this code: x = [i**2 for i in range(5)]; print(x)",
]


# ──────────────────────────────────────────────
#  CUSTOM CSS
# ──────────────────────────────────────────────

CUSTOM_CSS = """
body, .gradio-container {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background: #0f0f1a !important;
}
.header-block {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-radius: 16px; padding: 24px 32px; margin-bottom: 8px;
    border: 1px solid rgba(99,102,241,0.3);
    box-shadow: 0 0 40px rgba(99,102,241,0.15);
}
.send-btn {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    border: none !important; border-radius: 12px !important;
    color: white !important; font-weight: 600 !important;
}
.clear-btn {
    background: rgba(239,68,68,0.15) !important;
    border: 1px solid rgba(239,68,68,0.3) !important;
    border-radius: 12px !important; color: #fca5a5 !important;
    font-weight: 600 !important;
}
.example-btn {
    background: rgba(99,102,241,0.1) !important;
    border: 1px solid rgba(99,102,241,0.25) !important;
    border-radius: 20px !important; color: #a5b4fc !important;
    font-size: 13px !important;
}
.sidebar-box {
    background: #12121f;
    border: 1px solid rgba(99,102,241,0.15);
    border-radius: 16px; padding: 16px;
}
"""


# ──────────────────────────────────────────────
#  UI CONSTRUCTION
# ──────────────────────────────────────────────

def build_ui(langfuse_client=None) -> gr.Blocks:
    """
    Build and return the Gradio Blocks app.

    Parameters
    ----------
    langfuse_client : Langfuse | None
        A pre-initialised Langfuse client from main.py.
        If None, the agent runs without tracing — the UI is identical.
    """
    # Create the agent, injecting the Langfuse client so every
    # conversation turn will be traced automatically.
    agent = AIAgent(langfuse_client=langfuse_client)

    # Create the event handler functions bound to this agent instance
    bot_respond = make_bot_respond(agent)
    clear_chat  = make_clear(agent)

    with gr.Blocks(title="CodeMentor AI") as demo:

        # ── Header ──
        gr.HTML("""
        <div class="header-block">
            <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;">
                <div>
                    <h1 style="margin:0;font-size:28px;font-weight:800;
                               background:linear-gradient(135deg,#a5b4fc,#c4b5fd);
                               -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                        🤖 CodeMentor AI
                    </h1>
                    <p style="margin:6px 0 0;color:#94a3b8;font-size:15px;">
                        Your local AI tutor for coding, programming &amp; artificial intelligence
                    </p>
                </div>
                <div style="display:flex;flex-direction:column;align-items:flex-end;gap:8px;">
                    <div style="display:inline-flex;align-items:center;gap:6px;
                                background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.3);
                                border-radius:20px;padding:4px 14px;font-size:13px;color:#6ee7b7;">
                        🟢 qwen2:7b &nbsp;·&nbsp; Local
                    </div>
                    <div style="display:flex;flex-wrap:wrap;gap:6px;">
                        <span style="background:rgba(139,92,246,0.15);border:1px solid rgba(139,92,246,0.3);
                                     border-radius:6px;padding:2px 10px;font-size:12px;color:#c4b5fd;">🐍 run_python</span>
                        <span style="background:rgba(139,92,246,0.15);border:1px solid rgba(139,92,246,0.3);
                                     border-radius:6px;padding:2px 10px;font-size:12px;color:#c4b5fd;">🧮 calculate</span>
                        <span style="background:rgba(139,92,246,0.15);border:1px solid rgba(139,92,246,0.3);
                                     border-radius:6px;padding:2px 10px;font-size:12px;color:#c4b5fd;">💡 explain</span>
                        <span style="background:rgba(139,92,246,0.15);border:1px solid rgba(139,92,246,0.3);
                                     border-radius:6px;padding:2px 10px;font-size:12px;color:#c4b5fd;">📝 templates</span>
                        <span style="background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.3);
                                     border-radius:6px;padding:2px 10px;font-size:12px;color:#6ee7b7;">📊 Langfuse</span>
                    </div>
                </div>
            </div>
        </div>
        """)

        with gr.Row(equal_height=True):

            with gr.Column(scale=4):
                chatbot = gr.Chatbot(
                    label="",
                    height=520,
                    show_label=False,
                    render_markdown=True,
                    avatar_images=(
                        None,
                        "https://api.dicebear.com/7.x/bottts/svg?seed=codebot&backgroundColor=6366f1",
                    ),
                    placeholder=(
                        "<div style='text-align:center;color:#475569;padding:60px 20px;'>"
                        "<div style='font-size:48px;margin-bottom:12px;'>🚀</div>"
                        "<h3 style='color:#64748b;font-weight:600;'>Ask me anything about coding or AI</h3>"
                        "<p style='color:#475569;font-size:14px;'>"
                        "I can run code, explain concepts, generate templates, and more!"
                        "</p></div>"
                    ),
                )

                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="Ask a coding or AI question... (Press Enter to send)",
                        lines=1, max_lines=5, show_label=False,
                        scale=5, container=False,
                    )
                    send_btn  = gr.Button("Send ✈️",   scale=1, elem_classes=["send-btn"])
                    clear_btn = gr.Button("🗑️ Clear", scale=1, elem_classes=["clear-btn"])

                gr.HTML("<div style='margin-top:12px;color:#64748b;font-size:13px;font-weight:500;'>✨ Try an example:</div>")

                with gr.Row():
                    for ex in EXAMPLES[:4]:
                        b = gr.Button(ex[:50] + ("…" if len(ex) > 50 else ""), size="sm", elem_classes=["example-btn"])
                        b.click(fn=lambda e=ex: e, outputs=msg_input)

                with gr.Row():
                    for ex in EXAMPLES[4:]:
                        b = gr.Button(ex[:50] + ("…" if len(ex) > 50 else ""), size="sm", elem_classes=["example-btn"])
                        b.click(fn=lambda e=ex: e, outputs=msg_input)

            with gr.Column(scale=1):
                gr.HTML("""
                <div class="sidebar-box">
                    <div style='color:#a5b4fc;font-weight:700;font-size:14px;margin-bottom:12px;'>🧠 What I can do</div>
                    <div style='color:#94a3b8;font-size:13px;line-height:2;'>
                        ✅ Explain any programming concept<br>
                        ✅ Write &amp; run Python code<br>
                        ✅ Debug your errors<br>
                        ✅ Generate code templates<br>
                        ✅ Teach ML &amp; AI concepts<br>
                        ✅ Do math calculations<br>
                        ✅ Review &amp; improve code<br>
                        ✅ Suggest project ideas
                    </div>
                    <hr style='border-color:rgba(99,102,241,0.2);margin:16px 0;'>
                    <div style='color:#a5b4fc;font-weight:700;font-size:14px;margin-bottom:8px;'>📊 Observability</div>
                    <div style='color:#94a3b8;font-size:13px;line-height:2;'>
                        Every conversation is traced<br>
                        in Langfuse — view latency,<br>
                        token usage &amp; tool calls<br>
                        in the dashboard.
                    </div>
                    <hr style='border-color:rgba(99,102,241,0.2);margin:16px 0;'>
                    <div style='color:#a5b4fc;font-weight:700;font-size:14px;margin-bottom:8px;'>💬 Tips</div>
                    <div style='color:#94a3b8;font-size:13px;line-height:2;'>
                        • Tell me your experience level<br>
                        • Paste code to get help<br>
                        • Ask "why" not just "how"
                    </div>
                    <hr style='border-color:rgba(99,102,241,0.2);margin:16px 0;'>
                    <div style='color:#64748b;font-size:12px;text-align:center;'>
                        Powered by <strong style='color:#a5b4fc;'>qwen2:7b</strong><br>
                        Running locally via Ollama
                    </div>
                </div>
                """)

        # ── Event wiring ──
        msg_input.submit(
            fn=handle_send,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input],
        ).then(fn=bot_respond, inputs=chatbot, outputs=chatbot)

        send_btn.click(
            fn=handle_send,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input],
        ).then(fn=bot_respond, inputs=chatbot, outputs=chatbot)

        clear_btn.click(fn=clear_chat, outputs=[chatbot, msg_input])

    return demo