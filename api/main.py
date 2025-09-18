import re
from fastapi import FastAPI, HTTPException, Query
from elasticsearch import Elasticsearch
from contextlib import asynccontextmanager
import uvicorn
from typing import Optional

# --- 設定 ---
# ご自身の環境に合わせて変更してください
ELASTICSEARCH_HOSTS = ["http://localhost:9200"] 
INDEX_NAME = "pukiwiki"  # 検索対象のElasticsearchインデックス名

# --- グローバル変数 ---
es_client = None

# --- FastAPIのライフサイクル管理 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    アプリケーションの起動時と終了時に実行される処理を定義します。
    """
    # 起動時の処理
    global es_client
    try:
        # Elasticsearchに接続
        es_client = Elasticsearch(hosts=ELASTICSEARCH_HOSTS)
        if not es_client.ping():
            raise ConnectionError("Could not connect to Elasticsearch.")
        print("Successfully connected to Elasticsearch.")
    except Exception as e:
        print(f"Error connecting to Elasticsearch: {e}")
        # 接続に失敗した場合はNoneのままにしておく
        es_client = None
    
    yield
    
    # 終了時の処理
    if es_client:
        es_client.close()
        print("Elasticsearch connection closed.")

# FastAPIアプリケーションのインスタンスを作成
app = FastAPI(
    lifespan=lifespan,
    title="Wiki Search API",
    description="An API to search wiki pages from Elasticsearch.",
    version="1.0.0"
)

# --- ヘルパー関数 ---
def parse_wiki_body(body_text: str, keyword: str) -> list[str]:
    """
    与えられたwikiのbodyテキストから、キーワードにマッチする行のページタイトルを抽出します。
    
    Args:
        body_text (str): Elasticsearchから取得したbodyフィールドのテキスト。
        keyword (str): ユーザーが指定した検索キーワード。
    
    Returns:
        list[str]: 抽出されたページタイトルのリスト（重複なし）。
    """
    results = []
    # [[ページ名]] の形式を抽出するための正規表現パターン
    pattern = re.compile(r"\[\[(.*?)\]\]")
    
    for line in body_text.splitlines():
        # 行にキーワードが含まれているかチェック (大文字/小文字を無視)
        if keyword.lower() in line.lower():
            match = pattern.search(line)
            if match:
                page_title = match.group(1)
                # 結果リストに重複がなければ追加
                if page_title not in results:
                    results.append(page_title)
    return results

# --- APIエンドポイント定義 ---
@app.get("/search", tags=["Search"])
async def search_wiki(q: Optional[str] = Query(None, description="検索キーワード", min_length=1)):
    """
    指定されたキーワードでWikiのページを検索します。

    - `body` フィールドに対して全文検索を行います。
    - 検索にヒットしたドキュメントの中から、キーワードを含む行を特定し、その行のページタイトルを返します。
    """
    if es_client is None:
        raise HTTPException(status_code=503, detail="Elasticsearch service is unavailable.")

    if not q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required.")

    try:
        # Elasticsearchの検索クエリを作成
        # `match`クエリで`body`フィールドを対象に検索
        query = {
            "query": {
                "match": {
                    "body": {
                        "query": q,
                        "operator": "and"  # AND検索で検索精度を向上
                    }
                }
            },
            "size": 10  # 取得するドキュメント数の上限
        }

        response = es_client.search(index=INDEX_NAME, body=query)
        
        all_matched_pages = []
        # ヒットした各ドキュメントをループ処理
        for hit in response['hits']['hits']:
            if 'body' in hit['_source']:
                # bodyフィールドの内容を取得
                body_content = "\n".join(hit['_source']['body']) if isinstance(hit['_source']['body'], list) else hit['_source']['body']
                # bodyからキーワードにマッチするページ名を抽出
                pages = parse_wiki_body(body_content, q)
                
                # 全体の結果リストに結合し、重複を排除
                for page in pages:
                    if page not in all_matched_pages:
                        all_matched_pages.append(page)

        return {"query": q, "results": all_matched_pages}

    except Exception as e:
        # Elasticsearchからのエラーやその他の例外をハンドル
        raise HTTPException(status_code=500, detail=f"An error occurred during the search: {str(e)}")

@app.get("/", tags=["Root"])
def read_root():
    """
    APIのルートエンドポイント。APIが動作しているかを確認できます。
    """
    return {"message": "Welcome to the Wiki Search API. Use the /docs endpoint to see the API documentation."}

# このファイルが直接実行された場合にUvicornサーバーを起動
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)