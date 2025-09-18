# crawler/config.py
class pukiwiki:
    # Docker Compose内のサービス名'elasticsearch'を指定
    ELASTIC_SEARCH_ENDPOINT = "http://elasticsearch:9200"
    # 作成するインデックス名
    INDEX = "pukiwiki"
    # インデックス設定ファイルのコンテナ内パス
    INDEX_FILE = "/app/index.json"
    # PukiWikiデータディレクトリのコンテナ内パス
    PUKIWIKI_DATA_DIR = "/pukiwiki_data"