"""SQLite bağlantısı, Alembic migration'ları ve oturum başlangıcı."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing
from datetime import UTC, date, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import URL, Engine, create_engine, event, inspect, select, update
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from kelebek.config import get_data_dir, get_database_path

logger = logging.getLogger("kelebek.database")
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
ACADEMIC_YEAR_START_MONTH = 9


class Base(DeclarativeBase):
    """Tüm SQLAlchemy modellerinin ortak tabanı."""


def _migration_config(engine: Engine):
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    database_url = engine.url.render_as_string(hide_password=False)
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def _backup_database(db_path: Path) -> Path:
    """Migration öncesinde SQLite'ın tutarlı bir kopyasını al."""
    backup_dir = get_data_dir() / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_dir / f"pre-migration-{timestamp}.sqlite3"

    # Bağlantılar açıkça kapatılır; `with sqlite3.connect(...)` yalnızca işlemi
    # tamamlar, dosyayı serbest bırakmaz ve Windows'ta kilit bırakır.
    with closing(sqlite3.connect(db_path)) as source, closing(sqlite3.connect(backup_path)) as destination:
        source.backup(destination)

    logger.info("Migration öncesi yerel veritabanı yedeği oluşturuldu.")
    return backup_path


def _upgrade_schema(engine: Engine, db_path: Path, database_existed: bool) -> None:
    config = _migration_config(engine)
    script = ScriptDirectory.from_config(config)
    head_revision = script.get_current_head()

    with engine.connect() as connection:
        current_revision = MigrationContext.configure(connection).get_current_revision()
        if database_existed and db_path.stat().st_size > 0 and current_revision != head_revision:
            _backup_database(db_path)

        # Release SQLAlchemy's implicit read transaction before Alembic starts.
        # SQLite may persist DDL while rolling back the revision row on close.
        connection.commit()
        config.attributes["connection"] = connection

        # Recover the initial schema created by older startup code that left
        # academic_years in place but did not persist its Alembic revision.
        if current_revision is None:
            inspector = inspect(connection)
            table_names = set(inspector.get_table_names())
            if "academic_years" in table_names:
                expected_tables = {"academic_years", "alembic_version"}
                expected_columns = {
                    "id", "start_year", "end_year", "is_selected", "created_at"
                }
                actual_columns = {
                    column["name"] for column in inspector.get_columns("academic_years")
                }
                if table_names != expected_tables or actual_columns != expected_columns:
                    raise RuntimeError(
                        "Migration kaydı olmayan veritabanı beklenen başlangıç şemasıyla eşleşmiyor."
                    )
                command.stamp(config, "0001_academic_years")
                connection.commit()

        command.upgrade(config, "head")
        connection.commit()


def current_academic_year_start(today: date | None = None) -> int:
    """Eylül ayında başlayan eğitim-öğretim yılının başlangıç yılını hesapla."""
    today = today or date.today()
    return today.year if today.month >= ACADEMIC_YEAR_START_MONTH else today.year - 1


def _ensure_current_academic_year(session_factory: sessionmaker[Session]) -> None:
    """Güncel yılı oluştur ve uygulama açılışında varsayılan olarak seç."""
    from kelebek.models import AcademicYear

    start_year = current_academic_year_start()
    with session_factory.begin() as session:
        year = session.scalar(
            select(AcademicYear).where(AcademicYear.start_year == start_year)
        )
        if year is None:
            year = AcademicYear(start_year=start_year, end_year=start_year + 1)
            session.add(year)
            session.flush()

        session.execute(update(AcademicYear).values(is_selected=False))
        year.is_selected = True


def initialize_database(app) -> None:
    """Uygulama veritabanını hazırla ve migration'ları güvenli biçimde uygula."""
    from kelebek import models  # noqa: F401 — modelleri Base.metadata içine alır

    db_path = get_database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    database_existed = db_path.exists() and db_path.stat().st_size > 0

    database_url = URL.create("sqlite", database=str(db_path))
    engine = create_engine(database_url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(connection, _record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    _upgrade_schema(engine, db_path, database_existed)

    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    _ensure_current_academic_year(session_factory)

    app.extensions["kelebek_engine"] = engine
    app.extensions["kelebek_session_factory"] = session_factory
