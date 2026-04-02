import streamlit as st
import os
import json
import fitz  # PyMuPDF
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

# --- デザインテーマの設定 ---
THEMES = {
    "style_1": {
        "name": "① 高級・ラグジュアリー（落ち着いたトーン、富裕層向け）",
        "bg_color": (40, 40, 45), "text_color": "white", "accent_color": (180, 150, 80)
    },
    "style_2": {
        "name": "② ファミリー・温もり（明るく親しみやすい、子育て向け）",
        "bg_color": (255, 245, 235), "text_color": "black", "accent_color": (240, 130, 50)
    },
    "style_3": {
        "name": "③ スタイリッシュ・モダン（シンプルで都会的、単身・DINKS向け）",
        "bg_color": (240, 245, 255), "text_color": "black", "accent_color": (50, 100, 180)
    },
    "style_4": {
        "name": "④ 和モダン（伝統と新しさが融合した落ち着き）",
        "bg_color": (230, 225, 215), "text_color": "black", "accent_color": (100, 120, 80)
    },
    "style_5": {
        "name": "⑤ カジュアル・ポップ（軽快で若々しい印象）",
        "bg_color": (255, 250, 220), "text_color": "black", "accent_color": (250, 100, 130)
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

# --- 3. ファイルアップロードとデザイン選択UI ---
uploaded_file = st.file_uploader("販売図面のPDFをドラッグ＆ドロップ", type="pdf")

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
    format_func=lambda x: THEMES[x]["name"]
)

user_target_area = st.text_input("例：国分寺市南町、練馬区下石神井", key="user_target_area")

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
            theme_info = THEMES[selected_style_key]
            
            prompt = f"""
            不動産図面を解析し、以下の6ページ構成のパンフレット（4:3比率）を作成してください。
            今回のターゲットおよびデザインテーマは「{theme_info["name"]}」です。
            特に「main_copy」や「main_text」は、このテーマの客層に刺さるような魅力的な表現に調整してください。
            対象地域（空撮マップ用）は「{user_target_area if user_target_area else '物件所在地周辺'}」です。
            
            出力はJSON配列形式のみにしてください。
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
                "page": 4, "type": "interior_hq", "headline": "内観", "sub_headline": "建物内覧・完成予想図"
              }},
              {{
                "page": 5, "type": "interior", "headline": "内観ギャラリー", "source_pdf_page": 5
              }},
              {{ 
                "page": 6, "type": "company", 
                "company_name": "株式会社 東宝ハウス国分寺",
                "license": "東京都知事（9）第42787号",
                "address": "〒185-0021 東京都国分寺市南町3-22-2",
                "tel": "0120-13-3107"
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
            width = 1024
            height = 768
            
            theme_bg = theme_info["bg_color"]
            theme_tc = theme_info["text_color"]
            theme_ac = theme_info["accent_color"]

            for page_data in st.session_state.ai_data:
                st.write(f"🖼️ {page_data['page']}ページ目（{page_data['type']}）を合成中...")
                bg_image = None
                
                # ────────── ① 表紙 ──────────
                if page_data['type'] == 'cover':
                    template_path = f"{selected_style_key}_p1.png"
                    
                    if os.path.exists(template_path):
                        base_img = Image.open(template_path).resize((width, height)).convert("RGB")
                        
                        # テーマに合わせて用意した画像を動的加工！
                        enhancer_color = ImageEnhance.Color(base_img)
                        enhancer_brightness = ImageEnhance.Brightness(base_img)
                        enhancer_contrast = ImageEnhance.Contrast(base_img)
                        
                        if selected_style_key == "style_1":
                            bg_image = enhancer_color.enhance(0.7)
                            bg_image = ImageEnhance.Brightness(bg_image).enhance(0.85)
                        elif selected_style_key == "style_2":
                            bg_image = enhancer_color.enhance(1.2)
                            bg_image = ImageEnhance.Brightness(bg_image).enhance(1.1)
                        elif selected_style_key == "style_3":
                            bg_image = enhancer_color.enhance(0.4)
                            bg_image = enhancer_contrast.enhance(1.2)
                        elif selected_style_key == "style_4":
                            bg_image = enhancer_color.enhance(0.8)
                            bg_image = enhancer_contrast.enhance(0.9)
                        else:
                            bg_image = base_img
                    else:
                        bg_image = Image.new('RGB', (width, height), color=theme_bg)

                    draw = ImageDraw.Draw(bg_image)
                    max_w = width * 0.9

                    prop_name = page_data.get('property_name', 'THE HERITAGE').replace('\n', ' ')
                    side_copy = page_data.get('side_copy', '').replace('\n', ' ')
                    main_copy = page_data.get('main_copy', '').replace('\n', ' ')
                    price_text = page_data.get('price', '--- 万円').replace('\n', ' ')

                    font_prop = get_fitting_font(draw, prop_name, int(height * 0.12), max_w)
                    draw.text((width/2, height * 0.1), prop_name, font=font_prop, fill=theme_tc, anchor="mt")
                    
                    font_sub = get_fitting_font(draw, side_copy, int(height * 0.04), max_w)
                    draw.text((width/2, height * 0.35), side_copy, font=font_sub, fill=theme_tc, anchor="mt")

                    font_main = get_fitting_font(draw, main_copy, int(height * 0.08), max_w)
                    draw.text((width/2, height*0.55), main_copy, font=font_main, fill=theme_tc, anchor="mm")

                    font_price = get_fitting_font(draw, price_text, int(height * 0.1), width * 0.4)
                    p_w = draw.textbbox((0, 0), price_text, font=font_price)[2] - draw.textbbox((0, 0), price_text, font=font_price)[0]
                    
                    draw.rectangle([(width - p_w - 60, height * 0.8), (width - 20, height * 0.92)], fill=theme_ac)
                    draw.text((width - p_w/2 - 40, height * 0.86), price_text, font=font_price, fill="white", anchor="mm")

                # ────────── ② 空撮地図 ──────────
                elif page_data['type'] == 'aerial_map':
                    template_path_p2 = f"{selected_style_key}_p2.png"
                    
                    if os.path.exists(template_path_p2):
                        base_img = Image.open(template_path_p2).resize((width, height)).convert("RGB")
                        
                        # 2ページ目の画像もテーマに合わせて動的加工
                        enhancer_color = ImageEnhance.Color(base_img)
                        enhancer_brightness = ImageEnhance.Brightness(base_img)
                        enhancer_contrast = ImageEnhance.Contrast(base_img)
                        
                        if selected_style_key == "style_1":
                            bg_image = enhancer_color.enhance(0.7)
                            bg_image = ImageEnhance.Brightness(bg_image).enhance(0.85)
                        elif selected_style_key == "style_2":
                            bg_image = enhancer_color.enhance(1.2)
                            bg_image = ImageEnhance.Brightness(bg_image).enhance(1.1)
                        elif selected_style_key == "style_3":
                            bg_image = enhancer_color.enhance(0.4)
                            bg_image = enhancer_contrast.enhance(1.2)
                        else:
                            bg_image = base_img
                    else:
                        bg_image = Image.new('RGB', (width, height), color=theme_bg)

                    draw = ImageDraw.Draw(bg_image)
                    
                    try:
                        font_head = ImageFont.truetype(FONT_PATH, int(height * 0.07))
                        font_subhead = ImageFont.truetype(FONT_PATH, int(height * 0.04))
                        font_main = ImageFont.truetype(FONT_PATH, int(height * 0.03))
                        font_label = ImageFont.truetype(FONT_PATH, int(height * 0.025))
                    except:
                        font_head = font_subhead = font_main = font_label = ImageFont.load_default()

                    headline = page_data.get('headline', 'FUTURE VISION').replace('\n', ' ')
                    sub_headline = page_data.get('sub_headline', '').replace('\n', ' ')
                    main_text = page_data.get('main_text', '')

                    draw.text((width*0.05, height*0.05), headline, font=font_head, fill=theme_tc, anchor="la")
                    draw.text((width*0.05, height*0.13), sub_headline, font=font_subhead, fill=theme_tc, anchor="la")
                    draw.multiline_text((width*0.05, height*0.2), main_text, font=font_main, fill=theme_tc, spacing=10)

                    pins = []
                    plots_data = page_data.get('plots', [])
                    
                    for plot in plots_data:
                        px = int(plot.get('x', 0.5) * width)
                        py = int(plot.get('y', 0.5) * height)
                        plot_name = plot.get('name', '施設').replace('\n', ' ')
                        pins.append((px, py, plot_name))
                        
                        r = int(height * 0.01)
                        p_color = theme_ac if 'station' in plot.get('type', '') else (200, 50, 50)
                        draw.ellipse([px-r, py-r, px+r, py+r], fill=p_color, outline="white", width=2)
                        
                        draw.rectangle([px-r, py-r*2-int(height*0.045), px+r*6, py-r*2], fill=(255, 255, 255, 200), outline="lightgray")
                        draw.text((px+r*2, py-r*2-int(height*0.023)), plot_name, font=font_label, fill="black", anchor="lm")

                    if pins:
                        mx, my = pins[0][0], pins[0][1]
                        r = int(height * 0.01)
                        draw.ellipse([mx-r, my-r, mx+r, my+r], fill=(255, 255, 50), outline="white", width=4)
                        for i in range(int(height*0.4)):
                            draw.ellipse([mx-(r+i/5), my-(r*2+i)-r, mx+(r+i/5), my-(r*2+i)+r], fill=(255, 255, 150, int(255*(1-i/(height*0.4)))), outline=None)
                        draw.rectangle([mx+int(width*0.05), my-r-int(height*0.05), mx+int(width*0.3), my+r+int(height*0.05)], fill=theme_ac, outline="white", width=2)
                        draw.text((mx+int(width*0.17), my), "物件所在地", font=font_main, fill="white", anchor="mm")

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

                # ────────── ④ 内観レイアウト枠 ──────────
                elif page_data['type'] == 'interior_hq':
                    bg_image = Image.new('RGB', (width, height), color="white")
                    draw = ImageDraw.Draw(bg_image)
                    
                    draw.rectangle([(0, 0), (width, height * 0.12)], fill=theme_ac)
                    try: 
                        font_headline = ImageFont.truetype(FONT_PATH, int(height * 0.08))
                        font_subhead = ImageFont.truetype(FONT_PATH, int(height * 0.04))
                        font_placeholder = ImageFont.truetype(FONT_PATH, int(height * 0.03))
                    except: 
                        font_headline = ImageFont.load_default()
                        font_subhead = ImageFont.load_default()
                        font_placeholder = ImageFont.load_default()
                        
                    draw.text((width*0.05, height*0.06), "内 観", font=font_headline, fill="white", anchor="lm")
                    draw.text((width*0.25, height*0.06), page_data.get('sub_headline', ''), font=font_subhead, fill="white", anchor="lm")
                    
                    main_rect = [width*0.1, height*0.15, width*0.9, height*0.6]
                    draw_dashed_rectangle(draw, main_rect)
                    draw.text((width/2, height*0.37), "[メイン画像挿入枠]", font=font_placeholder, fill="gray", anchor="mm")
                    
                    sub_w, sub_h = width * 0.2, height * 0.2
                    for i in range(4):
                        start_x = width * 0.05 + (i * (sub_w + width * 0.04))
                        sub_rect = [start_x, height * 0.65, start_x + sub_w, height * 0.65 + sub_h]
                        draw_dashed_rectangle(draw, sub_rect)
                        draw.text((start_x + sub_w/2, height * 0.65 + sub_h/2), f"[画像 {i+1}]", font=font_placeholder, fill="gray", anchor="mm")

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
    prs.slide_width, prs.slide_height = Inches(10), Inches(7.5)

    for i, page_img in enumerate(st.session_state.finished_pages):
        slide = prs.slides.add_slide(prs.slide_layouts[6]) 
        
        img_io = BytesIO()
        page_img.save(img_io, format='PNG')
        img_io.seek(0)
        
        slide.shapes.add_picture(img_io, 0, 0, width=prs.slide_width, height=prs.slide_height)

        if i == 5 and st.session_state.ai_data:
            c_data = st.session_state.ai_data[5]
            
            tx_box = slide.shapes.add_textbox(Inches(0.5), Inches(5.6), Inches(9.0), Inches(1.7))
            fill = tx_box.fill
            fill.solid()
            fill.fore_color.rgb = RGBColor(255, 255, 255)
            
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