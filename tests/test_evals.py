from __future__ import annotations

from nexus.evaluation.demo import DemoResult, run_demo_evals


class FakeClient:
    def __init__(self, *args, **kwargs):
        self.calls = []
        self.text_model = kwargs.get("text_model") or "gemini-2.5-flash"

    async def reply(self, *, prompt, model=None, temperature=0.0, max_tokens=256):
        self.calls.append(prompt)
        if "email address" in prompt:
            return type("R", (), {"text": "ada@example.com"})()
        if "support, sales, or other" in prompt:
            return type("R", (), {"text": "support"})()
        return type("R", (), {"text": '{"answer": 4, "confidence": 1.0}'})()

    async def aclose(self):
        return None


def test_demo_evals(monkeypatch):
    import asyncio

    monkeypatch.setattr("nexus.evaluation.demo.GeminiClient", FakeClient)
    results = asyncio.run(run_demo_evals(model="gemini-2.5-flash"))
    assert all(isinstance(result, DemoResult) for result in results)
    assert len(results) >= 3
    assert any(result.name == "email_extraction" and result.passed for result in results)
