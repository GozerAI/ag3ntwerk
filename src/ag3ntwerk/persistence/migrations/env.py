"""
Alembic migration environment for ag3ntwerk.

Supports both SQLite and PostgreSQL backends.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from ag3ntwerk.persistence.database import DatabaseConfig

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# No MetaData object since we use raw SQL migrations
target_metadata = None


def get_url() -> str:
    """Get database URL from alembic config, falling back to environment."""
    # Prefer the URL set programmatically via alembic_cfg.set_main_option()
    url = config.get_main_option("sqlalchemy.url")
    if url:
        return url
    db_config = DatabaseConfig.from_env()
    return db_config.connection_string


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    Calls to context.execute() emit SQL to the script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Creates an Engine and associates a connection with the context.
    """
    from sqlalchemy import create_engine, pool

    url = get_url()

    # Use NullPool for SQLite to avoid locking issues
    if url.startswith("sqlite"):
        connectable = create_engine(
            url,
            poolclass=pool.NullPool,
        )
    else:
        connectable = create_engine(
            url,
            poolclass=pool.QueuePool,
            pool_size=5,
            max_overflow=10,
        )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
