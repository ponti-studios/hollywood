import os

import typer

from nexus.commands.job_post import convert_text_to_job_post
from nexus.lib.scrapers.base import get_filename_from_url, scrape_website

app = typer.Typer()


@app.command(name="scrape")
def _scrape_website(url: str = typer.Option(..., help="The URL to scrape")) -> str:
    text = scrape_website(url)
    filename = get_filename_from_url(url)
    output_path = os.path.join(os.getcwd(), f"{filename}.md")

    with open(output_path, "w") as f:
        f.write(str(text))

    return text


@app.command(name="job-post")
def crawl_job_post(url: str = typer.Option(..., help="The URL to crawl")):
    result = _scrape_website(url)
    if not result:
        raise ValueError("No text found on the website")

    response = convert_text_to_job_post(result)
    response.url = url

    output_path = os.path.join(
        os.getcwd(), f"{response.companyName.lower()} - {response.jobTitle.lower()}.json"
    )
    with open(output_path, "w") as f:
        f.write(response.model_dump_json())


if __name__ == "__main__":
    app()
