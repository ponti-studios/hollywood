# Inference Test Runner

Comprehensive bash script to run all Gemma 4 tool-calling inference tests with automatic logging to the inference database.

## Quick Start

### Run all 9 tests
```bash
just test-inference
```

### Run single quick test (smoke test)
```bash
just test-inference-quick
```

### Run with verbose output
```bash
just test-inference-verbose
```

### Run with custom model
```bash
just test-inference-model mlx-community/gemma-4-e2b-bf16
```

### Analyze results
```bash
just analyze-inference
just analyze-inference .data/api/inference.db 100
```

### Run directly with script
```bash
./scripts/run_inference_tests.sh
./scripts/run_inference_tests.sh --quick
./scripts/run_inference_tests.sh --verbose
```

## Features

✅ **Automated Prerequisites Check**
- Validates Python 3 installation
- Checks uv package manager
- Installs MLX stack if needed
- Downloads and caches Gemma 4 model (~10 GB first run)
- Validates test file syntax

✅ **Test Execution**
- Runs all 9 inference tests
- Each test logs to `.data/api/inference.db`
- Full pytest integration
- Supports verbose and quick modes

✅ **Result Analysis**
- Automatic analysis of test results
- Summary statistics per model
- Issue detection (role prefixes, long responses)
- Tool call vs direct answer tracking

✅ **Report Generation**
- Timestamped reports saved to `.data/reports/`
- Database query results included
- Easy to track test history

✅ **Colored Output**
- Clear visual feedback
- Section headers for readability
- Error highlighting
- Success confirmations

## Usage

### Basic Usage
```bash
./scripts/run_inference_tests.sh
```

### With Options
```bash
# Specify model
./scripts/run_inference_tests.sh --model mlx-community/gemma-4-e2b-bf16

# Custom database path
./scripts/run_inference_tests.sh --db /custom/path/inference.db

# Verbose pytest output
./scripts/run_inference_tests.sh --verbose

# Quick smoke test only
./scripts/run_inference_tests.sh --quick

# Show help
./scripts/run_inference_tests.sh --help
```

### Environment Variables
```bash
# Override model ID
export MODEL_ID=mlx-community/gemma-4-e2b-bf16
./scripts/run_inference_tests.sh

# Override database path
export INFERENCE_DB=.data/api/inference.db
./scripts/run_inference_tests.sh

# Enable verbose mode
export VERBOSE=true
./scripts/run_inference_tests.sh
```

## Output Structure

### Database Logging
```
.data/api/inference.db
├── inference_runs table
│   ├── id (unique run identifier)
│   ├── created_at (timestamp)
│   ├── model_id (model used)
│   ├── messages (conversation history)
│   ├── response (model output)
│   ├── prompt_tokens (token count)
│   ├── completion_tokens (token count)
│   └── latency_ms (inference time)
```

### Reports
```
.data/reports/
├── inference_report_1234567890.txt  (latest)
├── inference_report_1234567891.txt
└── ...
```

Each report includes:
- Timestamp
- Model ID
- Database path
- Test results summary
- Issue counts
- Latency statistics

### Console Output
```
[INFO] Checking Python environment...
[✓] Python 3.12.5 found
[INFO] Checking uv package manager...
[✓] uv is installed
...
════════════════════════════════════════════════════════════════
RUNNING ALL INFERENCE TESTS
════════════════════════════════════════════════════════════════

[INFO] Model: mlx-community/gemma-4-e2b-bf16
[INFO] Database: .data/api/inference.db
[INFO] Verbose: false

tests/test_tool_calls.py::TestToolCallDetection::test_calculate_multiplication PASSED
...
════════════════════════════════════════════════════════════════
TEST RESULTS ANALYSIS
════════════════════════════════════════════════════════════════

[mlx-community/gemma-4-e2b-bf16]
  Runs: 9
  Tool calls: 5 | Direct answers: 2
  Latency: 1245ms avg (min: 890, max: 1856)
  ✓ No issues detected
```

## Test Coverage

The script runs 9 tests across 3 categories:

### TestToolCallDetection (5 tests)
- `test_calculate_multiplication` — 137 × 49 should call calculator
- `test_calculate_complex_expression` — (88+12)×5 should call calculator
- `test_lookup_fact` — speed_of_light should call lookup
- `test_string_info` — string length should call string_info
- `test_multi_tool_available_picks_right_one` — 256×16 should pick calculator

### TestDirectAnswer (2 tests)
- `test_simple_factual_no_tool` — Sky color should answer directly
- `test_trivial_math_no_tool` — 2+2 should answer directly

### TestToolResultUsage (2 tests)
- `test_uses_calculator_result` — Should cite tool result
- `test_uses_lookup_result` — Should mention tool result

## Database Inspection

After tests complete, query the database:

```bash
# Analyze latest results
python scripts/analyze_inference_runs.py

# Filter by model
python scripts/analyze_inference_runs.py --model mlx-community/gemma-4-e2b-bf16

# Increase limit
python scripts/analyze_inference_runs.py --limit 200

# Combined
python scripts/analyze_inference_runs.py \
  --db .data/api/inference.db \
  --model mlx-community/gemma-4-e2b-bf16 \
  --limit 100
```

## Troubleshooting

### Issue: Permission Denied
```bash
chmod +x scripts/run_inference_tests.sh
```

### Issue: Python Not Found
```bash
# Install Python 3.12+
# macOS:
brew install python@3.12

# Then run:
./scripts/run_inference_tests.sh
```

### Issue: uv Not Found
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Issue: mlx-vlm Installation Failed
```bash
# Install manually first
python3 -m pip install mlx mlx-vlm

# Then run script
./scripts/run_inference_tests.sh
```

### Issue: Model Download Timeout
```bash
# Download manually first
python3 -c "from mlx_vlm import load; load('mlx-community/gemma-4-e2b-bf16')"

# Then run tests
./scripts/run_inference_tests.sh
```

### Issue: Tests Pass But Database Empty
```bash
# Check if pytest actually ran
ls -la .data/api/inference.db

# Verify with:
python scripts/analyze_inference_runs.py --db .data/api/inference.db
```

### Issue: Script Fails Early
```bash
# Run with verbose output
./scripts/run_inference_tests.sh --verbose

# Or check logs directly
cat .data/reports/inference_report_*.txt | tail -50
```

## Performance Notes

### Typical Timing
- Prerequisites check: 30-60 seconds
- Model download (first run): 5-10 minutes
- Quick test (1 test): 1-2 minutes
- Full suite (9 tests): 15-25 minutes
- Result analysis: 5-10 seconds

### Resource Requirements
- Disk space: ~15 GB (for model)
- Memory: 12-16 GB (for Gemma 4 on Apple Silicon)
- Network: ~10 GB download on first run

### Optimization Tips
- Run with `--quick` first to validate setup
- Use `--model` to test different model variants
- Runs are cached; second run skips model download
- Verbose mode shows real-time inference output

## Integration with CI/CD

### GitHub Actions Example
```yaml
- name: Run Gemma 4 Inference Tests
  run: |
    make setup-mlx
    make test-inference
```

### Pre-commit Hook
```bash
#!/bin/bash
# .git/hooks/pre-push
make test-inference-quick || exit 1
```

## Advanced Usage

### Custom Model
```bash
./scripts/run_inference_tests.sh \
  --model mlx-community/gemma-4-e2b-bf16 \
  --db .data/custom/db.sqlite
```

### Batch Multiple Models
```bash
for model in mlx-community/gemma-4-e2b-bf16; do
  echo "Testing $model..."
  ./scripts/run_inference_tests.sh --model "$model"
  sleep 5
done
```

### Parse Reports Programmatically
```python
import sqlite3
from pathlib import Path

db = sqlite3.connect(".data/api/inference.db")
cursor = db.cursor()
cursor.execute("SELECT model_id, COUNT(*), AVG(latency_ms) FROM inference_runs GROUP BY model_id")
for model_id, count, avg_latency in cursor:
    print(f"{model_id}: {count} runs, {avg_latency:.0f}ms avg")
```

## File Structure

```
nexus/
├── scripts/
│   ├── run_inference_tests.sh     (this runner)
│   ├── analyze_inference_runs.py  (result analysis)
│   └── __init__.py
├── tests/
│   ├── test_tool_calls.py         (9 inference tests)
│   └── ...
├── .data/
│   ├── api/
│   │   └── inference.db           (logs)
│   └── reports/
│       ├── inference_report_*.txt (timestamped)
│       └── ...
└── Makefile                       (convenience targets)
```

## See Also

- `QUICKSTART_PHASE1.md` — How to run tests manually
- `PHASE1_COMPLETION.md` — Detailed completion report
- `tests/test_tool_calls.py` — Test source code
- `scripts/analyze_inference_runs.py` — Result analysis tool

## License

Part of the nexus Gemma 4 posttraining lab.
