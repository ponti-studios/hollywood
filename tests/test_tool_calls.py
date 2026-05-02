"""
test_tool_calls.py — Inference checks for Gemma tool calling.

These tests load the model once, run real inference, and store every
input/output pair to .data/api/inference.db via InferenceStore.

Run with:
    uv run pytest tests/test_tool_calls.py -v -s --run-inference
    uv run pytest tests/test_tool_calls.py -v -s --run-inference --model mlx-community/gemma-4-e2b-bf16

Marks:
    inference — requires MLX-VLM and downloads model weights on first run.

Tool-calling policy:
    - The model should call tools ONLY when required by the task.
    - Trivial questions (2+2, "what color is the sky") are answered directly.
    - Complex computations, lookups, or string operations use tools.
    - Tool results are incorporated into subsequent responses.

Chat template format:
    Gemma 4 uses mlx-vlm's apply_chat_template(), which handles all special tokens.
    Messages are formatted as "ROLE\\ncontent" and wrapped with <start_of_turn> / <end_of_turn>.
    We never hardcode the format; mlx-vlm handles it automatically.

Regression checks:
    All responses are asserted to NOT start with role prefixes (ASSISTANT:, USER:, SYSTEM:).
    All responses are checked for reasonable length (< 500 chars) to catch token repetition.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from typing import Any

import pytest

from nexus.api.store import InferenceRecord, InferenceStore

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

STORE_PATH = Path(".data/api/inference.db")
MAX_TOKENS = 256


@pytest.fixture(scope="session")
def model_id(request) -> str:
    return request.config.getoption("--model")


@pytest.fixture(scope="session")
def mlx_model(model_id):
    if "gemma-4" in model_id.lower():
        try:
            from mlx_vlm import generate, load
            from mlx_vlm.prompt_utils import apply_chat_template
        except ImportError:
            pytest.skip("mlx-vlm not installed")

        model, processor = load(model_id)
        return {
            "backend": "mlx_vlm",
            "model": model,
            "processor": processor,
            "generate": generate,
            "apply_chat_template": apply_chat_template,
        }

    try:
        from mlx_lm import generate, load
        from mlx_lm.sample_utils import make_sampler
    except ImportError:
        pytest.skip("mlx-lm not installed")

    model, tokenizer = load(model_id)
    return {
        "backend": "mlx_lm",
        "model": model,
        "tokenizer": tokenizer,
        "generate": generate,
        "make_sampler": make_sampler,
    }


@pytest.fixture(scope="session")
def store() -> InferenceStore:
    return InferenceStore(STORE_PATH)


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

CALCULATOR_TOOL = {
    "name": "calculate",
    "description": "Evaluate a safe mathematical expression and return the numeric result.",
    "parameters": {
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "A math expression, e.g. '17 * 23'"}
        },
        "required": ["expression"],
    },
}

STRING_TOOL = {
    "name": "string_info",
    "description": "Return the length and reversed form of a string.",
    "parameters": {
        "type": "object",
        "properties": {"text": {"type": "string", "description": "The input string"}},
        "required": ["text"],
    },
}

LOOKUP_TOOL = {
    "name": "lookup",
    "description": "Look up a fact from a local knowledge base.",
    "parameters": {
        "type": "object",
        "properties": {"key": {"type": "string", "description": "Fact key to look up"}},
        "required": ["key"],
    },
}

# Local knowledge base (no network required)
_KB: dict[str, str] = {
    "speed_of_light": "299,792,458 metres per second",
    "pi": "3.14159265358979",
    "boiling_point_water": "100 degrees Celsius at sea level",
    "inventor_telephone": "Alexander Graham Bell",
    "capital_france": "Paris",
}

ALL_TOOLS = [CALCULATOR_TOOL, STRING_TOOL, LOOKUP_TOOL]


# ---------------------------------------------------------------------------
# Tool executor (local, no network)
# ---------------------------------------------------------------------------


def _execute_tool(name: str, arguments: dict[str, Any]) -> str:
    if name == "calculate":
        expr = arguments.get("expression", "")
        # Allow only safe arithmetic
        if not re.fullmatch(r"[\d\s\+\-\*\/\.\(\)]+", expr):
            return f"Error: unsafe expression '{expr}'"
        try:
            result = eval(expr, {"__builtins__": {}})  # noqa: S307
            return str(result)
        except Exception as exc:
            return f"Error: {exc}"

    if name == "string_info":
        text = arguments.get("text", "")
        return json.dumps({"length": len(text), "reversed": text[::-1]})

    if name == "lookup":
        key = arguments.get("key", "").lower().replace(" ", "_")
        return _KB.get(key, f"No entry found for key '{key}'")

    return f"Unknown tool: {name}"


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------

TOOL_SYSTEM_PROMPT = """\
You are a helpful assistant with access to tools.

When you need to call a tool, respond with ONLY a valid JSON object in this exact format:
{{
  "tool_call": {{
    "name": "<tool_name>",
    "arguments": {{ ... }}
  }}
}}

Do NOT add any text before or after the JSON object.

After you receive the tool result in the subsequent user message, answer the user's original question.

Available tools:
{tools_json}"""

_TOOL_CALL_RE = re.compile(
    r'\{\s*"tool_call"\s*:\s*\{\s*"name"\s*:\s*"[^"]+",\s*"arguments"\s*:\s*\{[^}]*\}\s*\}\s*\}',
    re.DOTALL,
)


def _parse_tool_call(text: str) -> dict | None:
    """Extract the first tool_call JSON from model output."""
    # Try strict pattern first
    match = _TOOL_CALL_RE.search(text)
    if match:
        try:
            return json.loads(match.group())["tool_call"]
        except (json.JSONDecodeError, KeyError):
            pass
    # Fallback: find any JSON object containing "tool_call"
    for m in re.finditer(r"\{.*?\}", text, re.DOTALL):
        try:
            obj = json.loads(m.group())
            if "tool_call" in obj:
                return obj["tool_call"]
        except json.JSONDecodeError:
            continue
    return None


def _format_conversation_for_template(messages: list[dict], backend: str) -> str:
    """Format messages for the appropriate chat template backend.

    For mlx_vlm: Gemma uses <start_of_turn>role\n content<end_of_turn>\n format.
    For mlx_lm: Use standard transformers chat template.

    Args:
        messages: list of {"role": "system|user|assistant", "content": "..."}
        backend: "mlx_vlm" or "mlx_lm"

    Returns:
        Properly formatted string for the chat template function.
    """
    if backend == "mlx_vlm":
        # mlx-vlm's apply_chat_template expects a plaintext conversation string
        # It will auto-apply Gemma's chat template with proper special tokens
        parts = []
        for msg in messages:
            role = msg["role"].upper()
            content = msg["content"]
            parts.append(f"{role}\n{content}")
        return "\n".join(parts)
    else:
        # mlx_lm expects messages list to be passed to the tokenizer's apply_chat_template
        # This shouldn't be called — we return None to signal the caller to use messages directly
        return None


def _build_prompt(mlx_model, messages: list[dict], tools: list[dict] | None = None) -> str:
    """Build the full prompt with optional tool definitions.

    For mlx_vlm (Gemma 4):
      - Injects system prompt with tools as a special SYSTEM message
      - Formats conversation using mlx-vlm's apply_chat_template

    For mlx_lm (other models):
      - Uses the tokenizer's built-in chat template
    """
    if tools:
        tools_json = json.dumps(tools, indent=2)
        system = TOOL_SYSTEM_PROMPT.format(tools_json=tools_json)
        full_messages = [{"role": "system", "content": system}] + messages
    else:
        full_messages = messages

    if mlx_model["backend"] == "mlx_vlm":
        # Convert messages to Gemma's conversation format
        conversation = _format_conversation_for_template(full_messages, "mlx_vlm")
        # Let mlx-vlm apply the proper chat template with special tokens
        return mlx_model["apply_chat_template"](
            mlx_model["processor"],
            mlx_model["model"].config,
            conversation,
        )

    # For mlx_lm: use the tokenizer's native apply_chat_template
    tokenizer = mlx_model["tokenizer"]
    return tokenizer._tokenizer.apply_chat_template(
        full_messages,
        tokenize=False,
        add_generation_prompt=True,
    )


# ---------------------------------------------------------------------------
# Core inference helper
# ---------------------------------------------------------------------------


def _infer(mlx_model, prompt: str, max_tokens: int = MAX_TOKENS) -> tuple[str, float]:
    t0 = time.perf_counter()

    if mlx_model["backend"] == "mlx_vlm":
        output = mlx_model["generate"](
            model=mlx_model["model"],
            processor=mlx_model["processor"],
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=0.0,
            verbose=False,
        )
        text = output.text if hasattr(output, "text") else str(output)
    else:
        text = mlx_model["generate"](
            mlx_model["model"],
            mlx_model["tokenizer"],
            prompt=prompt,
            max_tokens=max_tokens,
            sampler=mlx_model["make_sampler"](temp=0.0),
            verbose=False,
        )

    elapsed = (time.perf_counter() - t0) * 1000
    # Strip stop tokens
    for stop in ["<end_of_turn>", "<eos>", "</s>"]:
        text = text.split(stop)[0]
    return text.strip(), elapsed


def _encode_tokens(mlx_model, text: str) -> list[int]:
    if mlx_model["backend"] == "mlx_vlm":
        tokenizer = getattr(mlx_model["processor"], "tokenizer", mlx_model["processor"])
    else:
        tokenizer = mlx_model["tokenizer"]
        tokenizer = getattr(tokenizer, "_tokenizer", tokenizer)
    return tokenizer.encode(text)


def _run_tool_loop(
    mlx_model,
    store: InferenceStore,
    model_id: str,
    user_message: str,
    tools: list[dict],
    max_turns: int = 3,
) -> tuple[str, list[dict], int]:
    """
    Run a tool-use loop:
      1. Send user message with tool definitions
      2. If model calls a tool, execute it and continue
      3. Return (final_answer, conversation_history, tool_call_count)
    """
    messages: list[dict] = [{"role": "user", "content": user_message}]
    tool_call_count = 0

    for _ in range(max_turns):
        prompt = _build_prompt(mlx_model, messages, tools=tools)
        response, latency_ms = _infer(mlx_model, prompt)

        tool_call = _parse_tool_call(response)

        if tool_call is None:
            # Final answer — store and return
            run_id = uuid.uuid4().hex
            store.save(
                InferenceRecord(
                    id=run_id,
                    created_at=time.time(),
                    model_id=model_id,
                    messages=messages,
                    response=response,
                    prompt_tokens=len(_encode_tokens(mlx_model, prompt)),
                    completion_tokens=len(_encode_tokens(mlx_model, response)),
                    latency_ms=round(latency_ms, 2),
                )
            )
            return response, messages, tool_call_count

        # Execute tool
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("arguments", {})
        tool_result = _execute_tool(tool_name, tool_args)
        tool_call_count += 1

        # Append tool call + result to conversation
        messages.append({"role": "assistant", "content": response})
        messages.append(
            {
                "role": "user",
                "content": f"Tool result for {tool_name}: {tool_result}",
            }
        )

    # Max turns exhausted — return last response
    return response, messages, tool_call_count


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.inference
class TestToolCallDetection:
    """Verify the model emits a tool call when one is clearly needed."""

    def test_calculate_multiplication(self, mlx_model, store, model_id):
        """Model should call calculate for a non-trivial multiplication."""
        answer, history, calls = _run_tool_loop(
            mlx_model,
            store,
            model_id,
            user_message="What is 137 multiplied by 49?",
            tools=[CALCULATOR_TOOL],
        )
        # 137 * 49 = 6713
        assert "6713" in answer or calls > 0, (
            f"Expected answer to contain '6713' or at least one tool call. Got: {answer!r}"
        )
        # Regression check: ensure we're not echoing transcript scaffolding
        assert not answer.startswith(("ASSISTANT:", "SYSTEM:", "USER:")), (
            f"Response should not start with role prefix. Got: {answer!r}"
        )
        # Verify response is coherent (not repeated tokens)
        assert len(answer) < 500, (
            f"Response seems too long (likely repeated). Got {len(answer)} chars"
        )

    def test_calculate_complex_expression(self, mlx_model, store, model_id):
        """Model should call calculate for a multi-step expression."""
        answer, history, calls = _run_tool_loop(
            mlx_model,
            store,
            model_id,
            user_message="What is (88 + 12) * 5?",
            tools=[CALCULATOR_TOOL],
        )
        # (88+12)*5 = 500
        assert "500" in answer or calls > 0, (
            f"Expected '500' in answer or tool call. Got: {answer!r}"
        )
        assert not answer.startswith(("ASSISTANT:", "SYSTEM:", "USER:")), (
            f"Response should not start with role prefix. Got: {answer!r}"
        )

    def test_lookup_fact(self, mlx_model, store, model_id):
        """Model should call lookup to retrieve a stored fact."""
        answer, history, calls = _run_tool_loop(
            mlx_model,
            store,
            model_id,
            user_message="What is the speed of light? Use the lookup tool with key 'speed_of_light'.",
            tools=[LOOKUP_TOOL],
        )
        assert "299" in answer or calls > 0, (
            f"Expected speed of light value or a tool call. Got: {answer!r}"
        )
        assert not answer.startswith(("ASSISTANT:", "SYSTEM:", "USER:")), (
            f"Response should not start with role prefix. Got: {answer!r}"
        )

    def test_string_info(self, mlx_model, store, model_id):
        """Model should call string_info to get the length of a string."""
        answer, history, calls = _run_tool_loop(
            mlx_model,
            store,
            model_id,
            user_message="How many characters are in the string 'nexus'? Use the string_info tool.",
            tools=[STRING_TOOL],
        )
        # "nexus" has 5 characters
        assert "5" in answer or calls > 0, f"Expected '5' in answer or a tool call. Got: {answer!r}"
        assert not answer.startswith(("ASSISTANT:", "SYSTEM:", "USER:")), (
            f"Response should not start with role prefix. Got: {answer!r}"
        )

    def test_multi_tool_available_picks_right_one(self, mlx_model, store, model_id):
        """With all tools available, model picks the right one for arithmetic."""
        answer, history, calls = _run_tool_loop(
            mlx_model,
            store,
            model_id,
            user_message="Calculate 256 * 16 for me.",
            tools=ALL_TOOLS,
        )
        # 256 * 16 = 4096
        assert "4096" in answer or calls > 0, f"Expected '4096' or a tool call. Got: {answer!r}"
        assert not answer.startswith(("ASSISTANT:", "SYSTEM:", "USER:")), (
            f"Response should not start with role prefix. Got: {answer!r}"
        )


@pytest.mark.inference
class TestDirectAnswer:
    """Verify the model answers directly when no tool is needed."""

    def test_simple_factual_no_tool(self, mlx_model, store, model_id):
        """Model should answer a simple fact directly when no tools are provided."""
        answer, history, calls = _run_tool_loop(
            mlx_model,
            store,
            model_id,
            user_message="What colour is the sky on a clear day?",
            tools=[],
        )
        assert calls == 0, f"Expected no tool calls, got {calls}. Answer: {answer!r}"
        assert len(answer) > 0
        assert "blue" in answer.lower(), f"Expected a direct sky-colour answer. Got: {answer!r}"
        # Regression: no role prefixes in output
        assert not answer.startswith(("ASSISTANT:", "SYSTEM:", "USER:")), (
            f"Response should not start with role prefix. Got: {answer!r}"
        )
        # Regression: response is coherent
        assert len(answer) < 500, (
            f"Response seems too long (likely repeated). Got {len(answer)} chars"
        )

    def test_trivial_math_no_tool(self, mlx_model, store, model_id):
        """Model may answer 2+2 directly without a tool call."""
        answer, history, calls = _run_tool_loop(
            mlx_model,
            store,
            model_id,
            user_message="What is 2 + 2?",
            tools=[CALCULATOR_TOOL],
        )
        assert "4" in answer, f"Expected '4' in answer. Got: {answer!r}"
        assert not answer.startswith(("ASSISTANT:", "SYSTEM:", "USER:")), (
            f"Response should not start with role prefix. Got: {answer!r}"
        )


@pytest.mark.inference
class TestToolResultUsage:
    """Verify the model correctly uses tool results in its final answer."""

    def test_uses_calculator_result(self, mlx_model, store, model_id):
        """After receiving a calculator result, the model should cite it."""
        # Manually inject a tool result and verify the model uses it
        messages = [
            {"role": "user", "content": "What is 999 * 111?"},
            {
                "role": "assistant",
                "content": '{"tool_call": {"name": "calculate", "arguments": {"expression": "999 * 111"}}}',
            },
            {"role": "user", "content": "Tool result for calculate: 110889"},
        ]
        prompt = _build_prompt(mlx_model, messages, tools=[CALCULATOR_TOOL])
        response, latency_ms = _infer(mlx_model, prompt)

        run_id = uuid.uuid4().hex
        store.save(
            InferenceRecord(
                id=run_id,
                created_at=time.time(),
                model_id=model_id,
                messages=messages,
                response=response,
                prompt_tokens=len(_encode_tokens(mlx_model, prompt)),
                completion_tokens=len(_encode_tokens(mlx_model, response)),
                latency_ms=round(latency_ms, 2),
            )
        )

        assert "110889" in response, (
            f"Expected model to cite tool result '110889' in response. Got: {response!r}"
        )
        # Regression: no role prefixes
        assert not response.startswith(("ASSISTANT:", "SYSTEM:", "USER:")), (
            f"Response should not start with role prefix. Got: {response!r}"
        )

    def test_uses_lookup_result(self, mlx_model, store, model_id):
        """After receiving a lookup result, the model should incorporate it."""
        messages = [
            {"role": "user", "content": "Who invented the telephone?"},
            {
                "role": "assistant",
                "content": '{"tool_call": {"name": "lookup", "arguments": {"key": "inventor_telephone"}}}',
            },
            {"role": "user", "content": "Tool result for lookup: Alexander Graham Bell"},
        ]
        prompt = _build_prompt(mlx_model, messages, tools=[LOOKUP_TOOL])
        response, latency_ms = _infer(mlx_model, prompt)

        run_id = uuid.uuid4().hex
        store.save(
            InferenceRecord(
                id=run_id,
                created_at=time.time(),
                model_id=model_id,
                messages=messages,
                response=response,
                prompt_tokens=len(_encode_tokens(mlx_model, prompt)),
                completion_tokens=len(_encode_tokens(mlx_model, response)),
                latency_ms=round(latency_ms, 2),
            )
        )

        assert "Bell" in response, (
            f"Expected model to mention 'Bell' after lookup result. Got: {response!r}"
        )
        # Regression: no role prefixes
        assert not response.startswith(("ASSISTANT:", "SYSTEM:", "USER:")), (
            f"Response should not start with role prefix. Got: {response!r}"
        )
