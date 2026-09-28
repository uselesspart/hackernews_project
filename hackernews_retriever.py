import requests

API_BASE = "https://hacker-news.firebaseio.com/v0/"


class HNRetriever:
    """Тонкий клиент HN Firebase API. session — requests.Session (или совместимый объект)."""

    def __init__(self, url_base: str = API_BASE, timeout: float = 10):
        self.url_base = url_base
        self.timeout = timeout

    def _get(self, path: str, session=None):
        resp = (session or requests).get(f"{self.url_base}{path}", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def retrieve_item(self, item_id, session=None):
        return self._get(f"item/{item_id}.json", session)

    def get_maxitem_id(self, session=None) -> int:
        return self._get("maxitem.json", session)

    def retrieve_best_stories(self, session=None) -> list[int]:
        return self._get("beststories.json", session)
