import os
import re

for root, dirs, files in os.walk("."):
    # skip virtualenv, git metadata and other non-repo directories
    if root.startswith("./.venv") or ".venv" in root or root.startswith("./.git") or "site-packages" in root:
        continue
    for file in files:
        if file.endswith(".py"):
            filepath = os.path.join(root, file)
            # only attempt to read text files; skip non-utf8
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except (UnicodeDecodeError, PermissionError):
                continue
            new_content = re.sub(r"\bfrom lib\b", "from snakesss.lib", content)
            new_content = re.sub(r"\bfrom src\.cli\b", "from snakesss.cli", new_content)
            new_content = re.sub(r"\bfrom src\.", "from snakesss.", new_content)
            new_content = re.sub(r"\bimport src\.", "import snakesss.", new_content)
            new_content = re.sub(r"snakesss/", "snakesss/", new_content)
            if new_content != content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Updated {filepath}")
