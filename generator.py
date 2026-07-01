import os
from utils import FACTION_MAP, RARITY_MAP, SKILL_TYPE_MAP, format_growth, format_value

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
