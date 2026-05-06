import streamlit as st
import os
import json
import fitz  # PyMuPDF
import glob
import time
import random
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from google import genai
from dotenv import load_dotenv
from io import BytesIO
from pptx.enum.shapes import MSO_SHAPE
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from google.genai import types

# --- 1. 環境設定 ---
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

st.set_page_config(page_title="AI Pamphlet Builder", layout="wide")
st.title("🏡 AI Pamphlet Builder (Template Mode)")
st.write("用意したテンプレート画像とAIのテキスト解析を組み合わせ、全6ページのパワポ資料を安定して自動生成します。")

# フォントのパス（実行環境に合わせて確認してください）
FONT_PATH = './NotoSansCJKjp-Bold.ttf' 

# --- 修正：デザインテーマを6種＋その他に拡張 ---
THEMES = {
    "luxury":       {"name": "1 高級・ラグジュアリー", "bg_color": (40, 40, 45), "text_color": "white", "accent_color": (180, 150, 80)},
    "family":       {"name": "2 ファミリー・温もり", "bg_color": (255, 245, 235), "text_color": "black", "accent_color": (240, 130, 50)},
    "modern":       {"name": "3 スタイリッシュ・モダン", "bg_color": (240, 245, 255), "text_color": "black", "accent_color": (50, 100, 180)},
    "wa_modern":    {"name": "4 和モダン・伝統美", "bg_color": (230, 225, 215), "text_color": "black", "accent_color": (100, 120, 80)},
    "casual":       {"name": "5 カジュアル・ポップ", "bg_color": (255, 250, 220), "text_color": "black", "accent_color": (250, 100, 130)},
    "other":        {"name": "6 その他（自由入力スタイル）", "bg_color": (240, 240, 240), "text_color": "black", "accent_color": (100, 100, 100)}
}
# --- 追加：店舗ごとの詳細データ ---
BRANCH_DATA = {
    "練馬": {
        "full_name": "株式会社 東宝ハウス練馬",
        "license": "東京都知事（4）第86488号",
        "address": "〒178-0063 東京都練馬区東大泉1-27-22光和ビル2F",
        "tel": "0120-384-700"
    },
    "国分寺": {
        "full_name": "株式会社 東宝ハウス国分寺",
        "license": "東京都知事（9）第42787号",
        "address": "〒185-0021 東京都国分寺市南町3-22-2",
        "tel": "0120-13-3107"
    },
    "武蔵野": {
        "full_name": "株式会社 東宝ハウス武蔵野",
        "license": "東京都知事（3）第90333号",
        "address": "〒180-0004 東京都武蔵野市吉祥寺本町1-15-9",
        "tel": "0120-15-3101"
    },
}

# --- 2. メモリ（セッション状態）の初期化 ---
if "finished_pages" not in st.session_state:
    st.session_state.finished_pages = []
if "ai_data" not in st.session_state:
    st.session_state.ai_data = None
if "current_file" not in st.session_state:
    st.session_state.current_file = None
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""
if "cover_choices" not in st.session_state:
    st.session_state.cover_choices = []
if "selected_cover_index" not in st.session_state:
    st.session_state.selected_cover_index = 0    
    

# --- 修正：PDFだけでなく画像も許可し、特徴入力欄を追加 ---
col_u1, col_u2 = st.columns(2)
with col_u1:
    uploaded_file = st.file_uploader("販売図面（PDFまたは画像）をアップロード", type=["pdf", "png", "jpg", "jpeg"])
with col_u2:
    madori_file = st.file_uploader("間取り図の画像をアップロード（P.4用）", type=["png", "jpg", "jpeg"])

# 👇👇👇 ここから追加 👇👇👇
st.write("---")
st.subheader("🗺️ 地図画像のアップロード")
map_file = st.file_uploader("地図に使用するマップ画像をアップロード（P.3 MAP & ACCESS用）", type=["png", "jpg", "jpeg"])
st.caption("※アップロードすると、AIが自動で高級感のある色合いに調整し、駅徒歩バッジを配置します。")
# 👆👆👆 ここまで追加 👆👆👆

# 【重要】このファイル変更時のリセット処理はそのまま残します
if uploaded_file is not None and uploaded_file.name != st.session_state.current_file:
    st.session_state.finished_pages = []
    st.session_state.ai_data = None
    st.session_state.current_file = uploaded_file.name
    st.session_state.pdf_text = ""

# ✨✨ ここに構図（レイアウト）の選択UIを挿入 ✨✨
st.write("---")
st.subheader("🛋️ 理想の空間レイアウト（構図）を選択")
st.write("間取り図をどのようなカメラアングルで描画するか選択してください。")

# 画像を小さく並べるための設定
# ✨ 修正：間に「0.2」の小さな余白（スペーサー）を挟んで重なりを防止します
col_img1, col_space, col_img2, _ = st.columns([2, 0.2, 2, 4])

with col_img1:
    try:
        # width=350を消し、枠の幅に合わせて自動縮小する設定に変更
        st.image("1.jpg", caption="① 横長の広々としたレイアウト", use_container_width=True)
    except:
        st.info("※画像が見つかりません。1.jpgを配置してください。")

with col_img2:
    try:
        # こちらも枠に合わせて自動縮小
        st.image("2.jpg", caption="② 縦長の奥行きのあるレイアウト", use_container_width=True)
    except:
        st.info("※画像が見つかりません。2.jpgを配置してください。")

layout_styles = {
    "horizontal": "① 横長レイアウト（窓面が広く、開放感のある構図）",
    "vertical": "② 縦長レイアウト（手前から奥へと視線が抜ける奥行きのある構図）"
}
selected_layout_key = st.radio(
    "希望のレイアウト構図：",
    options=list(layout_styles.keys()),
    format_func=lambda x: layout_styles[x],
    horizontal=True
)

# --- 物件設定（画面からは非表示にし、裏側で「戸建て」に固定） ---
selected_property_key = "house"
selected_property_type_label = "戸建て"
selected_apt_scale = "house"

# 3. デザインテーマを「高級・ラグジュアリー」に固定
selected_style_key = "luxury"
theme_info = THEMES[selected_style_key]
custom_style_description = ""

# 4. 担当店舗の選択（ここで定義される）
st.write("---")
st.subheader("🏢 担当店舗の選択")
selected_branch_name = st.selectbox("担当店舗を選んでください：", list(BRANCH_DATA.keys()))

room_features_input = ""

# 6. スライドの向き選択
st.write("---")
st.subheader("📏 スライドの向きを選択")
orientation = st.radio("作成するパンフレットの向き：", ["横向き (Landscape)", "縦向き (Portrait)"], index=1)

# 👇👇👇 ここから追加（ページ選択UI） 👇👇👇
st.write("---")
st.subheader("🛠️ デバッグ・生成ページ設定")
st.caption("必要なページだけをチェックすると、時間とAPIコストを節約できます。")

page_options = {
    "cover": "P.1-2 表紙 (Imagen)",
    "aerial_map": "P.3 コンセプト (Placeholder)",
    "access": "P.4 地図 (Image Processing)",
    "floor_plan": "P.5 間取り (Imagen)",
    "interior_hq": "P.6 内観生成 (Imagen)",
    "interior": "P.7 ギャラリー (Layout)",
    "company": "P.8 会社案内 (Layout)"
}

selected_pages_keys = st.multiselect(
    "生成するページを選択：",
    options=list(page_options.keys()),
    default=list(page_options.keys()), # デフォルトは全選択
    format_func=lambda x: page_options[x]
)
# 👆👆👆 ここまで追加 👆👆👆

# 7. 生成ボタン（一括生成ボタン）
st.write("---")
btn_generate = st.button("🚀 パンフレットを生成する", disabled=not uploaded_file)

# 選択された店舗の詳細を取得
branch_info = BRANCH_DATA[selected_branch_name]

# --- 4. メイン処理（パンフレット一括生成） ---
gemini_client = genai.Client(api_key=gemini_api_key)

def generate_with_retry(model_name, prompt_contents, generation_config=None):
    # ✨ 修正1：待機時間を細かく、試行回数を増やしました
    wait_times = [30, 60, 120, 180, 240, 300, 360, 420, 480, 540, 600]
    max_attempts = len(wait_times) + 1
    
    # ✨ 修正2：メッセージが下に伸びないよう、専用の「入れ替え用の枠」を作ります
    warning_box = st.empty() 
    
    for attempt in range(max_attempts):
        try:
            time.sleep(2)
            if generation_config:
                res = gemini_client.models.generate_content(model=model_name, contents=prompt_contents, config=generation_config)
            else:
                res = gemini_client.models.generate_content(model=model_name, contents=prompt_contents)
            
            # 無事に生成できたら、警告メッセージの枠を消して綺麗にする
            warning_box.empty() 
            return res
            
        except Exception as inner_e:
            if ("503" in str(inner_e) or "429" in str(inner_e)) and attempt < len(wait_times):
                wait_sec = wait_times[attempt]
                # st.warningではなく、先ほど作った枠(warning_box)の中身を書き換える
                warning_box.warning(f"サーバー制限に到達しました。{wait_sec}秒待機して再試行します... (再試行 {attempt + 1}/{len(wait_times)})")
                time.sleep(wait_sec)
            else:
                # 別の致命的なエラーの場合は枠を消してエラーを投げる
                warning_box.empty()
                raise inner_e

if btn_generate and uploaded_file is not None:
    with st.status("📄 パンフレットを作成中...（約2分かかります）", expanded=True) as status:
        try:
            # --- 4-A. OCR ＆ 表紙生成 ---
            st.write("🔍 販売図面をAI（OCR）で読み取っています...")
            file_bytes = uploaded_file.getvalue()
            filename_lower = uploaded_file.name.lower()
            if filename_lower.endswith(".pdf"): mime_type = "application/pdf"
            elif filename_lower.endswith(".png"): mime_type = "image/png"
            else: mime_type = "image/jpeg"
            
            ocr_analysis = generate_with_retry(
                model_name='gemini-2.5-flash',
                prompt_contents=[
                    "図面から物件名、所在地、最寄り駅情報を正確に抽出してください。Imagen生成用の地名（市区町村）も特定してください。",
                    types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
                ]
            )
            st.session_state.pdf_text = ocr_analysis.text

            st.write("📸 表紙のデザイン案を2パターン生成中...")
            prop_type_en = "detached house" if selected_property_key == "house" else "apartment building"
            target_city_town = "Tokyo"
            if "所在地" in st.session_state.pdf_text:
                 target_city_town = st.session_state.pdf_text.split("所在地")[-1][:10]

            # ✨ 修正：LEON風のシーン設定に変更
            prompts = [
                # 案1：公園で遊ぶ幸せな4人家族
                f"High-end luxury magazine photography. A happy Japanese family (father, mother, and two children) playing happily in a beautiful sunny park in {target_city_town}. Bright natural daylight, soft sunlight filtering through trees. Modern and sophisticated casual style. NO text.",
                # 案2：昼間のリビングで寛ぐダンディな男性
                f"High-end luxury lifestyle photography. A sophisticated Japanese man relaxing and drinking coffee in a modern luxury living room with a large window view of a green garden in {target_city_town}. Bright natural daylight, morning sun, high ceiling, high-end interior. NO text."
            ]

            temp_choices = []
            for i, p in enumerate(prompts):
                img_res = gemini_client.models.generate_images(
                    model='imagen-4.0-generate-001',
                    prompt=p,
                    config=types.GenerateImagesConfig(
                        number_of_images=1, 
                        aspect_ratio="4:3" if orientation == "横向き (Landscape)" else "3:4"
                    )
                )
                temp_choices.append(Image.open(BytesIO(img_res.generated_images[0].image.image_bytes)))
            st.session_state.cover_choices = temp_choices

            # --- 4-B. 全ページデータ（JSON）の生成 ---

            st.write("AIが物件情報、指定地域、デザインテーマを分析中...")
            
            theme_info = THEMES[selected_style_key]
            current_theme_name = custom_style_description if selected_style_key == "other" else theme_info["name"]

            # ✨✨ ここから追加：マンションの外観サンプル画像を解析 ✨✨
            apt_style_prompt = ""
            if selected_property_key == "apartment":
                st.write(f"🏢 マンション規模（{selected_apt_scale}）のサンプル画像を解析中...")
                # 選択された規模に応じてファイル名を決定 (apt_low.jpg など)
                sample_img_path = f"apt_{selected_apt_scale}.jpg" 
                
                if os.path.exists(sample_img_path):
                    with open(sample_img_path, "rb") as f:
                        s_bytes = f.read()
                    try:
                        # 画像の外観特徴を英語のプロンプトに変換させる
                        analysis_apt = generate_with_retry(
                            model_name='gemini-2.5-flash',
                            prompt_contents=[
                                "Analyze this apartment building's exterior design (colors, materials, window styles, overall architectural shape). Generate a short, STRICT English prompt for an Image generation AI to create a building with a very similar architectural style. Output ONLY the English prompt string. Do NOT use markdown.",
                                types.Part.from_bytes(data=s_bytes, mime_type="image/jpeg")
                            ]
                        )
                        apt_style_prompt = analysis_apt.text.strip()
                    except Exception as e:
                        st.warning(f"マンション画像の解析エラー: {e}")
                else:
                    st.info(f"※ サンプル画像 ({sample_img_path}) が見つからないため、通常生成します。")

# --- 間取り図をAIに読み取らせる ---
            room_description = "A modern living room" # 読み取れなかった時の予備
            if madori_file:
                st.write("🔍 間取り図と入力された特徴から、強力な画像生成プロンプトを作成中...")
                m_bytes = madori_file.getvalue()
                
                # ✨ 追加：選択されたレイアウト構図の英語指示を定義
                layout_instruction = ""
                if selected_layout_key == "horizontal":
                    layout_instruction = "CAMERA ANGLE: Wide shot, landscape composition, parallel to the main window. Emphasize the horizontal breadth and spaciousness of the room. Bright, open feeling with massive windows spanning the background."
                else:
                    layout_instruction = "CAMERA ANGLE: Deep shot, one-point perspective, looking down the length of the room (e.g., from the dining area in the foreground towards the living area and window in the background). Emphasize depth and structured spatial arrangement."

                user_instruction = f"\n\n[USER'S ABSOLUTE REQUIREMENTS]\n{room_features_input}\n\n[COMPOSITION REQUIREMENT]\n{layout_instruction}"
                
                # ✨ 便利関数を使って間取り図を解析
                analysis = generate_with_retry(
                    model_name='gemini-2.5-flash',
                    prompt_contents=[
                        f"""Analyze the attached Japanese floor plan (LDK area) and generate a highly detailed, STRICT English prompt for an Image Generation AI.

{user_instruction}

[CRITICAL RULES TO OVERCOME AI BIAS]
1. Kitchen (Crucial): Image AIs always default to island kitchens. If the floor plan or user indicates a wall-mounted kitchen (壁付けキッチン), you MUST explicitly write: "single-wall kitchen, cabinets and stove placed flat against the back wall, NO island, NO peninsula, wide open floor space in front".
2. Windows: If a large window is requested, explicitly write: "massive wall-to-wall and floor-to-ceiling panoramic windows, clear view, no vertical pillars blocking the view".
3. Layout: Specify exactly where things are based on the floor plan (e.g., "kitchen on the left side, dining table in the center, large window at the far back"). Ensure it aligns perfectly with the COMPOSITION REQUIREMENT.
4. Style: Match the theme "{current_theme_name}". High-end architectural photography, 8k resolution.

[OUTPUT FORMAT]
Output ONLY the final English prompt string. Do NOT output any conversational text like "Here is the prompt". Do NOT use markdown blocks. Start directly with the description.""",
                        types.Part.from_bytes(data=m_bytes, mime_type="image/jpeg")
                    ]
                )
                room_description = analysis.text.strip()
                
            elif room_features_input:
                # 間取り図がなく、テキスト入力だけがある場合
                trans = generate_with_retry(
                    model_name='gemini-2.5-flash',
                    prompt_contents=[f"Translate the following interior design requirements into a highly detailed English prompt for an image generation AI. Output ONLY the English prompt string, no conversational text.\nRequirements: {room_features_input}\nTheme: {current_theme_name}"]
                )
                room_description = trans.text.strip()
            
            ratio_text = "4:3（横長）" if orientation == "横向き (Landscape)" else "3:4（縦長）"
            
            prompt = f"""
            あなたはプロの不動産ライターです。提供された【補助データ】を隅々まで解析し、以下の7ページ構成のパンフレット（比率 {ratio_text}）を作成してください。
            
            【データ抽出の絶対条件】
            1. **property_name_en**: 【補助データ】から物件名を特定してください。雑誌風のデザインにするため、可能な限り英語表記にするか、読みをアルファベットに変換してください。（例：ラ・フレーズ国分寺 → La Phrase Kokubunji）
            2. **city_town**: 物件の「所在地」から市区町村と町名を抽出してください。（例：東京都府中市美好町... → 府中市 美好町）
            3. **station_info**: 「交通」の項目から、最も主要な駅名と徒歩分数を抽出してください。改行を入れて見やすくしてください。（例：中央線 国分寺駅 徒歩5分 → 国分寺駅\n徒歩5分）
            4. **price**: 販売価格を抽出してください。
            5. **land_area**: 【補助データ】から土地面積を抽出してください。「土地」という文字と「㎡」単位を含めてください。（例：土地 100.77㎡）
            6. **building_area**: 【補助データ】から建物面積を抽出してください。「建物」という文字と「㎡」単位を含めてください。（例：建物 100.77㎡）
            7. **price_jp**: 【補助データ】から価格を日本語表記（万円単位）で抽出してください。（例：3,650万円）
            8. **デザインスタイル**: {current_theme_name} の雰囲気に合わせた魅力的な言葉選びをしてください。
            9. **property_name_jp**: 【補助データ】のOCRテキストの中から、最も目立つ場所に書かれている名称（通常はタイトル）、または物件概要欄から特定される物件名を日本語表記で特定し、抽出してください。（例：ラ・フレーズ国分寺）
            10. **city_town_clean**: 【補助データ】の所在地から市区町村と町名を抽出し、余計な文字（東京都など）を省いてください（例：府中市美好町）。これをImagen生成用に保持します。

            出力は必ず以下のJSON配列形式のみにしてください。
            [
              {{
                "page": 1, "type": "cover",
                "price": "抽出した価格", 
                "property_name_en": "抽出・変換した物件名（英字）", 
                "property_name_jp": "抽出した物件名（日本語）",
                "sub_copy": "テーマに合わせた洗練されたサブコピー（日本語）",
                "city_town": "抽出した地域名（例：府中市 美好町）",
                "station_info": "抽出した駅名と徒歩分数（例：国分寺駅\\n徒歩5分）"
              }},
              {{
                "page": 2, "type": "aerial_map",
                "headline": "FUTURE VISION", 
                "sub_headline": "未来を描く",
                "main_text": "【補助データ】の周辺環境情報を基に、このテーマの客層に刺さる紹介文を3〜4行で作成してください。",
                "city_town_clean": "抽出したImagen用地域名（例：府中市美好町）"
              }},
              {{
                "page": 3, "type": "access", "headline": "MAP & ACCESS", 
                "source_pdf_page": 1, 
                "access_info": "【補助データ】から交通アクセス情報（路線・駅名・徒歩分数など）を箇条書きで抽出してください。",
                "life_info": "【補助データ】の「周辺施設」などの項目から、施設名と距離（徒歩〇分など）を箇条書きで漏れなく抽出してください。"
              }},
              {{
                "page": 4, "type": "floor_plan",
                "property_name_jp": "抽出した物件名（日本語）",
                "land_area": "抽出した土地面積（例：土地 --- ㎡）",
                "building_area": "抽出した建物面積（例：建物 --- ㎡）",
                "price_jp": "抽出した価格（日本語表記、例：--- 万円）"
              }},
              {{
                "page": 5, "type": "interior_hq", "headline": "INTERIOR VISION", 
                "sub_headline": "間取り図から描き出した完成予想イメージ"
              }},
              {{
                "page": 6, "type": "interior", "headline": "内観ギャラリー", "source_pdf_page": 1 
              }},
              {{ 
                "page": 7, "type": "company", 
                "company_name": "{branch_info['full_name']}",
                "license": "{branch_info['license']}",
                "address": "{branch_info['address']}",
                "tel": "{branch_info['tel']}"
              }}
            ]
            
            【補助データ（図面から抽出されたテキスト）】:
            {st.session_state.pdf_text}
            """
            
            # ✨ 便利関数を使ってJSON（文章）を生成
            response = generate_with_retry(
                model_name='gemini-2.5-flash', 
                prompt_contents=prompt, 
                generation_config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            
            raw_json = response.text.strip()
            if raw_json.startswith("```json"): 
                raw_json = raw_json[7:-3].strip()
            elif raw_json.startswith("```"): 
                raw_json = raw_json[3:-3].strip()
                
            st.session_state.ai_data = json.loads(raw_json)
            
            # --- 描画用のヘルパー関数群 ---
            # ✨ 修正：PDFだけでなくJPG画像にも対応させた関数
            def get_source_image(file_bytes, filename, target_page_num):
                filename_lower = filename.lower()
                if filename_lower.endswith(".pdf"):
                    doc_temp = fitz.open(stream=file_bytes, filetype="pdf")
                    p_num = max(0, min(target_page_num, doc_temp.page_count - 1))
                    pix = doc_temp.load_page(p_num).get_pixmap(matrix=fitz.Matrix(2.5, 2.5))
                    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                else:
                    return Image.open(BytesIO(file_bytes)).convert("RGB")

            def get_fitting_font(draw_obj, text, initial_size, max_width):
                size = initial_size
                try: 
                    font = ImageFont.truetype(FONT_PATH, size)
                except: 
                    return ImageFont.load_default()
                while draw_obj.textbbox((0, 0), text, font=font)[2] > max_width and size > 10:
                    size -= 2
                    font = ImageFont.truetype(FONT_PATH, size)
                return font

            def draw_dashed_rectangle(draw, rect, outline="gray", width=2):
                x1, y1, x2, y2 = rect
                dash = 10
                for x in range(int(x1), int(x2), dash * 2): draw.line([(x, y1), (min(x + dash, x2), y1)], fill=outline, width=width)
                for x in range(int(x1), int(x2), dash * 2): draw.line([(x, y2), (min(x + dash, x2), y2)], fill=outline, width=width)
                for y in range(int(y1), int(y2), dash * 2): draw.line([(x1, y), (x1, min(y + dash, y2))], fill=outline, width=width)
                for y in range(int(y1), int(y2), dash * 2): draw.line([(x2, y), (x2, min(y + dash, y2))], fill=outline, width=width)

            # ✨修正：画像単体ではなく、ページデータとセット（タプル）で保存するリストに変更
            generated_pages_with_data = [] 
            
            # 向きに合わせてキャンバスサイズを入れ替える
            if orientation == "横向き (Landscape)":
                width, height = 1024, 768
            else:
                width, height = 768, 1024
            
            theme_bg = theme_info["bg_color"]
            theme_tc = theme_info["text_color"]
            theme_ac = theme_info["accent_color"]

            for page_data in st.session_state.ai_data:
                p_type = page_data['type']
                
                # ✨修正：選択されていないページは完全にスキップ（ダミー画像も入れない）
                if p_type not in selected_pages_keys:
                    st.write(f"⏭️ {page_data['page']}ページ目（{p_type}）はスキップします")
                    continue

                st.write(f"🖼️ {page_data['page']}ページ目（{p_type}）を合成中...")
                bg_image = None
                
# ────────── ① 表紙（生成した2パターンを両方とも追加する） ──────────
                if p_type == 'cover':
                    if st.session_state.cover_choices:
                        bg_image1 = st.session_state.cover_choices[0].copy().resize((width, height))
                        bg_image2 = st.session_state.cover_choices[1].copy().resize((width, height))
                        generated_pages_with_data.append((page_data, bg_image1))
                        generated_pages_with_data.append((page_data, bg_image2))
                    else:
                        bg_image = Image.new('RGB', (width, height), color=theme_bg)
                        generated_pages_with_data.append((page_data, bg_image))
                        generated_pages_with_data.append((page_data, bg_image.copy()))
                    continue # 表紙はここで追加完了したので、この下の処理をスキップ
                
                # ────────── ② コンセプト（旧：空撮地図） ──────────
                elif page_data['type'] == 'aerial_map':
                    st.write(f"🎨 コンセプトページのレイアウトを作成中...")

                    # ✨ 修正：AIによる画像生成をスキップし、PowerPoint側でプレースホルダーになるように設定
                    st.session_state.concept_img = None

                    # ✨ プレビュー画面用の背景（スッキリ分割レイアウト）
                    bg_image = Image.new('RGB', (width, height), color=(245, 240, 225)) # 上品なベージュ背景
                    draw = ImageDraw.Draw(bg_image)
                    
                    bronze_color = (215, 185, 140)
                    gray_color = (235, 235, 235)
                    
                    if orientation == "横向き (Landscape)":
                        # メイン画像枠をグレーで塗る（右半分）
                        draw.rectangle([(int(width * 0.45), 0), (width, height)], fill=gray_color)
                        # 写真1, 2の枠
                        frames = [
                            (width*0.3, height*0.6, width*0.55, height*0.86),
                            (width*0.75, height*0.06, width*0.95, height*0.4)
                        ]
                        # 装飾直線
                        draw.line([(width*0.05, height*0.17), (width*0.45, height*0.17)], fill=bronze_color, width=2)
                        
                        # テキスト位置
                        head_y, sub_y, main_y = height*0.06, height*0.21, height*0.33
                    else:
                        # 縦向き：メイン画像枠をグレーで塗る（下半分）
                        draw.rectangle([(0, int(height * 0.45)), (width, height)], fill=gray_color)
                        # 写真1, 2の枠
                        frames = [
                            (width*0.6, height*0.35, width*0.93, height*0.55),
                            (width*0.06, height*0.75, width*0.39, height*0.95)
                        ]
                        # 装飾直線
                        draw.line([(width*0.05, height*0.17), (width*0.95, height*0.17)], fill=bronze_color, width=2)
                        
                        # テキスト位置
                        head_y, sub_y, main_y = height*0.06, height*0.21, height*0.33

                    # サブ写真枠をプレビューに描画
                    for f in frames:
                        draw.rectangle(f, fill=(245, 245, 245), outline=bronze_color, width=2)

                    # --- テキスト描画 ---
                    try:
                        font_head = ImageFont.truetype(FONT_PATH, int(height * 0.05))
                        font_subhead = ImageFont.truetype(FONT_PATH, int(height * 0.035))
                        font_main = ImageFont.truetype(FONT_PATH, int(height * 0.018))
                    except:
                        font_head = font_subhead = font_main = ImageFont.load_default()

                    headline = "THE CONCEPT"
                    sub_headline = page_data.get('sub_headline', '五感を満たす、静謐の邸宅。')
                    main_text = page_data.get('main_text', '')

                    draw.text((width*0.05, head_y), headline, font=font_head, fill="black", anchor="la")
                    draw.text((width*0.05, sub_y), sub_headline, font=font_subhead, fill="black", anchor="la")
                    draw.multiline_text((width*0.05, main_y), main_text, font=font_main, fill=(80, 80, 80), spacing=8)

                # ────────── ③ アクセス・地図 ──────────
                elif page_data['type'] == 'access':
                    st.write(f"🎨 MAP & ACCESSの背景画像をAIで生成中...")
                    try:
                        # Imagenによるエレガントな背景の生成
                        image_result = gemini_client.models.generate_images(
                            model='imagen-4.0-generate-001',
                            prompt="A simple, elegant and abstract background for a luxury real estate map and access page. Clean white and soft gold geometric accents, minimal, premium corporate design, no text, no logos.",
                            config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="4:3" if orientation == "横向き (Landscape)" else "3:4")
                        )
                        generated_bytes = image_result.generated_images[0].image.image_bytes
                        bg_image = Image.open(BytesIO(generated_bytes)).convert("RGB").resize((width, height))
                    except Exception as e:
                        st.warning(f"3ページ目の画像生成エラー: {e}")
                        bg_image = Image.new('RGB', (width, height), color=(250, 250, 250))

                    # 画面全体に「白い半透明のフィルター」を強めに被せて、上に乗る文字や地図を見やすくする
                    overlay = Image.new('RGBA', bg_image.size, (255, 255, 255, 220)) 
                    bg_image = Image.alpha_composite(bg_image.convert('RGBA'), overlay).convert('RGB')
                    
                # ────────── ④ 間取り図 ──────────
                elif page_data['type'] == 'floor_plan':
                    st.write(f"🎨 間取り図ページの高級背景をAIで生成中...")
                    
                    # 1. AI（Imagen）でゴージャスな背景テクスチャを生成
                    # ✨修正：AIには線を描かせず、テクスチャ（石と木）だけを生成させる
                    bg_prompt = (
                        "A luxurious architectural background for a real estate floor plan. "
                        "Top 20% area: dark charcoal gray slate stone texture. "
                        "Bottom 80% area: seamless, rich, dark vertical espresso wood grain texture. "
                        "High-end, sophisticated, dark and moody, empty background, NO gold lines, NO borders, NO text, NO floor plan drawings."
                    )
                    
                    try:
                        image_result = gemini_client.models.generate_images(
                            model='imagen-4.0-generate-001',
                            prompt=bg_prompt,
                            config=types.GenerateImagesConfig(
                                number_of_images=1, 
                                aspect_ratio="4:3" if orientation == "横向き (Landscape)" else "3:4"
                            )
                        )
                        generated_bytes = image_result.generated_images[0].image.image_bytes
                        bg_image = Image.open(BytesIO(generated_bytes)).convert("RGB").resize((width, height))
                    except Exception as e:
                        st.warning(f"4ページ目の背景生成エラー: {e}")
                        bg_image = Image.new('RGB', (width, height), color=(35, 30, 25))

                    draw = ImageDraw.Draw(bg_image)
                    header_h = int(height * 0.20) # 上から20%の固定位置に設定

                    # ✨修正：ゴールドの棒線をプログラムで正確な位置に直接描画する
                    gold_light = (215, 185, 140)
                    gold_dark = (180, 150, 80)
                    draw.rectangle([(0, header_h - 12), (width, header_h + 12)], fill=gold_light)
                    draw.rectangle([(0, header_h - 8), (width, header_h + 8)], fill=gold_dark) # 立体感を出す

                    # 2. ユーザーがアップロードした正確な間取り図を配置
                    if madori_file:
                        m_img = Image.open(madori_file).convert("RGB")
                        
                        # 間取り図の周りにゴールドの太い装飾フレームをつける
                        frame_width = 15
                        m_img_with_frame = Image.new('RGB', (m_img.width + frame_width*2, m_img.height + frame_width*2), gold_light)
                        
                        # フレームの内側に少し暗い線を入れて立体感を出す
                        draw_frame = ImageDraw.Draw(m_img_with_frame)
                        draw_frame.rectangle([(5, 5), (m_img_with_frame.width-5, m_img_with_frame.height-5)], outline=(120, 90, 40), width=3)
                        
                        m_img_with_frame.paste(m_img, (frame_width, frame_width))
                        # ✨修正：間取り図が棒線に被らないよう、最大サイズを調整
                        m_img_with_frame.thumbnail((width * 0.85, height * 0.70))
                        
                        p_x = (width - m_img_with_frame.width) // 2
                        # ✨修正：間取り図の配置Y座標を、確実に棒線より下に指定する
                        p_y = header_h + 30 + (height - header_h - 30 - m_img_with_frame.height) // 2
                        bg_image.paste(m_img_with_frame, (int(p_x), int(p_y)))
                    else:
                        draw.text((width/2, height/2), "間取り図がアップロードされていません", fill="white", anchor="mm")
                
                # ────────── ⑤ 内観（間取り図を基にAI生成） ──────────
                elif page_data['type'] == 'interior_hq':
                    st.write(f"🎨 間取り図に合わせたお部屋を生成中...")
                    try:
                        image_result = gemini_client.models.generate_images(
                            model='imagen-4.0-generate-001',
                            prompt=room_description,
                            config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="4:3" if orientation == "横向き (Landscape)" else "3:4")
                        )
                        generated_bytes = image_result.generated_images[0].image.image_bytes
                        bg_image = Image.open(BytesIO(generated_bytes)).convert("RGB").resize((width, height))
                    except Exception as e:
                        st.error(f"内観生成エラー: {e}")
                        bg_image = Image.new('RGB', (width, height), color=(240, 240, 240))

                    # ✨ 画像の下部にシックな半透明帯を配置し、高級感を演出
                    overlay = Image.new('RGBA', bg_image.size, (0, 0, 0, 0))
                    draw_ov = ImageDraw.Draw(overlay)
                    draw_ov.rectangle([(0, height * 0.82), (width, height)], fill=(0, 0, 0, 180))
                    draw_ov.line([(0, height * 0.82), (width, height * 0.82)], fill=theme_ac + (255,), width=4)
                    bg_image = Image.alpha_composite(bg_image.convert('RGBA'), overlay).convert('RGB')
                    
                    draw = ImageDraw.Draw(bg_image)
                    f_h = get_fitting_font(draw, "INTERIOR VISION", int(height * 0.07), width * 0.5)
                    sub_text = page_data.get('sub_headline', '')
                    f_s = get_fitting_font(draw, sub_text, int(height * 0.03), width * 0.4)
                    draw.text((width*0.05, height*0.87), "INTERIOR VISION", font=f_h, fill="white", anchor="la")
                    draw.text((width*0.95, height*0.90), sub_text, font=f_s, fill="white", anchor="ra")
                
                # ────────── ⑥ 内観ギャラリー ──────────
                elif page_data['type'] == 'interior':
                    # ✨ 4ページ目と同じスタイリッシュなヘッダー
                    bg_image = Image.new('RGB', (width, height), color=theme_bg)
                    draw = ImageDraw.Draw(bg_image)
                    header_h = int(height * 0.15)
                    draw.line([(0, header_h), (width, header_h)], fill=theme_ac, width=4)
                    
                    f_h = get_fitting_font(draw, "INTERIOR GALLERY", int(height * 0.07), width * 0.5)
                    f_s = get_fitting_font(draw, "内観ギャラリー", int(height * 0.025), width * 0.4)
                    text_fill = "black" if theme_tc == "black" else "white"
                    draw.text((width*0.05, height*0.04), "INTERIOR GALLERY", font=f_h, fill=text_fill, anchor="la")
                    draw.text((width*0.05, height*0.11), "内観ギャラリー", font=f_s, fill=theme_ac, anchor="la")

                # ────────── ⑦ 会社案内 ──────────
                elif page_data['type'] == 'company':
                    bg_image = Image.new('RGB', (width, height), color='white')
                    # ✨ 枠の焼き付けを削除しました

                if bg_image:
                    generated_pages_with_data.append((page_data, bg_image))

            st.session_state.finished_pages = generated_pages_with_data
            status.update(label="✅ 全ページが完成しました！", state="complete", expanded=False)

        except Exception as e:
            st.error(f"作成中にエラーが発生しました: {e}")
            st.stop()

# --- 5. 画面表示とPowerPoint作成 ---
if st.session_state.finished_pages:
    # ✨ 追加：PowerPoint作成時にも、選んだテーマの文字色を認識させる
    theme_info = THEMES[selected_style_key]
    theme_tc = theme_info["text_color"]

    st.write("---")
    st.subheader("🎉 完成したパンフレット")
    
    # ✨修正：1枚だけ生成した場合に巨大化しないよう、最低でも5分割のサイズに抑える
    num_cols = max(len(st.session_state.finished_pages), 5)
    cols = st.columns(num_cols)
    
    # ブラウザ上に完成した画像を並べて表示する
    for i, (page_data, page_img) in enumerate(st.session_state.finished_pages):
        with cols[i]:
            st.write(f"**{page_data['type']}**")
            st.image(page_img, use_container_width=True)
            
    # パワポファイルの作成準備と、サイズ（縦・横）の設定
    prs = Presentation()
    if orientation == "横向き (Landscape)":
        prs.slide_width, prs.slide_height = Inches(10), Inches(7.5)
    else:
        prs.slide_width, prs.slide_height = Inches(7.5), Inches(10)
    
    # ✨ PowerPoint上に「自由に動かせる枠」を作るための便利機能
    def add_placeholder_box(slide_obj, left, top, width, height, text):
        tx_box = slide_obj.shapes.add_textbox(left, top, width, height)
        tx_box.fill.solid()
        tx_box.fill.fore_color.rgb = RGBColor(245, 245, 245)
        tx_box.line.color.rgb = RGBColor(210, 210, 210) 
        tx_box.line.width = Pt(1)
        tf = tx_box.text_frame
        tf.word_wrap = True
        tf.clear()
        p_en = tf.add_paragraph()
        p_en.text = "IMAGE PLACEHOLDER"
        p_en.font.size = Pt(11)
        p_en.font.bold = True
        p_en.font.color.rgb = RGBColor(170, 170, 170)
        p_en.alignment = PP_ALIGN.CENTER
        p_jp = tf.add_paragraph()
        clean_text = text.replace("【", "").replace("】", "").replace(" ", "")
        p_jp.text = clean_text
        p_jp.font.size = Pt(9)
        p_jp.font.color.rgb = RGBColor(140, 140, 140)
        p_jp.alignment = PP_ALIGN.CENTER

    # ✨ 駅徒歩用の円形グラフィック機能
    def add_station_info_circle(slide_obj, x, y, radius, text, color=(245, 240, 225)):
        circle = slide_obj.shapes.add_shape(MSO_SHAPE.OVAL, x, y, radius*2, radius*2)
        circle.fill.solid()
        circle.fill.fore_color.rgb = RGBColor(20, 20, 20)
        circle.line.color.rgb = RGBColor(color[0], color[1], color[2]) 
        circle.line.width = Pt(1.5)
        tf = circle.text_frame
        tf.word_wrap = True
        tf.clear()
        p = tf.add_paragraph()
        p.text = text
        p.font.size = Pt(11)
        p.font.color.rgb = RGBColor(color[0], color[1], color[2]) 
        p.font.name = "游明朝"
        p.alignment = PP_ALIGN.CENTER
        tf.margin_bottom = tf.margin_left = tf.margin_right = tf.margin_top = Inches(0.05)

    # --- ✨修正：インデックス番号ではなく、page_dataのタイプでパワポを作成する ---
    for i, (page_data, page_img) in enumerate(st.session_state.finished_pages):
        p_type = page_data['type']
        slide = prs.slides.add_slide(prs.slide_layouts[6]) 
        
        img_io = BytesIO()
        page_img.save(img_io, format='PNG')
        img_io.seek(0)
        
        # aerial_map以外は背景画像を貼り付ける
        if p_type != 'aerial_map':
            slide.shapes.add_picture(img_io, 0, 0, width=prs.slide_width, height=prs.slide_height)

        # ────────── ① 表紙 ──────────
        if p_type == 'cover':
            prop_name = page_data.get('property_name_jp', '物件名') 
            address_text = page_data.get('city_town', '') 
            sub_copy = page_data.get('sub_copy', '') 
            station_info = page_data.get('station_info', '').replace('\\n', '\n')

            sw = prs.slide_width
            sh = prs.slide_height
            gold_color = RGBColor(215, 185, 140)
            luxury_font = "游明朝"

            top_bar_h = Inches(1.8) if orientation == "横向き (Landscape)" else Inches(2.2)
            top_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, sw, top_bar_h)
            top_bar.fill.solid()
            top_bar.fill.fore_color.rgb = RGBColor(20, 20, 20)
            try: top_bar.fill.transparency = 0.4
            except: pass
            top_bar.line.fill.background() 

            bottom_bar_h = Inches(1.2) if orientation == "横向き (Landscape)" else Inches(1.5)
            bottom_bar_y = sh - bottom_bar_h
            bottom_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, bottom_bar_y, sw, bottom_bar_h)
            bottom_bar.fill.solid()
            bottom_bar.fill.fore_color.rgb = RGBColor(20, 20, 20)
            try: bottom_bar.fill.transparency = 0.4
            except: pass
            bottom_bar.line.fill.background()

            tx_addr = slide.shapes.add_textbox(Inches(0.4), Inches(0.25), Inches(4.0), Inches(0.4))
            p_addr = tx_addr.text_frame.paragraphs[0]
            p_addr.text = address_text
            p_addr.font.size = Pt(13)
            p_addr.font.name = luxury_font
            p_addr.font.color.rgb = RGBColor(230, 230, 230)
            p_addr.alignment = PP_ALIGN.LEFT

            logo_y = Inches(0.6)
            if len(prop_name) > 15:
                logo_font_size = Pt(36) if orientation == "横向き (Landscape)" else Pt(32)
            elif len(prop_name) > 10:
                logo_font_size = Pt(48) if orientation == "横向き (Landscape)" else Pt(42)
            else:
                logo_font_size = Pt(60) if orientation == "横向き (Landscape)" else Pt(54)

            tx_logo = slide.shapes.add_textbox(Inches(0.35), logo_y, sw - Inches(0.8), Inches(2.0))
            tf_logo = tx_logo.text_frame
            tf_logo.word_wrap = False
            p_logo = tf_logo.paragraphs[0]
            p_logo.text = prop_name
            p_logo.font.size = logo_font_size
            p_logo.font.bold = True
            p_logo.font.name = luxury_font
            p_logo.font.color.rgb = gold_color
            p_logo.alignment = PP_ALIGN.LEFT

            sub_y = bottom_bar_y + Inches(0.3)
            tx_sub = slide.shapes.add_textbox(Inches(1.5), sub_y, sw - Inches(1.8), Inches(1.0))
            tf_sub = tx_sub.text_frame
            tf_sub.word_wrap = True
            p_sub = tf_sub.paragraphs[0]
            p_sub.text = sub_copy
            p_sub.font.size = Pt(13)
            p_sub.font.name = luxury_font
            p_sub.font.color.rgb = RGBColor(240, 240, 240)
            p_sub.alignment = PP_ALIGN.CENTER

            circle_y = bottom_bar_y - Inches(0.5)
            add_station_info_circle(slide, Inches(0.4), circle_y, Inches(0.55), station_info, color=(215, 185, 140))

        # ────────── ② コンセプト ──────────
        elif p_type == 'aerial_map':
            background = slide.background
            fill = background.fill
            fill.solid()
            fill.fore_color.rgb = RGBColor(245, 240, 225)
            
            headline = "THE CONCEPT"
            sub_headline = page_data.get('sub_headline', '五感を満たす、静謐の邸宅。')
            main_text = page_data.get('main_text', '')
            bronze_rgb = RGBColor(215, 185, 140)
            headline_font = "Arial"
            main_font = "游ゴシック"
            
            if orientation == "横向き (Landscape)":
                tx_box_head = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(4.5), Inches(0.6))
                line1 = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(1.3), Inches(4.5), Pt(1))
                line1.fill.solid()
                line1.fill.fore_color.rgb = bronze_rgb
                line1.line.color.rgb = bronze_rgb
                tx_box_sub = slide.shapes.add_textbox(Inches(0.5), Inches(1.6), Inches(4.5), Inches(0.6))
                tx_box_main = slide.shapes.add_textbox(Inches(0.5), Inches(2.5), Inches(4.0), Inches(3.0))
                
                if "concept_img" in st.session_state and st.session_state.concept_img:
                    img_io_concept = BytesIO()
                    st.session_state.concept_img.save(img_io_concept, format='PNG')
                    img_io_concept.seek(0)
                    slide.shapes.add_picture(img_io_concept, Inches(4.5), Inches(0), width=Inches(5.5), height=Inches(7.5))
                else:
                    add_placeholder_box(slide, Inches(4.5), Inches(0), Inches(5.5), Inches(7.5), "メイン画像")
                add_placeholder_box(slide, Inches(3.0), Inches(4.5), Inches(2.5), Inches(2.0), "写真1")
                add_placeholder_box(slide, Inches(7.5), Inches(0.5), Inches(2.0), Inches(2.5), "写真2")
            else:
                tx_box_head = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(6.5), Inches(0.6))
                line1 = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(1.3), Inches(6.5), Pt(1))
                line1.fill.solid()
                line1.fill.fore_color.rgb = bronze_rgb
                line1.line.color.rgb = bronze_rgb
                tx_box_sub = slide.shapes.add_textbox(Inches(0.5), Inches(1.6), Inches(6.5), Inches(0.6))
                tx_box_main = slide.shapes.add_textbox(Inches(0.5), Inches(2.5), Inches(6.5), Inches(1.5))
                
                if "concept_img" in st.session_state and st.session_state.concept_img:
                    img_io_concept = BytesIO()
                    st.session_state.concept_img.save(img_io_concept, format='PNG')
                    img_io_concept.seek(0)
                    slide.shapes.add_picture(img_io_concept, Inches(0), Inches(4.5), width=Inches(7.5), height=Inches(5.5))
                else:
                    add_placeholder_box(slide, Inches(0), Inches(4.5), Inches(7.5), Inches(5.5), "メイン画像")
                add_placeholder_box(slide, Inches(4.5), Inches(3.5), Inches(2.5), Inches(2.0), "写真1")
                add_placeholder_box(slide, Inches(0.5), Inches(7.5), Inches(2.5), Inches(2.0), "写真2")

            tf_head = tx_box_head.text_frame
            p_head = tf_head.paragraphs[0]
            p_head.text = headline
            p_head.font.name = headline_font
            p_head.font.size = Pt(36)
            p_head.font.bold = True
            p_head.font.color.rgb = RGBColor(0,0,0)

            tf_sub = tx_box_sub.text_frame
            p_sub = tf_sub.paragraphs[0]
            p_sub.text = sub_headline
            p_sub.font.name = main_font
            p_sub.font.size = Pt(24)
            p_sub.font.bold = True
            p_sub.font.color.rgb = RGBColor(0,0,0)

            tf_main = tx_box_main.text_frame
            tf_main.word_wrap = True
            p_main = tf_main.paragraphs[0]
            p_main.text = main_text
            p_main.font.name = main_font
            p_main.font.size = Pt(13)
            p_main.font.color.rgb = RGBColor(80,80,80)

        # ────────── ③ MAP & ACCESS ──────────
        elif p_type == 'access':
            acc_text = page_data.get('access_info')
            if not acc_text: acc_text = "交通情報がありません"
            elif isinstance(acc_text, list): acc_text = "\n".join(str(x) for x in acc_text)
            else: acc_text = str(acc_text)

            life_text = page_data.get('life_info')
            if not life_text: life_text = "周辺施設情報がありません"
            elif isinstance(life_text, list): life_text = "\n".join(str(x) for x in life_text)
            else: life_text = str(life_text)

            gold_color = RGBColor(180, 150, 80)
            navy_color = RGBColor(20, 30, 60)
            text_color_rgb = RGBColor(40, 40, 40)
            
            gen_map_io = None
            if map_file:
                from PIL import ImageOps, ImageEnhance
                try:
                    map_img = Image.open(map_file).convert("RGB")
                    gray_img = map_img.convert("L")
                    inverted_img = ImageOps.invert(gray_img)
                    navy_bg = (15, 25, 45)
                    gold_line = (215, 185, 140)
                    styled_map = ImageOps.colorize(inverted_img, black=navy_bg, white=gold_line)
                    enhancer = ImageEnhance.Contrast(styled_map)
                    final_map = enhancer.enhance(1.3)
                    gen_map_io = BytesIO()
                    final_map.save(gen_map_io, format='PNG')
                    gen_map_io.seek(0)
                except Exception as e:
                    pass

            if orientation == "横向き (Landscape)":
                tx_box_head = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(5.0), Inches(0.8))
                tx_box_sub = slide.shapes.add_textbox(Inches(0.5), Inches(1.1), Inches(5.0), Inches(0.4))
                line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(1.5), Inches(9.0), Pt(1.5))
                line.fill.solid()
                line.fill.fore_color.rgb = gold_color
                line.line.color.rgb = gold_color

                if gen_map_io:
                    slide.shapes.add_picture(gen_map_io, Inches(0.5), Inches(1.7), width=Inches(9.0), height=Inches(4.2))
                else:
                    add_placeholder_box(slide, Inches(0.5), Inches(1.7), Inches(9.0), Inches(4.2), "【 MAP画像 挿入枠 】\n※画像をアップロードすると自動で高級な地図が生成されます")

                tx_box_acc = slide.shapes.add_textbox(Inches(0.5), Inches(6.1), Inches(4.3), Inches(1.2))
                tx_box_life = slide.shapes.add_textbox(Inches(5.2), Inches(6.1), Inches(4.3), Inches(1.2))
            else:
                tx_box_head = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(6.5), Inches(0.8))
                tx_box_sub = slide.shapes.add_textbox(Inches(0.5), Inches(1.2), Inches(6.5), Inches(0.4))
                line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(1.6), Inches(6.5), Pt(1.5))
                line.fill.solid()
                line.fill.fore_color.rgb = gold_color
                line.line.color.rgb = gold_color

                if gen_map_io:
                    slide.shapes.add_picture(gen_map_io, Inches(0.5), Inches(1.8), width=Inches(6.5), height=Inches(5.0))
                else:
                    add_placeholder_box(slide, Inches(0.5), Inches(1.8), Inches(6.5), Inches(5.0), "【 MAP画像 挿入枠 】\n※画像をアップロードすると自動で高級な地図が生成されます")
                
                tx_box_acc = slide.shapes.add_textbox(Inches(0.5), Inches(7.0), Inches(3.1), Inches(2.5))
                tx_box_life = slide.shapes.add_textbox(Inches(3.9), Inches(7.0), Inches(3.1), Inches(2.5))

            tf_head = tx_box_head.text_frame
            p_head = tf_head.paragraphs[0]
            p_head.text = "MAP & ACCESS"
            p_head.font.size = Pt(40)
            p_head.font.bold = True
            p_head.font.color.rgb = navy_color
            p_head.font.name = "Arial"

            tf_sub = tx_box_sub.text_frame
            p_sub = tf_sub.paragraphs[0]
            p_sub.text = "周辺環境・アクセス"
            p_sub.font.size = Pt(20)
            p_sub.font.bold = True
            p_sub.font.color.rgb = gold_color
            p_sub.font.name = "游ゴシック"

            tf_acc = tx_box_acc.text_frame
            tf_acc.word_wrap = True
            tf_acc.clear() 
            p_acc_head = tf_acc.add_paragraph()
            p_acc_head.text = "■ 交通アクセス"
            p_acc_head.font.size = Pt(16)
            p_acc_head.font.bold = True
            p_acc_head.font.color.rgb = gold_color 
            p_acc_head.font.name = "游ゴシック"
            p_acc_body = tf_acc.add_paragraph()
            p_acc_body.text = acc_text
            p_acc_body.font.size = Pt(13)
            p_acc_body.font.color.rgb = text_color_rgb 
            p_acc_body.font.name = "游ゴシック"

            tf_life = tx_box_life.text_frame
            tf_life.word_wrap = True
            tf_life.clear() 
            p_life_head = tf_life.add_paragraph()
            p_life_head.text = "■ Life Information"
            p_life_head.font.size = Pt(16)
            p_life_head.font.bold = True
            p_life_head.font.color.rgb = gold_color 
            p_life_head.font.name = "Arial"
            p_life_body = tf_life.add_paragraph()
            p_life_body.text = life_text
            p_life_body.font.size = Pt(13)
            p_life_body.font.color.rgb = text_color_rgb
            p_life_body.font.name = "游ゴシック"

        # ────────── ④ 間取り図 ──────────
        elif p_type == 'floor_plan':
            prop_name_jp = page_data.get('property_name_jp', '物件名')
            land_area = page_data.get('land_area', '')
            building_area = page_data.get('building_area', '')
            price_jp = page_data.get('price_jp', '--- 万円')

            if "情報なし" in land_area or "未定" in land_area: land_area = ""
            if "情報なし" in building_area or "未定" in building_area: building_area = ""
            
            if orientation == "横向き (Landscape)":
                tb_title = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(6.0), Inches(0.8))
                tb_area = slide.shapes.add_textbox(Inches(6.5), Inches(0.1), Inches(3.0), Inches(0.4))
                tb_price = slide.shapes.add_textbox(Inches(6.5), Inches(0.5), Inches(3.0), Inches(0.6))
            else:
                tb_title = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(4.0), Inches(0.8))
                tb_area = slide.shapes.add_textbox(Inches(4.5), Inches(0.1), Inches(2.5), Inches(0.5))
                tb_price = slide.shapes.add_textbox(Inches(4.5), Inches(0.6), Inches(2.5), Inches(0.8))
            
            gold_text_color = RGBColor(160, 130, 80)
            
            tf_title = tb_title.text_frame
            p_title = tf_title.paragraphs[0]
            p_title.text = prop_name_jp
            p_title.font.size = Pt(28)
            p_title.font.color.rgb = gold_text_color 
            p_title.font.bold = True
            p_title.font.name = "游明朝"
            
            tf_area = tb_area.text_frame
            p_area1 = tf_area.paragraphs[0]
            p_area1.text = land_area
            p_area1.font.size = Pt(12)
            p_area1.font.color.rgb = gold_text_color 
            p_area1.alignment = PP_ALIGN.RIGHT
            if building_area:
                p_area2 = tf_area.add_paragraph()
                p_area2.text = building_area
                p_area2.font.size = Pt(12)
                p_area2.font.color.rgb = gold_text_color 
                p_area2.alignment = PP_ALIGN.RIGHT
            
            tf_price = tb_price.text_frame
            p_price = tf_price.paragraphs[0]
            p_price.text = price_jp
            p_price.font.size = Pt(32)
            p_price.font.color.rgb = gold_text_color 
            p_price.font.bold = True
            p_price.font.name = "游明朝"
            p_price.alignment = PP_ALIGN.RIGHT

        # ────────── ⑥ 内観ギャラリー ──────────
        elif p_type == 'interior':
            if orientation == "横向き (Landscape)":
                add_placeholder_box(slide, Inches(0.5), Inches(1.1), Inches(9.0), Inches(3.0), "【 メイン画像 挿入枠 】\n※自由にサイズ変更・削除できます")
                add_placeholder_box(slide, Inches(0.5), Inches(4.3), Inches(4.3), Inches(1.4), "【 サブ画像 】")
                add_placeholder_box(slide, Inches(5.2), Inches(4.3), Inches(4.3), Inches(1.4), "【 サブ画像 】")
                add_placeholder_box(slide, Inches(0.5), Inches(5.9), Inches(4.3), Inches(1.4), "【 サブ画像 】")
                add_placeholder_box(slide, Inches(5.2), Inches(5.9), Inches(4.3), Inches(1.4), "【 サブ画像 】")
            else:
                add_placeholder_box(slide, Inches(0.5), Inches(1.5), Inches(6.5), Inches(4.0), "【 メイン画像 挿入枠 】\n※自由にサイズ変更・削除できます")
                add_placeholder_box(slide, Inches(0.5), Inches(5.7), Inches(3.1), Inches(1.8), "【 サブ画像 】")
                add_placeholder_box(slide, Inches(3.9), Inches(5.7), Inches(3.1), Inches(1.8), "【 サブ画像 】")
                add_placeholder_box(slide, Inches(0.5), Inches(7.7), Inches(3.1), Inches(1.8), "【 サブ画像 】")
                add_placeholder_box(slide, Inches(3.9), Inches(7.7), Inches(3.1), Inches(1.8), "【 サブ画像 】")

        # ────────── ⑦ 会社案内 ──────────
        elif p_type == 'company':
            if orientation == "横向き (Landscape)":
                add_placeholder_box(slide, Inches(0.5), Inches(0.2), Inches(9.0), Inches(3.2), "【 店舗案内図 挿入枠 】\n※自由にサイズ変更・削除できます")
                add_placeholder_box(slide, Inches(0.5), Inches(3.6), Inches(4.3), Inches(1.8), "【 店舗外観 挿入枠 】")
                add_placeholder_box(slide, Inches(5.2), Inches(3.6), Inches(4.3), Inches(1.8), "【 店舗内観 挿入枠 】")
                tx_box = slide.shapes.add_textbox(Inches(0.5), Inches(5.6), Inches(9.0), Inches(1.7))
            else:
                add_placeholder_box(slide, Inches(0.5), Inches(0.2), Inches(6.5), Inches(3.2), "【 店舗案内図 挿入枠 】\n※自由にサイズ変更・削除できます")
                add_placeholder_box(slide, Inches(0.5), Inches(3.6), Inches(3.1), Inches(3.5), "【 店舗外観 挿入枠 】")
                add_placeholder_box(slide, Inches(3.9), Inches(3.6), Inches(3.1), Inches(3.5), "【 店舗内観 挿入枠 】")
                tx_box = slide.shapes.add_textbox(Inches(0.5), Inches(7.5), Inches(6.5), Inches(2.0))
                 
            fill = tx_box.fill
            fill.solid()
            bg_r, bg_g, bg_b = theme_info["bg_color"]
            fill.fore_color.rgb = RGBColor(bg_r, bg_g, bg_b)
            
            ac_r, ac_g, ac_b = theme_info["accent_color"]
            tx_box.line.color.rgb = RGBColor(ac_r, ac_g, ac_b)
            tx_box.line.width = Pt(2)
            
            tf = tx_box.text_frame
            tf.word_wrap = True
            tf.clear() 
            
            text_color_rgb = RGBColor(0, 0, 0) if theme_tc == "black" else RGBColor(255, 255, 255)

            p_name = tf.add_paragraph()
            p_name.text = page_data.get('company_name', '株式会社 東宝ハウス')
            p_name.font.bold = True
            p_name.font.size = Pt(28)
            p_name.font.color.rgb = text_color_rgb
            p_name.alignment = PP_ALIGN.CENTER

            p_info = tf.add_paragraph()
            p_info.text = f"{page_data.get('license', '')}\n{page_data.get('address', '')}\nフリーダイヤル {page_data.get('tel', '')}"
            p_info.font.size = Pt(16)
            p_info.font.color.rgb = text_color_rgb
            p_info.alignment = PP_ALIGN.CENTER