import sys
import os
import argparse

# 起動時の依存モジュール自動セットアップチェック
def check_dependencies():
    packages = {
        "google.genai": "google-genai",
        "PIL": "Pillow",
        "dotenv": "python-dotenv"
    }
    missing = []
    for module_name, pip_name in packages.items():
        try:
            __import__(module_name)
        except ImportError:
            missing.append(pip_name)
            
    if missing:
        print(f"\n==================================================")
        print(f" 依存パッケージの自動セットアップ")
        print(f"==================================================")
        print(f"このツールの実行に必要な以下のライブラリが不足しています:")
        for pkg in missing:
            print(f" - {pkg}")
        print(f"--------------------------------------------------")
        
        try:
            choice = input("これらのライブラリを今すぐインストールしますか？ (y/n) [既定値: y]: ").strip().lower()
            if choice == "" or choice == "y" or choice == "yes":
                import subprocess
                print(f"\nライブラリをインストール中...")
                subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
                print("インストールが正常に完了しました！\n")
            else:
                print("\nエラー: 必要なライブラリがないためツールを実行できません。終了します。")
                sys.exit(1)
        except Exception as e:
            print(f"\nインストール中にエラーが発生しました: {e}")
            sys.exit(1)

# インポート前に依存パッケージチェックを実行
check_dependencies()

# 画像解析パイプラインのインポート
try:
    from parse_images import run_image_analysis_pipeline
except ImportError:
    print("Warning: parse_images.py not found. Image analysis will be unavailable.")
    run_image_analysis_pipeline = None

# 分割された自作モジュールからのインポート
try:
    from utils import load_config
    from loader import load_units
    from generator import generate_wiki_table, generate_summary_table
except ImportError as e:
    print(f"Error: Failed to import internal modules: {e}")
    sys.exit(1)


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


def main():
    # 引数解析
    parser = argparse.ArgumentParser(description="WarAlert ユニットドキュメント生成ツール")
    parser.add_argument("-i", "--input", help="入力データ（images, JSONファイル, CSVファイル, またはフォルダ）")
    parser.add_argument("-f", "--format", choices=["atwiki", "md"], help="出力形式 (atwiki, md)")
    parser.add_argument("-m", "--mode", choices=["single", "table"], help="生成モード (single: 個別カード, table: 比較一覧表)")
    parser.add_argument("-l", "--localize", choices=["localized", "raw"], help="ローカライズ設定 (localized: 日本語訳, raw: 生データ)")
    parser.add_argument("-y", "--non-interactive", action="store_true", help="対話型プロンプトをスキップして実行する")
    
    args = parser.parse_args()
    
    config = load_config()
    
    # デフォルト値の設定（config > デフォルト定数）
    default_output_format = config.get("output_format", "atwiki").lower()
    default_generation_mode = config.get("generation_mode", "single").lower()
    default_localize = config.get("localize", "localized").lower()
    
    default_input_path = "images" if run_image_analysis_pipeline else "."
    
    output_dir = config.get("output_dir", "output")
    json_dir = config.get("json_dir", "units")
    
    # 引数の指定がある場合はそちらを優先。ない場合はデフォルト値を使用
    input_path = args.input if args.input is not None else default_input_path
    output_format = args.format if args.format is not None else default_output_format
    generation_mode = args.mode if args.mode is not None else default_generation_mode
    localize = args.localize if args.localize is not None else default_localize
    
    # 非対話モードでない場合は、対話型のホーム画面メニューを表示
    if not args.non_interactive:
        print("\n" + "="*50)
        print("     WarAlert ユニットドキュメント生成ツール")
        print("="*50)
        print(" [メニュー]")
        print("  1: 処理を実行する (スクショ解析 ＆ ドキュメント生成)")
        print("  2: 高度な設定を変更して実行する (出力形式やモード等を個別指定)")
        print("  3: ヘルプ / 使い方を表示")
        print("  4: 終了")
        print("="*50)
        
        while True:
            choice = input("選択してください [1-4/Enter (既定値: 1)]: ").strip()
            if choice == "" or choice == "1":
                break
            elif choice == "2":
                print("\n設定を選択してください。（そのまま Enter を押すと既定値になります）")
                output_format_options = {
                    "atwiki": {"title": "アットウィキ形式 (atwiki)", "desc": "アットウィキ用の表組み・装飾コード（カラータグ等）テキスト"},
                    "md": {"title": "Markdown形式 (md)", "desc": "GitHubや一般的なドキュメントで使われる標準的なMarkdownテーブル"}
                }
                generation_mode_options = {
                    "single": {"title": "個別ファイル作成 (single)", "desc": "ユニットごとに、個別詳細カードとなるファイルを生成"},
                    "table": {"title": "1つの比較一覧表にまとめる (table)", "desc": "全ユニットの主要パラメータを1つの比較表テーブルに統合"}
                }
                localize_options = {
                    "localized": {"title": "日本語ローカライズ (localized)", "desc": "データ内の英語識別子を日本語に翻訳して出力 (例: 'gold' -> '金')"},
                    "raw": {"title": "生データ出力 (raw)", "desc": "データ内の英語識別子をそのまま出力 (例: 'gold' -> 'gold')"}
                }
                output_format = select_setting_interactive("出力形式", output_format_options, output_format)
                generation_mode = select_setting_interactive("生成モード", generation_mode_options, generation_mode)
                localize = select_setting_interactive("ローカライズ設定", localize_options, localize)
                break
            elif choice == "3":
                print("\n==================================================")
                print("◆ ヘルプ / 使い方")
                print("==================================================")
                print("本ツールは以下の流れでドキュメントを生成します。")
                print("1. 'images' フォルダ内のスクリーンショット画像を Gemini API を用いて解析します。")
                print("2. 解析結果のデータを 'units' フォルダへ JSON として保存します。")
                print("3. データをもとにアットウィキ形式（またはMarkdown形式）のドキュメントを 'output' フォルダに生成します。")
                print("\n[コマンドライン引数の利用方法]")
                print("  python WarAlertTool.py -f md -m table -y")
                print("  のように引数を指定すると、対話プロンプトなし（-y）で直接処理を実行できます。")
                print("==================================================\n")
                input("Enter キーを押すとホーム画面に戻ります...")
                print("\n" + "="*50)
                print("     WarAlert ユニットドキュメント生成ツール")
                print("="*50)
                print(" [メニュー]")
                print("  1: 処理を実行する (スクショ解析 ＆ ドキュメント生成)")
                print("  2: 高度な設定を変更して実行する (出力形式やモード等を個別指定)")
                print("  3: ヘルプ / 使い方を表示")
                print("  4: 終了")
                print("="*50)
            elif choice == "4":
                print("\n終了します。")
                sys.exit(0)
            else:
                print("無効な入力です。1〜4の番号を選択してください。")
        
    # 特例：imagesが選択された場合は画像解析パイプラインを走らせる
    if input_path == "images":
        if not run_image_analysis_pipeline:
            print("Error: Image analysis pipeline is unavailable.")
            sys.exit(1)
        analyzed = run_image_analysis_pipeline(image_dir="images", output_dir=json_dir)
        if not analyzed:
            print("\n画像解析パイプラインに失敗したか、対象画像が見つからないため、処理を中断します。")
            sys.exit(1)
        # 読み込み先を画像解析で生成されたJSONフォルダに切り替える
        input_path = json_dir
        
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    units = load_units(input_path)
    if not units:
        print(f"エラー: ユニットデータを '{input_path}' から読み込めませんでした。")
        sys.exit(1)
        
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

if __name__ == "__main__":
    main()
