"""
Basic tests — run with: pytest tests/
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent.tools import run_python, calculate, get_datetime, execute_tool


class TestRunPython:
    def test_basic_print(self):
        result = run_python("print('hello')")
        assert "hello" in result

    def test_math_output(self):
        result = run_python("print(2 + 2)")
        assert "4" in result

    def test_blocked_os_system(self):
        result = run_python("os.system('ls')")
        assert "Blocked" in result

    def test_syntax_error(self):
        result = run_python("def broken(:")
        assert "Error" in result

    def test_no_output(self):
        result = run_python("x = 5")
        assert "successfully" in result.lower()


class TestCalculate:
    def test_addition(self):
        result = calculate("2 + 3")
        assert "5" in result

    def test_power(self):
        result = calculate("2 ** 10")
        assert "1024" in result

    def test_sqrt(self):
        result = calculate("sqrt(16)")
        assert "4.0" in result or "4" in result

    def test_division_by_zero(self):
        result = calculate("1 / 0")
        assert "zero" in result.lower()


class TestGetDatetime:
    def test_returns_date_string(self):
        result = get_datetime()
        assert "Date:" in result
        assert "Time:" in result


class TestExecuteTool:
    def test_unknown_tool(self):
        result = execute_tool("nonexistent_tool", {})
        assert "Unknown" in result

    def test_dispatches_correctly(self):
        result = execute_tool("calculate", {"expression": "1 + 1"})
        assert "2" in result
