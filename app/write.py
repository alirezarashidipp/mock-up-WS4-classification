"""Format each successful result and atomically save accumulated rows."""

import csv
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.schema import Classification


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = list(rows[0])
    temporary = NamedTemporaryFile(
        mode="w", encoding="utf-8-sig", newline="", dir=path.parent, delete=False,
    )
    temporary_path = Path(temporary.name)
    try:
        with temporary as file:
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def save_row(path, results, source_row, result):
    row = dict(source_row)
    row.update(result.model_dump())
    citation_column = Classification.model_fields["citations"].alias
    lines = []
    for citation in row[citation_column]:
        lines.extend(citation.splitlines())
    row[citation_column] = "\n".join(lines)
    results.append(row)
    write_csv(path, results)
