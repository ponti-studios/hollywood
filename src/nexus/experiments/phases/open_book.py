"""
exp_02_open_book.py — Phase 2: Open-book benchmark with lightweight tool use.

This experiment keeps the existing knowledge-heavy benchmarks but allows the
small model to decide when to call a search tool before answering.
The reference model, when configured, remains a closed-book comparator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import httpx
from rich.console import Console

from nexus.experiments.benchmark_support import format_item, load_benchmark, score_answer
from nexus.experiments.config import BenchmarkSpec, ExperimentConfig, ModelSpec
from nexus.experiments.reference_cache import load_cache_metadata, load_reference_cache, save_reference_cache
from nexus.experiments.runner import BaseRunner
from nexus.experiments.scoring import BenchmarkScore, QuestionResult, aggregate_scores

console = Console()

SEARCH_RE = re.compile(r"\[SEARCH:(.*?)\]", re.IGNORECASE | re.DOTALL)
ANSWER_RE = re.compile(r"\[ANSWER:(.*?)\]", re.IGNORECASE | re.DOTALL)


class WikipediaSearchTool:
    """Very small search tool backed by Wikipedia's public search API."""

    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)

    def search(self, query: str, limit: int = 3) -> str:
        response = self._client.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "format": "json",
                "utf8": 1,
                "srlimit": limit,
                "srsearch": query,
            },
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("query", {}).get("search", [])
        if not rows:
            return "No search results found."

        snippets = []
        for row in rows[:limit]:
            title = row.get("title", "Untitled")
            snippet = re.sub(r"<.*?>", "", row.get("snippet", ""))
            snippets.append(f"Source: {title}\nSnippet: {snippet}")
        return "\n\n".join(snippets)


class OpenBookRunner(BaseRunner):
    def __init__(self, cfg: ExperimentConfig) -> None:
        super().__init__(cfg)
        self._benchmark_questions: dict[str, list[Any]] = {}
        self._benchmark_signatures: dict[str, str] = {}
        self._tool = WikipediaSearchTool()
        self._max_tool_calls = 3

    @property
    def reference_cache_score_version(self) -> str:
        return "phase2_v1"

    def load_models(self) -> None:
        self._prepare_benchmarks()
        for spec in self.cfg.models:
            if self._can_use_cached_reference(spec):
                console.print(
                    f"Using cached reference results for [cyan]{spec.model_id}[/cyan] ({spec.role}); skipping model load."
                )
                continue
            console.print(f"Loading [cyan]{spec.model_id}[/cyan] ({spec.role}) …")
            self._pipelines[spec.model_id] = self._build_pipeline(spec)
        console.print()

    def run(self) -> tuple[dict[str, BenchmarkScore], list[QuestionResult]]:
        scores: dict[str, BenchmarkScore] = {}
        all_results: list[QuestionResult] = []

        for benchmark_spec in self.cfg.benchmarks:
            results_per_benchmark = self._run_benchmark(benchmark_spec)
            all_results.extend(results_per_benchmark)

            for model_spec in self.cfg.models:
                model_results = [r for r in results_per_benchmark if r.model_id == model_spec.model_id]
                if not model_results:
                    continue
                score = aggregate_scores(model_results)
                score.provenance = self.result_provenance(model_spec.model_id, benchmark_spec.name)
                scores[f"{model_spec.role}/{benchmark_spec.name}"] = score

        return scores, all_results

    def _run_benchmark(self, spec: BenchmarkSpec) -> list[QuestionResult]:
        console.rule(f"[cyan]{spec.name}[/cyan]")
        questions = self._benchmark_questions[spec.name]
        console.print(f"  {len(questions)} questions loaded\n")

        results: list[QuestionResult] = []
        for model_spec in self.cfg.models:
            results.extend(self._evaluate_model(model_spec, spec.name, questions))
        return results

    def _prepare_benchmarks(self) -> None:
        if self._benchmark_questions:
            return
        for spec in self.cfg.benchmarks:
            questions = load_benchmark(spec, self.cfg)
            self._benchmark_questions[spec.name] = questions
            self._benchmark_signatures[spec.name] = self._compute_benchmark_signature(spec.name, questions)

    def _compute_benchmark_signature(self, benchmark_name: str, questions: list[Any]) -> str:
        payload: list[dict[str, str]] = []
        for item in questions:
            prompt, expected, question_id = format_item(benchmark_name, item)
            payload.append(
                {
                    "id": question_id,
                    "prompt": prompt,
                    "expected": json.dumps(expected, sort_keys=True),
                }
            )
        digest = hashlib.sha256(
            json.dumps(
                {
                    "score_version": self.reference_cache_score_version,
                    "benchmark": benchmark_name,
                    "questions": payload,
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        return digest[:16]

    def _cache_path(self, model_spec: ModelSpec, benchmark_name: str) -> Path:
        return self.reference_cache_path(
            model_spec.model_id,
            benchmark_name,
            self._benchmark_signatures[benchmark_name],
        )

    def _can_use_cached_reference(self, model_spec: ModelSpec) -> bool:
        if model_spec.role != "large":
            return False
        if not self.cfg.logging.use_reference_cache or self.cfg.logging.refresh_reference_cache:
            return False
        return all(self._cache_path(model_spec, spec.name).exists() for spec in self.cfg.benchmarks)

    def _load_cached_results(self, model_spec: ModelSpec, benchmark_name: str) -> list[QuestionResult] | None:
        if model_spec.role != "large" or not self.cfg.logging.use_reference_cache:
            return None
        if self.cfg.logging.refresh_reference_cache:
            return None

        path = self._cache_path(model_spec, benchmark_name)
        cached_results = load_reference_cache(
            path,
            score_version=self.reference_cache_score_version,
            benchmark_signature=self._benchmark_signatures[benchmark_name],
        )
        if cached_results is None:
            return None

        self.set_result_provenance(model_spec.model_id, benchmark_name, "cached")
        metadata = load_cache_metadata(path) or {}
        self.set_result_metadata(
            model_spec.model_id,
            benchmark_name,
            {"cached_at": metadata.get("created_at"), "cache_path": str(path)},
        )
        console.print(
            f"  [dim]cache hit[/dim] [cyan]{model_spec.model_id.split('/')[-1]}[/cyan] / {benchmark_name}"
        )
        return cached_results

    def _save_cached_results(self, model_spec: ModelSpec, benchmark_name: str, results: list[QuestionResult]) -> None:
        if model_spec.role != "large" or not self.cfg.logging.use_reference_cache:
            return
        path = self._cache_path(model_spec, benchmark_name)
        save_reference_cache(
            path,
            experiment_name=self.cfg.name,
            score_version=self.reference_cache_score_version,
            model_id=model_spec.model_id,
            role=model_spec.role,
            benchmark=benchmark_name,
            benchmark_signature=self._benchmark_signatures[benchmark_name],
            results=results,
        )
        console.print(
            f"  [dim]cached reference[/dim] [cyan]{model_spec.model_id.split('/')[-1]}[/cyan] / {benchmark_name}"
        )

    def _evaluate_model(self, model_spec: ModelSpec, benchmark_name: str, questions: list[Any]) -> list[QuestionResult]:
        cached = self._load_cached_results(model_spec, benchmark_name)
        if cached is not None:
            return cached

        self.set_result_provenance(model_spec.model_id, benchmark_name, "live")
        self.set_result_metadata(model_spec.model_id, benchmark_name, {})

        results: list[QuestionResult] = []
        correct = 0
        with self.progress_bar(len(questions), f"{model_spec.model_id} / {benchmark_name}") as progress:
            task = progress.add_task(
                f"[cyan]{model_spec.model_id.split('/')[-1]}[/cyan] on {benchmark_name}",
                total=len(questions),
            )
            for item in questions:
                question_prompt, expected, question_id = format_item(benchmark_name, item)
                if model_spec.role == "large":
                    predicted = self.generate(model_spec.model_id, question_prompt)
                    tool_calls = 0
                else:
                    predicted, tool_calls = self._agentic_answer(model_spec.model_id, question_prompt)

                is_correct = score_answer(benchmark_name, predicted, expected, item)
                if is_correct:
                    correct += 1
                results.append(
                    QuestionResult(
                        question_id=question_id,
                        question=question_prompt,
                        expected=str(expected),
                        predicted=predicted,
                        correct=is_correct,
                        model_id=model_spec.model_id,
                        benchmark=benchmark_name,
                        tool_calls=tool_calls,
                    )
                )
                progress.advance(task)

        acc = correct / len(questions) * 100 if questions else 0.0
        console.print(
            f"  [bold]{model_spec.model_id.split('/')[-1]}[/bold] → [green]{acc:.1f}%[/green] ({correct}/{len(questions)})\n"
        )
        self._save_cached_results(model_spec, benchmark_name, results)
        return results

    def _agentic_answer(self, model_id: str, task_prompt: str) -> tuple[str, int]:
        transcript: list[tuple[str, str]] = []
        tool_calls = 0

        while tool_calls < self._max_tool_calls:
            prompt = self._build_agent_prompt(task_prompt, transcript)
            raw = self.generate(model_id, prompt).strip()
            answer_match = ANSWER_RE.search(raw)
            if answer_match:
                return answer_match.group(1).strip(), tool_calls

            search_match = SEARCH_RE.search(raw)
            if not search_match:
                return raw, tool_calls

            query = search_match.group(1).strip()
            if not query:
                return raw, tool_calls

            tool_calls += 1
            try:
                tool_result = self._tool.search(query)
            except Exception as exc:
                tool_result = f"Search failed: {exc}"
            transcript.append((query, tool_result))

        final_prompt = self._build_agent_prompt(task_prompt, transcript, must_answer=True)
        raw = self.generate(model_id, final_prompt).strip()
        answer_match = ANSWER_RE.search(raw)
        if answer_match:
            return answer_match.group(1).strip(), tool_calls
        return raw, tool_calls

    def _build_agent_prompt(
        self,
        task_prompt: str,
        transcript: list[tuple[str, str]],
        *,
        must_answer: bool = False,
    ) -> str:
        lines = [
            "You are solving an open-book benchmark question.",
            "You may either request a search or provide the final answer.",
            "Respond using exactly one of these formats:",
            "[SEARCH: concise factual query]",
            "[ANSWER: final answer]",
        ]
        if must_answer:
            lines.append("You have reached the search limit. You must answer now.")
        lines.extend(["", "Task:", task_prompt])
        if transcript:
            lines.append("")
            lines.append("Search transcript:")
            for i, (query, result) in enumerate(transcript, start=1):
                lines.append(f"Search {i}: {query}")
                lines.append(result)
        return "\n".join(lines)


def build_default_config(
    small_model: str,
    large_model: str | None,
    samples: int,
    no_wandb: bool,
) -> ExperimentConfig:
    from nexus.experiments.config import LoggingSpec

    models = [ModelSpec(model_id=small_model, role="small")]
    if large_model:
        models.append(ModelSpec(model_id=large_model, role="large"))

    return ExperimentConfig(
        name="exp_02_open_book",
        description="Phase 2: Open-book benchmark with search tool use",
        phase=2,
        models=models,
        benchmarks=[
            BenchmarkSpec(name="triviaqa", samples=samples),
            BenchmarkSpec(name="mmlu", samples=samples),
        ],
        logging=LoggingSpec(wandb_project=None if no_wandb else "3b-logic-broker"),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 2: open-book benchmark")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--small-model", default="google/gemma-3-4b-it")
    parser.add_argument("--large-model", default=None)
    parser.add_argument("--samples", type=int, default=500)
    parser.add_argument("--no-wandb", action="store_true")
    args = parser.parse_args()

    if args.config:
        cfg = ExperimentConfig.from_yaml(args.config)
    else:
        cfg = build_default_config(
            small_model=args.small_model,
            large_model=args.large_model,
            samples=args.samples,
            no_wandb=args.no_wandb,
        )

    OpenBookRunner(cfg).execute()


if __name__ == "__main__":
    main()
