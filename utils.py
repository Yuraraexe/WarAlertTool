import json
import os
import sys
import re

# ローカライズ用マッピングデータのロード
def load_localization_data():
    local_json_path = "localize.json"
    if not os.path.exists(local_json_path):
        print(f"Error: Localization file '{local_json_path}' not found.")
        sys.exit(1)
    try:
        with open(local_json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error: Failed to load '{local_json_path}' ({e}).")
        sys.exit(1)

LOCALIZATION = load_localization_data()

# 表示用マッピング
FACTION_MAP = LOCALIZATION.get("faction", {})
RARITY_MAP = LOCALIZATION.get("rarity", {})
SKILL_TYPE_MAP = LOCALIZATION.get("skill_type", {})

# CSV読み込み用マッピング（表示用マッピングを反転して動的に生成）
CSV_FACTION_MAP = {v: k for k, v in FACTION_MAP.items()}
CSV_RARITY_MAP = {v: k for k, v in RARITY_MAP.items()}
CSV_SKILL_TYPE_MAP = {v: k for k, v in SKILL_TYPE_MAP.items()}


def format_value(value, unit=""):
    if value is None:
        return "-"
    return f"{value}{unit}"

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
