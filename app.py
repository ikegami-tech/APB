import streamlit as st
import os
import json
import fitz  # PyMuPDF
import glob
import time
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

# --- 修正：PDFだけでなく画像も許可し、特徴入力欄を追加 ---
col_u1, col_u2 = st.columns(2)
with col_u1:
    uploaded_file = st.file_uploader("販売図面（PDFまたは画像）をアップロード", type=["pdf", "png", "jpg", "jpeg"])
with col_u2:
    madori_file = st.file_uploader("間取り図の画像をアップロード（P.4用）", type=["png", "jpg", "jpeg"])
    
    # ✨ 追加：間取り図から生成される画像の特徴を入力する項目
    room_features_input = st.text_area(
        "💡 お部屋の特徴（AIに確実に反映させたい部分）",
        placeholder="例：キッチンは壁付けI型で右奥。バルコニー側の窓は壁一面の大きなサッシ。対面キッチンにはしない。"
    )

if uploaded_file is not None and uploaded_file.name != st.session_state.current_file:
    st.session_state.finished_pages = []
    st.session_state.ai_data = None
    st.session_state.current_file = uploaded_file.name
    st.session_state.pdf_text = ""
st.write("---")
st.subheader("🏠 物件・表紙の設定")
col_p1, col_p2 = st.columns(2)

with col_p1:
    property_types = {"house": "戸建て", "apartment": "マンション"}
    selected_property_key = st.radio(
        "物件の種別：", 
        options=list(property_types.keys()), 
        format_func=lambda x: property_types[x],
        horizontal=True
    )
    selected_property_type_label = property_types[selected_property_key]

with col_p2:
    if selected_property_key == "apartment":
        apt_scales = {"low": "低層", "mid": "中層", "high": "高層タワー"}
        selected_apt_scale = st.selectbox(
            "マンションの規模（データ用）：",
            options=list(apt_scales.keys()),
            format_func=lambda x: apt_scales[x]
        )
    else:
        selected_apt_scale = "house"

# ✨ 追加：表紙のイメージテーマを選択（5つの選択肢）
st.write("🖼️ **表紙の背景イメージ（街並み）を選択してください**")
NEIGHBORHOOD_THEMES = {
    "green": "1. 自然豊かな街並み（街路樹・公園・緑が多い）",
    "urban": "2. 都会的・モダンな街並み（洗練されたビル・舗装された道路）",
    "quiet": "3. 閑静な住宅街（落ち着いた雰囲気・邸宅地）",
    "station": "4. 利便性の高い駅前（賑わい・店舗・明るい夜景も可）",
    "open": "5. 開放感のある街並み（空が広い・リバーサイド・並木道）"
}
selected_neighborhood_key = st.radio(
    "表紙に使用するイメージ：",
    options=list(NEIGHBORHOOD_THEMES.keys()),
    format_func=lambda x: NEIGHBORHOOD_THEMES[x],
    horizontal=False
)
# ここまでを追加
st.write("---")
st.subheader("🎨 パンフレットのデザインテーマを選択")
selected_style_key = st.radio(
    "デザインの方向性を選んでください：", 
    options=list(THEMES.keys()), 
    format_func=lambda x: THEMES[x]["name"],
    index=0
)
theme_info = THEMES[selected_style_key]

# --- 追加：⑦その他を選択した場合の自由入力欄 ---
custom_style_description = ""
if selected_style_key == "other":
    custom_style_description = st.text_input(
        "どのようなデザインスタイルにしたいか入力してください：",
        placeholder="例：北欧風の明るい木目調、ヴィンテージ風のレンガ造り、など"
    )

# --- 修正：店舗選択UIを追加 ---
st.write("---")
st.subheader("🏢 担当店舗の選択")
selected_branch_name = st.selectbox("担当店舗を選んでください：", list(BRANCH_DATA.keys()))

# --- 修正：スライドの向き選択UIを追加 ---
st.write("---")
st.subheader("📏 スライドの向きを選択")
orientation = st.radio("作成するパンフレットの向き：", ["横向き (Landscape)", "縦向き (Portrait)"], index=0)
# 選択された店舗の詳細を取得
branch_info = BRANCH_DATA[selected_branch_name]

generate_btn = st.button("🚀 選択したデザインで全6ページを生成開始", disabled=not uploaded_file)

# --- 4. メイン処理 ---
if generate_btn and uploaded_file is not None:
    
    # まずGeminiクライアントを初期化します（これを最初に行うことでエラーを防ぎます）
    gemini_client = genai.Client(api_key=gemini_api_key)

    # ✨ 修正：段階的に待機時間を長くして5回まで再試行する最強の便利関数
    def generate_with_retry(model_name, prompt_contents, generation_config=None):
        # 待機時間（秒）の設定：30秒, 1分(60秒), 3分(180秒), 5分(300秒), 10分(600秒)
        wait_times = [30, 60, 180, 300, 600]
        max_attempts = len(wait_times) + 1 # 初回1回 ＋ 再試行5回 ＝ 計6回トライ
        
        for attempt in range(max_attempts):
            try:
                # 意図的に毎回2秒休ませてからリクエストを送る（連投によるエラーを未然に防止）
                time.sleep(2)
                
                if generation_config:
                    return gemini_client.models.generate_content(model=model_name, contents=prompt_contents, config=generation_config)
                else:
                    return gemini_client.models.generate_content(model=model_name, contents=prompt_contents)
            
            except Exception as inner_e:
                # 503(混雑) または 429(制限超過) エラーなら指定時間待機する
                if ("503" in str(inner_e) or "429" in str(inner_e)) and attempt < len(wait_times):
                    wait_sec = wait_times[attempt]
                    
                    # 画面表示用に「○分」か「○秒」の分かりやすい文字列を作る
                    if wait_sec >= 60:
                        time_str = f"{wait_sec // 60}分"
                    else:
                        time_str = f"{wait_sec}秒"
                    
                    st.warning(f"サーバー制限に到達しました。{time_str}待機して再試行します... (再試行 {attempt + 1}/5)")
                    time.sleep(wait_sec)
                else:
                    # 全く別のエラー、または5回の長期待機がすべて失敗した場合はエラーを出してストップ
                    raise inner_e

    # --- 販売図面（PDF/画像）の文字読み取り（OCR） ---
    if not st.session_state.pdf_text:
        st.write("📄 販売図面をAI（OCR）で読み取っています...")
        file_bytes = uploaded_file.getvalue()
        filename_lower = uploaded_file.name.lower()
        
        if filename_lower.endswith(".pdf"): mime_type = "application/pdf"
        elif filename_lower.endswith(".png"): mime_type = "image/png"
        else: mime_type = "image/jpeg"
            
        try:
            # ✨ 便利関数を使ってOCRを実行
            ocr_analysis = generate_with_retry(
                model_name='gemini-2.5-flash',
                prompt_contents=[
                    "この販売図面（画像またはPDF）に書かれているすべての文字情報を、正確に読み取ってテキスト化してください。物件名（フリガナや英語名も）、価格、所在地、交通（最寄り駅と徒歩分数）などの主要項目は絶対に漏らさないでください。",
                    types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
                ]
            )
            st.session_state.pdf_text = ocr_analysis.text
        except Exception as e:
            st.error(f"図面の読み取りエラー: {e}")
            st.session_state.pdf_text = "読み取り失敗"

    with st.status("🎨 6ページのパンフレットを作成中...（約1分かかります）", expanded=True) as status:
        try:
            st.write("AIが物件情報、指定地域、デザインテーマを分析中...")
            
            theme_info = THEMES[selected_style_key]
            current_theme_name = custom_style_description if selected_style_key == "other" else theme_info["name"]

            # --- 間取り図をAIに読み取らせる ---
            room_description = "A modern living room" # 読み取れなかった時の予備
            if madori_file:
                st.write("🔍 間取り図と入力された特徴から、強力な画像生成プロンプトを作成中...")
                m_bytes = madori_file.getvalue()
                user_instruction = f"\n\n[USER'S ABSOLUTE REQUIREMENTS]\n{room_features_input}" if room_features_input else ""
                
                # ✨ 便利関数を使って間取り図を解析
                analysis = generate_with_retry(
                    model_name='gemini-2.5-flash',
                    prompt_contents=[
                        f"""Analyze the attached Japanese floor plan (LDK area) and generate a highly detailed, STRICT English prompt for an Image Generation AI.

{user_instruction}

[CRITICAL RULES TO OVERCOME AI BIAS]
1. Kitchen (Crucial): Image AIs always default to island kitchens. If the floor plan or user indicates a wall-mounted kitchen (壁付けキッチン), you MUST explicitly write: "single-wall kitchen, cabinets and stove placed flat against the back wall, NO island, NO peninsula, wide open floor space in front".
2. Windows: If a large window is requested, explicitly write: "massive wall-to-wall and floor-to-ceiling panoramic windows, clear view, no vertical pillars blocking the view".
3. Layout: Specify exactly where things are based on the floor plan (e.g., "kitchen on the left side, dining table in the center, large window at the far back").
4. Style: Match the theme "{current_theme_name}". High-end architectural photography, 8k resolution.

[OUTPUT FORMAT]
Output ONLY the final English prompt string. Do NOT output any conversational text like "Here is the prompt". Do NOT use markdown blocks. Start directly with the description.""",
                        types.Part.from_bytes(data=m_bytes, mime_type="image/jpeg")
                    ]
                )
                room_description = analysis.text.strip()
                
            elif room_features_input:
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
                
                ## ────────── ① 表紙 ──────────
                if page_data['type'] == 'cover':
                    st.write(f"🎨 表紙の背景（街並み）をAIで生成中...（テーマ: {NEIGHBORHOOD_THEMES[selected_neighborhood_key]}）")

                    # ✨ 追加：ユーザーが選択した物件種別（戸建て/マンション）の英語
                    property_type_en = "detached houses" if selected_property_key == "house" else "apartment buildings"

                    # ✨ 修正：日本の一般的な住宅街、建築事情をより強く反映した街並みプロンプト
                    neighborhood_prompts = {
                        "green": f"A peaceful Japanese residential street with lush greenery, street trees, and sunlight filtering through leaves, featuring modern Japanese {property_type_en}. Wide, well-paved road.",
                        "urban": f"A sophisticated modern Japanese cityscape with clean architecture, paved streets, and a stylish urban atmosphere, featuring modern Japanese {property_type_en} and office buildings. Eye-level view.",
                        "quiet": f"An upscale, quiet Japanese residential neighborhood with elegant streetscapes and a peaceful atmosphere, featuring large and high-end Japanese {property_type_en}. Asphalt road, power lines (not dominant).",
                        "station": f"A vibrant and convenient Japanese station-front area with high-end shops, clean streets, and a lively atmosphere, featuring Japanese {property_type_en} and commercial buildings.",
                        "open": f"An open and airy Japanese streetscape with a wide blue sky, near a river or a wide tree-lined boulevard, featuring Japanese {property_type_en}."
                    }
                    
                    target_cityscape = neighborhood_prompts[selected_neighborhood_key]

                    try:
                        # 街並みを主役にしつつ、テキスト用の余白を考慮したプロンプト
                        prompt=f"Photorealistic high-end architectural photography of a {target_cityscape} in Japan. Eye-level view, wide angle, clean and bright. Full frame single image, NO buildings in the center to allow for text placement. NO text, NO logos, NO people."
                        image_result = gemini_client.models.generate_images(
                            model='imagen-4.0-generate-001',
                            prompt=prompt,
                            config=types.GenerateImagesConfig(
                                number_of_images=1,
                                aspect_ratio="4:3" if orientation == "横向き (Landscape)" else "3:4"
                            )
                        )
                        generated_bytes = image_result.generated_images[0].image.image_bytes
                        bg_image = Image.open(BytesIO(generated_bytes)).convert("RGB").resize((width, height))
                    except Exception as e:
                        st.error(f"表紙画像生成エラー: {e}") 
                        bg_image = Image.new('RGB', (width, height), color=theme_bg)
                
                # ────────── ② 空撮地図 ──────────
                elif page_data['type'] == 'aerial_map':
                    st.write(f"🎨 空撮マップの背景画像をAIで生成中...（種別: {selected_property_type_label}）")

                    target_city_town = page_data.get('city_town_clean', '日本の都市部')
                    
                    # ✨ 修正：空撮画像も、選んだ規模に合わせて街並みを変える
                    if selected_property_key == "house":
                        aerial_desc = "dense suburban residential area in Japan, featuring realistic Japanese detached houses, narrow streets, and typical roofing"
                    else:
                        if selected_apt_scale == "low":
                            aerial_desc = "peaceful Japanese residential neighborhood, featuring 3-story low-rise apartment buildings and houses, lots of green trees"
                        elif selected_apt_scale == "mid":
                            aerial_desc = "typical Japanese urban cityscape, featuring medium-density mid-rise 6-story apartment buildings and roads"
                        else: # high
                            aerial_desc = "dense urban Japanese cityscape, featuring realistic high-rise tower mansions, large roads, and skyscrapers"

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
                        image_result = gemini_client.models.generate_images(
                            model='imagen-4.0-generate-001',
                            prompt="Photorealistic beautiful nature background, lush green trees, soft sunlight, bright and clean landscape, suitable for a real estate flyer background. NO text, NO logos.",
                            config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="4:3" if orientation == "横向き (Landscape)" else "3:4")
                        )
                        generated_bytes = image_result.generated_images[0].image.image_bytes
                        base_bg = Image.open(BytesIO(generated_bytes)).convert("RGB").resize((width, height))
                        bg_image = Image.blend(base_bg, Image.new('RGB', (width, height), color=(255, 255, 255)), alpha=0.5)
                    except Exception as e:
                        st.warning(f"3ページ目の画像生成エラー: {e}")
                        bg_image = Image.new('RGB', (width, height), color=(240, 245, 240))

                    draw = ImageDraw.Draw(bg_image)
                    draw.rectangle([(0, 0), (width, height * 0.12)], fill=theme_ac)
                    try: font_headline = ImageFont.truetype(FONT_PATH, int(height * 0.08))
                    except: font_headline = ImageFont.load_default()
                    draw.text((width*0.05, height*0.06), "MAP & ACCESS", font=font_headline, fill="white", anchor="lm")
                    # ✨ 枠の焼き付けを削除しました

                # ────────── ④ 間取り図 ──────────
                elif page_data['type'] == 'floor_plan':
                    bg_image = Image.new('RGB', (width, height), color="white")
                    draw = ImageDraw.Draw(bg_image)
                    header_h = int(height * 0.16)
                    draw.rectangle([(0, 0), (width, header_h)], fill=theme_ac)

                    if madori_file:
                        m_img = Image.open(madori_file).convert("RGB")
                        m_img.thumbnail((width * 0.9, height * 0.8))
                        p_x = (width - m_img.width) // 2
                        p_y = (header_h + (height - header_h - m_img.height) // 2)
                        bg_image.paste(m_img, (int(p_x), int(p_y)))
                    else:
                        draw.text((width/2, height/2), "間取り図がアップロードされていません", fill="gray", anchor="mm")
                
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

                    draw = ImageDraw.Draw(bg_image)
                    draw.rectangle([(0, 0), (width, height * 0.12)], fill=(20, 35, 75))
                    f_h = get_fitting_font(draw, "INTERIOR VISION", int(height * 0.08), width * 0.5)
                    sub_text = page_data.get('sub_headline', '')
                    f_s = get_fitting_font(draw, sub_text, int(height * 0.04), width * 0.4)
                    draw.text((width*0.05, height*0.06), "INTERIOR VISION", font=f_h, fill="white", anchor="lm")
                    draw.text((width*0.95, height*0.06), sub_text, font=f_s, fill="white", anchor="rm")
                
                # ────────── ⑥ 内観ギャラリー ──────────
                elif page_data['type'] == 'interior':
                    bg_image = Image.new('RGB', (width, height), color="white")
                    draw = ImageDraw.Draw(bg_image)
                    draw.rectangle([(0, 0), (width, height * 0.12)], fill=theme_ac)
                    
                    f_h = get_fitting_font(draw, "INTERIOR GALLERY", int(height * 0.08), width * 0.5)
                    f_s = get_fitting_font(draw, "内観ギャラリー", int(height * 0.04), width * 0.4)
                    draw.text((width*0.05, height*0.06), "INTERIOR GALLERY", font=f_h, fill="white", anchor="lm")
                    draw.text((width*0.95, height*0.06), "内観ギャラリー", font=f_s, fill="white", anchor="rm")
                    # ✨ 枠の焼き付けを削除しました

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

    # ✨ PowerPoint上に「自由に動かせる枠」を作るための便利機能
    def add_placeholder_box(slide_obj, left, top, width, height, text):
        tx_box = slide_obj.shapes.add_textbox(left, top, width, height)
        tx_box.fill.solid()
        tx_box.fill.fore_color.rgb = RGBColor(245, 245, 245) # 薄いグレー背景
        tx_box.line.color.rgb = RGBColor(180, 180, 180)      # 枠線
        tf = tx_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = text
        p.font.size = Pt(14)
        p.font.color.rgb = RGBColor(100, 100, 100)

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

        # ✨ 修正：1ページ目（表紙）に全テキストを手入力（編集可能）な状態で配置
        if i == 0 and st.session_state.ai_data:
            p1_data = st.session_state.ai_data[0]
            city_town_text = p1_data.get('city_town', '地域名')
            station_info_text = p1_data.get('station_info', '駅徒歩X分')
            property_name_jp_text = p1_data.get('property_name_jp', '物件名')
            sub_copy_text = p1_data.get('sub_copy', 'サブコピー')
            
            # テーマに合わせて文字色を決定
            text_color_rgb = RGBColor(0, 0, 0) if theme_tc == "black" else RGBColor(255, 255, 255)
            
            if orientation == "横向き (Landscape)":
                # 物件名とサブコピー（左上）
                tx_box_prop = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9.0), Inches(0.8))
                tx_box_sub = slide.shapes.add_textbox(Inches(0.5), Inches(1.3), Inches(9.0), Inches(0.6))
                # 所在地と駅徒歩（下部）
                tx_box_city = slide.shapes.add_textbox(Inches(6.5), Inches(6.5), Inches(3.0), Inches(0.8))
                add_station_info_circle(slide, Inches(0.5), Inches(5.8), Inches(0.8), station_info_text)
            else:
                # 物件名とサブコピー（左上）
                tx_box_prop = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(6.5), Inches(0.8))
                tx_box_sub = slide.shapes.add_textbox(Inches(0.5), Inches(1.3), Inches(6.5), Inches(0.8))
                # 所在地と駅徒歩（下部）
                tx_box_city = slide.shapes.add_textbox(Inches(3.5), Inches(8.5), Inches(3.5), Inches(0.8))
                add_station_info_circle(slide, Inches(0.5), Inches(7.5), Inches(1.0), station_info_text)
            
            # 物件名のテキスト設定
            tf_prop = tx_box_prop.text_frame
            tf_prop.word_wrap = True
            p_prop = tf_prop.paragraphs[0]
            p_prop.text = property_name_jp_text
            p_prop.font.size = Pt(40)
            p_prop.font.bold = True
            p_prop.font.color.rgb = text_color_rgb
            
            # サブコピーのテキスト設定
            tf_sub = tx_box_sub.text_frame
            tf_sub.word_wrap = True
            p_sub = tf_sub.paragraphs[0]
            p_sub.text = sub_copy_text
            p_sub.font.size = Pt(18)
            p_sub.font.bold = True
            p_sub.font.color.rgb = text_color_rgb

            # 所在地のテキスト設定
            tf_city = tx_box_city.text_frame
            tf_city.word_wrap = True
            p_city = tf_city.paragraphs[0]
            p_city.text = city_town_text
            p_city.font.size = Pt(28)
            p_city.font.bold = True
            p_city.font.color.rgb = text_color_rgb
            p_city.alignment = PP_ALIGN.RIGHT

        # (以下、既存のページ処理が続く...)

        # 3ページ目（MAP & ACCESS）
        if i == 2 and st.session_state.ai_data:
            p3_data = st.session_state.ai_data[2]
            acc_text = p3_data.get('access_info', '交通情報がありません')
            if isinstance(acc_text, list): acc_text = "\n".join(str(x) for x in acc_text)
            life_text = p3_data.get('life_info', '周辺施設情報がありません')
            if isinstance(life_text, list): life_text = "\n".join(str(x) for x in life_text)
            
            if orientation == "横向き (Landscape)":
                add_placeholder_box(slide, Inches(0.5), Inches(1.1), Inches(4.5), Inches(3.0), "【 MAP画像 挿入枠 】\n※自由にサイズ変更・削除できます")
                tx_box_acc = slide.shapes.add_textbox(Inches(0.5), Inches(4.5), Inches(4.0), Inches(2.5))
                tx_box_life = slide.shapes.add_textbox(Inches(5.0), Inches(4.5), Inches(4.5), Inches(2.5))
            else:
                add_placeholder_box(slide, Inches(0.5), Inches(1.5), Inches(6.5), Inches(3.5), "【 MAP画像 挿入枠 】\n※自由にサイズ変更・削除できます")
                tx_box_acc = slide.shapes.add_textbox(Inches(0.5), Inches(5.5), Inches(6.5), Inches(1.5))
                tx_box_life = slide.shapes.add_textbox(Inches(0.5), Inches(7.2), Inches(6.5), Inches(2.5))
            
            tf_acc = tx_box_acc.text_frame
            tf_acc.word_wrap = True
            p_acc = tf_acc.add_paragraph()
            p_acc.text = "【 交通アクセス 】\n" + acc_text
            p_acc.font.size = Pt(14)
            p_acc.font.color.rgb = RGBColor(50, 50, 50)
            
            tf_life = tx_box_life.text_frame
            tf_life.word_wrap = True
            p_life = tf_life.add_paragraph()
            p_life.text = "【 Life Information 】\n" + life_text
            p_life.font.size = Pt(14)
            p_life.font.color.rgb = RGBColor(50, 50, 50)

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
            
            tf_title = tb_title.text_frame
            p_title = tf_title.paragraphs[0]
            p_title.text = prop_name_jp
            p_title.font.size = Pt(28)
            p_title.font.color.rgb = RGBColor(255, 255, 255)
            p_title.font.bold = True
            
            tf_area = tb_area.text_frame
            p_area1 = tf_area.paragraphs[0]
            p_area1.text = land_area
            p_area1.font.size = Pt(12)
            p_area1.font.color.rgb = RGBColor(255, 255, 255)
            p_area1.alignment = PP_ALIGN.RIGHT
            if building_area:
                p_area2 = tf_area.add_paragraph()
                p_area2.text = building_area
                p_area2.font.size = Pt(12)
                p_area2.font.color.rgb = RGBColor(255, 255, 255)
                p_area2.alignment = PP_ALIGN.RIGHT
            
            tf_price = tb_price.text_frame
            p_price = tf_price.paragraphs[0]
            p_price.text = price_jp
            p_price.font.size = Pt(32)
            p_price.font.color.rgb = RGBColor(255, 255, 255)
            p_price.font.bold = True
            p_price.alignment = PP_ALIGN.RIGHT

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
            fill.fore_color.rgb = RGBColor(195, 160, 100)
            
            tf = tx_box.text_frame
            tf.word_wrap = True
            tf.clear() 
            
            p_name = tf.add_paragraph()
            p_name.text = c_data.get('company_name', '株式会社 東宝ハウス')
            p_name.font.bold = True
            p_name.font.size = Pt(28)
            p_name.alignment = PP_ALIGN.CENTER

            p_info = tf.add_paragraph()
            p_info.text = f"{c_data.get('license', '')}\n{c_data.get('address', '')}\nフリーダイヤル {c_data.get('tel', '')}"
            p_info.font.size = Pt(16)
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