# search.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import json

# crawler.py と同じ設定とクライアントクラスをインポート
from config import pukiwiki as config
from els.client import ElsClient

# --- Flaskアプリケーションの初期化 ---
app = Flask(__name__)
# CORS(Cross-Origin Resource Sharing)を有効にする
# これにより、別ドメインで動作するフロントエンドJSからAPIを呼び出せるようになります
CORS(app) 

# --- Elasticsearchクライアントの初期化 ---
try:
    client = ElsClient(config.ELASTIC_SEARCH_ENDPOINT, config.INDEX)
    # 接続テスト
    client.get_index() 
    print("Successfully connected to Elasticsearch.")
except Exception as e:
    print(f"Error: Failed to connect to Elasticsearch. {e}")
    client = None


# --- 検索APIのエンドポイント ---
@app.route('/search', methods=['GET'])
def search():
    """
    GET /search?q=<keyword>
    """
    if not client:
        return jsonify({"error": "Elasticsearch client is not available."}), 503 # Service Unavailable

    # クエリパラメータ 'q' から検索キーワードを取得
    keyword = request.args.get('q', '')
    if not keyword:
        return jsonify({"total": 0, "hits": [], "error": "Query parameter 'q' is required."}), 400 # Bad Request

    # Elasticsearchの検索クエリを構築
    # titleとbodyの両方を対象に検索し、結果をハイライトする
    query = {
        "query": {
            "multi_match": {
                "query": keyword,
                "fields": ["title", "body"],
                "operator": "and" # AND検索で、より関連性の高い結果を優先
            }
        },
        "highlight": {
            "fields": {
                "body": {
                    "fragment_size": 150,  # ハイライトする本文の断片（スニペット）の長さ
                    "number_of_fragments": 1 # 返すスニペットの数
                }
            },
            "pre_tags": ["<mark>"], # ハイライト箇所の前に挿入するタグ
            "post_tags": ["</mark>"] # ハイライト箇所の後に挿入するタグ
        },
        "_source": ["title", "title_url_encoded", "modified"], # 取得するフィールドを限定
        "size": 20 # 一度に返す結果の件数
    }

    try:
        # Elasticsearchに検索リクエストを送信
        response = client.search(json.dumps(query)).read().decode("utf-8")
        raw_results = json.loads(response)

        # フロントエンドで使いやすいように結果を整形
        hits = []
        if "hits" in raw_results and "hits" in raw_results["hits"]:
            for hit in raw_results["hits"]["hits"]:
                source = hit.get("_source", {})
                highlight = hit.get("highlight", {}).get("body", [])
                
                # ハイライトされたスニペットを結合
                snippet = " ... ".join(highlight) if highlight else ""
                
                hits.append({
                    "id": hit.get("_id"),
                    "title": source.get("title"),
                    "url_title": source.get("title_url_encoded"), # PukiWikiのURL用
                    "modified": source.get("modified"),
                    "snippet": snippet # 検索キーワードがハイライトされた本文の一部
                })

        formatted_results = {
            "total": raw_results.get("hits", {}).get("total", {}).get("value", 0),
            "hits": hits
        }
        
        return jsonify(formatted_results)

    except Exception as e:
        print(f"An error occurred during search: {e}")
        return jsonify({"error": "An internal error occurred."}), 500


# --- サーバーの起動 ---
if __name__ == '__main__':
    # 開発用のサーバーを起動します。
    # 本番環境ではGunicornなどのWSGIサーバーを使用することを推奨します。
    app.run(host='0.0.0.0', port=5000, debug=True)