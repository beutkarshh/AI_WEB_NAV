from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DB_PATH = Path("data/artifacts/nav.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

ENGINE = create_engine(f"sqlite:///{DB_PATH.as_posix()}", future=True)
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, future=True)

def init_db():
    with ENGINE.begin() as conn:
        # Pragmas for speed & stability
        conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
        conn.exec_driver_sql("PRAGMA synchronous=NORMAL;")

        # Load and split migrations into individual statements
        sql = Path("app/utils/sql/migrations.sql").read_text(encoding="utf-8")

        # naive split on ';' is fine for our simple DDL (no triggers/procs)
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        for stmt in statements:
            conn.exec_driver_sql(stmt)
