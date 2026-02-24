import os
import pandas
import sqlite3
from typer import Typer, Argument, Option


app = Typer(name="csv-to-sqlite")


@app.command(name="csv-to-sqlite")
def csv_to_sqlite(path: str = Argument(..., help="Path to the CSV file")):
    """
    Convert a CSV file to a SQLite database
    """

    """
    The user may provide a path relative to where the script is run
    If the path does not begin with `/`, the path starts with `.`, or does not start with either
    assume it is relative.
    """
    if (
        not path.startswith("/")
        or path.startswith(".")
        or (not path.startswith("/") and not path.startswith("."))
    ):
        path = os.path.join(os.getcwd(), path)

    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    # with open(path, "r") as csv_file:
    #     csv_reader = csv.reader(csv_file)

    # Connect to SQLite database and create table. Drop table if it already exists.
    conn = sqlite3.connect(os.path.join(os.getcwd(), "data.db"))
    # conn.execute("DROP TABLE IF EXISTS data")
    # conn.execute(f"CREATE TABLE data ({', '.join(headers)})")
    # conn.commit()

    df = pandas.read_csv(path)
    df.to_sql("data", conn, index=False, if_exists="replace")
    conn.close()


@app.command(name="import-trips")
def import_trips(
    path: str = Option("/Users/charlesponti/Developer/snakesss/trips.csv", help="Path to the trips CSV file"),
    db_path: str = Option("trips.db", help="Path to the SQLite database file"),
):
    """
    Import trips data from CSV into SQLite database
    """
    # Ensure the file exists
    if not os.path.exists(path):
        raise FileNotFoundError(f"Trips file not found: {path}")

    print(f"Importing trips data from {path}")

    # Connect to SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create trips table with appropriate schema
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS trips (
        id INTEGER PRIMARY KEY,
        start_date TEXT,
        end_date TEXT,
        city TEXT,
        state TEXT,
        country TEXT,
        people TEXT,
        travel_details TEXT,
        price REAL,
        status TEXT,
        number_of_travelers INTEGER
    )
    """
    )

    # Create hotels table for potential future use
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS hotels (
        id INTEGER PRIMARY KEY,
        trip_id INTEGER,
        hotel_name TEXT,
        check_in_date TEXT,
        check_out_date TEXT,
        city TEXT,
        state TEXT,
        country TEXT,
        price REAL,
        status TEXT,
        number_of_travelers INTEGER,
        FOREIGN KEY (trip_id) REFERENCES trips (id)
    )
    """
    )

    # Read the CSV file into a pandas DataFrame
    df = pandas.read_csv(path)

    # Convert date columns to proper format
    df["start_date"] = pandas.to_datetime(df["start_date"]).dt.strftime("%Y-%m-%d")
    df["end_date"] = pandas.to_datetime(df["end_date"]).dt.strftime("%Y-%m-%d")

    # Fix column names - if 'Travel Details' exists, rename to 'travel_details'
    if "Travel Details" in df.columns:
        df = df.rename(columns={"Travel Details": "travel_details"})

    # Import data into the trips table
    df.to_sql("trips", conn, if_exists="replace", index=False)

    # Create a people table if it doesn't exist
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS people (
        id INTEGER PRIMARY KEY,
        trip_id INTEGER,
        first TEXT,
        middle TEXT,
        last TEXT,
        FOREIGN KEY (trip_id) REFERENCES trips (id)
    )
    """
    )

    # Process people data
    people_records = []

    for idx, row in df.iterrows():
        if pandas.isna(row["people"]) or not row["people"]:
            continue

        # Split the people string into individual names
        people_list = row["people"].split(", ")

        for person in people_list:
            if not person:
                continue

            # Parse the name
            parts = person.split()
            if len(parts) == 1:
                first, middle, last = parts[0], None, None
            elif len(parts) == 2:
                first, middle, last = parts[0], None, parts[1]
            else:
                first, middle, last = parts[0], " ".join(parts[1:-1]), parts[-1]

            people_records.append({"trip_id": idx, "first": first, "middle": middle, "last": last})

    # Convert records to DataFrame and import into people table
    if people_records:
        people_df = pandas.DataFrame(people_records)
        people_df.to_csv("people.csv", index=False)
        people_df.to_sql("people", conn, if_exists="replace", index=False)

    print(f"Successfully imported {len(df)} trips into {db_path}")

    # Commit changes and close connection
    conn.commit()
    conn.close()


if __name__ == "__main__":
    app()
