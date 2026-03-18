"""
Tool Definitions and Executors
Each tool has a schema (for the model to understand) and an executor function.
"""

import math
import datetime
import subprocess
import sys
import io
import contextlib


# ──────────────────────────────────────────────
#  TOOL SCHEMAS  (shown to the model)
# ──────────────────────────────────────────────

TOOLS = [
    {
        "name": "run_python",
        "description": "Execute Python code and return the output. Use for calculations, demonstrations, or testing code snippets.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"}
            },
            "required": ["code"],
        },
    },
    {
        "name": "calculate",
        "description": "Evaluate a safe mathematical expression. Supports +, -, *, /, **, sqrt, sin, cos, log, etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression to evaluate"}
            },
            "required": ["expression"],
        },
    },
    {
        "name": "get_datetime",
        "description": "Get the current date and time.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "explain_concept",
        "description": "Generate a structured explanation of a programming or AI concept with examples.",
        "parameters": {
            "type": "object",
            "properties": {
                "concept": {"type": "string", "description": "The concept to explain"},
                "level": {
                    "type": "string",
                    "description": "beginner | intermediate | advanced",
                },
            },
            "required": ["concept"],
        },
    },
    {
        "name": "generate_code_template",
        "description": "Generate a starter code template for a given programming task or pattern.",
        "parameters": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "What the code should do"},
                "language": {
                    "type": "string",
                    "description": "Programming language (python, javascript, etc.)",
                },
            },
            "required": ["task", "language"],
        },
    },
]


# ──────────────────────────────────────────────
#  TOOL EXECUTORS
# ──────────────────────────────────────────────

def run_python(code: str) -> str:
    """Safely execute Python code and capture output."""
    # Basic safety check — block dangerous imports
    blocked = ["os.system", "subprocess", "shutil.rmtree", "__import__('os')", "eval(", "exec("]
    for b in blocked:
        if b in code:
            return f"⚠️ Blocked: '{b}' is not allowed for safety reasons."

    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    try:
        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
            exec(code, {"__builtins__": __builtins__, "math": math})  # noqa: S102

        output = stdout_capture.getvalue()
        error = stderr_capture.getvalue()

        if error:
            return f"Output:\n{output}\nWarning:\n{error}" if output else f"Error:\n{error}"
        return output if output else "✅ Code executed successfully (no output)."

    except Exception as e:
        return f"❌ Runtime Error: {type(e).__name__}: {str(e)}"


def calculate(expression: str) -> str:
    """Safely evaluate a math expression."""
    # Allow only safe math operations
    allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
    allowed_names["abs"] = abs
    allowed_names["round"] = round

    try:
        # Strip anything non-math
        safe_expr = expression.replace("^", "**")
        result = eval(safe_expr, {"__builtins__": {}}, allowed_names)  # noqa: S307
        return f"{expression} = {result}"
    except ZeroDivisionError:
        return "❌ Division by zero."
    except Exception as e:
        return f"❌ Could not evaluate: {str(e)}"


def get_datetime() -> str:
    """Return current date and time."""
    now = datetime.datetime.now()
    return (
        f"📅 Date: {now.strftime('%A, %B %d, %Y')}\n"
        f"🕐 Time: {now.strftime('%I:%M %p')}\n"
        f"🌍 Timezone: Local System Time"
    )


def explain_concept(concept: str, level: str = "beginner") -> str:
    """Return a structured explanation placeholder — the model will fill this in."""
    return (
        f"Concept: {concept}\n"
        f"Level: {level}\n"
        f"[Use your knowledge to provide a {level}-level explanation with examples, "
        f"analogies, and code snippets where appropriate.]"
    )


def generate_code_template(task: str, language: str = "python") -> str:
    """Return a template prompt — the model will generate the actual code."""
    return (
        f"Task: {task}\n"
        f"Language: {language}\n"
        f"[Generate a clean, well-commented starter template for this task in {language}. "
        f"Include docstrings, type hints if applicable, and usage examples.]"
    )


# ──────────────────────────────────────────────
#  DISPATCHER
# ──────────────────────────────────────────────

TOOL_MAP = {
    "run_python": lambda args: run_python(args.get("code", "")),
    "calculate": lambda args: calculate(args.get("expression", "")),
    "get_datetime": lambda args: get_datetime(),
    "explain_concept": lambda args: explain_concept(
        args.get("concept", ""), args.get("level", "beginner")
    ),
    "generate_code_template": lambda args: generate_code_template(
        args.get("task", ""), args.get("language", "python")
    ),
}


def execute_tool(name: str, args: dict) -> str:
    """Dispatch a tool call by name."""
    if name not in TOOL_MAP:
        return f"❌ Unknown tool: '{name}'. Available: {list(TOOL_MAP.keys())}"
    try:
        return TOOL_MAP[name](args)
    except Exception as e:
        return f"❌ Tool error: {str(e)}"
