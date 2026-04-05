from __future__ import annotations

from pathlib import Path

import click
from flask import current_app

from .backup import export_snapshot_to_file, import_snapshot_from_file
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

    @app.cli.command("export-data")
    @click.option("--output", required=True, type=click.Path(dir_okay=False, path_type=Path))
    def export_data_command(output: Path) -> None:
        stats = export_snapshot_to_file(output)
        click.echo(
            f"Exported {stats.movies} movies and {stats.reviews} reviews to {output}"
        )

    @app.cli.command("import-data")
    @click.option("--input", "input_path", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option(
        "--replace/--merge",
        default=True,
        help="Replace current rows before import, or merge into the current database.",
    )
    def import_data_command(input_path: Path, replace: bool) -> None:
        stats = import_snapshot_from_file(input_path, replace=replace)
        click.echo(
            "Imported {movies} movies and {reviews} reviews from {path} ({mode})".format(
                movies=stats.movies,
                reviews=stats.reviews,
                path=input_path,
                mode="replace" if replace else "merge",
            )
        )
