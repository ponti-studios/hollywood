"""
CLI entry points for the nexus posttraining lab.

Commands:
  nexus api    serve
  nexus train  --recipe configs/recipes/sft_lora.yaml
  nexus eval   --checkpoint .data/checkpoints/my-run
  nexus data   download --name tatsu-lab/alpaca
  nexus serve  --model google/gemma-3-1b-it
"""

import logging

import typer
from rich.console import Console
from rich.logging import RichHandler

# Configure logging to use Rich for beautiful output
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)

# The root Typer app — sub-apps are added below
app = typer.Typer(
    name="nexus",
    help="Gemma 3 posttraining lab for Apple Silicon.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)

# Import and register sub-commands
from nexus.cli.api import api_app                # noqa: E402
from nexus.cli.train import train_app            # noqa: E402
from nexus.cli.eval import eval_app              # noqa: E402
from nexus.cli.data import data_app              # noqa: E402
from nexus.cli.serve import serve_app            # noqa: E402
from nexus.cli.experiment import experiment_app  # noqa: E402

app.add_typer(api_app,        name="api",        help="Start the Nexus API server.         nexus api serve")
app.add_typer(train_app,      name="train",      help="Run a posttraining recipe.         nexus train run --recipe ...")
app.add_typer(eval_app,       name="eval",       help="Evaluate a trained model.           nexus eval perplexity --checkpoint ...")
app.add_typer(data_app,       name="data",       help="Download and inspect datasets.      nexus data list / download / inspect")
app.add_typer(serve_app,      name="serve",      help="Serve a model locally via MLX.      nexus serve chat --model ...")
app.add_typer(experiment_app, name="experiment", help="Run benchmark experiments.          nexus experiment run --phase 1")
