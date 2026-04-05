import json
import tempfile
import unittest
from pathlib import Path

from app import create_app
from app.backup import build_snapshot, restore_snapshot
from app.extensions import db
from app.models import Movie, Review


class BackupTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "AUTO_SYNC_ENABLED": False,
            }
        )

    def seed_data(self):
        movie = Movie(
            douban_subject_id="42",
            title="迁移测试片",
            douban_url="https://movie.douban.com/subject/42/",
            poster_url="https://example.com/poster.jpg",
            douban_score=8.3,
            douban_star=45,
            douban_vote_count=888,
            release_year="2026",
            duration="120分钟",
            region="中国大陆",
            director="导演甲",
            actors="演员甲 / 演员乙",
            source_city="beijing",
            is_now_playing=True,
        )
        db.session.add(movie)
        db.session.flush()

        review = Review(
            movie_id=movie.id,
            reviewer_token="token-1",
            reviewer_name="阿青",
            rating=9,
            content="一部值得迁移验证的电影。",
        )
        db.session.add(review)
        db.session.commit()

    def test_snapshot_round_trip_replace(self):
        with self.app.app_context():
            self.seed_data()
            snapshot = build_snapshot()

            db.session.query(Review).delete()
            db.session.query(Movie).delete()
            db.session.commit()

            stats = restore_snapshot(snapshot, replace=True)

            movie = db.session.query(Movie).one()
            review = db.session.query(Review).one()
            self.assertEqual(stats.movies, 1)
            self.assertEqual(stats.reviews, 1)
            self.assertEqual(movie.title, "迁移测试片")
            self.assertEqual(review.rating, 9)
            self.assertEqual(review.movie_id, movie.id)

    def test_import_command_replaces_database(self):
        with self.app.app_context():
            self.seed_data()
            runner = self.app.test_cli_runner()

            with tempfile.TemporaryDirectory() as tempdir:
                backup_path = Path(tempdir) / "snapshot.json"
                export_result = runner.invoke(
                    args=["export-data", "--output", str(backup_path)]
                )
                self.assertEqual(export_result.exit_code, 0, export_result.output)

                db.session.query(Review).delete()
                db.session.query(Movie).delete()
                db.session.commit()

                import_result = runner.invoke(
                    args=["import-data", "--input", str(backup_path), "--replace"]
                )
                self.assertEqual(import_result.exit_code, 0, import_result.output)

                snapshot = json.loads(backup_path.read_text(encoding="utf-8"))
                self.assertEqual(snapshot["schema_version"], 1)
                self.assertEqual(db.session.query(Movie).count(), 1)
                self.assertEqual(db.session.query(Review).count(), 1)

    def test_merge_updates_existing_rows(self):
        with self.app.app_context():
            self.seed_data()
            snapshot = build_snapshot()
            movie_payload = snapshot["movies"][0]
            movie_payload["title"] = "迁移后的片名"
            movie_payload["reviews"][0]["rating"] = 7
            movie_payload["reviews"][0]["content"] = "合并导入后已更新。"

            stats = restore_snapshot(snapshot, replace=False)

            movie = db.session.query(Movie).one()
            review = db.session.query(Review).one()
            self.assertEqual(stats.movies, 1)
            self.assertEqual(stats.reviews, 1)
            self.assertEqual(movie.title, "迁移后的片名")
            self.assertEqual(review.rating, 7)
            self.assertEqual(review.content, "合并导入后已更新。")


if __name__ == "__main__":
    unittest.main()
