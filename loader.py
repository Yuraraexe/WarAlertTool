import os
import csv
import json
from utils import CSV_FACTION_MAP, CSV_RARITY_MAP, CSV_SKILL_TYPE_MAP

def load_single_unit_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading JSON file {file_path}: {e}")
        return None

def load_units_from_csv(csv_path):
    units_data = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("名前") == "名前" or not row.get("名前"):
                    continue
                    
                def get_float(val):
                    try:
                        return float(val) if val.strip() != "" else None
                    except (ValueError, AttributeError):
                        return None
                        
                def get_int(val):
                    try:
                        return int(val) if val.strip() != "" else None
                    except (ValueError, AttributeError):
                        return None

                def get_str(val):
                    return val.strip() if val and val.strip() != "" else None

                skills = []
                for i in range(1, 4):
                    s_name = get_str(row.get(f"スキル{i}_名前", ""))
                    if s_name:
                        s_type_raw = get_str(row.get(f"スキル{i}_タイプ", "アクティブ"))
                        s_type = CSV_SKILL_TYPE_MAP.get(s_type_raw, "active")
                        s_desc = get_str(row.get(f"スキル{i}_説明", ""))
                        s_cd = get_int(row.get(f"スキル{i}_クールタイム", ""))
                        skills.append({
                            "name": s_name,
                            "type": s_type,
                            "description": s_desc,
                            "cooldown": s_cd
                        })

                rarity_raw = get_str(row.get("レア度"))
                rarity = CSV_RARITY_MAP.get(rarity_raw, "white")
                
                faction_raw = get_str(row.get("陣営"))
                faction = CSV_FACTION_MAP.get(faction_raw, "germany")

                unit_data = {
                    "name": get_str(row.get("名前", "ユニット名")),
                    "rarity": rarity,
                    "faction": faction,
                    "level": get_int(row.get("レベル")),
                    "description": get_str(row.get("説明")),
                    "costs": {
                        "supplies": get_int(row.get("物資")),
                        "oil": get_int(row.get("石油")),
                        "manpower": get_int(row.get("人的資源")),
                        "slots": get_int(row.get("編成スロット")),
                        "cooldown": get_int(row.get("生産クールタイム"))
                    },
                    "status": {
                        "hp": get_float(row.get("最大HP")),
                        "damage": get_float(row.get("ダメージ")),
                        "armor": get_float(row.get("装甲")),
                        "piercing": get_float(row.get("穿甲")),
                        "speed": get_float(row.get("移動速度")),
                        "range": get_float(row.get("最大攻撃距離")),
                        "front_armor": get_float(row.get("正面装甲")),
                        "side_back_armor": get_float(row.get("後側方装甲")),
                        "turret_speed": get_float(row.get("砲塔回転速度")),
                        "vision": get_float(row.get("視界")),
                        "hit_area": get_float(row.get("被弾面積"))
                    },
                    "skills": skills
                }
                units_data.append((f"{csv_path}:{reader.line_num}", unit_data))
    except Exception as e:
        print(f"Error loading CSV file {csv_path}: {e}")
    return units_data

def load_units(path):
    if os.path.isdir(path):
        units_data = []
        for file in sorted(os.listdir(path)):
            if file.endswith(".json") and file != "config.json":
                file_path = os.path.join(path, file)
                data = load_single_unit_json(file_path)
                if data:
                    units_data.append((file_path, data))
        return units_data
    elif os.path.isfile(path):
        if path.endswith(".csv"):
            return load_units_from_csv(path)
        else:
            data = load_single_unit_json(path)
            if data:
                if isinstance(data, list):
                    return [(f"{path}[{idx}]", item) for idx, item in enumerate(data)]
                else:
                    return [(path, data)]
    return []
