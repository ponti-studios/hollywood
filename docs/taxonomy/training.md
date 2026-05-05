# Training

Training is updating model parameters or adapters to create a new model state — SFT, DPO, ORPO, GRPO, LoRA fine-tuning.

Current implementation lives in `src/nexus/trainers/` driven by YAML recipes in `configs/recipes/` via `src/nexus/cli/train.py`. Training does not yet produce durable run or artifact records on the platform ledger.

The package is currently named `trainers` rather than `training` — that is the one naming gap still open in this area.
