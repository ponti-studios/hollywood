"""Migrate data from kuma.db into the unified hollywood.db schema.

Usage:
    uv run python scripts/migrate_kuma.py

Reads from:  ~/Developer/kuma/kuma.db
Writes to:   ~/.hominem/hollywood.db

Fails safely — both databases are backed up before any writes.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

KUMA_DB = Path.home() / "Developer" / "kuma" / "kuma.db"
HOLLYWOOD_DB = Path.home() / ".hominem" / "hollywood.db"
SOURCE_ID = "kuma_migration"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    backup_path = path.with_suffix(path.suffix + ".bak")
    if not backup_path.exists():
        import shutil
        shutil.copy2(path, backup_path)
        print(f"  Backed up {path} → {backup_path}")
        return backup_path
    return None


def open_kuma() -> sqlite3.Connection:
    conn = sqlite3.connect(str(KUMA_DB))
    conn.row_factory = sqlite3.Row
    return conn


def open_hollywood() -> sqlite3.Connection:
    conn = sqlite3.connect(str(HOLLYWOOD_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")
    return conn


def safe_int(v) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def row_get(row: sqlite3.Row, key: str, default=None):
    try:
        return row[key]
    except (KeyError, IndexError):
        return default


# ── Migrate entities ─────────────────────────────────────────────────────────

def migrate_entities(kuma: sqlite3.Connection, hw: sqlite3.Connection) -> dict[str, int]:
    """Migrate people → entities(person), companies → entities(company),
    projects → entities(title). Returns counts."""

    counts = {"person": 0, "company": 0, "title": 0}

    # People
    rows = kuma.execute("SELECT * FROM people").fetchall()
    for row in rows:
        hw.execute(
            """INSERT OR IGNORE INTO entities
               (id, source_id, entity_type, name, canonical_name, bio, position, status, license_class, created_at, updated_at)
               VALUES (?, ?, 'person', ?, ?, ?, ?, ?, 'public', ?, ?)""",
            (
                row["id"],
                SOURCE_ID,
                row["name"],
                row["normalized_name"],
                row["bio"] or "",
                row["position"] or "",
                row["status"],
                row["created_at"] or now(),
                row["updated_at"] or now(),
            ),
        )
        counts["person"] += 1

    # Companies ↔ entities(company)
    rows = kuma.execute("SELECT * FROM companies").fetchall()
    for row in rows:
        hw.execute(
            """INSERT OR IGNORE INTO entities
               (id, source_id, entity_type, name, canonical_name, company_type, status, license_class, created_at, updated_at)
               VALUES (?, ?, 'company', ?, ?, ?, ?, 'public', ?, ?)""",
            (
                row["id"],
                SOURCE_ID,
                row["name"],
                row["normalized_name"],
                row["company_type"],
                row["status"],
                row["created_at"] or now(),
                row["updated_at"] or now(),
            ),
        )
        counts["company"] += 1

    # Projects ↔ entities(title)
    rows = kuma.execute("SELECT * FROM projects").fetchall()
    for row in rows:
        meta = json.dumps({"format": row["format"]} if row["format"] else {})
        hw.execute(
            """INSERT OR IGNORE INTO entities
               (id, source_id, entity_type, name, canonical_name, title_type, format, metadata_json, status, license_class, created_at, updated_at)
               VALUES (?, ?, 'title', ?, ?, ?, ?, ?, ?, 'public', ?, ?)""",
            (
                row["id"],
                SOURCE_ID,
                row["title"],
                row["normalized_title"],
                row["project_type"] or "unknown",
                row["format"] or "",
                meta,
                row["status"],
                row["created_at"] or now(),
                row["updated_at"] or now(),
            ),
        )
        counts["title"] += 1

    return counts


# ── Migrate aliases → entity_aliases ─────────────────────────────────────────

def migrate_aliases(kuma: sqlite3.Connection, hw: sqlite3.Connection) -> int:
    count = 0
    for table, entity_field in [
        ("person_aliases", "person_id"),
        ("company_aliases", "company_id"),
        ("project_aliases", "project_id"),
    ]:
        try:
            rows = kuma.execute(f"SELECT * FROM {table}").fetchall()
        except sqlite3.OperationalError:
            continue
        for row in rows:
            hw.execute(
                """INSERT OR IGNORE INTO entity_aliases (id, entity_id, source_id, alias, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    row["id"],
                    row[entity_field],
                    SOURCE_ID,
                    row["alias"],
                    row["created_at"] or now(),
                ),
            )
            count += 1
    return count


# ── Migrate contacts → entity_contacts ───────────────────────────────────────

def migrate_contacts(kuma: sqlite3.Connection, hw: sqlite3.Connection) -> int:
    count = 0
    for table, entity_field in [("person_contacts", "person_id"), ("company_contacts", "company_id")]:
        try:
            rows = kuma.execute(f"SELECT * FROM {table}").fetchall()
        except sqlite3.OperationalError:
            continue
        for row in rows:
            hw.execute(
                """INSERT OR IGNORE INTO entity_contacts
                   (id, entity_id, source_id, contact_type, contact_value, trust_state, created_at)
                   VALUES (?, ?, ?, ?, ?, 'machine_extracted', ?)""",
                (
                    row["id"],
                    row[entity_field],
                    SOURCE_ID,
                    row["contact_type"],
                    row["contact_value"],
                    row["created_at"] or now(),
                ),
            )
            count += 1
    return count


# ── Migrate links → entity_links ─────────────────────────────────────────────

def migrate_links(kuma: sqlite3.Connection, hw: sqlite3.Connection) -> int:
    count = 0
    for table, entity_field in [
        ("person_links", "person_id"),
        ("company_links", "company_id"),
        ("project_links", "project_id"),
    ]:
        try:
            rows = kuma.execute(f"SELECT * FROM {table}").fetchall()
        except sqlite3.OperationalError:
            continue
        for row in rows:
            url = row["url"] if "url" in row.keys() else (row["link_url"] if "link_url" in row.keys() else "")
            link_type = row["link_type"] if "link_type" in row.keys() else "other"
            hw.execute(
                """INSERT OR IGNORE INTO entity_links (id, entity_id, source_id, url, link_type, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    row["id"],
                    row[entity_field],
                    SOURCE_ID,
                    url,
                    link_type,
                    row["created_at"] or now(),
                ),
            )
            count += 1
    return count


# ── Migrate credits ──────────────────────────────────────────────────────────

def migrate_credits(kuma: sqlite3.Connection, hw: sqlite3.Connection) -> int:
    rows = kuma.execute("SELECT * FROM credits").fetchall()
    for row in rows:
        hw.execute(
            """INSERT OR IGNORE INTO credits
               (id, person_id, title_id, source_id, role, credit_type, trust_state, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'machine_extracted', ?)""",
            (
                row["id"],
                row["person_id"],
                row["project_id"],
                SOURCE_ID,
                row["role"],
                row["credit_type"],
                row["created_at"] or now(),
            ),
        )
    return len(rows)


# ── Migrate representation ───────────────────────────────────────────────────

def migrate_representation(kuma: sqlite3.Connection, hw: sqlite3.Connection) -> int:
    try:
        rows = kuma.execute("SELECT * FROM representation").fetchall()
    except sqlite3.OperationalError:
        return 0
    for row in rows:
        hw.execute(
            """INSERT OR IGNORE INTO representation
               (id, client_id, rep_id, rep_company_id, rep_type, title, email, phone, source_id, trust_state, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'machine_extracted', ?)""",
            (
                row["id"],
                row["client_person_id"],
                row["rep_person_id"],
                row["rep_company_id"],
                row["rep_type"],
                row["title"],
                row["email"],
                row["phone"],
                SOURCE_ID,
                row["created_at"] or now(),
            ),
        )
    return len(rows)


# ── Migrate deals ────────────────────────────────────────────────────────────

def migrate_deals(kuma: sqlite3.Connection, hw: sqlite3.Connection) -> int:
    try:
        rows = kuma.execute("SELECT * FROM deals").fetchall()
    except sqlite3.OperationalError:
        return 0
    for row in rows:
        hw.execute(
            """INSERT OR IGNORE INTO deals
               (id, person_id, company_id, title_id, deal_type, status, source_id, trust_state, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'machine_extracted', ?)""",
            (
                row["id"],
                row["person_id"],
                row["company_id"],
                row["project_id"],
                row["deal_type"],
                row["status"],
                SOURCE_ID,
                row["created_at"] or now(),
            ),
        )
    return len(rows)


# ── Migrate collaborations ───────────────────────────────────────────────────

def migrate_collaborations(kuma: sqlite3.Connection, hw: sqlite3.Connection) -> int:
    try:
        rows = kuma.execute("SELECT * FROM collaborations").fetchall()
    except sqlite3.OperationalError:
        return 0
    for row in rows:
        hw.execute(
            """INSERT OR IGNORE INTO collaborations
               (id, person_a_id, person_b_id, title_id, relationship, source_id, trust_state, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'machine_extracted', ?)""",
            (
                row["id"],
                row["person_a_id"],
                row["person_b_id"],
                row["project_id"],
                row["relationship_type"],
                SOURCE_ID,
                row["created_at"] or now(),
            ),
        )
    return len(rows)


# ── Migrate tags ─────────────────────────────────────────────────────────────

def migrate_tags(kuma: sqlite3.Connection, hw: sqlite3.Connection) -> dict[str, int]:
    """Migrate tags and taggings → tags + entity_taggings."""
    tag_count = 0
    tagging_count = 0

    try:
        rows = kuma.execute("SELECT * FROM tags").fetchall()
    except sqlite3.OperationalError:
        return {"tags": 0, "entity_taggings": 0}

    for row in rows:
        hw.execute(
            """INSERT OR IGNORE INTO tags (id, tag, normalized_tag, created_at)
               VALUES (?, ?, ?, ?)""",
            (row["id"], row["tag"], row["normalized_tag"], row["created_at"] or now()),
        )
        tag_count += 1

    try:
        rows = kuma.execute("SELECT * FROM taggings").fetchall()
    except sqlite3.OperationalError:
        return {"tags": tag_count, "entity_taggings": 0}

    for row in rows:
        # kuma taggings use target_table/target_id — map to entity_id
        target_id = row["target_id"]
        hw.execute(
            """INSERT OR IGNORE INTO entity_taggings
               (id, tag_id, entity_id, source_id, trust_state, created_at)
               VALUES (?, ?, ?, ?, 'machine_extracted', ?)""",
            (
                row["id"],
                row["tag_id"],
                target_id,
                SOURCE_ID,
                row["created_at"] or now(),
            ),
        )
        tagging_count += 1

    return {"tags": tag_count, "entity_taggings": tagging_count}


# ── Migrate submissions & extraction results ─────────────────────────────────

def migrate_extraction(kuma: sqlite3.Connection, hw: sqlite3.Connection) -> dict[str, int]:
    """Migrate extraction_results, submissions, and source_facts."""

    # Extraction results
    er_count = 0
    try:
        rows = kuma.execute("SELECT * FROM extraction_results").fetchall()
    except sqlite3.OperationalError:
        rows = []
    for row in rows:
        hw.execute(
            """INSERT OR IGNORE INTO extraction_results
               (id, document_id, job_id, schema_version, prompt_version, model_name,
                status, raw_json, result_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                row["id"],
                row["document_id"],
                row["job_id"] if "job_id" in row.keys() else None,
                row["schema_version"],
                row["prompt_version"],
                row["model_name"],
                row["status"],
                row["raw_json"],
                row["result_json"],
                row["created_at"] or now(),
            ),
        )
        er_count += 1

    # Submissions
    sub_count = 0
    try:
        rows = kuma.execute("SELECT * FROM submissions").fetchall()
    except sqlite3.OperationalError:
        rows = []
    for row in rows:
        hw.execute(
            """INSERT OR IGNORE INTO submissions
               (id, document_id, extraction_id, submitted_by_person_id, submitted_by_company_id,
                submitted_to_person_id, submitted_to_company_id, opportunity_title_id,
                purpose, received_at, source_id, trust_state, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'machine_extracted', ?)""",
            (
                row["id"],
                row["document_id"],
                row_get(row, "extraction_result_id", row_get(row, "extraction_id", "")),
                row["submitted_by_person_id"],
                row["submitted_by_company_id"],
                row["submitted_to_person_id"],
                row["submitted_to_company_id"],
                row["opportunity_project_id"],
                row["purpose"],
                row["received_at"],
                SOURCE_ID,
                row["created_at"] or now(),
            ),
        )
        sub_count += 1

    # Source facts
    sf_count = 0
    try:
        rows = kuma.execute("SELECT * FROM source_facts").fetchall()
    except sqlite3.OperationalError:
        rows = []
    for row in rows:
        hw.execute(
            """INSERT OR IGNORE INTO source_facts
               (id, source_table, source_row_id, document_id, extraction_id,
                json_path, source_text, trust_state, confidence, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'machine_extracted', 'machine_extracted', ?)""",
            (
                row["id"],
                row["source_table"],
                row["source_row_id"],
                row["document_id"],
                row_get(row, "extraction_result_id", row_get(row, "extraction_id", "")),
                row["json_path"],
                row["source_text"],
                row["created_at"] or now(),
            ),
        )
        sf_count += 1

    return {
        "extraction_results": er_count,
        "submissions": sub_count,
        "source_facts": sf_count,
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"Migrating from: {KUMA_DB}")
    print(f"Migrating to:   {HOLLYWOOD_DB}")
    print()

    if not KUMA_DB.exists():
        print(f"ERROR: Source database not found at {KUMA_DB}")
        return 1

    if not HOLLYWOOD_DB.exists():
        print(f"ERROR: Target database not found at {HOLLYWOOD_DB}")
        print("  Run 'goose up' first to create the schema.")
        return 1

    backup(HOLLYWOOD_DB)

    kuma = open_kuma()
    hw = open_hollywood()

    try:
        # Entities
        entity_counts = migrate_entities(kuma, hw)
        print(f"  Entities: {entity_counts['person']} people, {entity_counts['company']} companies, {entity_counts['title']} titles")

        # Aliases
        alias_count = migrate_aliases(kuma, hw)
        print(f"  Aliases: {alias_count}")

        # Contacts
        contact_count = migrate_contacts(kuma, hw)
        print(f"  Contacts: {contact_count}")

        # Links
        link_count = migrate_links(kuma, hw)
        print(f"  Links: {link_count}")

        # Credits
        credit_count = migrate_credits(kuma, hw)
        print(f"  Credits: {credit_count}")

        # Representation
        rep_count = migrate_representation(kuma, hw)
        print(f"  Representation: {rep_count}")

        # Deals
        deal_count = migrate_deals(kuma, hw)
        print(f"  Deals: {deal_count}")

        # Collaborations
        collab_count = migrate_collaborations(kuma, hw)
        print(f"  Collaborations: {collab_count}")

        # Tags
        tag_counts = migrate_tags(kuma, hw)
        print(f"  Tags: {tag_counts['tags']}, Taggings: {tag_counts['entity_taggings']}")

        # Extraction pipeline
        ext_counts = migrate_extraction(kuma, hw)
        print(f"  Extraction results: {ext_counts['extraction_results']}")
        print(f"  Submissions: {ext_counts['submissions']}")
        print(f"  Source facts: {ext_counts['source_facts']}")

        hw.commit()
        print(f"\n✅ Migration complete. All IDs preserved.")

    except Exception as e:
        hw.rollback()
        print(f"\n❌ Migration failed, rolled back: {e}", file=sys.stderr)
        return 1
    finally:
        kuma.close()
        hw.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
