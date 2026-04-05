from __future__ import annotations

import secrets
from pathlib import Path
from urllib.parse import urlparse

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
import requests

from .scraper import USER_AGENT
from .services import (
    ensure_fresh_movies,
    get_movie_by_subject,
    get_movie_detail,
    homepage_stats,
    list_now_playing,
    upsert_review,
)


bp = Blueprint("main", __name__)

COOKIE_NAME = "movie_reviewer"


def city_label(city: str) -> str:
    return {
        "beijing": "北京",
        "shanghai": "上海",
        "guangzhou": "广州",
        "shenzhen": "深圳",
    }.get(city, city)


def poster_cache_path(movie) -> Path | None:
    if not movie.poster_url:
        return None
    suffix = Path(urlparse(movie.poster_url).path).suffix or ".jpg"
    cache_dir = Path(current_app.instance_path) / "posters"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{movie.douban_subject_id}{suffix}"


def cache_poster(movie) -> Path | None:
    cache_path = poster_cache_path(movie)
    if cache_path is None:
        return None

    if not cache_path.exists():
        response = requests.get(
            movie.poster_url,
            headers={
                "User-Agent": USER_AGENT,
                "Referer": "https://movie.douban.com/",
            },
            timeout=30,
        )
        response.raise_for_status()
        cache_path.write_bytes(response.content)

    return cache_path


@bp.route("/")
def home():
    search = request.args.get("q", "").strip()
    sort = request.args.get("sort", "douban").strip() or "douban"
    city = current_app.config["DOUBAN_CITY"]

    try:
        ensure_fresh_movies(city=city, max_age_hours=current_app.config["SYNC_INTERVAL_HOURS"])
    except Exception as exc:  # pragma: no cover - logs only
        current_app.logger.exception("request sync failed: %s", exc)

    movies = list_now_playing(search=search, sort=sort, city=city)
    stats = homepage_stats(city=city)
    featured = movies[0] if movies else None

    return render_template(
        "index.html",
        brand_name=current_app.config["BRAND_NAME"],
        movies=movies,
        featured=featured,
        stats=stats,
        search=search,
        sort=sort,
        city=city,
        city_label=city_label(city),
        sort_options={
            "douban": "按豆瓣分数",
            "community": "按站内分数",
            "comments": "按评论热度",
            "title": "按片名",
        },
    )


@bp.route("/movies/<subject_id>")
def movie_detail(subject_id: str):
    city = current_app.config["DOUBAN_CITY"]
    try:
        ensure_fresh_movies(city=city, max_age_hours=current_app.config["SYNC_INTERVAL_HOURS"])
    except Exception as exc:  # pragma: no cover - logs only
        current_app.logger.exception("request sync failed: %s", exc)

    reviewer_token = request.cookies.get(COOKIE_NAME)
    detail = get_movie_detail(subject_id=subject_id, reviewer_token=reviewer_token)
    if detail is None:
        abort(404)

    return render_template(
        "movie_detail.html",
        brand_name=current_app.config["BRAND_NAME"],
        city=city,
        city_label=city_label(city),
        **detail,
    )


@bp.route("/movies/<subject_id>/reviews", methods=["POST"])
def submit_review(subject_id: str):
    detail = get_movie_detail(subject_id=subject_id, reviewer_token=request.cookies.get(COOKIE_NAME))
    if detail is None:
        abort(404)

    movie = detail["movie"]
    reviewer_name = request.form.get("reviewer_name", "").strip()
    content = request.form.get("content", "").strip()
    honeypot = request.form.get("website", "").strip()
    rating_value = request.form.get("rating", "").strip()
    reviewer_token = request.cookies.get(COOKIE_NAME) or secrets.token_hex(24)

    if honeypot:
        flash("提交失败。", "error")
        return redirect(url_for("main.movie_detail", subject_id=subject_id, _anchor="reviews"))

    if len(reviewer_name) < 2 or len(reviewer_name) > 24:
        flash("昵称需要在 2 到 24 个字符之间。", "error")
        return redirect(url_for("main.movie_detail", subject_id=subject_id, _anchor="review-form"))

    if len(content) < 8 or len(content) > 800:
        flash("评论需要在 8 到 800 个字符之间。", "error")
        return redirect(url_for("main.movie_detail", subject_id=subject_id, _anchor="review-form"))

    try:
        rating = int(rating_value)
    except ValueError:
        flash("评分必须是 1 到 10 的整数。", "error")
        return redirect(url_for("main.movie_detail", subject_id=subject_id, _anchor="review-form"))

    if rating < 1 or rating > 10:
        flash("评分必须是 1 到 10 的整数。", "error")
        return redirect(url_for("main.movie_detail", subject_id=subject_id, _anchor="review-form"))

    _, created = upsert_review(
        movie=movie,
        reviewer_token=reviewer_token,
        reviewer_name=reviewer_name,
        rating=rating,
        content=content,
    )

    response = make_response(
        redirect(url_for("main.movie_detail", subject_id=subject_id, _anchor="reviews"))
    )
    response.set_cookie(
        COOKIE_NAME,
        reviewer_token,
        max_age=60 * 60 * 24 * 365 * 3,
        samesite="Lax",
    )
    flash("评论已发布。" if created else "你的评论已更新。", "success")
    return response


@bp.route("/health")
def health():
    stats = homepage_stats(city=current_app.config["DOUBAN_CITY"])
    return jsonify(
        {
            "status": "ok",
            "brand": current_app.config["BRAND_NAME"],
            "city": current_app.config["DOUBAN_CITY"],
            "movies": stats["total_movies"],
            "reviews": stats["total_reviews"],
        }
    )


@bp.route("/posters/<subject_id>")
def poster(subject_id: str):
    movie = get_movie_by_subject(subject_id)
    if movie is None or not movie.poster_url:
        abort(404)

    try:
        cache_path = cache_poster(movie)
    except requests.RequestException:
        return redirect(movie.poster_url)

    if cache_path is None:
        abort(404)

    return send_file(cache_path, max_age=60 * 60 * 24)


@bp.app_template_global("poster_src")
def poster_src(movie):
    if not movie.poster_url:
        return None
    return url_for("main.poster", subject_id=movie.douban_subject_id)


@bp.app_template_filter("datetime_cn")
def datetime_cn(value):
    if value is None:
        return "尚未同步"
    return value.strftime("%Y-%m-%d %H:%M")
