from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select, text

from .extensions import db
from .models import Movie, Review

SNAPSHOT_VERSION = 1

MOVIE_FIELDS = (
    "id",
    "douban_subject_id",
    "title",
    "douban_url",
    "poster_url",
    "douban_score",
    "douban_star",
    "douban_vote_count",
    "release_year",
    "duration",
    "region",
    "director",
    "actors",
    "source_city",
    "is_now_playing",
    "last_synced_at",
    "created_at",
    "updated_at",
)

REVIEW_FIELDS = (
    "id",
    "reviewer_token",
    "reviewer_name",
    "rating",
    "content",
    "created_at",
    "updated_at",
)


@dataclass(slots=True)
class SnapshotStats:
    movies: int
    reviews: int


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed
    return parsed.astimezone(UTC).replace(tzinfo=None)


def review_to_dict(review: Review) -> dict:
    payload = {field: getattr(review, field) for field in REVIEW_FIELDS}
    for key in ("created_at", "updated_at"):
        payload[key] = serialize_datetime(payload[key])
    return payload


def movie_to_dict(movie: Movie) -> dict:
    payload = {field: getattr(movie, field) for field in MOVIE_FIELDS}
    for key in ("last_synced_at", "created_at", "updated_at"):
        payload[key] = serialize_datetime(payload[key])
    payload["reviews"] = [review_to_dict(review) for review in sorted(movie.reviews, key=lambda item: item.id)]
    return payload


def build_snapshot() -> dict:
    movies = db.session.scalars(select(Movie).order_by(Movie.id.asc())).all()
    return {
        "schema_version": SNAPSHOT_VERSION,
        "exported_at": serialize_datetime(utc_now()),
        "movies": [movie_to_dict(movie) for movie in movies],
    }


def snapshot_stats(snapshot: dict) -> SnapshotStats:
    movies = snapshot.get("movies", [])
    return SnapshotStats(
        movies=len(movies),
        reviews=sum(len(movie.get("reviews", [])) for movie in movies),
    )


def export_snapshot_to_file(path: Path) -> SnapshotStats:
    snapshot = build_snapshot()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return snapshot_stats(snapshot)


def load_snapshot(path: Path) -> dict:
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    version = snapshot.get("schema_version")
    if version != SNAPSHOT_VERSION:
        raise RuntimeError(f"Unsupported snapshot version: {version}")
    return snapshot


def apply_movie_payload(movie: Movie, payload: dict) -> None:
    for field in MOVIE_FIELDS:
        if field == "id":
            continue
        value = payload.get(field)
        if field in {"last_synced_at", "created_at", "updated_at"}:
            value = parse_datetime(value)
        setattr(movie, field, value)


def apply_review_payload(review: Review, payload: dict) -> None:
    for field in REVIEW_FIELDS:
        if field == "id":
            continue
        value = payload.get(field)
        if field in {"created_at", "updated_at"}:
            value = parse_datetime(value)
        setattr(review, field, value)


def restore_snapshot(snapshot: dict, replace: bool = True) -> SnapshotStats:
    movies = snapshot.get("movies", [])

    if replace:
        db.session.query(Review).delete()
        db.session.query(Movie).delete()
        db.session.flush()
        _restore_with_replace(movies)
    else:
        _restore_with_merge(movies)

    db.session.commit()
    _reset_identity_sequences()
    db.session.commit()
    return snapshot_stats(snapshot)


def _restore_with_replace(movie_payloads: list[dict]) -> None:
    for payload in movie_payloads:
        movie = Movie(
            id=payload.get("id"),
            douban_subject_id=payload["douban_subject_id"],
        )
        apply_movie_payload(movie, payload)
        db.session.add(movie)
        db.session.flush()

        for review_payload in payload.get("reviews", []):
            review = Review(
                id=review_payload.get("id"),
                movie_id=movie.id,
                reviewer_token=review_payload["reviewer_token"],
            )
            apply_review_payload(review, review_payload)
            db.session.add(review)


def _restore_with_merge(movie_payloads: list[dict]) -> None:
    for payload in movie_payloads:
        movie = db.session.scalar(
            select(Movie).where(Movie.douban_subject_id == payload["douban_subject_id"])
        )
        if movie is None:
            movie = Movie(douban_subject_id=payload["douban_subject_id"])
            db.session.add(movie)
            db.session.flush()

        apply_movie_payload(movie, payload)
        db.session.flush()

        for review_payload in payload.get("reviews", []):
            review = db.session.scalar(
                select(Review).where(
                    Review.movie_id == movie.id,
                    Review.reviewer_token == review_payload["reviewer_token"],
                )
            )
            if review is None:
                review = Review(movie_id=movie.id, reviewer_token=review_payload["reviewer_token"])
                db.session.add(review)
            apply_review_payload(review, review_payload)


def _reset_identity_sequences() -> None:
    if db.engine is None or db.engine.dialect.name != "postgresql":
        return

    db.session.execute(
        text(
            """
            SELECT setval(
                pg_get_serial_sequence('movies', 'id'),
                COALESCE((SELECT MAX(id) FROM movies), 1),
                (SELECT COUNT(*) > 0 FROM movies)
            )
            """
        )
    )
    db.session.execute(
        text(
            """
            SELECT setval(
                pg_get_serial_sequence('reviews', 'id'),
                COALESCE((SELECT MAX(id) FROM reviews), 1),
                (SELECT COUNT(*) > 0 FROM reviews)
            )
            """
        )
    )


def import_snapshot_from_file(path: Path, replace: bool = True) -> SnapshotStats:
    snapshot = load_snapshot(path)
    return restore_snapshot(snapshot, replace=replace)
