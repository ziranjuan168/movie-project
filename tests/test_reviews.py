import unittest

from app import create_app
from app.extensions import db
from app.models import Movie
from app.services import get_movie_detail, upsert_review


class ReviewServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "AUTO_SYNC_ENABLED": False,
            }
        )

    def test_upsert_review_updates_existing_row(self):
        with self.app.app_context():
            movie = Movie(
                douban_subject_id="1",
                title="测试电影",
                douban_url="https://example.com",
                poster_url=None,
                source_city="beijing",
            )
            db.session.add(movie)
            db.session.commit()

            review, created = upsert_review(movie, "token-1", "阿青", 8, "第一条评论内容")
            self.assertTrue(created)
            self.assertEqual(review.rating, 8)

            review, created = upsert_review(movie, "token-1", "阿青", 9, "更新后的评论内容")
            self.assertFalse(created)
            self.assertEqual(review.rating, 9)

            detail = get_movie_detail(subject_id="1", reviewer_token="token-1")
            self.assertEqual(detail["community_score"], 9.0)
            self.assertEqual(detail["review_count"], 1)
            self.assertEqual(detail["existing_review"].content, "更新后的评论内容")


if __name__ == "__main__":
    unittest.main()
