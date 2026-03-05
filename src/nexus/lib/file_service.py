import os
from datetime import datetime
from typing import List, Tuple
from urllib.parse import urlparse

import requests
from nexus.config import ROOT_DIR


class FileRepository:
    @staticmethod
    def get_file_lines(file_path) -> List[str]:
        with open(file_path, "r") as file:
            return file.readlines()

    @staticmethod
    def get_file_contents(filepath: str):
        abs_filepath = os.path.join(ROOT_DIR, filepath)

        try:
            with open(abs_filepath, "r") as file:
                content = file.read()
                return content
        except FileNotFoundError:
            raise FileNotFoundError(f"Error: {filepath} does not exist in the {dir} folder.")
        except Exception as e:
            return f"An error occurred: {str(e)}"

    @staticmethod
    def get_file_line_items(file_path: str) -> Tuple[List[str], float]:
        """Get the contents of a file as a list of lines and the time taken to process the file."""
        start_time = datetime.now()
        file_lines = FileRepository.get_file_lines(file_path=file_path)
        lines = []

        print(len(file_lines))
        for line in file_lines:
            line = line.strip()
            if len(line) == 0 or line.startswith("#"):
                continue
            lines.append(line)

        end_time = datetime.now()

        return lines, (end_time - start_time).total_seconds()

    @staticmethod
    def download_file(url: str, directory: str) -> dict[str, str | bool]:
        """Download a file from a URL and save it to the specified directory."""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()

            # Extract the filename from the URL
            parsed_url = urlparse(url)
            file_name = os.path.basename(parsed_url.path)

            # Define the path where the will be saved
            destination_path = os.path.join(directory, file_name)

            # Check if the file already exists
            if os.path.exists(destination_path):
                return {"success": False, "error": "File already exists. Skipping download."}

            # Save the image to the specified directory
            with open(destination_path, "wb") as download_file:
                for chunk in response.iter_content(1024):
                    download_file.write(chunk)

            return {"success": True, "error": False}

        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to download '{url}': {e}")
