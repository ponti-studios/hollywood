from typing import Any, Dict

import pandas
from openai.types import CompletionUsage


def calculate_token_costs(
    completion_usage: CompletionUsage | None, input_price: float = 0.0000025, output_price: float = 0.00001
) -> Dict[str, Any]:
    """Calculate the cost of API usage based on token counts and pricing"""

    if not completion_usage:
        return {"input_tokens": 0, "output_tokens": 0, "input_cost": 0, "output_cost": 0, "total_cost": 0}

    prompt_tokens = completion_usage.prompt_tokens
    completion_tokens = completion_usage.completion_tokens

    input_cost = prompt_tokens * input_price
    output_cost = completion_tokens * output_price
    total_cost = input_cost + output_cost

    return {
        "input_tokens": prompt_tokens,
        "output_tokens": completion_tokens,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": total_cost,
    }


def token_costs_to_dataframe(token_costs: Dict[str, Any]) -> pandas.DataFrame:
    """Convert token costs to a pandas DataFrame"""

    return pandas.DataFrame(token_costs, index=[0])
