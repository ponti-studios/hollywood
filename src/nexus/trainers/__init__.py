"""Training workflows for Nexus.

Import concrete trainers directly from their modules, e.g.
`from nexus.trainers.dpo import run_dpo`.

This package intentionally avoids eager imports so missing optional trainer
features do not break unrelated commands during package import.
"""
