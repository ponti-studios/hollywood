"""
eval.py — CLI commands for evaluating trained models.

Usage:
  nexus eval perplexity --checkpoint .data/checkpoints/my-run --dataset tatsu-lab/alpaca
  nexus eval judge      --checkpoint .data/checkpoints/my-run --prompts path/to/prompts.txt
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from nexus.api.backends import DEFAULT_API_BASE_URL, ApiBackends
from nexus.api.models import ChatCompletionRequest, ChatMessage
from nexus.runtime import ensure_apple_runtime

eval_app = typer.Typer(no_args_is_help=True)
console = Console()


@eval_app.command("perplexity")
def eval_perplexity(
    checkpoint: Path = typer.Option(
        ...,
        "--checkpoint",
        "-c",
        help="Path to a trained model checkpoint directory.",
        exists=True,
    ),
    dataset: str = typer.Option(
        "tatsu-lab/alpaca",
        "--dataset",
        "-d",
        help="HuggingFace dataset to evaluate on.",
    ),
    max_samples: int = typer.Option(
        200,
        "--max-samples",
        help="Number of examples to evaluate (more = slower but more accurate).",
    ),
    split: str = typer.Option("test", "--split", help="Dataset split to use."),
) -> None:
    """Compute perplexity of a trained model on a dataset.

    Perplexity measures how well the model predicts the evaluation text.
    Lower = better. Compare against the base model to see if training helped.
    """
    ensure_apple_runtime(console)

    from datasets import load_dataset

    from nexus.config import ModelConfig
    from nexus.device import get_device
    from nexus.evaluation.metrics import compute_perplexity, save_metrics
    from nexus.models.loader import load_model, load_tokenizer

    console.print(f"\n[bold]Evaluating:[/bold] {checkpoint}")
    console.print(f"Dataset: {dataset} ({split}, max={max_samples})\n")

    # Load model from checkpoint directory
    model_cfg = ModelConfig(model_id=str(checkpoint))
    tokenizer = load_tokenizer(model_cfg)
    model = load_model(model_cfg)

    # Load evaluation data
    ds = load_dataset(dataset, split=split)
    if max_samples:
        ds = ds.select(range(min(max_samples, len(ds))))  # type: ignore

    # Get text column (different datasets use different column names)
    text_col = "text" if "text" in ds.column_names else ds.column_names[0]
    texts = ds[text_col]  # type: ignore

    device = get_device()
    ppl = compute_perplexity(model, tokenizer, texts, device=device)

    metrics = {"perplexity": ppl, "dataset": dataset, "n_samples": len(texts)}
    save_metrics(metrics, checkpoint)

    console.print(f"\n[bold]Perplexity:[/bold] [green]{ppl:.2f}[/green]")


@eval_app.command("judge")
def eval_judge(
    checkpoint: Path = typer.Option(
        ...,
        "--checkpoint",
        "-c",
        help="Path to a trained model checkpoint directory.",
        exists=True,
    ),
    prompts_file: Path | None = typer.Option(
        None,
        "--prompts",
        help="Text file with one prompt per line. Defaults to built-in test prompts.",
    ),
    judge_model: str = typer.Option(
        "HuggingFaceTB/SmolLM2-135M-Instruct",
        "--judge",
        help="Model served by the Nexus API to use as judge.",
    ),
    num_prompts: int = typer.Option(
        20,
        "--num-prompts",
        help="Number of prompts to evaluate.",
    ),
) -> None:
    """Evaluate response quality using an LLM-as-judge.

    Generates responses from your trained model and scores them using
    the compose-backed Nexus API. No external API keys required.
    """

    import httpx

    from nexus.evaluation.judge import judge_responses, print_judge_summary

    # Load prompts
    if prompts_file and prompts_file.exists():
        prompts = [line.strip() for line in prompts_file.read_text().splitlines() if line.strip()]
    else:
        prompts = DEFAULT_EVAL_PROMPTS

    prompts = prompts[:num_prompts]

    console.print(f"\n[bold]Generating responses:[/bold] {checkpoint}")
    api_base = DEFAULT_API_BASE_URL
    backend = ApiBackends.default()
    examples = []
    with httpx.Client(base_url=api_base, timeout=None) as client:
        for prompt in prompts:
            response = client.post(
                "/v1/chat/completions",
                json=ChatCompletionRequest(
                    model=backend.text_model_id,
                    messages=[ChatMessage(role="user", content=prompt)],
                    max_tokens=256,
                    temperature=0.0,
                ).model_dump(),
            )
            response.raise_for_status()
            body = response.json()
            text = str(body["choices"][0]["message"]["content"])
            examples.append({"prompt": prompt, "response": text})

    # Judge responses
    results = judge_responses(examples, judge_model_id=judge_model)
    print_judge_summary(results)

    # Save results
    import json

    output = checkpoint / "judge_results.json"
    with open(output, "w") as f:
        json.dump(
            [
                {
                    "prompt": r.prompt,
                    "response": r.response,
                    "score": r.score,
                    "reasoning": r.reasoning,
                }
                for r in results
            ],
            f,
            indent=2,
        )
    console.print(f"\nResults saved to {output}")


# A small set of test prompts for quick evaluation
DEFAULT_EVAL_PROMPTS = [
    "Explain what a neural network is in simple terms.",
    "Write a Python function that reverses a string.",
    "What are the pros and cons of remote work?",
    "Summarise the water cycle in three sentences.",
    "How do I make a good cup of coffee?",
    "What is the difference between supervised and unsupervised learning?",
    "Write a haiku about machine learning.",
    "Explain gradient descent like I'm 10 years old.",
    "What are three tips for better sleep?",
    "Write a function to check if a number is prime.",
]
