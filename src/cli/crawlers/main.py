import os

import typer

from snakesss.cli.crawlers.job_post import convert_text_to_job_post
from snakesss.lib.scrapers.zillow_scraper import scrape_zillow

# Updated import to use the lib module
from snakesss.lib.scrapers import scrape_website, get_filename_from_url

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


@app.command(name="zillow")
def crawl_zillow(url: str = typer.Option(..., help="The URL to scrape")):
    # Get home details using the extracted scraper function
    result, filename, markdown_filename = scrape_zillow(url)
    with open(os.path.join(os.getcwd(), markdown_filename), "w") as f:
        f.write(result.text)
        print(f"Home details saved to ./{markdown_filename}")

    with open(os.path.join(os.getcwd(), filename), "w") as f:
        f.write(result.model_dump_json(indent=2))
        print(f"Home details saved to ./{filename}")


if __name__ == "__main__":
    app()
