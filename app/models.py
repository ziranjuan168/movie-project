from __future__ import annotations

from datetime import UTC, datetime

from .extensions import db


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Movie(db.Model):
    __tablename__ = "movies"

    id = db.Column(db.Integer, primary_key=True)
    douban_subject_id = db.Column(db.String(32), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    douban_url = db.Column(db.String(512), nullable=False)
    poster_url = db.Column(db.String(512), nullable=True)
    douban_score = db.Column(db.Float, nullable=True)
    douban_star = db.Column(db.Integer, nullable=True)
    douban_vote_count = db.Column(db.Integer, nullable=False, default=0)
    release_year = db.Column(db.String(16), nullable=True)
    duration = db.Column(db.String(64), nullable=True)
    region = db.Column(db.String(128), nullable=True)
    director = db.Column(db.String(255), nullable=True)
    actors = db.Column(db.Text, nullable=True)
    source_city = db.Column(db.String(64), nullable=False, default="beijing")
    is_now_playing = db.Column(db.Boolean, nullable=False, default=True, index=True)
    last_synced_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    reviews = db.relationship(
        "Review",
        back_populates="movie",
        cascade="all, delete-orphan",
        order_by="desc(Review.updated_at)",
    )


class Review(db.Model):
    __tablename__ = "reviews"
    __table_args__ = (
        db.UniqueConstraint("movie_id", "reviewer_token", name="uq_review_movie_reviewer"),
    )

    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"), nullable=False, index=True)
    reviewer_token = db.Column(db.String(64), nullable=False, index=True)
    reviewer_name = db.Column(db.String(40), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    movie = db.relationship("Movie", back_populates="reviews")
