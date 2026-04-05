from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Iterable

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
)


@dataclass(slots=True)
class ScrapedMovie:
    subject_id: str
    title: str
    douban_url: str
    poster_url: str | None
    douban_score: float | None
    douban_star: int | None
    douban_vote_count: int
    release_year: str | None
    duration: str | None
    region: str | None
    director: str | None
    actors: str | None
    source_city: str


class DoubanNowPlayingScraper:
    def __init__(self, city: str = "beijing") -> None:
        self.city = city

    @property
    def url(self) -> str:
        return f"https://movie.douban.com/cinema/nowplaying/{self.city}/"

    def fetch(self) -> list[ScrapedMovie]:
        html = self._fetch_html()
        movies = list(self.parse(html))
        if not movies:
            raise RuntimeError("豆瓣热映页面已返回，但未解析到任何电影。")
        return movies

    def _fetch_html(self) -> str:
        curl_html = self._fetch_with_curl()
        if curl_html:
            return curl_html
        return self._fetch_with_requests()

    def _fetch_with_curl(self) -> str | None:
        try:
            result = subprocess.run(
                [
                    "curl",
                    "-sSL",
                    "--max-time",
                    "30",
                    "-A",
                    USER_AGENT,
                    self.url,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout
        except (FileNotFoundError, subprocess.CalledProcessError):
            return None

    def _fetch_with_requests(self) -> str:
        session = requests.Session()
        retry = Retry(
            total=4,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset({"GET"}),
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        response = session.get(self.url, headers={"User-Agent": USER_AGENT}, timeout=30)
        response.raise_for_status()
        return response.text

    def parse(self, html: str) -> Iterable[ScrapedMovie]:
        soup = BeautifulSoup(html, "html.parser")
        items = soup.select("#nowplaying li.list-item")
        for item in items:
            title = (item.get("data-title") or "").strip()
            subject_id = (item.get("data-subject") or item.get("id") or "").strip()
            if not title or not subject_id:
                continue

            enough = (item.get("data-enough") or "").lower() == "true"
            score = self._parse_float(item.get("data-score"))
            if not enough and (score is None or score == 0):
                score = None

            poster = item.select_one(".poster img")
            link = item.select_one(".poster a") or item.select_one(".stitle a")

            yield ScrapedMovie(
                subject_id=subject_id,
                title=title,
                douban_url=(link.get("href") if link else "").strip(),
                poster_url=(poster.get("src") if poster else None),
                douban_score=score,
                douban_star=self._parse_int(item.get("data-star")),
                douban_vote_count=self._parse_int(item.get("data-votecount")) or 0,
                release_year=(item.get("data-release") or "").strip() or None,
                duration=(item.get("data-duration") or "").strip() or None,
                region=(item.get("data-region") or "").strip() or None,
                director=(item.get("data-director") or "").strip() or None,
                actors=(item.get("data-actors") or "").strip() or None,
                source_city=self.city,
            )

    @staticmethod
    def _parse_float(value: str | None) -> float | None:
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    @staticmethod
    def _parse_int(value: str | None) -> int | None:
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None

