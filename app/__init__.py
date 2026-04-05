from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from flask import Flask

from .cli import register_commands
from .extensions import db
from .routes import bp
from .scheduler import start_scheduler


def normalize_database_url(uri: str) -> str:
    parsed = urlparse(uri)
    if parsed.scheme == "postgres":
        return urlunparse(parsed._replace(scheme="postgresql+psycopg"))
    if parsed.scheme == "postgresql":
        return urlunparse(parsed._replace(scheme="postgresql+psycopg"))
    return uri


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    default_db_path = Path(app.instance_path) / "movie.db"
    database_url = normalize_database_url(
        os.getenv("DATABASE_URL", f"sqlite:///{default_db_path}")
    )

    app.config.from_mapping(
        BRAND_NAME="映准",
        SECRET_KEY=os.getenv("SECRET_KEY", "local-dev-secret"),
        SQLALCHEMY_DATABASE_URI=database_url,
        DOUBAN_CITY=os.getenv("DOUBAN_CITY", "beijing"),
        AUTO_SYNC_ENABLED=os.getenv("AUTO_SYNC_ENABLED", "true").lower() in {"1", "true", "yes"},
        SYNC_INTERVAL_HOURS=int(os.getenv("SYNC_INTERVAL_HOURS", "6")),
        SCHEDULER_TIMEZONE=os.getenv("SCHEDULER_TIMEZONE", "Asia/Shanghai"),
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    app.register_blueprint(bp)
    register_commands(app)

    with app.app_context():
        db.create_all()

    if not app.config.get("TESTING") and os.getenv("FLASK_RUN_FROM_CLI") != "true":
        start_scheduler(app)

    return app
