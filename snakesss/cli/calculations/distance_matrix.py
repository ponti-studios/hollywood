from enum import Enum
import numpy as np
from scipy.spatial import distance_matrix
import typer
import pandas as pd
import json
from pathlib import Path
from typing import List, Tuple

app = typer.Typer(name="distance-matrix")


def parse_coordinates(coord_str: str) -> Tuple[float, float]:
    """Parse coordinate string in format 'x,y'"""
    x, y = map(float, coord_str.split(","))
    return (x, y)


def calculate_distance_matrix(coordinates: np.ndarray, metric: str = "euclidean") -> np.ndarray:
    """Calculate distance matrix using specified metric"""
    p_value = {"manhattan": 1, "euclidean": 2, "chebyshev": np.inf}.get(metric, 2)

    return distance_matrix(coordinates, coordinates, p=p_value)


class OutputFormat(str, Enum):
    text = "text"
    csv = "csv"
    json = "json"


@app.command()
def calculate(
    coordinates: List[str] = typer.Argument(
        None, help="List of coordinates in format 'x,y'. Example: 0,0 1,1 2,1"
    ),
    input_file: Path = typer.Option(
        None, "--file", "-f", help="Input file containing coordinates (one pair per line: x,y)"
    ),
    metric: str = typer.Option(
        "euclidean", "--metric", "-m", help="Distance metric: manhattan, euclidean, or chebyshev"
    ),
    output_format: OutputFormat = typer.Option(
        "text", "--output", "-o", help="Output format (text, csv, or json)"
    ),
):
    """Calculate distances between coordinates using various metrics"""
    if not coordinates and not input_file:
        typer.echo("Please provide coordinates or an input file", err=True)
        raise typer.Exit(1)

    # Get coordinates from file or arguments
    if input_file:
        try:
            with open(input_file) as f:
                coordinates = [line.strip() for line in f if line.strip()]
        except Exception as e:
            typer.echo(f"Error reading file: {e}", err=True)
            raise typer.Exit(1)

    try:
        # Convert coordinates to numpy array
        coord_array = np.array([parse_coordinates(c) for c in coordinates])

        # Calculate distance matrix
        result = calculate_distance_matrix(coord_array, metric)

        # Format output
        if output_format == "text":
            typer.echo(f"\nDistance Matrix ({metric} distance):")
            typer.echo(result)
        elif output_format == "csv":
            df = pd.DataFrame(result)
            typer.echo(df.to_csv(index=False))
        else:  # json
            typer.echo(json.dumps({"metric": metric, "matrix": result.tolist()}, indent=2))

    except Exception as e:
        typer.echo(f"Error calculating distances: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
