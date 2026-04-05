from __future__ import annotations

import click
from flask import current_app

from .extensions import db
from .services import sync_now_playing


def register_commands(app) -> None:
    @app.cli.command("init-db")
    def init_db_command() -> None:
        db.create_all()
        click.echo("Database initialized.")

    @app.cli.command("sync-movies")
    @click.option("--city", default=None, help="Douban city slug, defaults to app config.")
    def sync_movies_command(city: str | None) -> None:
        result = sync_now_playing(city=city or current_app.config["DOUBAN_CITY"])
        click.echo(
            "Synced {fetched} movies (created {created}, refreshed {refreshed}, deactivated {deactivated})".format(
                fetched=result.fetched,
                created=result.created,
                refreshed=result.refreshed,
                deactivated=result.deactivated,
            )
        )

