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
    "練馬": {
        "full_name": "株式会社 東宝ハウス練馬",
        "license": "東京都知事（4）第86488号",
        "address": "〒178-0063 東京都練馬区東大泉1-27-22光和ビル2F",
        "tel": "0120-384-700"
    }
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
# ✨ 修正：画面を「1 : 1 : 2」の比率で分割し、右側に余白を作って間隔を詰める
col_img1, col_img2, _ = st.columns([1, 1, 2])
with col_img1:
    try:
        st.image("1.jpg", caption="① 横長の広々としたレイアウト", width=350)
    except:
        st.info("※画像が見つかりません。1.jpgを配置してください。")
with col_img2:
    try:
        st.image("2.jpg", caption="② 縦長の奥行きのあるレイアウト", width=350)
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
# ✨✨ 追加はここまで ✨✨

st.write("---")
st.subheader("🏠 物件・表紙の設定")

st.write("---")
st.subheader("🏠 物件の設定")

# 1. 物件種別の選択
property_types = {"house": "戸建て", "apartment": "マンション"}
selected_property_key = st.radio(
    "物件の種別：", 
    options=list(property_types.keys()), 
    format_func=lambda x: property_types[x],
    horizontal=True
)
selected_property_type_label = property_types[selected_property_key]

# 2. マンション規模の選択
if selected_property_key == "apartment":
    apt_scales = {
        "low": "低層（5階以下）", 
        "mid_high": "中層・高層（6階以上）"
    }
    col_scale, _, _ = st.columns(3)
    with col_scale:
        selected_apt_scale = st.selectbox(
            "マンションの規模（データ用）：",
            options=list(apt_scales.keys()),
            format_func=lambda x: apt_scales[x]
        )
else:
    selected_apt_scale = "house"

# 3. デザインテーマを「高級・ラグジュアリー」に固定
selected_style_key = "luxury"
theme_info = THEMES[selected_style_key]
custom_style_description = ""

# 4. 担当店舗の選択（ここで定義される）
st.write("---")
st.subheader("🏢 担当店舗の選択")
selected_branch_name = st.selectbox("担当店舗を選んでください：", list(BRANCH_DATA.keys()))

# 5. 店舗情報を取得（必ず st.selectbox より下に書く）
branch_info = BRANCH_DATA[selected_branch_name]

st.write("---")
st.subheader("💡 お部屋の特徴設定")
room_features_input = st.text_area(
    "間取り図から生成される画像の特徴（AIに確実に反映させたい部分）",
    placeholder="例：キッチンは壁付けI型で右奥。バルコニー側の窓は壁一面の大きなサッシ。",
    height=100
)

# 6. スライドの向き選択
st.write("---")
st.subheader("📏 スライドの向きを選択")
orientation = st.radio("作成するパンフレットの向き：", ["横向き (Landscape)", "縦向き (Portrait)"], index=1)

# 7. 生成ボタン
generate_btn = st.button("🚀 選択したデザインで全6ページを生成開始", disabled=not uploaded_file)
# 選択された店舗の詳細を取得
branch_info = BRANCH_DATA[selected_branch_name]

# --- 4. メイン処理（表紙4案生成 ＆ 全ページ生成） ---

# まずGeminiクライアントを初期化
gemini_client = genai.Client(api_key=gemini_api_key)

# ✨ 修正：再試行関数（これはそのまま維持します）
def generate_with_retry(model_name, prompt_contents, generation_config=None):
    wait_times = [30, 60, 180, 300, 600]
    max_attempts = len(wait_times) + 1
    for attempt in range(max_attempts):
        try:
            time.sleep(2)
            if generation_config:
                return gemini_client.models.generate_content(model=model_name, contents=prompt_contents, config=generation_config)
            else:
                return gemini_client.models.generate_content(model=model_name, contents=prompt_contents)
        except Exception as inner_e:
            if ("503" in str(inner_e) or "429" in str(inner_e)) and attempt < len(wait_times):
                wait_sec = wait_times[attempt]
                st.warning(f"サーバー制限に到達しました。{wait_sec}秒待機して再試行します... (再試行 {attempt + 1}/5)")
                time.sleep(wait_sec)
            else:
                raise inner_e

# ✨ 2つのステップに分けるためのボタン配置
col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    btn_gen_covers = st.button("🎨 まずは表紙案を4つ作成する", disabled=not uploaded_file)
with col_btn2:
    btn_gen_all = st.button("🚀 選んだ表紙で全ページを完成させる", disabled=not st.session_state.cover_choices)

# --- 4-A. 表紙案を4つ生成する処理 ---
if btn_gen_covers and uploaded_file is not None:
    # 1. OCR（文字読み取り）がまだなら実行
    if not st.session_state.pdf_text:
        with st.status("📄 販売図面をAI（OCR）で読み取っています..."):
            file_bytes = uploaded_file.getvalue()
            filename_lower = uploaded_file.name.lower()
            if filename_lower.endswith(".pdf"): mime_type = "application/pdf"
            elif filename_lower.endswith(".png"): mime_type = "image/png"
            else: mime_type = "image/jpeg"
            
            try:
                ocr_analysis = generate_with_retry(
                    model_name='gemini-2.5-flash',
                    prompt_contents=[
                        "図面から物件名、所在地、最寄り駅情報を正確に抽出してください。Imagen生成用の地名（市区町村）も特定してください。",
                        types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
                    ]
                )
                st.session_state.pdf_text = ocr_analysis.text
            except Exception as e:
                st.error(f"OCRエラー: {e}")
                st.stop()

# 2. LEON風の表紙画像をシチュエーション別に4枚生成
    with st.status("📸 異なるシチュエーションで表紙デザインを4案生成中...") as status:
        prop_type_en = "detached house" if selected_property_key == "house" else "apartment building"
        target_city_town = "Tokyo"
        if "所在地" in st.session_state.pdf_text:
             target_city_town = st.session_state.pdf_text.split("所在地")[-1][:10]

# ✨ 修正箇所：1つではなく、4つの異なるシチュエーションをリストで作ります
        base_style = "High-end luxury lifestyle magazine cover photography. Cinematic lighting, professional architectural and lifestyle photography, 8k resolution. Top area is clear for typography. NO text, NO logos, NO written words."
        
        # --- ここを書き換え ---
        prompts = [
            f"High-end luxury magazine photography. A happy Japanese family playing on a stylish street in {target_city_town}, featuring modern {prop_type_en}. Golden hour, NO text.",
            f"High-end luxury magazine photography. A dandy Japanese man drinking coffee in a luxury modern living room in {target_city_town}. Cinematic lighting, NO text.",
            f"High-end luxury magazine photography. A happy Japanese family playing in a private lush green garden in {target_city_town}. Warm sunlight, NO text.",
            f"High-end luxury magazine photography. A happy Japanese family enjoying a picnic in a large green park in {target_city_town}. Airy atmosphere, NO text."
        ]

        try:
            temp_choices = []
            # 4つのプロンプトをループで1枚ずつ生成します
            for i, p in enumerate(prompts):
                st.write(f"案 {i+1} を作成中...")
                img_res = gemini_client.models.generate_images(
                    model='imagen-4.0-generate-001',
                    prompt=p,
                    config=types.GenerateImagesConfig(
                        number_of_images=1, 
                        aspect_ratio="4:3" if orientation == "横向き (Landscape)" else "3:4"
                    )
                )
                temp_choices.append(Image.open(BytesIO(img_res.generated_images[0].image.image_bytes)))
            
            # 全て生成し終わったらセッションに保存してリロード
            st.session_state.cover_choices = temp_choices
            st.rerun()

        except Exception as e:
            st.error(f"画像生成中にエラーが発生しました: {e}")

# --- 4-B. 生成された4案を表示して選ばせるUI ---
if st.session_state.cover_choices and not st.session_state.finished_pages:
    st.write("---")
    st.subheader("📸 お好きな表紙デザインを1つ選んでください")
    cols = st.columns(4)
    for idx, img in enumerate(st.session_state.cover_choices):
        with cols[idx]:
            st.image(img, caption=f"デザイン案 {idx+1}", use_container_width=True)
            if st.button(f"案 {idx+1} を選択", key=f"select_cover_{idx}"):
                st.session_state.selected_cover_index = idx
                st.success(f"案 {idx+1} を選択しました！上の「全ページを完成させる」ボタンを押してください。")

# ✅ 修正：ここに条件を追加します
if btn_gen_all: 
    # 右上の「全ページを完成させる」ボタンが押された時だけ、以下の処理が動く
    with st.status("🎨 6ページのパンフレットを作成中...（約1分かかります）", expanded=True) as status:
        try:
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
                "main_text": "【補助データ】の周辺環境情報を基に、このテーマの客層に刺さる紹介文を3〜4行で作成してください。"
                "city_town_clean": "抽出したImagen用地域名（例：府中市美好町）" # ✨ここに追加
              }},
              {{
                "page": 3, "type": "access", "headline": "MAP & ACCESS", 
                "source_pdf_page": 1, 
                "life_info": "【補助データ】からスーパー、学校、公園などの施設名と距離を箇条書きで抽出してください。"
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

            generated_pages = []
            # 向きに合わせてキャンバスサイズを入れ替える
            if orientation == "横向き (Landscape)":
                width, height = 1024, 768
            else:
                width, height = 768, 1024
            
            theme_bg = theme_info["bg_color"]
            theme_tc = theme_info["text_color"]
            theme_ac = theme_info["accent_color"]

            for page_data in st.session_state.ai_data:
                st.write(f"🖼️ {page_data['page']}ページ目（{page_data['type']}）を合成中...")
                bg_image = None
                
# ────────── ① 表紙（LEON風：背景画像のみをセット） ──────────
                if page_data['type'] == 'cover':
                    # 【重要】文字を書くコードはすべて削除し、選んだ画像をセットするだけにします
                    if st.session_state.cover_choices:
                        bg_image = st.session_state.cover_choices[st.session_state.selected_cover_index].copy().resize((width, height))
                    else:
                        bg_image = Image.new('RGB', (width, height), color=theme_bg)
                
                # ────────── ② 空撮地図 ──────────
                elif page_data['type'] == 'aerial_map':
                    st.write(f"🎨 空撮マップの背景画像をAIで生成中...（種別: {selected_property_type_label}）")

                    target_city_town = page_data.get('city_town_clean', '日本の都市部')
                    
                    # ✨ 修正：空撮画像も、選んだ規模に合わせて街並みを変える
                    if selected_property_key == "house":
                        aerial_desc = f"sprawling suburban residential area in {target_city_town}, Japan, featuring realistic Japanese detached houses (建売住宅) and specific local landmarks like Sayama green tea fields (狭山茶の茶畑) nearby. Shows visible local amenities like a large supermarket (イオン/マルエツ), a primary school complex with sports fields, and building density with narrow streets."
                    else:
                        if selected_apt_scale == "low":
                            aerial_desc = f"peaceful suburban Japanese residential neighborhood in {target_city_town}, Japan, featuring 3-story low-rise apartment buildings and realistic detached houses, with extensive green spaces and local parks."
                        elif selected_apt_scale == "mid":
                            aerial_desc = f"typical Japanese urban cityscape in {target_city_town}, Japan, featuring medium-density mid-rise 6-story apartment buildings and local amenity areas, with narrow streets and building density."
                        else: # high
                            aerial_desc = f"dense urban Japanese cityscape in {target_city_town}, Japan, featuring realistic high-rise tower mansions, large roads, and skyscrapers near a prominent train station, with realistic signage."
                        
                        # ✨✨ 追加：解析したマンションの外観特徴をプロンプトに強力に反映させる ✨✨
                        if apt_style_prompt:
                            aerial_desc += f" The main focal point is a massive, prominent apartment building with this specific architectural style: [{apt_style_prompt}]."

                    try:
                        base_prompt = (
                            f"Photorealistic drone photography, bird's-eye view, Google Earth style aerial shot of {aerial_desc} in {target_city_town}, Tokyo area, Japan. "
                            "Highly detailed, true-to-life lighting. Features typical realistic Japanese townscape, building density, narrow asphalt streets with utility poles, "
                            "realistic Japanese housing materials like siding walls and tiled roofs, realistic signage, and urban infrastructure. "
                            "Shows sprawling suburban landscape, building density, narrow streets, and the proximity to green spaces like Sayama Hills. "
                            "NOT a 3D render, NOT a miniature toy, NO tilt-shift effect, NO cartoon, NO text, NO labels. Professional real estate photography."
                        )
                        
                        negative_prompt = (
                            "No brick architecture, no large grassy lawns, no classic Western-style town layouts, no sprawling Western-style suburbia, no prominent Western-style churches or buildings."
                        )
                        
                        final_prompt = f"{base_prompt} Avoid {negative_prompt}"
                        
                        image_result = gemini_client.models.generate_images(
                            model='imagen-4.0-generate-001',
                            prompt=final_prompt,
                            config=types.GenerateImagesConfig(
                                number_of_images=1,
                                aspect_ratio="4:3" if orientation == "横向き (Landscape)" else "3:4"
                            )
                        )
                        generated_bytes = image_result.generated_images[0].image.image_bytes
                        bg_image = Image.open(BytesIO(generated_bytes)).convert("RGB").resize((width, height))
                    except Exception as e:
                        st.warning(f"2ページ目の画像生成をスキップしました: {e}")
                        bg_image = Image.new('RGB', (width, height), color=theme_bg)

                    draw = ImageDraw.Draw(bg_image)
                    try:
                        font_head = ImageFont.truetype(FONT_PATH, int(height * 0.07))
                        font_subhead = ImageFont.truetype(FONT_PATH, int(height * 0.04))
                        font_main = ImageFont.truetype(FONT_PATH, int(height * 0.03))
                    except:
                        font_head = font_subhead = font_main = ImageFont.load_default()

                    headline = page_data.get('headline', 'FUTURE VISION').replace('\n', ' ')
                    sub_headline = page_data.get('sub_headline', '').replace('\n', ' ')
                    main_text = page_data.get('main_text', '')

                    off = 2
                    draw.text((width*0.05+off, height*0.05+off), headline, font=font_head, fill="black", anchor="la")
                    draw.text((width*0.05, height*0.05), headline, font=font_head, fill="white", anchor="la")
                    draw.text((width*0.05+off, height*0.13+off), sub_headline, font=font_subhead, fill="black", anchor="la")
                    draw.text((width*0.05, height*0.13), sub_headline, font=font_subhead, fill="white", anchor="la")
                    draw.multiline_text((width*0.05+off, height*0.2+off), main_text, font=font_main, fill="black", spacing=10)
                    draw.multiline_text((width*0.05, height*0.2), main_text, font=font_main, fill="white", spacing=10)

                # ────────── ③ アクセス・地図 ──────────
                elif page_data['type'] == 'access':
                    st.write(f"🎨 MAP & ACCESSの背景画像をAIで生成中...")
                    try:
                        # Imagenによる森の画像生成
                        image_result = gemini_client.models.generate_images(
                            model='imagen-4.0-generate-001',
                            prompt="Photorealistic beautiful nature background, lush green trees, soft sunlight, bright and clean landscape, suitable for a real estate flyer background. NO text, NO logos.",
                            config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="4:3" if orientation == "横向き (Landscape)" else "3:4")
                        )
                        generated_bytes = image_result.generated_images[0].image.image_bytes
                        bg_image = Image.open(BytesIO(generated_bytes)).convert("RGB").resize((width, height))
                    except Exception as e:
                        st.warning(f"3ページ目の画像生成エラー: {e}")
                        bg_image = Image.new('RGB', (width, height), color=(255, 255, 255))

                    # ✨ 画面全体に「白い半透明のフィルター」を被せて、森をうっすら透けさせる
                    overlay = Image.new('RGBA', bg_image.size, (255, 255, 255, 225)) 
                    bg_image = Image.alpha_composite(bg_image.convert('RGBA'), overlay).convert('RGB')
                    
                    draw = ImageDraw.Draw(bg_image)
                    
                    # ✨ ヘッダーの下にスタイリッシュなアクセントラインを引く
                    draw.line([(width*0.05, height*0.15), (width*0.95, height*0.15)], fill=theme_ac, width=3)
                    
                    try: 
                        font_headline = ImageFont.truetype(FONT_PATH, int(height * 0.08))
                        font_sub = ImageFont.truetype(FONT_PATH, int(height * 0.03))
                    except: 
                        font_headline = font_sub = ImageFont.load_default()
                    
                    # 白背景ベースなので、文字色は黒とアクセントカラーに変更
                    draw.text((width*0.05, height*0.05), "MAP & ACCESS", font=font_headline, fill="black", anchor="la")
                    draw.text((width*0.05, height*0.12), "周辺環境・アクセス", font=font_sub, fill=theme_ac, anchor="la")

                # ────────── ④ 間取り図 ──────────
                elif page_data['type'] == 'floor_plan':
                    # ✨ テーマ背景色を適用し、アクセントラインでスタイリッシュに
                    bg_image = Image.new('RGB', (width, height), color=theme_bg)
                    draw = ImageDraw.Draw(bg_image)
                    header_h = int(height * 0.15)
                    draw.line([(0, header_h), (width, header_h)], fill=theme_ac, width=4)

                    if madori_file:
                        m_img = Image.open(madori_file).convert("RGB")
                        # 間取り図にうっすら枠線をつけてカード風にする処理
                        border_color = (200, 200, 200)
                        m_img_with_border = Image.new('RGB', (m_img.width + 4, m_img.height + 4), border_color)
                        m_img_with_border.paste(m_img, (2, 2))
                        m_img_with_border.thumbnail((width * 0.85, height * 0.75))
                        
                        p_x = (width - m_img_with_border.width) // 2
                        p_y = (header_h + (height - header_h - m_img_with_border.height) // 2)
                        bg_image.paste(m_img_with_border, (int(p_x), int(p_y)))
                    else:
                        draw.text((width/2, height/2), "間取り図がアップロードされていません", fill=theme_tc, anchor="mm")
                
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
                    generated_pages.append(bg_image)

            st.session_state.finished_pages = generated_pages
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
    
    cols = st.columns(len(st.session_state.finished_pages))
    for i, page_img in enumerate(st.session_state.finished_pages):
        with cols[i]:
            st.write(f"**P.{i+1}**")
            st.image(page_img, use_container_width=True)

    prs = Presentation()
    if orientation == "横向き (Landscape)":
        prs.slide_width, prs.slide_height = Inches(10), Inches(7.5)
    else:
        prs.slide_width, prs.slide_height = Inches(7.5), Inches(10)

    # ✨ PowerPoint上に「自由に動かせる枠」を作るための便利機能（スタイリッシュ版）
    def add_placeholder_box(slide_obj, left, top, width, height, text):
        tx_box = slide_obj.shapes.add_textbox(left, top, width, height)
        
        # ✨ 修正：塗りつぶしを透明ではなく、非常に薄いグレーにして「画像置き場」感を出す
        tx_box.fill.solid()
        tx_box.fill.fore_color.rgb = RGBColor(245, 245, 245)
        
        # ✨ 修正：枠線をテーマカラーから、悪目立ちしないスタイリッシュなグレーの細線に変更
        tx_box.line.color.rgb = RGBColor(210, 210, 210) 
        tx_box.line.width = Pt(1)
        
        tf = tx_box.text_frame
        tf.word_wrap = True
        tf.clear()
        
        # ✨ 追加：1行目に英語のダミーテキスト（IMAGE PLACEHOLDER）を配置してデザイン性を高める
        p_en = tf.add_paragraph()
        p_en.text = "IMAGE PLACEHOLDER"
        p_en.font.size = Pt(11)
        p_en.font.bold = True
        p_en.font.color.rgb = RGBColor(170, 170, 170) # 薄めのグレー
        p_en.alignment = PP_ALIGN.CENTER
        
        # ✨ 修正：2行目に元の日本語テキストを、かっこよく控えめな色とサイズで配置
        p_jp = tf.add_paragraph()
        # テキスト内の【 】などの記号を消してクリーンにする
        clean_text = text.replace("【", "").replace("】", "").replace(" ", "")
        p_jp.text = clean_text
        p_jp.font.size = Pt(9)
        p_jp.font.color.rgb = RGBColor(140, 140, 140)
        p_jp.alignment = PP_ALIGN.CENTER

        # 日本語を縦書き（改行区切り）に変換する関数
    def to_vertical(text):
        return "\n".join(list(text))

    # ✨ 追加：駅徒歩用の円形グラフィックを追加する機能
    def add_station_info_circle(slide_obj, x, y, radius, text, color=(255, 255, 255)):
        # 円形グラフィックを追加
        circle = slide_obj.shapes.add_shape(MSO_SHAPE.OVAL, x, y, radius*2, radius*2)
        circle.fill.solid()
        circle.fill.fore_color.rgb = RGBColor(0, 0, 0) # 黒背景
        circle.line.color.rgb = RGBColor(255, 255, 255) # 白枠
        circle.line.width = Pt(1.5)
        
        # テキストを配置
        tf = circle.text_frame
        tf.word_wrap = True
        # テキストフレームを円に合わせる
        tf.clear() # デフォルトのテキストをクリア
        p = tf.add_paragraph()
        p.text = text
        p.font.size = Pt(14)
        p.font.color.rgb = RGBColor(color[0], color[1], color[2]) # 白文字
        p.font.bold = True
        p.alignment = PP_ALIGN.CENTER
        # テキストフレームの余白を調整
        tf.margin_bottom = tf.margin_left = tf.margin_right = tf.margin_top = Inches(0.1)


    for i, page_img in enumerate(st.session_state.finished_pages):
        slide = prs.slides.add_slide(prs.slide_layouts[6]) 
        
        img_io = BytesIO()
        page_img.save(img_io, format='PNG')
        img_io.seek(0)
        slide.shapes.add_picture(img_io, 0, 0, width=prs.slide_width, height=prs.slide_height)

# --- パワポ 1ページ目（LEON風：文字あふれ防止・4パターンランダム） ---
        if i == 0 and st.session_state.ai_data:
            p1_data = st.session_state.ai_data[0]
            prop_name = p1_data.get('property_name_jp', '物件名').upper() 
            address_text = p1_data.get('city_town', '') 
            sub_copy = p1_data.get('sub_copy', '') 
            station_info = p1_data.get('station_info', '').replace('\\n', '\n')

            def to_vertical(text):
                return "\n".join(list(text))

            v_address = to_vertical(address_text)
            layout_pattern = random.randint(1, 4)
            sw = prs.slide_width
            sh = prs.slide_height

            # --- ① 物件名（ロゴ）のサイズ自動調整 ---
            if orientation == "横向き (Landscape)":
                if len(prop_name) > 10: logo_font_size = Pt(60)
                elif len(prop_name) > 7: logo_font_size = Pt(70)
                else: logo_font_size = Pt(85)
                logo_y = Inches(0.4)
            else:
                if len(prop_name) > 10: logo_font_size = Pt(38)
                elif len(prop_name) > 7: logo_font_size = Pt(45)
                else: logo_font_size = Pt(55)
                # ✨ 修正1：上端ギリギリを防ぐため、少し下へ(0.6 -> 0.8)
                logo_y = Inches(0.8)

            tx_logo = slide.shapes.add_textbox(Inches(0.5), logo_y, sw - Inches(1.0), Inches(1.2))
            tf_logo = tx_logo.text_frame
            tf_logo.word_wrap = False
            p_logo = tf_logo.paragraphs[0]
            p_logo.text = prop_name
            p_logo.font.size = logo_font_size
            p_logo.font.bold = True
            p_logo.font.color.rgb = RGBColor(255, 255, 255)
            p_logo.alignment = PP_ALIGN.CENTER

            # --- ② パターン別配置（座標の最適化） ---
            if layout_pattern == 1:
                tx_addr = slide.shapes.add_textbox(sw - Inches(1.0), Inches(2.0), Inches(0.8), sh - Inches(4.0))
                # ✨ 修正2：キャッチコピー全体を上へ移動 (sh - Inches(2.2) -> sh * 0.6)
                tx_sub = slide.shapes.add_textbox(Inches(0.5), sh * 0.6, sw - Inches(1.0), Inches(0.8))
                sub_align = PP_ALIGN.LEFT
                current_sub_text = sub_copy
            
            elif layout_pattern == 2:
                tx_addr = slide.shapes.add_textbox(Inches(0.2), Inches(2.0), Inches(0.8), sh - Inches(4.0))
                # ✨ 修正2：キャッチコピー全体を上へ移動
                tx_sub = slide.shapes.add_textbox(Inches(0.5), sh * 0.6, sw - Inches(1.0), Inches(0.8))
                sub_align = PP_ALIGN.RIGHT
                current_sub_text = sub_copy

            elif layout_pattern == 3:
                tx_addr = slide.shapes.add_textbox(sw - Inches(1.0), Inches(2.0), Inches(0.8), sh - Inches(4.0))
                tx_sub = slide.shapes.add_textbox(Inches(0.5), Inches(2.5), Inches(0.8), sh * 0.5)
                sub_align = PP_ALIGN.CENTER
                current_sub_text = to_vertical(sub_copy[:15])
            
            else:
                tx_addr = slide.shapes.add_textbox(Inches(0.2), Inches(2.0), Inches(0.8), sh - Inches(4.0))
                # ✨ 修正2：キャッチコピー全体を上へ移動
                tx_sub = slide.shapes.add_textbox(Inches(0.5), sh * 0.55, sw - Inches(1.0), Inches(1.0))
                sub_align = PP_ALIGN.CENTER
                current_sub_text = sub_copy

            # --- ③ 住所（縦書き）の設定 ---
            tf_addr = tx_addr.text_frame
            tf_addr.text = v_address
            addr_font_size = Pt(20) if orientation == "縦向き (Portrait)" else Pt(24)
            for para in tf_addr.paragraphs:
                para.font.size = addr_font_size
                para.font.bold = True
                para.font.color.rgb = RGBColor(255, 255, 255)
                para.alignment = PP_ALIGN.CENTER

            # --- ④ キャッチコピーの設定 ---
            tf_sub = tx_sub.text_frame
            tf_sub.text = current_sub_text
            sub_font_size = Pt(16) if orientation == "縦向き (Portrait)" else Pt(22)
            for para in tf_sub.paragraphs:
                para.font.size = sub_font_size
                para.font.bold = True
                para.font.color.rgb = RGBColor(255, 255, 255)
                para.alignment = sub_align

            # --- ⑤ 駅情報サークル（見切れ解消のため上へ移動） ---
            # ✨ 修正3：円を上へ移動 (sh - Inches(1.3) -> sh - Inches(2.0))
            circle_y = sh - Inches(2.0)
            add_station_info_circle(slide, Inches(0.3), circle_y, Inches(0.7), station_info)

        # 3ページ目（MAP & ACCESS）
        if i == 2 and st.session_state.ai_data:
            p3_data = st.session_state.ai_data[2]
            acc_text = p3_data.get('access_info', '交通情報がありません')
            if isinstance(acc_text, list): acc_text = "\n".join(str(x) for x in acc_text)
            life_text = p3_data.get('life_info', '周辺施設情報がありません')
            if isinstance(life_text, list): life_text = "\n".join(str(x) for x in life_text)
            
            # --- テキストボックスの配置 ---
            if orientation == "横向き (Landscape)":
                add_placeholder_box(slide, Inches(0.5), Inches(1.5), Inches(4.5), Inches(5.5), "【 MAP画像 挿入枠 】\n※自由にサイズ変更・削除できます")
                tx_box_acc = slide.shapes.add_textbox(Inches(5.5), Inches(1.5), Inches(4.0), Inches(2.0))
                tx_box_life = slide.shapes.add_textbox(Inches(5.5), Inches(3.8), Inches(4.0), Inches(3.2))
            else:
                add_placeholder_box(slide, Inches(0.5), Inches(1.5), Inches(6.5), Inches(3.5), "【 MAP画像 挿入枠 】\n※自由にサイズ変更・削除できます")
                tx_box_acc = slide.shapes.add_textbox(Inches(0.5), Inches(5.5), Inches(6.5), Inches(1.5))
                tx_box_life = slide.shapes.add_textbox(Inches(0.5), Inches(7.2), Inches(6.5), Inches(2.5))
            
            # ✨ 修正：文字色をテーマに合わせ、見出しを強調してかっこよくする
            text_color_rgb = RGBColor(0, 0, 0) if theme_tc == "black" else RGBColor(255, 255, 255)
            ac_r, ac_g, ac_b = theme_info["accent_color"]
            accent_color_rgb = RGBColor(ac_r, ac_g, ac_b)

            # --- 交通アクセスのテキスト設定 ---
            tf_acc = tx_box_acc.text_frame
            tf_acc.word_wrap = True
            tf_acc.clear() # 初期化
            
            p_acc_head = tf_acc.add_paragraph()
            p_acc_head.text = "■ 交通アクセス"
            p_acc_head.font.size = Pt(16)
            p_acc_head.font.bold = True
            p_acc_head.font.color.rgb = accent_color_rgb # 見出しはアクセントカラー
            
            p_acc_body = tf_acc.add_paragraph()
            p_acc_body.text = acc_text
            p_acc_body.font.size = Pt(14)
            p_acc_body.font.color.rgb = text_color_rgb # 本文はテーマカラー

            # --- 周辺環境のテキスト設定 ---
            tf_life = tx_box_life.text_frame
            tf_life.word_wrap = True
            tf_life.clear() # 初期化
            
            p_life_head = tf_life.add_paragraph()
            p_life_head.text = "■ Life Information"
            p_life_head.font.size = Pt(16)
            p_life_head.font.bold = True
            p_life_head.font.color.rgb = accent_color_rgb # 見出しはアクセントカラー
            
            p_life_body = tf_life.add_paragraph()
            p_life_body.text = life_text
            p_life_body.font.size = Pt(14)
            p_life_body.font.color.rgb = text_color_rgb # 本文はテーマカラー

        # 4ページ目（間取り図）
        if i == 3 and st.session_state.ai_data:
            p4_data = st.session_state.ai_data[3]
            prop_name_jp = p4_data.get('property_name_jp', '物件名')
            land_area = p4_data.get('land_area', '')
            building_area = p4_data.get('building_area', '')
            price_jp = p4_data.get('price_jp', '--- 万円')

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
            
            # 4ページ目（間取り図）
        if i == 3 and st.session_state.ai_data:
            p4_data = st.session_state.ai_data[3]
            # ... (中略。座標設定などはそのまま) ...
            
            # ✨ 修正：文字色をテーマカラー（theme_tc）に合わせる
            text_color_rgb = RGBColor(0, 0, 0) if theme_tc == "black" else RGBColor(255, 255, 255)
            
            tf_title = tb_title.text_frame
            p_title = tf_title.paragraphs[0]
            p_title.text = prop_name_jp
            p_title.font.size = Pt(28)
            p_title.font.color.rgb = text_color_rgb # ここを変更
            p_title.font.bold = True
            
            tf_area = tb_area.text_frame
            p_area1 = tf_area.paragraphs[0]
            p_area1.text = land_area
            p_area1.font.size = Pt(12)
            p_area1.font.color.rgb = text_color_rgb # ここを変更
            p_area1.alignment = PP_ALIGN.RIGHT
            if building_area:
                p_area2 = tf_area.add_paragraph()
                p_area2.text = building_area
                p_area2.font.size = Pt(12)
                p_area2.font.color.rgb = text_color_rgb # ここを変更
                p_area2.alignment = PP_ALIGN.RIGHT
            
            tf_price = tb_price.text_frame
            p_price = tf_price.paragraphs[0]
            p_price.text = price_jp
            p_price.font.size = Pt(32)
            p_price.font.color.rgb = text_color_rgb # ここを変更
            p_price.font.bold = True
            p_price.alignment = PP_ALIGN.RIGHT

        # 7ページ目（会社案内）
        if i == 6 and st.session_state.ai_data:
            c_data = st.session_state.ai_data[6]
            
            # --- 消えてしまっていた座標設定（tx_boxの定義） ---
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
            # ✨ 修正：テーマの背景色・アクセントカラーを使う
            bg_r, bg_g, bg_b = theme_info["bg_color"]
            fill.fore_color.rgb = RGBColor(bg_r, bg_g, bg_b)
            
            # 枠線もつける
            ac_r, ac_g, ac_b = theme_info["accent_color"]
            tx_box.line.color.rgb = RGBColor(ac_r, ac_g, ac_b)
            tx_box.line.width = Pt(2)
            
            tf = tx_box.text_frame
            tf.word_wrap = True
            tf.clear() 
            
            # 文字色
            text_color_rgb = RGBColor(0, 0, 0) if theme_tc == "black" else RGBColor(255, 255, 255)

            p_name = tf.add_paragraph()
            p_name.text = c_data.get('company_name', '株式会社 東宝ハウス')
            p_name.font.bold = True
            p_name.font.size = Pt(28)
            p_name.font.color.rgb = text_color_rgb
            p_name.alignment = PP_ALIGN.CENTER

            p_info = tf.add_paragraph()
            p_info.text = f"{c_data.get('license', '')}\n{c_data.get('address', '')}\nフリーダイヤル {c_data.get('tel', '')}"
            p_info.font.size = Pt(16)
            p_info.font.color.rgb = text_color_rgb
            p_info.alignment = PP_ALIGN.CENTER

        # 6ページ目（内観ギャラリー）
        if i == 5:
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

        # 7ページ目（会社案内）
        if i == 6 and st.session_state.ai_data:
            c_data = st.session_state.ai_data[6]
            
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
            # ✨ 修正：テーマの背景色・アクセントカラーを使う
            bg_r, bg_g, bg_b = theme_info["bg_color"]
            fill.fore_color.rgb = RGBColor(bg_r, bg_g, bg_b)
            
            # 枠線もつける
            ac_r, ac_g, ac_b = theme_info["accent_color"]
            tx_box.line.color.rgb = RGBColor(ac_r, ac_g, ac_b)
            tx_box.line.width = Pt(2)
            
            tf = tx_box.text_frame
            tf.word_wrap = True
            tf.clear() 
            
            # 文字色
            text_color_rgb = RGBColor(0, 0, 0) if theme_tc == "black" else RGBColor(255, 255, 255)

            p_name = tf.add_paragraph()
            p_name.text = c_data.get('company_name', '株式会社 東宝ハウス')
            p_name.font.bold = True
            p_name.font.size = Pt(28)
            p_name.font.color.rgb = text_color_rgb
            p_name.alignment = PP_ALIGN.CENTER

            p_info = tf.add_paragraph()
            p_info.text = f"{c_data.get('license', '')}\n{c_data.get('address', '')}\nフリーダイヤル {c_data.get('tel', '')}"
            p_info.font.size = Pt(16)
            p_info.font.color.rgb = text_color_rgb
            p_info.alignment = PP_ALIGN.CENTER

    pptx_out = BytesIO()
    prs.save(pptx_out)
    
    st.download_button(
        label="📥 PowerPointでダウンロード", 
        data=pptx_out.getvalue(), 
        file_name="Property_Pamphlet.pptx", 
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    
    st.write("---")
    if st.button("🔄 最初からやり直す"):
        st.session_state.finished_pages = []
        st.session_state.ai_data = None
        st.session_state.pdf_text = ""
        st.rerun()