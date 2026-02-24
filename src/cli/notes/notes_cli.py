"""
!TODO Analyze documents and apply tags
!TODO Analyze documents line-by-line
!TODO Fix base-level grammar and spelling mistakes
"""

import json
import os

import openai
import typer

from snakesss.lib.file_service import FileRepository
from snakesss.lib.writing.utils import (
    get_document_sections,
    get_empty_sections,
    get_formatted_line,
    get_section_names,
    get_words,
    has_self_referential_pronouns,
)
import snakesss.cli.notes.process_markdown as process_markdown

# Initialize OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")

notes_app = typer.Typer(name="notes")
notes_app.add_typer(process_markdown.app, name="process")


def save_lines_to_file(filename: str, lines: list[str] | set[str]):
    with open(filename, "w") as f:
        for line in lines:
            f.write(f"{line}\n")
    print(f"{len(lines)} lines saved to {filename}")


@notes_app.command(name="remove-duplicate-lines", help="Remove duplicate lines from a file.")
def remove_duplicate_lines(
    file: str = typer.Argument(help="The file to remove duplicates from."),
):
    with open(file, "r") as f:
        lines = f.readlines()
        print(f"Number of lines: {len(lines)}")
        formatted_lines: set[str] = set()

        for line in lines:
            formatted_line = get_formatted_line(line, lines)
            if formatted_line not in formatted_lines and formatted_line is not None:
                formatted_lines.add(formatted_line)

    save_lines_to_file(f"{file}-deduped-lines.txt", formatted_lines)


@notes_app.command(name="remove-self-referential-lines", help="Remove lines that contain personal pronouns.")
def remove_self_referential_lines(
    file: str = typer.Argument(help="The file to remove self-referential lines from."),
):
    lines = FileRepository.get_file_lines(file)
    self_referential_lines: set[str] = set()
    non_self_referential_lines: set[str] = set()
    for line in lines:
        if has_self_referential_pronouns(get_words(line)):
            self_referential_lines.add(line)
        else:
            non_self_referential_lines.add(line)

    save_lines_to_file(f"{file}-self-referential.txt", self_referential_lines)
    save_lines_to_file(f"{file}-non-self-referential.txt", non_self_referential_lines)


@notes_app.command(name="sort-file", help="Sort the lines in a file.")
def sort_file(file: str):
    sorted_lines: list[str] = []
    with open(file, "r") as f:
        lines = f.readlines()
        sorted_lines = [line for line in sorted(lines)]
    with open(f"{file}-sorted.txt", "w") as f:
        for line in sorted_lines:
            f.write(line)


@notes_app.command(name="count-line-items", help="Count the number of line items in a file.")
def count_line_items(file_path: str = typer.Argument(..., help="Path to the file to be parsed")):
    lines, seconds_taken = FileRepository.get_file_line_items(file_path=file_path)

    print("Time taken to process file in seconds:", seconds_taken)
    return len(lines)


@notes_app.command(name="get-empty-sections", help="Get the empty sections from a file.")
def get_file_empty_sections(file_path: str = typer.Argument(..., help="Path to the file to be parsed")):
    file_lines = FileRepository.get_file_lines(file_path=file_path)
    sections = get_document_sections(file_lines)[0]
    empty_sections = get_empty_sections(sections)

    typer.echo(json.dumps(empty_sections, indent=4))


@notes_app.command(name="get-section-names", help="Get the section names from a file.")
def get_file_section_names(file_path: str = typer.Argument(..., help="Path to the file to be parsed")):
    file_lines = FileRepository.get_file_lines(file_path=file_path)
    sections = get_document_sections(file_lines)[0]
    section_names = get_section_names(sections)

    typer.echo(json.dumps(section_names, indent=4))


@notes_app.command(name="get-file-sections", help="Get the sections from a file.")
def get_file_sections(
    file_path: str = typer.Argument(..., help="Path to the file to be parsed"),
    get_empty_sections: bool = typer.Option(False, help="Whether to get the empty sections."),
    only_names: bool = typer.Option(False, help="Whether to only get the section names."),
):
    file_lines = FileRepository.get_file_lines(file_path=file_path)
    sections = get_document_sections(file_lines, get_empty_sections=get_empty_sections)

    if get_empty_sections:
        typer.echo(json.dumps(sections[1], indent=4))
    else:
        typer.echo(json.dumps(sections, indent=4))


if __name__ == "__main__":
    notes_app()
