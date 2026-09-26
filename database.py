import sqlite3
import json
from contextlib import closing
from pathlib import Path
from itertools import combinations

from scoring import SCORING_VERSION
from crypto_utils import decrypt_value, encrypt_value


DB_PATH = Path(__file__).resolve().parent / "data.db"
SENSITIVE_FIELDS = {
    "name": str,
    "revenue": float,
    "tax_percent": float,
    "employees": int,
    "social_media": str,
    "phone": str,
}


def _decrypt_company(row: sqlite3.Row) -> dict:
    company = dict(row)
    company["commerce_signal"] = bool(company["commerce_signal"])
    company["commerce_keywords"] = json.loads(company["commerce_keywords"] or "[]")
    for field, value_type in SENSITIVE_FIELDS.items():
        if company[field] is not None:
            company[field] = value_type(decrypt_value(company[field]))
    return company


def init_db():
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                revenue REAL,
                tax_percent REAL,
                employees INTEGER,
                social_media TEXT,
                phone TEXT,
                commerce_signal INTEGER DEFAULT 0,
                commerce_keywords TEXT,
                region TEXT,
                sector TEXT,
                risk_score INTEGER,
                recommendation TEXT,
                source TEXT NOT NULL CHECK (source IN ('upload', 'manual')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Миграция существующей базы без изменения сохранённых записей.
        columns = {row[1] for row in connection.execute("PRAGMA table_info(companies)")}
        if "scoring_version" not in columns:
            connection.execute("ALTER TABLE companies ADD COLUMN scoring_version TEXT")
        if "phone" not in columns:
            connection.execute("ALTER TABLE companies ADD COLUMN phone TEXT")
        if "commerce_signal" not in columns:
            connection.execute("ALTER TABLE companies ADD COLUMN commerce_signal INTEGER DEFAULT 0")
        if "commerce_keywords" not in columns:
            connection.execute("ALTER TABLE companies ADD COLUMN commerce_keywords TEXT")


def _insert_company(connection, data: dict) -> int:
    if data.get("source") not in ("upload", "manual"):
        raise ValueError("Источник должен быть 'upload' или 'manual'.")

    fields = (
        "name", "revenue", "tax_percent", "employees", "social_media",
        "region", "sector", "risk_score", "recommendation", "source", "phone",
        "commerce_signal", "commerce_keywords", "scoring_version",
    )
    data = {**data, "commerce_signal": int(bool(data.get("commerce_signal", False))),
            "commerce_keywords": json.dumps(data.get("commerce_keywords", []), ensure_ascii=False)}
    values = tuple(
        encrypt_value(str(data[field]))
        if field in SENSITIVE_FIELDS and data.get(field) is not None
        else data.get(field)
        for field in fields
    )
    cursor = connection.execute(
        "INSERT INTO companies (" + ", ".join(fields) + ") VALUES (" + ", ".join("?" for _ in fields) + ")",
        values,
    )
    return cursor.lastrowid


def insert_companies(records: list[dict]) -> list[int]:
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        return [_insert_company(connection, data) for data in records]


def insert_company(data: dict) -> int:
    return insert_companies([data])[0]


def get_company(id: int) -> dict | None:
    with closing(sqlite3.connect(DB_PATH)) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT * FROM companies WHERE id = ?", (id,)
        ).fetchone()
        return _decrypt_company(row) if row is not None else None


def get_all_companies() -> list[dict]:
    with closing(sqlite3.connect(DB_PATH)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT * FROM companies ORDER BY id"
        ).fetchall()
        return [_decrypt_company(row) for row in rows]


def update_company_score(id: int, risk_score: int, recommendation: str):
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        connection.execute(
            """
            UPDATE companies
            SET risk_score = ?, recommendation = ?
            WHERE id = ?
            """,
            (risk_score, recommendation, id),
        )


def find_linked_companies() -> list[dict]:
    companies = get_all_companies()
    pairs = []
    for field, reason in (("phone", "same phone"), ("social_media", "same social media")):
        groups = {}
        for company in companies:
            value = (company.get(field) or "").strip().casefold()
            if value:
                groups.setdefault(value, []).append({
                    "id": company["id"], "name": company["name"],
                    "risk_score": company["risk_score"] if company.get("scoring_version") == SCORING_VERSION else None,
                })
        for group in groups.values():
            for source, target in combinations(group, 2):
                pairs.append({"source": source, "target": target, "reason": reason})
    return pairs
