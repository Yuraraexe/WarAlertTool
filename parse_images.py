import os
import sys
import json
import re
import time
import io
from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# .envファイルからの簡易パース関数 (環境変数を汚さない)
def load_env_key(env_path=".env"):
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    if key.strip() == "GEMINI_API_KEY":
                        return val.strip().strip('"').strip("'")
    return None

def load_config():
    config_path = "config.json"
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # // コメントと /* */ コメントを正規表現で除去
                content_clean = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
                content_clean = re.sub(r'/\*.*?\*/', '', content_clean, flags=re.DOTALL)
                return json.loads(content_clean)
        except Exception as e:
            print(f"Warning: Failed to load config.json ({e}). Using default settings.")
    return {}

# Pydantic モデル定義
class Skill(BaseModel):
    name: str = Field(description="スキル名。画像左下のスキル欄から取得。")
    type: Literal["active", "passive"] = Field(description="スキルの種類（アクティブなら 'active'、パッシブなら 'passive' を設定）。")
    description: str = Field(description="スキルの効果説明文。")
    cooldown: Optional[int] = Field(description="スキルのクールタイム（秒数）。パッシブなどでクールタイムがない場合は None。")

class Costs(BaseModel):
    supplies: Optional[int] = Field(description="物資コスト。画像左上の盾マークの下にある「人型」アイコン of 数値。")
    oil: Optional[int] = Field(description="石油コスト。画像左上の盾マークの下にある「ドラム缶」アイコン of 数値。")
    manpower: Optional[int] = Field(description="人的資源コスト。画像左上の盾マークの下にある「パラシュート」アイコン of 数値。")
    slots: Optional[int] = Field(description="編成スロット。画像左上にある「盾」アイコンの中 of 数値。")
    cooldown: Optional[int] = Field(description="生産クールタイム。画面に記載がない場合は None。")

class Status(BaseModel):
    hp: Optional[float] = Field(description="最大HP。ステータス欄の「HP:」の基本値。")
    hp_growth: Optional[float] = Field(description="最大HPのレベルアップ上昇値。HPの右側にある黄色の「+」以降の数値。")
    damage: Optional[float] = Field(description="ダメージ。ステータス欄の「ダメージ:」の基本値。")
    damage_growth: Optional[float] = Field(description="ダメージのレベルアップ上昇値。ダメージの右側にある黄色の「+」以降の数値。")
    armor: Optional[float] = Field(description="装甲。ステータス欄の「装甲:」の値。")
    piercing: Optional[float] = Field(description="穿甲。ステータス欄の「穿甲:」の値。")
    speed: Optional[float] = Field(description="移動速度。ステータス欄の「速度:」の値。")
    range: Optional[float] = Field(description="最大攻撃距離。ステータス欄の「射程:」の値。")
    front_armor: Optional[float] = Field(description="正面装甲。ステータス欄や詳細に見当たらない場合は None。")
    side_back_armor: Optional[float] = Field(description="後側方装甲。見当たらない場合は None。")
    turret_speed: Optional[float] = Field(description="砲塔回転速度。見当たらない場合は None。")
    vision: Optional[float] = Field(description="視界。見当たらない場合は None。")
    hit_area: Optional[float] = Field(description="被弾面積。見当たらない場合は None。")

class UnitData(BaseModel):
    name: str = Field(description="ユニット名。画像左上の白文字の大きな名前（例：ヴルフラーメン40）。")
    rarity: Literal["gold", "purple", "blue", "white"] = Field(description="レア度（'gold', 'purple', 'blue', 'white' のいずれか）。カード枠の色やデザインから判定。")
    faction: Literal["germany", "usa", "ussr"] = Field(description="陣営。ドイツなら 'germany'、アメリカなら 'usa'、ソ連なら 'ussr' を設定。")
    level: Optional[int] = Field(description="レベル。ユニット名の下にある「Lv.」の数値。")
    description: str = Field(description="ユニットの説明文。ゲーム内の説明など。画像から読み取れない場合は推測または空欄。")
    costs: Costs
    status: Status
    skills: List[Skill]

def parse_image_to_json(client, image_path, model_name="gemini-2.5-flash"):
    try:
        with Image.open(image_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            max_size = 1280
            if max(img.width, img.height) > max_size:
                if img.width > img.height:
                    new_width = max_size
                    new_height = int(img.height * (max_size / img.width))
                else:
                    new_height = max_size
                    new_width = int(img.width * (max_size / img.height))
                
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                print(f"  [リサイズ] {img.width}x{img.height} に変換しました。")
            
            img_io = io.BytesIO()
            img.save(img_io, format='JPEG', quality=85)
            image_bytes = img_io.getvalue()
            print(f"  [圧縮完了] ファイルサイズ: {len(image_bytes)} バイト (約{len(image_bytes)/1024:.1f} KB)")
            
    except Exception as e:
        print(f"エラー: 画像ファイル {image_path} の読み込み・処理に失敗しました: {e}")
        return None
        
    mime_type = "image/jpeg"
    image_part = types.Part.from_bytes(
        data=image_bytes,
        mime_type=mime_type
    )
    
    prompt = """
    添付されたゲーム詳細画面のスクリーンショット画像から、ユニットの基本情報、生産コスト、ステータス、スキル情報を正確に読み取ってください。
    特に以下の対応関係に注意してください：
    - 物資コスト: 盾アイコンの下の「人型」アイコンの数値
    - 石油コスト: 盾アイコンの下の「ドラム缶」アイコンの数値
    - 人的資源コスト: 盾アイコンの下の「パラシュート」アイコンの数値
    - 編成スロット: 盾アイコンの中の数値
    - HP上昇値: ステータス欄の「HP:」の右側にある黄色の「+」以降の数値
    - ダメージ上昇値: ステータス欄の「ダメージ:」の右側にある黄色の「+」以降の数値
    - レア度: ユニットの背景やカードのデザインから「金」なら "gold"、「紫」なら "purple"、「青」なら "blue"、「白」なら "white" を設定してください。
    - 陣営: 背景の国旗や軍章（鉄十字＝ドイツなら "germany"、五芒星＝アメリカなら "usa"、鎌と槌＝ソ連なら "ussr"）から判別して設定してください。
    """
    
    max_retries = 3
    retry_delay = 5  # 秒
    
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[image_part, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=UnitData,
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"警告: {image_path} の解析中にエラーが発生しました (試行 {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                print(f"{retry_delay}秒後に再試行します...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                print("最大試行回数に達したため、解析を断念します。")
                return None

def run_image_analysis_pipeline(image_dir, output_dir):
    import hashlib
    
    print("\n" + "="*50)
    print("◆ 画像解析（Gemini API）パイプラインの実行")
    print("="*50)
    
    api_key = load_env_key(".env")
    if not api_key:
        print("エラー: .env ファイルに GEMINI_API_KEY が設定されていません。")
        print("画像を解析するには、.envファイルを作成し APIキーを設定する必要があります。")
        print("詳細手順はマニュアル（README.md）をご参照ください。")
        return False
        
    client = genai.Client(api_key=api_key)
    model_name = "gemini-2.5-flash"
    
    if not os.path.exists(image_dir) or not os.listdir(image_dir):
        print(f"エラー: 画像フォルダ '{image_dir}' が空か存在しません。")
        print("解析対象のスクリーンショットを配置して再実行してください。")
        return False
        
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    image_extensions = (".png", ".jpg", ".jpeg", ".webp")
    image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(image_extensions)]
    
    if not image_files:
        print(f"エラー: '{image_dir}' フォルダ内に画像が見つかりません。")
        return False
        
    # キャッシュファイルのロード
    cache_path = os.path.join(output_dir, "processed_cache.json")
    cache = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load cache file ({e}). Starting fresh.")

    def get_file_md5(file_path):
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    print(f"検出された画像数: {len(image_files)}")
    analyzed_files = []
    
    for file in image_files:
        image_path = os.path.join(image_dir, file)
        
        # ハッシュ計算による重複チェック
        try:
            md5_val = get_file_md5(image_path)
        except Exception as e:
            print(f"Warning: Failed to calculate hash for {file} ({e}). Processing normally.")
            md5_val = None
            
        if md5_val and md5_val in cache:
            cached_info = cache[md5_val]
            cached_json_path = cached_info.get("output_json")
            if cached_json_path and os.path.exists(cached_json_path):
                try:
                    with open(cached_json_path, 'r', encoding='utf-8') as f:
                        cached_data = json.load(f)
                    print(f"[{file}] すでに解析済みです。キャッシュからロードします。")
                    analyzed_files.append((cached_json_path, cached_data))
                    continue
                except Exception as e:
                    print(f"Warning: Failed to load cached JSON {cached_json_path} ({e}). Re-analyzing image.")

        print(f"\n[{file}] 解析中...")
        result = parse_image_to_json(client, image_path, model_name)
        if result:
            unit_name = result.get("name", "unknown")
            output_file = os.path.join(output_dir, f"{unit_name}.json")
            
            with open(output_file, 'w', encoding='utf-8') as out_f:
                json.dump(result, out_f, indent=2, ensure_ascii=False)
                
            print(f"-> 解析完了。データを保存しました: {output_file}")
            analyzed_files.append((output_file, result))
            
            # キャッシュの更新
            if md5_val:
                cache[md5_val] = {
                    "image_file": file,
                    "output_json": output_file,
                    "timestamp": time.time()
                }
                try:
                    with open(cache_path, 'w', encoding='utf-8') as f:
                        json.dump(cache, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    print(f"Warning: Failed to save cache ({e})")
        else:
            print(f"-> {file} の解析に失敗しました。")
            
    print(f"\n画像解析が完了しました (成功: {len(analyzed_files)}/{len(image_files)})")
    return analyzed_files

def main():
    print("--------------------------------------------------")
    print("ゲーム画面画像パラメータ解析ツール (Gemini API)")
    print("--------------------------------------------------")
    
    config = load_config()
    image_dir = config.get("image_dir", "images")
    output_dir = config.get("json_dir", "units")
    
    run_image_analysis_pipeline(image_dir, output_dir)

if __name__ == "__main__":
    main()
