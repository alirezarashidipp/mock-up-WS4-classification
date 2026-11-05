import csv
import os
from pathlib import Path
from tempfile import NamedTemporaryFile


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, strict=True)
        columns = reader.fieldnames or []
        if not columns:
            raise ValueError("CSV headers must be nonblank and unique.")
        if len(columns) != len(set(columns)):
            raise ValueError("CSV headers must be nonblank and unique.")
        for name in columns:
            if not name.strip():
                raise ValueError("CSV headers must be nonblank and unique.")
        rows = list(reader)
    for row in rows:
        if None in row or None in row.values():
            raise ValueError("CSV rows must have the same number of cells as the headers.")
    return rows


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
