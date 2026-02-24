"""
The Fibonacci sequence is defined as:
  •	 F(0) = 0
  •	 F(1) = 1
  •	 F(n) = F(n-1) + F(n-2)  for  n > 1

Our goal is to calculate  F(n)  efficiently, where F(n) is the is the number at the nth position of
the Fibonacci sequence.
"""

import typer


app = typer.Typer(name="fibonacci")


# Recursion
def fibonacci_recursion(n: int) -> int:
    if n <= 1:
        return n

    # f(14) + f(13)
    # (f(12) + f(13)) + (f(12) - f(11))
    # (f(11) + f(12)) + (f(11) + f(12)) + (f(11) + f(12)) - (f(10) + f(11))
    # ...
    # This continues to break down until reaching the base cases f(1) and f(0)
    return fibonacci_recursion(n - 1) + fibonacci_recursion(n - 2)


# Memoized
def fibonacci_memo(n: int, memo: dict) -> int:
    if n <= 1:
        return n

    if n in memo.keys():
        return memo[n]

    # To eliminate recalculation
    memo[n] = fibonacci_memo(n - 1, memo) + fibonacci_memo(n - 2, memo)

    return memo[n]


# Dynamic programming
def fibonacci_dynamic(n: int) -> int:
    if n <= 1:
        return n

    # To maintain consistent memory allocation (O(1)), this implementation
    # stores the last two values of the Fibonacci sequence
    prev_value, new_value = 0, 1
    for _ in range(2, n + 1):
        prev_value, new_value = new_value, prev_value + new_value

    return new_value


@app.command("calculate")
def calculate(
    position: int = typer.Argument(..., help="Position in the Fibonacci sequence to calculate"),
    method: str = typer.Option("all", help="Method to use for calculation: recursion, memo, dynamic"),
):
    """Calculate the nth Fibonacci number using various methods"""
    result = 0

    if method == "recursion":
        result = fibonacci_recursion(position)
        typer.echo(f"Recursion: F({position}) = {result}")
        return
    elif method == "memo":
        result = fibonacci_memo(position, {})
        typer.echo(f"Memoized: F({position}) = {result}")
        return
    elif method == "dynamic":
        # Dynamic programming
        result = fibonacci_dynamic(position)

    print(f"Recursion: F({position}) = {result}")


if __name__ == "__main__":
    app()
