"""
Gradio UI — Clean, professional chat interface for CodeMentor AI.
Compatible with Gradio 5.x / 6.x

Key format change from Gradio 4 → 5/6:
  History is no longer a list of [user, bot] pairs.
  It is now a flat list of {"role": ..., "content": ...} dicts,
  exactly matching the OpenAI/Ollama message format.
"""

import gradio as gr
from agent.agent import AIAgent

# One shared agent instance for the whole session
agent = AIAgent()


# ──────────────────────────────────────────────
#  EVENT HANDLER FUNCTIONS
# ──────────────────────────────────────────────

def handle_send(message: str, history: list):
    """
    Called the instant the user hits Send or presses Enter.

    We immediately append TWO new entries to the history:
      - A "user" message containing what they typed
      - An "assistant" message with empty content (a placeholder)

    The empty assistant placeholder is important — it tells Gradio
    that a bot reply is coming, and bot_respond() will fill it in
    progressively as the model streams its response.

    We also return an empty string as the second output so the
    text input box is cleared right away, making the UI feel snappy.
    """
    if not message.strip():
        return history, ""

    history = history + [
        {"role": "user",      "content": message},
        {"role": "assistant", "content": ""},   # placeholder filled by bot_respond
    ]
    return history, ""


def bot_respond(history: list):
    """
    Generator function that streams the agent's reply into the chat.

    Because this function uses 'yield' instead of 'return', it is a
    Python generator. Each time it yields, Gradio re-renders the
    chatbot component with the updated history — this is what creates
    the live 'typing' streaming effect you see on screen.

    We find the last assistant entry (which handle_send created as "")
    and progressively overwrite its "content" field with each new chunk
    that arrives from the model.
    """
    # Safety check: if history is empty or last message isn't the assistant placeholder, do nothing
    if not history or history[-1]["role"] != "assistant":
        yield history
        return

    # The user's message is always the second-to-last entry
    user_message = history[-2]["content"]

    # Stream partial responses from the agent, updating the placeholder in real time
    for partial_response in agent.stream_response(user_message):
        history[-1]["content"] = partial_response  # fill the assistant placeholder progressively
        yield history


def clear_chat():
    """Wipes the visual chat history and resets the agent's internal memory."""
    agent.reset()
    return [], ""


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
    border-radius: 16px;
    padding: 24px 32px;
    margin-bottom: 8px;
    border: 1px solid rgba(99, 102, 241, 0.3);
    box-shadow: 0 0 40px rgba(99, 102, 241, 0.15);
}
.send-btn {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    border: none !important;
    border-radius: 12px !important;
    color: white !important;
    font-weight: 600 !important;
}
.clear-btn {
    background: rgba(239, 68, 68, 0.15) !important;
    border: 1px solid rgba(239, 68, 68, 0.3) !important;
    border-radius: 12px !important;
    color: #fca5a5 !important;
    font-weight: 600 !important;
}
.example-btn {
    background: rgba(99, 102, 241, 0.1) !important;
    border: 1px solid rgba(99, 102, 241, 0.25) !important;
    border-radius: 20px !important;
    color: #a5b4fc !important;
    font-size: 13px !important;
}
.sidebar-box {
    background: #12121f;
    border: 1px solid rgba(99, 102, 241, 0.15);
    border-radius: 16px;
    padding: 16px;
}
"""


# ──────────────────────────────────────────────
#  UI CONSTRUCTION
# ──────────────────────────────────────────────

def build_ui() -> gr.Blocks:
    """
    Builds and returns the Gradio Blocks app.

    gr.Blocks is Gradio's low-level layout system. Think of it like
    building a webpage with div elements — you nest Rows and Columns
    to control how components are arranged, then wire up events
    (clicks, submits) to Python functions.
    """
    with gr.Blocks(title="CodeMentor AI") as demo:

        # ── Header banner (pure HTML — Gradio passes this straight to the browser) ──
        gr.HTML("""
        <div class="header-block">
            <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px;">
                <div>
                    <h1 style="margin:0; font-size:28px; font-weight:800;
                               background: linear-gradient(135deg, #a5b4fc, #c4b5fd);
                               -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                        🤖 CodeMentor AI
                    </h1>
                    <p style="margin:6px 0 0; color:#94a3b8; font-size:15px;">
                        Your local AI tutor for coding, programming &amp; artificial intelligence
                    </p>
                </div>
                <div style="display:flex; flex-direction:column; align-items:flex-end; gap:8px;">
                    <div style="display:inline-flex; align-items:center; gap:6px;
                                background:rgba(16,185,129,0.15); border:1px solid rgba(16,185,129,0.3);
                                border-radius:20px; padding:4px 14px; font-size:13px; color:#6ee7b7;">
                        🟢 qwen2:7b &nbsp;·&nbsp; Local
                    </div>
                    <div style="display:flex; flex-wrap:wrap; gap:6px;">
                        <span style="background:rgba(139,92,246,0.15); border:1px solid rgba(139,92,246,0.3);
                                     border-radius:6px; padding:2px 10px; font-size:12px; color:#c4b5fd;">🐍 run_python</span>
                        <span style="background:rgba(139,92,246,0.15); border:1px solid rgba(139,92,246,0.3);
                                     border-radius:6px; padding:2px 10px; font-size:12px; color:#c4b5fd;">🧮 calculate</span>
                        <span style="background:rgba(139,92,246,0.15); border:1px solid rgba(139,92,246,0.3);
                                     border-radius:6px; padding:2px 10px; font-size:12px; color:#c4b5fd;">💡 explain</span>
                        <span style="background:rgba(139,92,246,0.15); border:1px solid rgba(139,92,246,0.3);
                                     border-radius:6px; padding:2px 10px; font-size:12px; color:#c4b5fd;">📝 templates</span>
                    </div>
                </div>
            </div>
        </div>
        """)

        with gr.Row(equal_height=True):

            # ── Left column: the main chat area ──
            with gr.Column(scale=4):

                # gr.Chatbot renders the conversation.
                # In Gradio 5/6, it defaults to the "messages" format,
                # meaning history must be a list of {"role":..., "content":...} dicts.
                chatbot = gr.Chatbot(
                    label="",
                    height=520,
                    show_label=False,
                    render_markdown=True,   # renders **bold**, `code`, etc. in responses
                    avatar_images=(
                        None,  # user avatar (None = default)
                        "https://api.dicebear.com/7.x/bottts/svg?seed=codebot&backgroundColor=6366f1",
                    ),
                    placeholder=(
                        "<div style='text-align:center; color:#475569; padding:60px 20px;'>"
                        "<div style='font-size:48px; margin-bottom:12px;'>🚀</div>"
                        "<h3 style='color:#64748b; font-weight:600;'>Ask me anything about coding or AI</h3>"
                        "<p style='color:#475569; font-size:14px;'>"
                        "I can run code, explain concepts, generate templates, and more!"
                        "</p></div>"
                    ),
                )

                # Input row: text box and buttons sit side by side (scale controls width ratio)
                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="Ask a coding or AI question... (Press Enter to send)",
                        lines=1,
                        max_lines=5,
                        show_label=False,
                        scale=5,        # takes up 5/7 of the row width
                        container=False,
                    )
                    send_btn  = gr.Button("Send ✈️", scale=1, elem_classes=["send-btn"])
                    clear_btn = gr.Button("🗑️ Clear", scale=1, elem_classes=["clear-btn"])

                # Example prompt buttons — two rows of four
                gr.HTML("<div style='margin-top:12px; color:#64748b; font-size:13px; font-weight:500;'>✨ Try an example:</div>")

                with gr.Row():
                    for ex in EXAMPLES[:4]:
                        ex_btn = gr.Button(
                            ex[:50] + ("…" if len(ex) > 50 else ""),
                            size="sm",
                            elem_classes=["example-btn"],
                        )
                        # The default-argument trick (e=ex) is necessary here.
                        # Without it, all buttons would capture the same loop variable
                        # (the last value of 'ex') due to Python's closure behaviour.
                        ex_btn.click(fn=lambda e=ex: e, outputs=msg_input)

                with gr.Row():
                    for ex in EXAMPLES[4:]:
                        ex_btn = gr.Button(
                            ex[:50] + ("…" if len(ex) > 50 else ""),
                            size="sm",
                            elem_classes=["example-btn"],
                        )
                        ex_btn.click(fn=lambda e=ex: e, outputs=msg_input)

            # ── Right column: info sidebar ──
            with gr.Column(scale=1):
                gr.HTML("""
                <div class="sidebar-box">
                    <div style='color:#a5b4fc; font-weight:700; font-size:14px; margin-bottom:12px;'>
                        🧠 What I can do
                    </div>
                    <div style='color:#94a3b8; font-size:13px; line-height:2;'>
                        ✅ Explain any programming concept<br>
                        ✅ Write &amp; run Python code<br>
                        ✅ Debug your errors<br>
                        ✅ Generate code templates<br>
                        ✅ Teach ML &amp; AI concepts<br>
                        ✅ Do math calculations<br>
                        ✅ Review &amp; improve code<br>
                        ✅ Suggest project ideas
                    </div>
                    <hr style='border-color: rgba(99,102,241,0.2); margin: 16px 0;'>
                    <div style='color:#a5b4fc; font-weight:700; font-size:14px; margin-bottom:8px;'>
                        💬 Tips
                    </div>
                    <div style='color:#94a3b8; font-size:13px; line-height:2;'>
                        • Tell me your experience level<br>
                        • Paste code to get help<br>
                        • Ask "why" not just "how"<br>
                        • Request step-by-step guides
                    </div>
                    <hr style='border-color: rgba(99,102,241,0.2); margin: 16px 0;'>
                    <div style='color:#64748b; font-size:12px; text-align:center;'>
                        Powered by <strong style='color:#a5b4fc;'>qwen2:7b</strong><br>
                        Running locally via Ollama
                    </div>
                </div>
                """)

        # ── Event wiring — this is where the UI becomes interactive ──
        #
        # Each interaction is a two-step chain using .then():
        #
        #   Step 1 — handle_send():
        #     Runs instantly when the user submits.
        #     Appends user message + empty assistant placeholder to history.
        #     Clears the text input box.
        #
        #   Step 2 — bot_respond():
        #     Runs immediately after Step 1.
        #     Streams the model's response into the assistant placeholder.
        #     Because it's a generator (uses yield), Gradio re-renders
        #     the chatbot on every yield, producing the streaming effect.
        #
        # We wire both msg_input.submit (Enter key) and send_btn.click
        # to the same chain so both trigger identical behaviour.

        msg_input.submit(
            fn=handle_send,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input],
        ).then(
            fn=bot_respond,
            inputs=chatbot,
            outputs=chatbot,
        )

        send_btn.click(
            fn=handle_send,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input],
        ).then(
            fn=bot_respond,
            inputs=chatbot,
            outputs=chatbot,
        )

        clear_btn.click(
            fn=clear_chat,
            outputs=[chatbot, msg_input],
        )

    return demo