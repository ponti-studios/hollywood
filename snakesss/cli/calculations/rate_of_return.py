from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="rate-of-return")


def calculate_nominal_return(initial_value: float, final_value: float, years: int) -> float:
    """
    Calculate the nominal rate of return over a given period using the Compound Annual Growth Rate (CAGR) formula.

    The nominal return represents the average annual return on an investment, without adjusting for inflation or other factors. This is useful to evaluate the investment's performance over time.

    Parameters:
    -----------
    initial_value : float
        The starting value of the investment.

    final_value : float
        The ending value of the investment after the specified number of years.

    years : int
        The number of years over which the investment grows.

    Returns:
    --------
    float
        The nominal annual rate of return (as a decimal, e.g., 0.08 for 8%).

    Formula:
    --------
    Nominal Return = (Final Value / Initial Value) ^ (1 / Years) - 1

    Steps:
    ------
    1. Calculate the total growth factor by dividing the final value by the initial value.
    2. Annualize the growth by taking the nth root of the growth factor, where n is the number of years.
    3. Subtract 1 from the result to convert the growth factor into the nominal rate of return.

    Example:
    --------
    For an investment that grows from $1,000 to $1,500 over 5 years:
    - Total Growth Factor = 1,500 / 1,000 = 1.5
    - Annual Growth Factor = 1.5 ^ (1/5) ≈ 1.08447
    - Nominal Return = 1.08447 - 1 ≈ 0.08447 (or 8.45% annually)
    """
    return (final_value / initial_value) ** (1 / years) - 1


def calculate_real_return(nominal_return: float, inflation_rate: float) -> float:
    """
    Calculate the real rate of return adjusted for inflation using the Fisher equation.

    The real rate of return accounts for the effect of inflation, providing a more accurate measure of the actual growth in purchasing power.

    Parameters:
    ----------
    nominal_return : float
        The nominal rate of return (as a decimal, e.g., 0.05 for 5%).

    inflation_rate : float
        The inflation rate (as a decimal, e.g., 0.02 for 2% inflation).

    Returns:
    -------
    float
        The real rate of return, adjusted for inflation (as a decimal).

    Formula:
    --------
    Real Return = ((1 + Nominal Return) / (1 + Inflation Rate)) - 1

    Steps:
    ------
    1. Add 1 to the nominal return to account for the growth of the investment.
    2. Add 1 to the inflation rate to adjust for the increase in the cost of goods.
    3. Divide the adjusted nominal return by the adjusted inflation rate to factor in inflation's impact.
    4. Subtract 1 from the result to obtain the real rate of return.
    """
    return (1 + nominal_return) / (1 + inflation_rate) - 1


@app.command(name="house-value")
def calculate_house_value(
    initial_value: float = typer.Argument(..., help="The initial value of the house (e.g., 405000)"),
    sale_price: float = typer.Argument(..., help="The yearly increase in house value (e.g., 600000)"),
    years: int = typer.Argument(..., help="Number of years (e.g., 12)"),
    inflation_rate: Annotated[
        float, typer.Argument(help="Average inflation rate (e.g., 0.03 for 3%)")
    ] = 0.03,
):
    """
    A CLI tool to calculate nominal and real rates of return on house value.
    """

    # Calculate nominal return
    nominal_return = calculate_nominal_return(initial_value, sale_price, years)

    # Calculate real return adjusted for inflation
    real_return = calculate_real_return(nominal_return, inflation_rate)

    # Output the results
    console = Console()
    table = Table(title="Rate of Return Results")
    table.add_column("Metric", justify="left", style="bold")
    table.add_column("Value", justify="right")
    table.add_row("Initial Value", f"${initial_value:,.2f}")
    table.add_row(f"Final Value after {years} years", f"${sale_price:,.2f}")
    table.add_row("Nominal Annual Return", f"{nominal_return * 100:.2f}%")
    table.add_row(
        f"Real Annual Return (adjusted for {inflation_rate * 100:.2f}% inflation)",
        f"{real_return * 100:.2f}%",
    )
    console.print(table)


if __name__ == "__main__":
    app()
