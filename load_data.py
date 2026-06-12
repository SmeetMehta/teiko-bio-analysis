"""
load_data.py - Part 1: Data Management

Initializes the SQLite database with a relational schema and loads all rows
from cell-count.csv.

Usage:
    python load_data.py
"""

import csv
import sqlite3
import os

DB_PATH = "cell_counts.db"
CSV_PATH = "cell-count.csv"


def create_schema(conn):
    """Create the relational database schema."""
    cursor = conn.cursor()

    # Projects table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            project_id TEXT PRIMARY KEY
        )
    """)

    # Subjects table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            subject_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            condition TEXT NOT NULL,
            age INTEGER NOT NULL,
            sex TEXT NOT NULL,
            treatment TEXT NOT NULL,
            response TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(project_id)
        )
    """)

    # Samples table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS samples (
            sample_id TEXT PRIMARY KEY,
            subject_id TEXT NOT NULL,
            sample_type TEXT NOT NULL,
            time_from_treatment_start INTEGER NOT NULL,
            FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
        )
    """)

    # Cell counts table (normalized: one row per sample per population)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cell_counts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sample_id TEXT NOT NULL,
            population TEXT NOT NULL,
            count INTEGER NOT NULL,
            FOREIGN KEY (sample_id) REFERENCES samples(sample_id)
        )
    """)

    # Indexes for common queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_subjects_project ON subjects(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_subjects_condition ON subjects(condition)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_subjects_treatment ON subjects(treatment)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_subjects_response ON subjects(response)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_samples_subject ON samples(subject_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_samples_time ON samples(time_from_treatment_start)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_samples_type ON samples(sample_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cell_counts_sample ON cell_counts(sample_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cell_counts_population ON cell_counts(population)")

    conn.commit()


def load_data(conn):
    """Load data from cell-count.csv into the database."""
    cursor = conn.cursor()

    populations = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]
    projects_seen = set()
    subjects_seen = set()

    with open(CSV_PATH, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            project_id = row["project"]
            subject_id = row["subject"]
            sample_id = row["sample"]

            # Insert project if not seen
            if project_id not in projects_seen:
                cursor.execute(
                    "INSERT OR IGNORE INTO projects (project_id) VALUES (?)",
                    (project_id,)
                )
                projects_seen.add(project_id)

            # Insert subject if not seen
            if subject_id not in subjects_seen:
                response = row["response"] if row["response"] else None
                cursor.execute(
                    """INSERT OR IGNORE INTO subjects 
                       (subject_id, project_id, condition, age, sex, treatment, response) 
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (subject_id, project_id, row["condition"], int(row["age"]),
                     row["sex"], row["treatment"], response)
                )
                subjects_seen.add(subject_id)

            # Insert sample
            cursor.execute(
                """INSERT OR IGNORE INTO samples 
                   (sample_id, subject_id, sample_type, time_from_treatment_start) 
                   VALUES (?, ?, ?, ?)""",
                (sample_id, subject_id, row["sample_type"],
                 int(row["time_from_treatment_start"]))
            )

            # Insert cell counts for each population
            for pop in populations:
                cursor.execute(
                    "INSERT INTO cell_counts (sample_id, population, count) VALUES (?, ?, ?)",
                    (sample_id, pop, int(row[pop]))
                )

    conn.commit()


def main():
    """Main entry point."""
    # Remove existing database if present
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    try:
        create_schema(conn)
        load_data(conn)
        print(f"Database created successfully: {DB_PATH}")

        # Verify
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM samples")
        print(f"  Samples loaded: {cursor.fetchone()[0]}")
        cursor.execute("SELECT COUNT(*) FROM subjects")
        print(f"  Subjects loaded: {cursor.fetchone()[0]}")
        cursor.execute("SELECT COUNT(*) FROM cell_counts")
        print(f"  Cell count records: {cursor.fetchone()[0]}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
