import streamlit as st
import os
import json
import fitz  # PyMuPDF
import glob
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from google import genai
from dotenv import load_dotenv
from io import BytesIO
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

# --- 修正：PDFだけでなく画像も許可する ---
col_u1, col_u2 = st.columns(2)
with col_u1:
    uploaded_file = st.file_uploader("販売図面（PDFまたは画像）をアップロード", type=["pdf", "png", "jpg", "jpeg"])
with col_u2:
    madori_file = st.file_uploader("間取り図の画像をアップロード（P.4用）", type=["png", "jpg", "jpeg"])

if uploaded_file is not None and uploaded_file.name != st.session_state.current_file:
    st.session_state.finished_pages = []
    st.session_state.ai_data = None
    st.session_state.current_file = uploaded_file.name
    st.session_state.pdf_text = ""

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
    
    if not st.session_state.pdf_text:
        st.write("PDF図面を解析中...")
        pdf_bytes = uploaded_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        extracted_text = ""
        for page_num in range(doc.page_count):
            extracted_text += doc.load_page(page_num).get_text()
            
        st.session_state.pdf_text = extracted_text

    with st.status("🎨 6ページのパンフレットを作成中...（約1分かかります）", expanded=True) as status:
        try:
            st.write("AIが物件情報、指定地域、デザインテーマを分析中...")
            gemini_client = genai.Client(api_key=gemini_api_key)
            # --- ここを追加：間取り図をAIに読み取らせる ---
            room_description = "A modern living room" # 読み取れなかった時の予備
            if madori_file:
                st.write("🔍 間取り図からお部屋のレイアウトを解析中...")
                m_bytes = madori_file.getvalue()
                # AIに間取り図を見せて、その形を言葉で説明させます
                analysis = gemini_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        "この間取り図に基づいた3Dインテリア画像を作りたいです。部屋の配置、窓の位置、キッチンの形を詳しく英語で説明してください。スタイルはモダンで。",
                        types.Part.from_bytes(data=m_bytes, mime_type="image/jpeg")
                    ]
                )
                room_description = analysis.text
            theme_info = THEMES[selected_style_key]
            
            # --- 修正：ユーザーの自由入力プロンプトを反映させる ---
            current_theme_name = custom_style_description if selected_style_key == "other" else theme_info["name"]
            
            # 比率の指示を動的に変える
            ratio_text = "4:3（横長）" if orientation == "横向き (Landscape)" else "3:4（縦長）"
            
            # --- 修正：7ページ構成（4ページ目に間取り図）のプロンプト全文 ---
            prompt = f"""
            不動産図面を解析し、以下の7ページ構成のパンフレット（比率 {ratio_text}）を作成してください。
            
            【デザインの最優先条件】
            ・デザインスタイル: {current_theme_name}
            
            上記スタイルと指示に合わせ、1ページ目の背景画像生成プロンプトや、メインキャッチコピー、周辺環境の説明文（main_text）を調整してください。
            
            対象地域（空撮マップ用）は「物件所在地周辺」です。
            [
              {{
                "page": 1, "type": "cover",
                "price": "抽出価格（例：5,480万円）", 
                "main_copy": "テーマに合わせたメインキャッチコピー", 
                "side_copy": "テーマに合わせたサブコピー",
                "property_name": "抽出した物件名"
              }},
              {{
                "page": 2, "type": "aerial_map",
                "headline": "FUTURE VISION", 
                "sub_headline": "未来を描く",
                "main_text": "テーマに合わせた周辺環境の魅力テキスト（3〜4行程度）", 
                "plots": [
                  {{"name": "最寄り駅", "x": 0.3, "y": 0.4, "type": "station"}},
                  {{"name": "小学校", "x": 0.7, "y": 0.6, "type": "school"}},
                  {{"name": "公園", "x": 0.8, "y": 0.3, "type": "park"}}
                ]
              }},
              {{
                "page": 3, "type": "access", "headline": "MAP & ACCESS", 
                "source_pdf_page": 4, "life_info": "周辺施設情報を改行ありの箇条書きで"
              }},
              {{
                "page": 4, "type": "floor_plan",
                "headline": "FLOOR PLAN", 
                "sub_headline": "洗練された居住空間"
              }},
              {{
                "page": 5, "type": "interior_hq", "headline": "INTERIOR VISION", 
                "sub_headline": "間取り図から描き出した完成予想イメージ"
              }},
              {{
                "page": 6, "type": "interior", "headline": "内観ギャラリー", "source_pdf_page": 5
              }},
              {{ 
                "page": 7, "type": "company", 
                "company_name": "{branch_info['full_name']}",
                "license": "{branch_info['license']}",
                "address": "{branch_info['address']}",
                "tel": "{branch_info['tel']}"
              }}
            ]
            【補助データ】: {st.session_state.pdf_text}
            """
            
            response = gemini_client.models.generate_content(
                model='gemini-2.5-flash', 
                contents=prompt, 
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            
            raw_json = response.text.strip()
            if raw_json.startswith("```json"): 
                raw_json = raw_json[7:-3].strip()
            elif raw_json.startswith("```"): 
                raw_json = raw_json[3:-3].strip()
                
            st.session_state.ai_data = json.loads(raw_json)
            
            # --- 描画用のヘルパー関数群 ---
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
                
                # ────────── ① 表紙 ──────────
                if page_data['type'] == 'cover':
                    st.write(f"🎨 表紙の背景画像をAIで生成中...（テーマ: {theme_info['name']}）")
                    try:
                        # ✨ 修正：モデル名を安定版にし、configの囲いを正確に記述
                        image_result = gemini_client.models.generate_images(
                            model='imagen-4.0-generate-001', # 最も安定しているモデル名
                            prompt=f"日本の閑静な住宅街にある、洗練された現代的な一戸建て住宅の外観。モダンな建築デザイン。青空と美しい植栽。テーマは「{theme_info['name']}」。高品質な建築写真スタイル。",
                            config=types.GenerateImagesConfig(
                                number_of_images=1,
                                aspect_ratio="4:3" if orientation == "横向き (Landscape)" else "3:4"
                            )
                        )
                        generated_bytes = image_result.generated_images[0].image.image_bytes
                        bg_image = Image.open(BytesIO(generated_bytes)).convert("RGB").resize((width, height))
                    except Exception as e:
                        st.error(f"1ページ目の画像生成でエラー: {e}")
                        bg_image = Image.new('RGB', (width, height), color=theme_bg)

                    draw = ImageDraw.Draw(bg_image)
                    max_w = width * 0.9

                    prop_name = page_data.get('property_name', 'THE HERITAGE').replace('\n', ' ')
                    side_copy = page_data.get('side_copy', '').replace('\n', ' ')
                    main_copy = page_data.get('main_copy', '').replace('\n', ' ')
                    price_text = page_data.get('price', '--- 万円').replace('\n', ' ')

                    # --- デザイン設定（練馬HP風） ---
                    navy_color = (20, 35, 75)     # 影に使う信頼の紺
                    gold_color = (195, 160, 100)  # アクセントの金
                    off = 2                        # 影のズレ幅

                    # 1. 物件名（白文字 + 紺の影）
                    font_prop = get_fitting_font(draw, prop_name, int(height * 0.12), max_w)
                    draw.text((width/2+off, height*0.1+off), prop_name, font=font_prop, fill=navy_color, anchor="mt")
                    draw.text((width/2, height * 0.1), prop_name, font=font_prop, fill="white", anchor="mt")

                    # 2. サブコピー（白文字 + 紺の影）
                    font_sub = get_fitting_font(draw, side_copy, int(height * 0.04), max_w)
                    draw.text((width/2+off, height*0.35+off), side_copy, font=font_sub, fill=navy_color, anchor="mt")
                    draw.text((width/2, height * 0.35), side_copy, font=font_sub, fill="white", anchor="mt")

                    # 3. メインコピー（白文字 + 紺の影）
                    font_main = get_fitting_font(draw, main_copy, int(height * 0.08), max_w)
                    draw.text((width/2+off, height*0.55+off), main_copy, font=font_main, fill=navy_color, anchor="mm")
                    draw.text((width/2, height*0.55), main_copy, font=font_main, fill="white", anchor="mm")

                    # 4. 価格ボックス（ゴールド背景 + 白文字）
                    font_price = get_fitting_font(draw, price_text, int(height * 0.1), width * 0.4)
                    p_w = draw.textbbox((0, 0), price_text, font=font_price)[2] - draw.textbbox((0, 0), price_text, font=font_price)[0]
                    draw.rectangle([(width - p_w - 60, height * 0.8), (width - 20, height * 0.92)], fill=gold_color)
                    draw.text((width - p_w/2 - 40, height * 0.86), price_text, font=font_price, fill="white", anchor="mm")

                # ────────── ② 空撮地図 ──────────
                elif page_data['type'] == 'aerial_map':
                    st.write(f"🎨 空撮マップの背景画像をAIで生成中...（テーマ: {theme_info['name']}）")
                    try:
                        # ✨ 修正：ここが文法エラーでスキップの原因でした！configの囲いを追加
                        image_result = gemini_client.models.generate_images(
                            model='imagen-4.0-generate-001',
                            prompt=f"日本の都市近郊にある、整然とした典型的な住宅街の空撮写真。一戸建てが並ぶ閑静な街並み。テーマは「{theme_info['name']}」。クリーンな風景写真。",
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

                    # 影のズレ幅
                    off = 1

                    # Headline
                    draw.text((width*0.05+off, height*0.05+off), headline, font=font_head, fill="black", anchor="la") # 影
                    draw.text((width*0.05, height*0.05), headline, font=font_head, fill="white", anchor="la")        # 本体

                    # Sub Headline
                    draw.text((width*0.05+off, height*0.13+off), sub_headline, font=font_subhead, fill="black", anchor="la") # 影
                    draw.text((width*0.05, height*0.13), sub_headline, font=font_subhead, fill="white", anchor="la")         # 本体

                    # Main Text（ multiline_text には影も2回書きます）
                    draw.multiline_text((width*0.05+off, height*0.2+off), main_text, font=font_main, fill="black", spacing=10) # 影
                    draw.multiline_text((width*0.05, height*0.2), main_text, font=font_main, fill="white", spacing=10)         # 本体

                    # --- 以前あった「ピン描画(for plot in plots_data)」と「物件所在地(if pins)」のコードを削除しました ---

                # ────────── ③ アクセス・地図 ──────────
                elif page_data['type'] == 'access':
                    bg_image = Image.new('RGB', (width, height), color=(250, 253, 250))
                    draw = ImageDraw.Draw(bg_image)
                    
                    draw.rectangle([(0, 0), (width, height * 0.12)], fill=theme_ac)
                    try: 
                        font_headline = ImageFont.truetype(FONT_PATH, int(height * 0.08))
                        font_body = ImageFont.truetype(FONT_PATH, int(height * 0.04))
                        font_life = ImageFont.truetype(FONT_PATH, int(height * 0.045))
                    except: 
                        font_headline = ImageFont.load_default()
                        font_body = ImageFont.load_default()
                        font_life = ImageFont.load_default()

                    draw.text((width*0.05, height*0.06), "MAP & ACCESS", font=font_headline, fill="white", anchor="lm")

                    doc_for_map = fitz.open(stream=pdf_bytes, filetype="pdf")
                    target_page = max(0, min(page_data.get('source_pdf_page', 4) - 1, doc_for_map.page_count - 1))
                    pix = doc_for_map.load_page(target_page).get_pixmap(matrix=fitz.Matrix(2.5, 2.5))
                    map_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    m_draw = ImageDraw.Draw(map_img)
                    pin_x, pin_y = map_img.width / 2, map_img.height / 2
                    r = 15
                    m_draw.ellipse([pin_x-r, pin_y-r*2, pin_x+r, pin_y], fill=(255, 0, 0), outline="white", width=2)
                    m_draw.polygon([(pin_x-r, pin_y-r), (pin_x+r, pin_y-r), (pin_x, pin_y+10)], fill=(255, 0, 0), outline="white")
                    
                    map_img.thumbnail((width * 0.5, height * 0.7))
                    bg_image.paste(map_img, (int(width * 0.05), int(height * 0.2)))

                    draw.rectangle([(width*0.6, height*0.2), (width*0.9, height*0.26)], fill=theme_ac)
                    draw.text((width*0.75, height*0.23), "Life Information", font=font_life, fill="white", anchor="mm")
                    
                    life_info_text = page_data.get('life_info', '情報なし')
                    draw.multiline_text((width*0.6, height*0.3), life_info_text, font=font_body, fill=(50, 50, 50))

                    # ────────── ④ 間取り図（新規追加） ──────────
                elif page_data['type'] == 'floor_plan':
                    bg_image = Image.new('RGB', (width, height), color="white")
                    draw = ImageDraw.Draw(bg_image)
                    
                    # ヘッダー（ネイビー）
                    draw.rectangle([(0, 0), (width, height * 0.12)], fill=(20, 35, 75))
                    try:
                        f_h = ImageFont.truetype(FONT_PATH, int(height * 0.08))
                        f_s = ImageFont.truetype(FONT_PATH, int(height * 0.04))
                    except: f_h = f_s = ImageFont.load_default()
                    
                    draw.text((width*0.05, height*0.06), "FLOOR PLAN", font=f_h, fill="white", anchor="lm")
                    draw.text((width*0.4, height*0.06), page_data.get('sub_headline', ''), font=f_s, fill="white", anchor="lm")

                    # アップロードされた間取り図を中央に配置
                    if madori_file:
                        m_img = Image.open(madori_file).convert("RGB")
                        m_img.thumbnail((width * 0.8, height * 0.7))
                        p_x, p_y = (width - m_img.width) // 2, (height * 0.15 + (height * 0.8 - m_img.height) // 2)
                        bg_image.paste(m_img, (int(p_x), int(p_y)))
                    else:
                        draw.text((width/2, height/2), "間取り図がアップロードされていません", fill="gray", anchor="mm")

                # ────────── ⑤ 内観（間取り図を基にAI生成） ──────────
                elif page_data['type'] == 'interior_hq':
                    st.write(f"🎨 間取り図に合わせたお部屋を生成中...")
                    try:
                        # 1箇所目で作った「間取りの説明」を使って絵を描きます
                        image_result = gemini_client.models.generate_images(
                            model='imagen-4.0-generate-001',
                            prompt=f"Photorealistic high-end interior, {room_description}, architectural photography style, 8k.",
                            config=types.GenerateImagesConfig(
                                number_of_images=1,
                                aspect_ratio="4:3" if orientation == "横向き (Landscape)" else "3:4"
                            )
                        )
                        generated_bytes = image_result.generated_images[0].image.image_bytes
                        bg_image = Image.open(BytesIO(generated_bytes)).convert("RGB").resize((width, height))
                    except Exception as e:
                        st.error(f"内観生成エラー: {e}")
                        bg_image = Image.new('RGB', (width, height), color="white")

                    draw = ImageDraw.Draw(bg_image)
                    # ヘッダー（紺色）を上から重ねる
                    draw.rectangle([(0, 0), (width, height * 0.12)], fill=(20, 35, 75))
                    try:
                        f_h = ImageFont.truetype(FONT_PATH, int(height * 0.08))
                        f_s = ImageFont.truetype(FONT_PATH, int(height * 0.04))
                    except: f_h = f_s = ImageFont.load_default()
                    draw.text((width*0.05, height*0.06), "INTERIOR VISION", font=f_h, fill="white", anchor="lm")
                    draw.text((width*0.45, height*0.06), page_data.get('sub_headline', ''), font=f_s, fill="white", anchor="lm")
                # ────────── ⑤ 内観（PDFそのまま抽出） ──────────
                elif page_data['type'] == 'interior':
                    doc_for_interior = fitz.open(stream=pdf_bytes, filetype="pdf")
                    target_page = max(0, min(page_data.get('source_pdf_page', 5) - 1, doc_for_interior.page_count - 1))
                    pix = doc_for_interior.load_page(target_page).get_pixmap(matrix=fitz.Matrix(3, 3))
                    extracted_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    bg_image = Image.new('RGB', (width, height), color="white")
                    extracted_img.thumbnail((width * 0.9, height * 0.9))
                    
                    paste_x, paste_y = (width - extracted_img.width) // 2, (height - extracted_img.height) // 2
                    bg_image.paste(extracted_img, (paste_x, paste_y))

                # ────────── ⑥ 会社案内 ──────────
                elif page_data['type'] == 'company':
                    bg_image = Image.new('RGB', (width, height), color='white')
                    draw = ImageDraw.Draw(bg_image)
                    
                    draw_dashed_rectangle(draw, [width*0.05, height*0.02, width*0.95, height*0.45], outline="lightgray")
                    draw.text((width/2, height*0.23), "【 店舗案内図 挿入エリア 】", fill="gray", anchor="mm")

                    draw_dashed_rectangle(draw, [width*0.05, height*0.47, width*0.48, height*0.72], outline="lightgray")
                    draw_dashed_rectangle(draw, [width*0.52, height*0.47, width*0.95, height*0.72], outline="lightgray")
                    draw.text((width*0.26, height*0.6), "【店舗外観】", fill="gray", anchor="mm")
                    draw.text((width*0.73, height*0.6), "【店舗内観】", fill="gray", anchor="mm")

                    try: 
                        font_msg = ImageFont.truetype(FONT_PATH, int(height * 0.035))
                        font_company = ImageFont.truetype(FONT_PATH, int(height * 0.05))
                    except: 
                        font_msg = ImageFont.load_default()
                        font_company = ImageFont.load_default()
                        
                    draw.text((width/2, height*0.76), "ご質問・現地確認のご希望に関してはご連絡下さい。", font=font_msg, fill="gray", anchor="mm")
                    company_info_text = f"{page_data.get('company_name', '')}    TEL: {page_data.get('tel', '')}"
                    draw.text((width/2, height*0.85), company_info_text, font=font_company, fill="lightgray", anchor="mm")
                    draw.text((width/2, height*0.92), "※PowerPoint上で編集可能なテキストボックスになります", font=font_msg, fill="lightgray", anchor="mm")

                if bg_image:
                    generated_pages.append(bg_image)

            st.session_state.finished_pages = generated_pages
            status.update(label="✅ 全6ページが完成しました！", state="complete", expanded=False)

        except Exception as e:
            st.error(f"作成中にエラーが発生しました: {e}")
            st.stop()

# --- 5. 画面表示とPowerPoint作成 ---
if st.session_state.finished_pages:
    st.write("---")
    st.subheader("🎉 完成したパンフレット")
    
    cols = st.columns(len(st.session_state.finished_pages))
    for i, page_img in enumerate(st.session_state.finished_pages):
        with cols[i]:
            st.write(f"**P.{i+1}**")
            st.image(page_img, use_container_width=True)

    prs = Presentation()
    # 向きに合わせてスライドサイズを設定
    if orientation == "横向き (Landscape)":
        prs.slide_width, prs.slide_height = Inches(10), Inches(7.5)
    else:
        prs.slide_width, prs.slide_height = Inches(7.5), Inches(10)

    for i, page_img in enumerate(st.session_state.finished_pages):
        slide = prs.slides.add_slide(prs.slide_layouts[6]) 
        
        img_io = BytesIO()
        page_img.save(img_io, format='PNG')
        img_io.seek(0)
        
        slide.shapes.add_picture(img_io, 0, 0, width=prs.slide_width, height=prs.slide_height)

        if i == 6 and st.session_state.ai_data:
            c_data = st.session_state.ai_data[6]
            
            tx_box = slide.shapes.add_textbox(Inches(0.5), Inches(5.6), Inches(9.0), Inches(1.7))
            fill = tx_box.fill
            fill.solid()
            # 会社のテキストボックス背景をゴールドに変更
            fill.fore_color.rgb = RGBColor(195, 160, 100)
            
            tf = tx_box.text_frame
            tf.word_wrap = True
            tf.clear() 
            
            p_name = tf.add_paragraph()
            p_name.text = c_data.get('company_name', '株式会社 東宝ハウス国分寺')
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