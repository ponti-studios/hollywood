import os
from datetime import datetime
from typing import List, Tuple

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


