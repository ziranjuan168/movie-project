import unittest

from app.scraper import DoubanNowPlayingScraper


SAMPLE_HTML = """
<div id="nowplaying">
  <div class="mod-bd">
    <ul class="lists">
      <li
        id="35010610"
        class="list-item"
        data-title="挽救计划"
        data-score="8.5"
        data-star="45"
        data-release="2026"
        data-duration="156分钟"
        data-region="美国"
        data-director="菲尔·罗德 克里斯托弗·米勒"
        data-actors="瑞恩·高斯林 / 桑德拉·惠勒"
        data-category="nowplaying"
        data-enough="True"
        data-showed="True"
        data-votecount="254588"
        data-subject="35010610"
      >
        <ul class="">
          <li class="poster">
            <a href="https://movie.douban.com/subject/35010610/?from=playing_poster">
              <img src="https://img9.doubanio.com/view/photo/s_ratio_poster/public/p2930195706.jpg" />
            </a>
          </li>
        </ul>
      </li>
    </ul>
  </div>
</div>
"""


class ScraperTestCase(unittest.TestCase):
    def test_parse_now_playing_html(self):
        scraper = DoubanNowPlayingScraper(city="beijing")
        movies = list(scraper.parse(SAMPLE_HTML))

        self.assertEqual(len(movies), 1)
        movie = movies[0]
        self.assertEqual(movie.subject_id, "35010610")
        self.assertEqual(movie.title, "挽救计划")
        self.assertEqual(movie.douban_score, 8.5)
        self.assertEqual(movie.douban_vote_count, 254588)
        self.assertTrue(movie.poster_url.endswith(".jpg"))


if __name__ == "__main__":
    unittest.main()
