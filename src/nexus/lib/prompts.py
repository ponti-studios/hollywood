"""Prompt management utilities."""

import os
import shutil
from pathlib import Path

from nexus.config import ROOT_DIR

# User config directory for prompts
USER_PROMPTS_DIR = Path.home() / ".config" / "nexus" / "prompts"

# Bundled prompts directory
BUNDLED_PROMPTS_DIR = Path(__file__).parent / "prompts"


def get_prompt(prompt_name: str) -> str:
    """Get a prompt by name, checking user prompts first, then falling back to bundled.

    On first run, copies bundled prompts to user's config directory.
    """
    # Ensure user config directory exists
    USER_PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

    # Check if user has this prompt
    user_prompt_path = USER_PROMPTS_DIR / f"{prompt_name}.md"
    bundled_prompt_path = BUNDLED_PROMPTS_DIR / f"{prompt_name}.md"

    # First run: copy bundled prompts to user directory
    if not USER_PROMPTS_DIR.exists() or not any(USER_PROMPTS_DIR.glob("*.md")):
        _copy_default_prompts()

    # Check user prompts first
    if user_prompt_path.exists():
        with open(user_prompt_path, "r") as f:
            return f.read()

    # Fall back to bundled prompts
    if bundled_prompt_path.exists():
        with open(bundled_prompt_path, "r") as f:
            return f.read()

    raise FileNotFoundError(f"Prompt '{prompt_name}' not found in user or bundled prompts")


def _copy_default_prompts() -> None:
    """Copy bundled prompts to user config directory on first run."""
    USER_PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

    if BUNDLED_PROMPTS_DIR.exists():
        for prompt_file in BUNDLED_PROMPTS_DIR.glob("*.md"):
            user_path = USER_PROMPTS_DIR / prompt_file.name
            if not user_path.exists():
                shutil.copy2(prompt_file, user_path)


def list_user_prompts() -> list[str]:
    """List all user prompts."""
    if not USER_PROMPTS_DIR.exists():
        return []
    return [p.stem for p in USER_PROMPTS_DIR.glob("*.md")]


def list_bundled_prompts() -> list[str]:
    """List all bundled prompts."""
    if not BUNDLED_PROMPTS_DIR.exists():
        return []
    return [p.stem for p in BUNDLED_PROMPTS_DIR.glob("*.md")]
