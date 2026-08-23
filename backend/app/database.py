from sqlalchemy import inspect
from sqlmodel import Session, SQLModel, create_engine

from .settings import get_settings

settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)


def get_session():
    with Session(engine) as session:
        yield session


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
    # Lightweight upgrade path for shopping databases created before user accounts.
    if not settings.database_url.startswith("sqlite"):
        return
    inspector = inspect(engine)
    for table_name in ("shoppingitem", "historyevent"):
        if table_name in inspector.get_table_names():
            columns = {column["name"] for column in inspector.get_columns(table_name)}
            if "user_id" not in columns:
                with engine.begin() as connection:
                    connection.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN user_id INTEGER")
