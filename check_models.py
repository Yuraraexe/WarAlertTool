import os
from dotenv import load_dotenv
from google import genai

# .envファイルをロード
load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("エラー: .env または環境変数に GEMINI_API_KEY が設定されていません。")
    print(".env ファイルを作成し、'GEMINI_API_KEY=あなたのAPIキー' を記述してください。")
    exit(1)

try:
    # 新しい google-genai SDK を使用してクライアントを初期化
    client = genai.Client(api_key=api_key)
    
    print("利用可能なモデル一覧を取得中...")
    response = client.models.list()
    
    print("\n--- 利用可能なモデル一覧 ---")
    for model in response:
        print(f"- {model.name} ({model.display_name})")
except Exception as e:
    print(f"エラーが発生しました: {e}")
