"""SQLite storage layer."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "students.db"
SUBJECTS = ["Maths", "Physics", "Chemistry", "English", "CS"]
REQUIRED = ["name", "maths", "physics", "chemistry", "english", "cs", "attendance"]


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS students(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            maths REAL, physics REAL, chemistry REAL, english REAL, cs REAL,
            attendance REAL)""")

        seen_names = set()
        duplicate_ids = []
        trimmed_names = []
        for row in c.execute("SELECT id, name FROM students ORDER BY id").fetchall():
            normalized_name = row["name"].strip().casefold()
            if normalized_name in seen_names:
                duplicate_ids.append((row["id"],))
            else:
                seen_names.add(normalized_name)
                if row["name"] != row["name"].strip():
                    trimmed_names.append((row["name"].strip(), row["id"]))
        if trimmed_names:
            c.executemany("UPDATE students SET name=? WHERE id=?", trimmed_names)
        if duplicate_ids:
            c.executemany("DELETE FROM students WHERE id=?", duplicate_ids)
        c.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_students_unique_name "
            "ON students(lower(trim(name)))"
        )
        is_empty = c.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0
    if is_empty:
        load_csv(BASE_DIR / "data" / "sample_students.csv")


def load_csv(src, replace=False):
    """Load a CSV into the DB and return the number added and skipped."""
    df = pd.read_csv(src)
    df.columns = [c.strip().lower() for c in df.columns]
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError("Missing columns: " + ", ".join(missing))
    df = df[REQUIRED].copy()
    for col in REQUIRED[1:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna()
    df["name"] = df["name"].astype(str).str.strip()
    df = df[df["name"] != ""]
    df[REQUIRED[1:]] = df[REQUIRED[1:]].clip(0, 100)
    if df.empty:
        raise ValueError("No valid rows found in the file.")

    df["_name_key"] = df["name"].str.casefold()
    duplicate_rows = df["_name_key"].duplicated(keep="first")
    skipped = int(duplicate_rows.sum())
    df = df.loc[~duplicate_rows].drop(columns="_name_key")

    with get_conn() as c:
        if replace:
            c.execute("DELETE FROM students")
        else:
            existing_names = {
                row[0].strip().casefold()
                for row in c.execute("SELECT name FROM students").fetchall()
            }
            already_present = df["name"].str.casefold().isin(existing_names)
            skipped += int(already_present.sum())
            df = df.loc[~already_present]

        if not df.empty:
            c.executemany(
                "INSERT INTO students(name,maths,physics,chemistry,english,cs,attendance) "
                "VALUES (?,?,?,?,?,?,?)",
                df[REQUIRED].itertuples(index=False, name=None),
            )
    return len(df), skipped


def get_df():
    with get_conn() as c:
        df = pd.read_sql_query("SELECT * FROM students", c)
    return df.rename(columns={"id": "ID", "name": "Name", "maths": "Maths", "physics": "Physics",
                              "chemistry": "Chemistry", "english": "English", "cs": "CS",
                              "attendance": "Attendance"})


def add_student(name, values):
    normalized_name = name.strip().casefold()
    with get_conn() as c:
        existing_names = c.execute("SELECT name FROM students").fetchall()
        if any(row[0].strip().casefold() == normalized_name for row in existing_names):
            raise ValueError(f"A student named {name.strip()} already exists.")
        c.execute("INSERT INTO students(name,maths,physics,chemistry,english,cs,attendance) "
                  "VALUES (?,?,?,?,?,?,?)", [name.strip(), *values])


def delete_student(sid):
    with get_conn() as c:
        c.execute("DELETE FROM students WHERE id=?", (sid,))
