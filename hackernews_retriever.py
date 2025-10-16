import requests

class HNRetriever:

    url_base = ""

    def __init__(self):
        self.url_base = "https://hacker-news.firebaseio.com/v0/"

    def retrieve_item(self, item_id, session=None, timeout=10):
        url = f"{self.url_base}item/{item_id}.json"
        sess = session or requests
        resp = sess.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return data

    def get_maxitem_id(self):
        url = f"{self.url_base}maxitem.json?print=pretty"
        response = requests.get(url)
        return response.json()
    
    def retrieve_best_stories(self):
        url = f"{self.url_base}beststories.json?print=pretty"
        response = requests.get(url)
        return response.json()
    
retriever = HNRetriever()
max_item = retriever.get_maxitem_id()
