"""
### Inspiration
This script was inspired by my desire to grab the icons from this [IconScout](https://iconscout.com/free-3d-illustration-pack/social-media-127)
page without having to manually download each one.

I used the Chrome Developer tools to write a JavaScript snippet that would extract the URLs of the images, save them to an arraym and then
copy the array to the clipboard. Here's the JavaScript snippet I wrote:
```javascript
const urls = (
    Array
        .from(document.querySelectorAll('.thumb_PdMgf source'))
        .flatMap(item => item.srcset.split(', '))
        .filter(item => item.indexOf('2x') > -1)
        .map(item => item.replace(' 2x', ''))
);

copy(urls) # Copy the URLs to the clipboard
```
I then pasted the copied URLs into a JSON file and ran the script to download all the images to a specified directory.

### What it does
This script reads a JSON file containing a list of image URLs and downloads each image to a specified directory.


### How to use
1. Create a JSON file with a list of image URLs.
2. Run the script with the path to the JSON file and the directory where you want to save the images.
3. The script will download each image to the specified directory. If the image already exists in the directory, it skips the download.
4. Profit!
"""

import json
import os
from typing import Annotated, Optional
import requests
import typer
from urllib.parse import urlparse

app = typer.Typer()


def download_image(url: str, directory: str) -> tuple[Exception | None, str | None]:
    """Download an image from a URL and save it to the specified directory."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # Extract the image filename from the URL
        parsed_url = urlparse(url)
        image_name = os.path.basename(parsed_url.path)

        # Define the path where the image will be saved
        image_path = os.path.join(directory, image_name)

        # Check if the image already exists
        if os.path.exists(image_path):
            raise FileExistsError("Image '{image_name}' already exists. Skipping download.")

        # Save the image to the specified directory
        with open(image_path, "wb") as image_file:
            for chunk in response.iter_content(1024):
                image_file.write(chunk)

        return None, image_name

    except requests.RequestException as e:
        return e, None


@app.command()
def download_images(
    json_filename: Annotated[str, typer.Option(help="JSON file containing image URLs")],
    directory: Annotated[Optional[str], typer.Argument(help="Directory to save the images")],
):
    """Read a JSON file and download images from the URLs listed in the JSON."""
    try:
        # Read the JSON file
        with open(json_filename, "r") as file:
            urls = json.load(file)

        # Ensure the JSON file contains a list of URLs
        if not isinstance(urls, list):
            typer.echo("The JSON file must contain a list of URLs.")
            raise typer.Exit(code=1)

        # Download each image from the list of URLs
        for url in urls:
            err, image_name = download_image(url, directory or os.getcwd())
            if err:
                typer.echo(f"Could not download {url}", err=True)
            else:
                typer.echo(f"Downloaded '{image_name}' successfully.")

    except FileNotFoundError:
        typer.echo(f"File '{json_filename}' not found.")
        raise typer.Exit(code=1)
    except json.JSONDecodeError:
        typer.echo(f"File '{json_filename}' is not a valid JSON file.")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
