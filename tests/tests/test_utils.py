import os
import sys

import pytest

# Add the project root directory to Python's module search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snakesss.lib.writing.utils import (
    Section,
    get_document_sections,
    get_formatted_line,
    get_header_line_contents,
    get_section_names,
    get_words,
    has_text,
    is_bullet_point,
    is_extra_empty_line,
    is_sub_bullet_point,
)


def test_get_words():
    assert get_words("Hello, world!") == ["hello", "world"]


def test_is_sub_bullet_point():
    assert is_sub_bullet_point("  - Sub-bullet")
    assert not is_sub_bullet_point("- Not sub-bullet")


def test_has_text():
    assert has_text("  Text  ")
    assert not has_text("   ")


def test_is_bullet_point():
    assert is_bullet_point("- Bullet")
    assert is_bullet_point("• Bullet")
    assert not is_bullet_point("Not bullet")


def test_is_extra_empty_line():
    assert is_extra_empty_line("", [""])
    assert not is_extra_empty_line("", ["Text"])


@pytest.mark.parametrize(
    "line,lines,expected",
    [
        ("# Header", [], None),
        ("- Bullet", [], "- Bullet"),
        ("  - Sub-bullet", [], "  - Sub-bullet"),
        ("Text", [], "- Text"),
        ("", [""], None),
    ],
)
def test_get_formatted_line(line, lines, expected):
    assert get_formatted_line(line, lines) == expected


def test_get_header_line_contents():
    assert get_header_line_contents("# Header") == (1, "Header")
    assert get_header_line_contents("### Sub-header") == (3, "Sub-header")


def test_get_empty_sections():
    input_lines = [
        "# Section 1",
        "## Subsection 1",
        "## Subsection 2",
    ]
    expected = (
        {
            "__text__": [],
            "sections": {
                "Section 1": {
                    "__text__": [],
                    "sections": {
                        "Subsection 1": {"__text__": [], "sections": {}},
                        "Subsection 2": {"__text__": [], "sections": {}},
                    },
                }
            },
        },
        ["Section 1", "Subsection 1"],
    )
    assert get_document_sections(input_lines, get_empty_sections=True) == expected


def test_empty_document():
    assert get_document_sections([]) == ({"__text__": [], "sections": {}}, [])


def test_single_section():
    input_lines = ["# Section 1", "text 1", "text 2"]
    expected = (
        {
            "__text__": [],
            "sections": {
                "Section 1": {"__text__": ["text 1", "text 2"], "sections": {}},
            },
        },
        [],
    )
    assert get_document_sections(input_lines) == expected, []


def test_nested_sections():
    input_lines = [
        "# Section 1",
        "main text",
        "## Subsection 1",
        "sub text",
        "### Sub-subsection 1",
        "deep text",
    ]
    expected = (
        {
            "__text__": [],
            "sections": {
                "Section 1": {
                    "__text__": ["main text"],
                    "sections": {
                        "Subsection 1": {
                            "__text__": ["sub text"],
                            "sections": {"Sub-subsection 1": {"__text__": ["deep text"], "sections": {}}},
                        }
                    },
                }
            },
        },
        [],
    )
    assert get_document_sections(input_lines) == expected


def test_multiple_sections_same_level():
    input_lines = ["# Section 1", "text 1", "# Section 2", "text 2"]
    expected = (
        {
            "__text__": [],
            "sections": {
                "Section 1": {"__text__": ["text 1"], "sections": {}},
                "Section 2": {"__text__": ["text 2"], "sections": {}},
            },
        },
        [],
    )
    assert get_document_sections(input_lines) == expected


def test_mixed_depth_sections():
    input_lines = [
        "# Section 1",
        "text 1",
        "## Subsection 1",
        "sub text 1",
        "# Section 2",
        "text 2",
        "## Subsection 2",
        "sub text 2",
    ]
    expected = (
        {
            "__text__": [],
            "sections": {
                "Section 1": {
                    "__text__": ["text 1"],
                    "sections": {"Subsection 1": {"__text__": ["sub text 1"], "sections": {}}},
                },
                "Section 2": {
                    "__text__": ["text 2"],
                    "sections": {"Subsection 2": {"__text__": ["sub text 2"], "sections": {}}},
                },
            },
        },
        [],
    )
    assert get_document_sections(input_lines) == expected


def test_skipping_header_levels():
    input_lines = ["# Section 1", "text 1", "### Deep subsection", "deep text"]
    expected = (
        {
            "__text__": [],
            "sections": {
                "Section 1": {
                    "__text__": ["text 1"],
                    "sections": {"Deep subsection": {"__text__": ["deep text"], "sections": {}}},
                }
            },
        },
        [],
    )
    assert get_document_sections(input_lines) == expected


def test_empty_sections():
    input_lines = [
        "# Section 1",
        "## Subsection 1",
        "## Subsection 2",
    ]
    expected = (
        {
            "__text__": [],
            "sections": {
                "Section 1": {
                    "__text__": [],
                    "sections": {
                        "Subsection 1": {"__text__": [], "sections": {}},
                        "Subsection 2": {"__text__": [], "sections": {}},
                    },
                }
            },
        },
        [],
    )
    assert get_document_sections(input_lines) == expected


def test_get_section_names():
    doc = {
        "__text__": [],
        "sections": {
            "Section 1": {
                "__text__": [],
                "sections": {
                    "Subsection 1": {"__text__": [], "sections": {}},
                    "Subsection 2": {"__text__": [], "sections": {}},
                },
            }
        },
    }

    names = get_section_names(Section(**doc))
    assert names == ["Section 1", "Subsection 1", "Subsection 2"]
