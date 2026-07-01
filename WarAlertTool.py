import json
import sys
import os
import csv
import re

# 画像解析パイプラインのインポート
try:
    from parse_images import run_image_analysis_pipeline
except ImportError:
    print("Warning: parse_images.py not found. Image analysis will be unavailable.")
    run_image_analysis_pipeline = None

# ローカライズ用マッピングデータのロード
def load_localization_data():
    local_json_path = "localize.json"
    if os.path.exists(local_json_path):
        try:
            with open(local_json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load localize.json ({e}). Using default mappings.")
    
    # フォールバック用デフォルト定義
    return {
        "faction": {"germany": "ドイツ", "usa": "アメリカ", "ussr": "ソ連"},
        "rarity": {"gold": "金", "purple": "紫", "blue": "青", "white": "白"},
        "skill_type": {"active": "アクティブ", "passive": "パッシブ"},
        "csv_mapping": {
            "faction": {"ドイツ": "germany", "アメリカ": "usa", "ソ連": "ussr"},
            "rarity": {"金": "gold", "紫": "purple", "青": "blue", "白": "white"},
            "skill_type": {"アクティブ": "active", "パッシブ": "passive"}
        }
    }

LOCALIZATION = load_localization_data()

# 表示用マッピング
FACTION_MAP = LOCALIZATION.get("faction", {})
RARITY_MAP = LOCALIZATION.get("rarity", {})
SKILL_TYPE_MAP = LOCALIZATION.get("skill_type", {})

# CSV読み込み用マッピング
CSV_FACTION_MAP = LOCALIZATION.get("csv_mapping", {}).get("faction", {})
CSV_RARITY_MAP = LOCALIZATION.get("csv_mapping", {}).get("rarity", {})
CSV_SKILL_TYPE_MAP = LOCALIZATION.get("csv_mapping", {}).get("skill_type", {})


def format_growth(value, growth):
    if value is None:
        return "-"
    if growth is not None:
        return f"{value} (+{growth})"
    return str(value)

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

def build_header(text, level, output_format):
    match output_format:
        case "md":
            md_level = level + 1
            return f"{'#' * md_level} {text}\n"
        case "atwiki" | _:
            return f"{'*' * level}{text}"

def build_image(name, output_format):
    match output_format:
        case "md":
            return f"![{name}](画像ファイルのパス)\n"
        case "atwiki" | _:
            return f"image(画像ファイル,width=150,height=225,title=任意,left)"

def build_table(rows, output_format):
    lines = []
    match output_format:
        case "md":
            col_count = len(rows[0]) * 2
            headers = []
            for _ in range(len(rows[0])):
                headers.extend(["パラメータ", "値"])
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("| " + " | ".join([":---"] * col_count) + " |")
            
            for row in rows:
                cells = []
                for k, v in row:
                    cells.extend([k, v])
                lines.append("| " + " | ".join(cells) + " |")
            return "\n".join(lines) + "\n"
        case "atwiki" | _:
            for row in rows:
                cells = []
                for k, v in row:
                    cells.extend([k, v])
                lines.append("|" + "|".join(cells) + "|")
            return "\n".join(lines)

def generate_wiki_table(data, output_format="atwiki", localize="localized"):
    name = data.get("name", "ユニット名")
    description = data.get("description", "説明文")
    
    # ステータス情報
    status = data.get("status", {})
    hp_val = status.get("hp")
    hp_growth = status.get("hp_growth")
    hp_str = format_growth(hp_val, hp_growth)
    
    damage_val = status.get("damage")
    damage_growth = status.get("damage_growth")
    damage_str = format_growth(damage_val, damage_growth)
    
    speed_val = status.get("speed")
    speed_str = format_value(speed_val)
    
    armor_val = status.get("armor")
    armor_str = format_value(armor_val)
    
    piercing_val = status.get("piercing")
    piercing_str = format_value(piercing_val)
    
    range_val = status.get("range")
    range_str = format_value(range_val)
    
    front_armor_val = status.get("front_armor")
    front_armor_str = format_value(front_armor_val)
    
    side_back_armor_val = status.get("side_back_armor")
    side_back_armor_str = format_value(side_back_armor_val)
    
    turret_speed_val = status.get("turret_speed")
    turret_speed_str = format_value(turret_speed_val)
    
    vision_val = status.get("vision")
    vision_str = format_value(vision_val)
    
    hit_area_val = status.get("hit_area")
    hit_area_str = format_value(hit_area_val)

    # コスト情報
    costs = data.get("costs", {})
    supplies = format_value(costs.get("supplies"))
    oil = format_value(costs.get("oil"))
    manpower = format_value(costs.get("manpower"))
    cooldown = format_value(costs.get("cooldown"), "秒")
    slots = format_value(costs.get("slots"))

    # スキル情報
    skills = data.get("skills", [])
    skills_list = []
    for skill in skills:
        s_name = skill.get("name", "スキル名")
        s_type_raw = skill.get("type", "active")
        if localize == "localized":
            s_type = SKILL_TYPE_MAP.get(s_type_raw, "アクティブ")
        else:
            s_type = s_type_raw
        s_desc = skill.get("description", "スキル説明")
        s_cd = skill.get("cooldown")
        
        # タイプによる色分け
        type_color = "#F54738" if s_type_raw == "active" else "#3F51B5"
        
        cd_str = f"クールタイム{s_cd}秒" if s_cd is not None else "クールタイムなし"
        
        match output_format:
            case "md":
                skill_str = f"【<span style=\"color:{type_color};\">{s_type}効果</span>】 {s_name}  \n{s_desc}  \n{cd_str}"
            case "atwiki" | _:
                skill_str = f"【&color({type_color}){{{s_type}効果}}】 {s_name}\n{s_desc}\n{cd_str}"
            
        skills_list.append(skill_str)
        
    skills_output = "\n\n".join(skills_list) if skills_list else "なし"

    # テーブル用データ定義
    status_rows = [
        [("最大HP", hp_str), ("ダメージ", damage_str), ("移動速度", speed_str)],
        [("装甲", armor_str), ("穿甲", piercing_str), ("最大攻撃距離", range_str)],
        [("正面装甲", front_armor_str), ("後側方装甲", side_back_armor_str), ("砲塔回転速度", turret_speed_str)],
        [("視界", vision_str), ("被弾面積", hit_area_str), ("-", "-")]
    ]

    costs_rows = [
        [("物資", supplies), ("石油", oil)],
        [("人的資源", manpower), ("生産クールタイム", cooldown)],
        [("編成スロット数", slots), ("-", "-")]
    ]

    # テンプレートに従ってフォーマットを構築
    wiki_content = []
    
    if output_format == "md":
        wiki_content.append(build_header(name, level=1, output_format=output_format))
    else:
        wiki_content.append(f"**{name}")
    wiki_content.append(build_image(name, output_format))
    
    wiki_content.append(build_header("説明", level=2, output_format=output_format))
    wiki_content.append(f"{description}\n" if output_format == "md" else description)
    
    wiki_content.append(build_header("ステータス", level=2, output_format=output_format))
    wiki_content.append(build_table(status_rows, output_format))
    
    wiki_content.append(build_header("固定武装", level=2, output_format=output_format))
    wiki_content.append("- \n" if output_format == "md" else "-")
    
    wiki_content.append(build_header("生産コスト", level=2, output_format=output_format))
    wiki_content.append(build_table(costs_rows, output_format))
    
    wiki_content.append(build_header("スキル情報", level=2, output_format=output_format))
    wiki_content.append(skills_output)
        
    return "\n".join(wiki_content)

def generate_summary_table(units_data, output_format, localize="localized"):
    headers = [
        "陣営", "レア度", "ユニット名", "最大HP", "ダメージ", 
        "装甲", "穿甲", "移動速度", "最大攻撃距離", 
        "物資", "石油", "人的資源", "編成スロット", "スキル"
    ]
    
    rows = []
    for data in units_data:
        name = data.get("name", "未定義")
        rarity_raw = data.get("rarity", "-")
        faction_raw = data.get("faction", "-")
        
        if localize == "localized":
            rarity = RARITY_MAP.get(rarity_raw, rarity_raw)
            faction = FACTION_MAP.get(faction_raw, faction_raw)
        else:
            rarity = rarity_raw
            faction = faction_raw
        
        status = data.get("status", {})
        hp_str = format_growth(status.get("hp"), status.get("hp_growth"))
        damage_str = format_growth(status.get("damage"), status.get("damage_growth"))
        speed_str = format_value(status.get("speed"))
        armor_str = format_value(status.get("armor"))
        piercing_str = format_value(status.get("piercing"))
        range_str = format_value(status.get("range"))
        
        costs = data.get("costs", {})
        supplies = format_value(costs.get("supplies"))
        oil = format_value(costs.get("oil"))
        manpower = format_value(costs.get("manpower"))
        slots = format_value(costs.get("slots"))
        
        skills = data.get("skills", [])
        skill_names = [s.get("name", "未定義") for s in skills]
        skills_str = ", ".join(skill_names) if skill_names else "-"
        
        row = [
            faction, rarity, name, hp_str, damage_str,
            armor_str, piercing_str, speed_str, range_str,
            supplies, oil, manpower, slots, skills_str
        ]
        rows.append(row)
        
    lines = []
    match output_format:
        case "md":
            lines.append("## ユニットパラメータ比較表\n")
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("| " + " | ".join([":---"] * len(headers)) + " |")
            for row in rows:
                lines.append("| " + " | ".join(row) + " |")
            return "\n".join(lines) + "\n"
        case "atwiki" | _:
            at_headers = [f"~{h}" for h in headers]
            lines.append("|" + "|".join(at_headers) + "|h")
            for row in rows:
                lines.append("|" + "|".join(row) + "|")
            return "\n".join(lines)

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
                if row.get("名前") == "名前":
                    continue
                    
                def get_float(val):
                    try:
                        return float(val) if val.strip() != "" else None
                    except ValueError:
                        return None
                        
                def get_int(val):
                    try:
                        return int(val) if val.strip() != "" else None
                    except ValueError:
                        return None

                def get_str(val):
                    return val.strip() if val.strip() != "" else None

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
                        "hp_growth": get_float(row.get("HP上昇値")),
                        "damage": get_float(row.get("ダメージ")),
                        "damage_growth": get_float(row.get("ダメージ上昇値")),
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

def select_setting_interactive(name, options, default_value):
    print(f"\n==================================================")
    print(f"◆ {name}の選択")
    print(f"==================================================")
    for idx, (key, info) in enumerate(options.items(), 1):
        print(f" {idx}: {info['title']}")
        print(f"    -> {info['desc']}")
    print(f"--------------------------------------------------")
    print(f"※ 何も入力せず Enter を押すと、デフォルト設定値 [{default_value}] を使用します。")
    print(f"==================================================")
    
    while True:
        try:
            choice = input(f"番号を選択してください [1-{len(options)}/Enter]: ").strip()
            if choice == "":
                return default_value
            
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(options):
                return list(options.keys())[choice_idx]
        except (ValueError, IndexError):
            pass
        
        print("無効な入力です。もう一度入力してください。")

def select_input_path_interactive():
    print("\n==================================================")
    print("◆ 入力データの選択")
    print("==================================================")
    print(" どのファイルまたはフォルダからユニットデータを読み込みますか？")
    print("--------------------------------------------------")
    
    candidates = []
    
    # 0. 画像解析から生成（基本フローとして最優先で探索）
    if os.path.exists("images") and os.path.isdir("images"):
        image_extensions = (".png", ".jpg", ".jpeg", ".webp")
        has_images = any(f.lower().endswith(image_extensions) for f in os.listdir("images"))
        if has_images:
            candidates.append(("images", "フォルダ内のスクリーンショット画像を解析してデータ化し、ドキュメントを生成 (本ツールの推奨基本フロー)"))

    # 1. CSVファイルの探索
    for f in sorted(os.listdir(".")):
        if f.endswith(".csv"):
            candidates.append((f, "CSV形式のユニットデータ一覧ファイル"))
            
    # 2. JSONファイル（config.jsonを除く）の探索
    for f in sorted(os.listdir(".")):
        if f.endswith(".json") and f != "config.json" and f != "sample_unit.json":
            candidates.append((f, "個別ユニットデータJSONファイル"))
            
    # 3. フォルダの探索
    exclude_dirs = ["output", ".git", "__pycache__", "units"]
    for d in sorted(os.listdir(".")):
        if os.path.isdir(d) and d not in exclude_dirs and not d.startswith("."):
            candidates.append((d, "ユニットデータJSONファイルが複数入ったフォルダ"))
            
    if os.path.exists("units") and os.path.isdir("units"):
        candidates.append(("units", "解析済みユニットデータJSONファイルが複数入ったフォルダ"))
    if os.path.exists("sample_unit.json") and os.path.isfile("sample_unit.json"):
        candidates.append(("sample_unit.json", "サンプルユニットのJSONファイル"))

    print(" 0: パスを手動で入力する (任意のファイルやフォルダを指定)")
    for idx, (path, desc) in enumerate(candidates, 1):
        print(f" {idx}: {path}")
        print(f"    -> {desc}")
    print("==================================================")
    
    while True:
        choice = input(f"番号を選択してください [0-{len(candidates)}]: ").strip()
        if choice == "0":
            custom_path = input("パスを入力してください: ").strip()
            if os.path.exists(custom_path):
                return custom_path
            else:
                print(f"エラー: 指定されたパス '{custom_path}' が見つかりません。")
        else:
            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(candidates):
                    return candidates[choice_idx][0]
            except (ValueError, IndexError):
                pass
            print("無効な入力です。もう一度選択してください。")

if __name__ == "__main__":
    print("\n" + "="*50)
    print("     WarAlert ユニットドキュメント生成ツール")
    print("="*50)
    print("このツールは、ユニットデータ (JSON/CSV) から")
    print("アットウィキ用テキストやMarkdownファイルを自動生成します。")
    print("画面の指示に従って設定を選択してください。")
    print("（[Enter] を押すと、既定の推奨設定で進みます）")
    print("="*50)

    input_path = select_input_path_interactive()
        
    config = load_config()
    default_output_format = config.get("output_format", "atwiki").lower()
    default_generation_mode = config.get("generation_mode", "single").lower()
    default_localize = config.get("localize", "localized").lower()
    output_dir = config.get("output_dir", "output")
    json_dir = config.get("json_dir", "units")
    
    # 特例：imagesが選択された場合は画像解析パイプラインを走らせる
    if input_path == "images":
        analyzed = run_image_analysis_pipeline(image_dir="images", output_dir=json_dir)
        if not analyzed:
            print("\n画像解析パイプラインに失敗、またはキャンセルされたため、処理を中断します。")
            sys.exit(1)
        # 読み込み先を、画像解析で生成されたJSON群のフォルダに切り替える
        input_path = json_dir
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    units = load_units(input_path)
    if not units:
        print("エラー: ユニットデータを読み込めませんでした。")
        sys.exit(1)
        
    # 対話型でモードとフォーマット、ローカライズを選択
    output_format_options = {
        "atwiki": {
            "title": "アットウィキ形式 (atwiki)",
            "desc": "アットウィキ用の表組み・装飾コード（カラータグ等）を含んだテキストを生成します。"
        },
        "md": {
            "title": "Markdown形式 (md)",
            "desc": "GitHubや一般的なドキュメントで使われる標準的なMarkdownテーブルを生成します。"
        }
    }
    generation_mode_options = {
        "single": {
            "title": "個別ファイル作成 (single)",
            "desc": "ユニットごとに、個別詳細カードとなるファイルを生成します。"
        },
        "table": {
            "title": "1つの比較一覧表にまとめる (table)",
            "desc": "全ユニットの主要パラメータを1つの比較表テーブルに統合して出力します。"
        }
    }
    localize_options = {
        "localized": {
            "title": "日本語ローカライズ (localized)",
            "desc": "データ内の英語識別子を日本語に翻訳して出力します（例: 'gold' -> '金'）"
        },
        "raw": {
            "title": "生データ出力 (raw)",
            "desc": "データ内の英語識別子をそのまま出力します（例: 'gold' -> 'gold'）"
        }
    }
    
    output_format = select_setting_interactive("出力形式", output_format_options, default_output_format)
    generation_mode = select_setting_interactive("生成モード", generation_mode_options, default_generation_mode)
    localize = select_setting_interactive("ローカライズ設定", localize_options, default_localize)
        
    match generation_mode:
        case "table":
            units_data = [data for _, data in units]
            output_text = generate_summary_table(units_data, output_format, localize=localize)
            
            match output_format:
                case "md":
                    output_file = os.path.join(output_dir, "summary_table.md")
                case "atwiki" | _:
                    output_file = os.path.join(output_dir, "summary_table_wiki.txt")
                    
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output_text)
                
            print(f"\nSuccessfully generated summary table: {output_file} (Format: {output_format}, Localize: {localize})")
            
        case "single" | _:
            print() # 改行
            for file_path, data in units:
                name = data.get("name", "unknown")
                output_text = generate_wiki_table(data, output_format, localize=localize)
                
                match output_format:
                    case "md":
                        output_file = os.path.join(output_dir, f"{name}.md")
                    case "atwiki" | _:
                        output_file = os.path.join(output_dir, f"{name}_wiki.txt")
                        
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(output_text)
                print(f"Successfully generated unit card: {output_file} (Format: {output_format}, Localize: {localize})")
