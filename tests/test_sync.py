import unittest
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import Movie
from app.scraper import ScrapedMovie
from app.services import ensure_fresh_movies, latest_sync_at, utc_now


class SyncServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "AUTO_SYNC_ENABLED": False,
            }
        )

    def test_ensure_fresh_movies_syncs_when_empty(self):
        with self.app.app_context():
            with patch(
                "app.services.DoubanNowPlayingScraper.fetch",
                return_value=[
                    ScrapedMovie(
                        subject_id="42",
                        title="新电影",
                        douban_url="https://movie.douban.com/subject/42/",
                        poster_url=None,
                        douban_score=7.8,
                        douban_star=40,
                        douban_vote_count=1234,
                        release_year="2026",
                        duration="120分钟",
                        region="中国大陆",
                        director="导演甲",
                        actors="演员甲 / 演员乙",
                        source_city="beijing",
                    )
                ],
            ):
                result = ensure_fresh_movies(city="beijing", max_age_hours=6)

            self.assertIsNotNone(result)
            self.assertEqual(result.fetched, 1)
            self.assertEqual(db.session.query(Movie).count(), 1)
            self.assertIsNotNone(latest_sync_at(city="beijing"))

    def test_ensure_fresh_movies_skips_recent_data(self):
        with self.app.app_context():
            db.session.add(
                Movie(
                    douban_subject_id="1",
                    title="现有电影",
                    douban_url="https://movie.douban.com/subject/1/",
                    poster_url=None,
                    source_city="beijing",
                    is_now_playing=True,
                    last_synced_at=utc_now(),
                )
            )
            db.session.commit()

            with patch("app.services.DoubanNowPlayingScraper.fetch") as fetch:
                result = ensure_fresh_movies(city="beijing", max_age_hours=6)

            self.assertIsNone(result)
            fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
