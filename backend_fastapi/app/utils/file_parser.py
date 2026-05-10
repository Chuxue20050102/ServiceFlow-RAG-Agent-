import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import tiktoken


REQUIRED_TICKET_COLUMNS = {"ticket_id", "user_id", "content", "source", "created_at"}


def parse_ticket_file(file_path: str | Path) -> list[dict[str, Any]]:
    path = Path(file_path)
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    elif path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    else:
        raise ValueError("Only CSV, XLS, and XLSX ticket files are supported.")

    missing_columns = REQUIRED_TICKET_COLUMNS - set(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required columns: {missing}")

    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        content = str(row["content"]).strip()
        if not content or content.lower() == "nan":
            continue

        rows.append(
            {
                "ticket_id": str(row["ticket_id"]).strip(),
                "user_id": str(row["user_id"]).strip(),
                "content": content,
                "source": str(row["source"]).strip(),
                "submitted_at": _parse_datetime(row["created_at"]),
            }
        )

    return rows


def parse_knowledge_file(file_path: str | Path) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix not in {".txt", ".md"}:
        raise ValueError("MVP supports TXT and Markdown rule documents first.")

    return path.read_text(encoding="utf-8").strip()


def split_text(text: str, chunk_size: int = 600, overlap: int = 80) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []

    sections = split_markdown_sections(normalized)
    chunks: list[str] = []

    for section in sections:
        if token_count(section) <= chunk_size:
            chunks.append(section)
        else:
            chunks.extend(split_by_tokens(section, chunk_size, overlap))

    return chunks


def normalize_text(text: str) -> str:
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def split_markdown_sections(text: str) -> list[str]:
    parts = re.split(r"(?=^#{1,6}\s+)", text, flags=re.MULTILINE)
    sections = [part.strip() for part in parts if part.strip()]
    return sections or [text]


def split_by_tokens(text: str, chunk_size: int, overlap: int) -> list[str]:
    encoding = get_encoding()
    tokens = encoding.encode(text)
    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk = encoding.decode(tokens[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        if end == len(tokens):
            break
        start = max(end - overlap, start + 1)

    return chunks


def token_count(text: str) -> int:
    return len(get_encoding().encode(text))


def get_encoding():
    return tiktoken.get_encoding("cl100k_base")


def _parse_datetime(value: Any) -> datetime | None:
    if pd.isna(value):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()
