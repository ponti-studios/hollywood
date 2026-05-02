import sys
from pathlib import Path

DEFAULT_INFERENCE_MODEL = "mlx-community/gemma-4-e2b-bf16"


def pytest_addoption(parser):
    parser.addoption("--model", default=DEFAULT_INFERENCE_MODEL, help="MLX model to test")
    parser.addoption(
        "--run-inference",
        action="store_true",
        default=False,
        help="Run tests marked inference; may download/load local model weights",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-inference"):
        return

    import pytest

    skip_inference = pytest.mark.skip(reason="requires --run-inference")
    for item in items:
        if "inference" in item.keywords:
            item.add_marker(skip_inference)


def pytest_configure(config):
    project_root = Path(config.rootdir)
    sys.path.insert(0, str(project_root))
