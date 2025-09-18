# crawler/els/client.py
import urllib.request
from urllib.error import HTTPError

class ElsClient:
    """urllibを使ったシンプルなElasticsearchクライアント"""
    def __init__(self, endpoint, index_name):
        self.endpoint = endpoint
        self.index_name = index_name
        self.base_url = f"{self.endpoint}/{self.index_name}"

    def _request(self, method, path, data=None, ctype="application/json"):
        url = f"{self.endpoint}{path}"
        headers = {"Content-Type": ctype}
        
        body = data.encode('utf-8') if data else None
        
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        return urllib.request.urlopen(req)

    def get_index(self):
        return self._request("GET", f"/{self.index_name}")

    def add_index(self, settings_json):
        return self._request("PUT", f"/{self.index_name}", data=settings_json)

    def delete_index(self):
        try:
            return self._request("DELETE", f"/{self.index_name}")
        except HTTPError as e:
            # 存在しない場合も成功として扱う
            if e.code == 404:
                return e
            raise

    def search(self, query_json):
        return self._request("POST", f"/{self.index_name}/_search", data=query_json)

    def bulk(self, bulk_data):
        # Bulk APIはContent-Typeが異なる
        return self._request("POST", "/_bulk", data=bulk_data, ctype="application/x-ndjson")

    def delete_by_query(self, query_json):
        return self._request("POST", f"/{self.index_name}/_delete_by_query", data=query_json)
    