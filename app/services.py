from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, or_, select

from .extensions import db
from .models import Movie, Review
from .scraper import DoubanNowPlayingScraper


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass(slots=True)
class SyncResult:
    fetched: int
    created: int
    refreshed: int
    deactivated: int
    synced_at: datetime


@dataclass(slots=True)
class MovieCard:
    movie: Movie
    community_score: float | None
    review_count: int


def review_metrics_subquery():
    return (
        db.session.query(
            Review.movie_id.label("movie_id"),
            func.round(func.avg(Review.rating), 1).label("community_score"),
            func.count(Review.id).label("review_count"),
        )
        .group_by(Review.movie_id)
        .subquery()
    )


def list_now_playing(search: str = "", sort: str = "douban", city: str = "beijing") -> list[MovieCard]:
    metrics = review_metrics_subquery()
    query = (
        db.session.query(
            Movie,
            metrics.c.community_score,
            func.coalesce(metrics.c.review_count, 0).label("review_count"),
        )
        .outerjoin(metrics, metrics.c.movie_id == Movie.id)
        .filter(Movie.is_now_playing.is_(True), Movie.source_city == city)
    )

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Movie.title.ilike(like),
                Movie.director.ilike(like),
                Movie.actors.ilike(like),
                Movie.region.ilike(like),
            )
        )

    if sort == "community":
        query = query.order_by(
            func.coalesce(metrics.c.community_score, 0).desc(),
            func.coalesce(metrics.c.review_count, 0).desc(),
            func.coalesce(Movie.douban_score, 0).desc(),
        )
    elif sort == "comments":
        query = query.order_by(
            func.coalesce(metrics.c.review_count, 0).desc(),
            func.coalesce(metrics.c.community_score, 0).desc(),
            func.coalesce(Movie.douban_score, 0).desc(),
        )
    elif sort == "title":
        query = query.order_by(Movie.title.asc())
    else:
        query = query.order_by(
            func.coalesce(Movie.douban_score, 0).desc(),
            Movie.douban_vote_count.desc(),
            Movie.title.asc(),
        )

    return [
        MovieCard(
            movie=movie,
            community_score=float(community_score) if community_score is not None else None,
            review_count=int(review_count or 0),
        )
        for movie, community_score, review_count in query.all()
    ]


def get_movie_by_subject(subject_id: str) -> Movie | None:
    return db.session.scalar(select(Movie).where(Movie.douban_subject_id == subject_id))


def get_movie_detail(subject_id: str, reviewer_token: str | None = None):
    movie = get_movie_by_subject(subject_id)
    if movie is None:
        return None

    community_score, review_count = db.session.query(
        func.round(func.avg(Review.rating), 1),
        func.count(Review.id),
    ).filter(Review.movie_id == movie.id).one()

    reviews = db.session.scalars(
        select(Review).where(Review.movie_id == movie.id).order_by(Review.updated_at.desc())
    ).all()

    existing_review = None
    if reviewer_token:
        existing_review = db.session.scalar(
            select(Review).where(
                Review.movie_id == movie.id,
                Review.reviewer_token == reviewer_token,
            )
        )

    return {
        "movie": movie,
        "community_score": float(community_score) if community_score is not None else None,
        "review_count": int(review_count or 0),
        "reviews": reviews,
        "existing_review": existing_review,
    }


def homepage_stats(city: str = "beijing") -> dict[str, int | float | datetime | None]:
    total_movies = db.session.scalar(
        select(func.count(Movie.id)).where(Movie.is_now_playing.is_(True), Movie.source_city == city)
    ) or 0
    total_reviews = db.session.scalar(select(func.count(Review.id))) or 0
    avg_douban = db.session.scalar(
        select(func.round(func.avg(Movie.douban_score), 1)).where(
            Movie.is_now_playing.is_(True),
            Movie.source_city == city,
            Movie.douban_score.isnot(None),
        )
    )
    last_sync = db.session.scalar(
        select(func.max(Movie.last_synced_at)).where(
            Movie.is_now_playing.is_(True), Movie.source_city == city
        )
    )

    return {
        "total_movies": int(total_movies),
        "total_reviews": int(total_reviews),
        "avg_douban": float(avg_douban) if avg_douban is not None else None,
        "last_sync": last_sync,
    }


def sync_now_playing(city: str = "beijing") -> SyncResult:
    scraper = DoubanNowPlayingScraper(city=city)
    scraped_movies = scraper.fetch()
    if not scraped_movies:
        raise RuntimeError("同步结果为空，已放弃更新数据库。")

    scraped_ids = {item.subject_id for item in scraped_movies}
    synced_at = utc_now()
    created = 0
    refreshed = 0

    for item in scraped_movies:
        movie = get_movie_by_subject(item.subject_id)
        if movie is None:
            movie = Movie(douban_subject_id=item.subject_id)
            db.session.add(movie)
            created += 1
        else:
            refreshed += 1

        movie.title = item.title
        movie.douban_url = item.douban_url or f"https://movie.douban.com/subject/{item.subject_id}/"
        movie.poster_url = item.poster_url
        movie.douban_score = item.douban_score
        movie.douban_star = item.douban_star
        movie.douban_vote_count = item.douban_vote_count
        movie.release_year = item.release_year
        movie.duration = item.duration
        movie.region = item.region
        movie.director = item.director
        movie.actors = item.actors
        movie.source_city = item.source_city
        movie.is_now_playing = True
        movie.last_synced_at = synced_at

    deactivated = 0
    stale_movies = db.session.scalars(
        select(Movie).where(
            Movie.source_city == city,
            Movie.is_now_playing.is_(True),
            Movie.douban_subject_id.notin_(scraped_ids),
        )
    ).all()
    for movie in stale_movies:
        movie.is_now_playing = False
        deactivated += 1

    db.session.commit()
    return SyncResult(
        fetched=len(scraped_movies),
        created=created,
        refreshed=refreshed,
        deactivated=deactivated,
        synced_at=synced_at,
    )


def upsert_review(
    movie: Movie,
    reviewer_token: str,
    reviewer_name: str,
    rating: int,
    content: str,
) -> tuple[Review, bool]:
    review = db.session.scalar(
        select(Review).where(
            Review.movie_id == movie.id,
            Review.reviewer_token == reviewer_token,
        )
    )
    created = review is None
    if review is None:
        review = Review(movie=movie, reviewer_token=reviewer_token)
        db.session.add(review)

    review.reviewer_name = reviewer_name
    review.rating = rating
    review.content = content
    db.session.commit()
    return review, created
