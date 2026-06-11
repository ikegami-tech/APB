from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import os
import json
import time
from io import BytesIO
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from google import genai
from google.genai import types
from dotenv import load_dotenv

# --- 環境設定とGeminiの準備 ---
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")
# APIキーがあればGeminiクライアントを準備
gemini_client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None

FONT_PATH = './NotoSansCJKjp-Bold.ttf'

# --- 店舗・テーマデータの定義（app.pyからお引越し） ---
THEMES = {
    "luxury":       {"name": "1 高級・ラグジュアリー", "bg_color": (40, 40, 45), "text_color": "white", "accent_color": (180, 150, 80)},
    "family":       {"name": "2 ファミリー・温もり", "bg_color": (255, 245, 235), "text_color": "black", "accent_color": (240, 130, 50)},
    "modern":       {"name": "3 スタイリッシュ・モダン", "bg_color": (240, 245, 255), "text_color": "black", "accent_color": (50, 100, 180)},
    "wa_modern":    {"name": "4 和モダン・伝統美", "bg_color": (230, 225, 215), "text_color": "black", "accent_color": (100, 120, 80)},
    "casual":       {"name": "5 カジュアル・ポップ", "bg_color": (255, 250, 220), "text_color": "black", "accent_color": (250, 100, 130)},
    "other":        {"name": "6 その他（自由入力スタイル）", "bg_color": (240, 240, 240), "text_color": "black", "accent_color": (100, 100, 100)}
}

BRANCH_DATA = {
    "練馬": {
        "full_name": "株式会社 東宝ハウス練馬",
        "license": "東京都知事（4）第86488号",
        "address": "〒178-0063 東京都練馬区東大泉1-27-22光和ビル2F",
        "tel": "0120-384-700",
        "login_id": "th-nerima",      
        "password": "th-nerima"   
    },
    "国分寺": {
        "full_name": "株式会社 東宝ハウス国分寺",
        "license": "東京都知事（9）第42787号",
        "address": "〒185-0021 東京都国分寺市南町3-22-2",
        "tel": "0120-13-3107",
        "login_id": "kokubunji",   
        "password": "kokubunji"   
    },
    "武蔵野": {
        "full_name": "株式会社 東宝ハウス武蔵野",
        "license": "東京都知事（3）第90333号",
        "address": "〒180-0004 東京都武蔵野市吉祥寺本町1-15-9",
        "tel": "0120-15-3101",
        "login_id": "musashino",   
        "password": "musashino"   
    },
}

app = FastAPI(title="らくらく販売図面 APIサーバー")
# （これより下はそのまま残します）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🌟 ここを追加：静的ファイル（CSS, JS）を配信するための設定
app.mount("/static", StaticFiles(directory="static"), name="static")

# (上のimportやmiddleware設定はそのまま)

# 🌟 1. ログイン画面（最初のアドレス）
# 🌟 ブラウザからのアイコン要求（favicon）エラーを無視する設定
from fastapi.responses import Response
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204) # 「アイコンは無いから探さなくていいよ」と返事する
    html_path = os.path.join(os.path.dirname(__file__), "templates", "login.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()

# 🌟 2. 総合メニューポータル画面
@app.get("/menu", response_class=HTMLResponse)
def read_menu():
    html_path = os.path.join(os.path.dirname(__file__), "templates", "menu.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()

# 🌟 3. APB（パンフレット作成）画面
@app.get("/apb", response_class=HTMLResponse)
def read_apb():
    html_path = os.path.join(os.path.dirname(__file__), "templates", "apb.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()

# 🌟 4. 販売図面作成画面（旧index.html）
@app.get("/zumen", response_class=HTMLResponse)
def read_zumen():
    html_path = os.path.join(os.path.dirname(__file__), "templates", "zumen.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()
# ==========================================
# 🎨 パワポ装飾・画像処理用の便利ツール群
# ==========================================

def get_fitting_font(draw_obj, text, initial_size, max_width):
    """画像（PIL）に文字を入れる際、枠にはみ出さないようにサイズを自動調整する機能"""
    size = initial_size
    try: 
        font = ImageFont.truetype(FONT_PATH, size)
    except: 
        return ImageFont.load_default()
    while draw_obj.textbbox((0, 0), text, font=font)[2] > max_width and size > 10:
        size -= 2
        font = ImageFont.truetype(FONT_PATH, size)
    return font

def add_placeholder_box(slide_obj, left, top, width, height, text, luxury_gold_rgb=None, show_icon=False, label_text="MAIN SLOT"):
    """パワポ内に、高級感のあるゴールド枠線付きのプレースホルダー（画像挿入枠）を作る機能"""
    tx_box = slide_obj.shapes.add_textbox(left, top, width, height)
    tx_box.fill.solid()
    tx_box.fill.fore_color.rgb = RGBColor(245, 245, 245) # 予備の薄いグレー
    
    if luxury_gold_rgb:
        tx_box.line.color.rgb = luxury_gold_rgb
    else:
        tx_box.line.color.rgb = RGBColor(185, 160, 110) # デフォルトゴールド
    tx_box.line.width = Pt(1)
    
    tf = tx_box.text_frame
    tf.word_wrap = True
    tf.clear()
    
    if show_icon:
        p_label = tf.add_paragraph()
        p_label.text = label_text
        p_label.font.size = Pt(9)
        p_label.font.name = "游ゴシック"
        p_label.font.color.rgb = RGBColor(150, 150, 150)
        p_label.alignment = PP_ALIGN.CENTER
        
        p_icon = tf.add_paragraph()
        p_icon.text = "🔍"
        p_icon.font.size = Pt(12)
        p_icon.alignment = PP_ALIGN.CENTER
        
    p_jp = tf.add_paragraph()
    clean_text = text.replace("【", "").replace("】", "").replace(" ", "")
    p_jp.text = clean_text
    p_jp.font.size = Pt(11)
    p_jp.font.name = "游明朝"
    p_jp.font.color.rgb = RGBColor(80, 80, 80)
    p_jp.alignment = PP_ALIGN.CENTER

def add_station_info_circle(slide_obj, x, y, radius, text, color=(245, 240, 225)):
    """表紙などに使われる、駅徒歩情報の「円形グラフィック」を作る機能"""
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
def generate_with_retry(model_name, prompt_contents, generation_config=None):
    """
    Geminiサーバーが混雑して429（回数制限）や503（一時停止）のエラーが出た際に、
    自動的に少し待ってから最大11回まで粘り強く再試行する、システムの守り神となる関数です。
    """
    wait_times = [30, 60, 120, 180, 240, 300, 360, 420, 480, 540, 600]
    max_attempts = len(wait_times) + 1
    
    for attempt in range(max_attempts):
        try:
            time.sleep(2)
            if generation_config:
                res = gemini_client.models.generate_content(model=model_name, contents=prompt_contents, config=generation_config)
            else:
                res = gemini_client.models.generate_content(model=model_name, contents=prompt_contents)
            return res
        except Exception as inner_e:
            # サーバー制限エラーを検知した場合、待機してリトライ
            if ("503" in str(inner_e) or "429" in str(inner_e)) and attempt < len(wait_times):
                wait_sec = wait_times[attempt]
                print(f"⚠️ Geminiの制限に達しました。{wait_sec}秒待機して自動再試行します... (試行 {attempt + 1}/{len(wait_times)})")
                time.sleep(wait_sec)
            else:
                raise inner_e
# --- ここから APB（パンフレット自動作成）用の本番処理 ---
@app.post("/generate_apb")
async def generate_apb(
    zumen_file: UploadFile = File(None),
    madori_file: UploadFile = File(None),
    empty_file: UploadFile = File(None),
    map_file: UploadFile = File(None),
    orientation: str = Form("portrait"),
    selected_pages: list[str] = Form([])
):
    import base64
    print("🚀 【APB】本番用のパンフレット生成プログラムを起動しました...")
    
    # 🌟 画面プレビュー用の軽量画像を格納するリスト
    preview_list = []
    
    def image_to_base64(img_obj):
        """Imageオブジェクトを画面表示用に小さく縮小し、軽量なJPEGに圧縮して変換する安全関数"""
        try:
            preview_img = img_obj.copy()
            preview_img.thumbnail((300, 300)) # 横幅最大300pxに縮小
            buf = BytesIO()
            preview_img.save(buf, format="JPEG", quality=50) # 高圧縮JPEGで激軽化
            return base64.b64encode(buf.getvalue()).decode('utf-8')
        except Exception as e:
            print(f"プレビュー画像変換エラー: {e}")
            dummy = Image.new('RGB', (100, 100), color=(200, 200, 200))
            buf = BytesIO()
            dummy.save(buf, format="JPEG")
            return base64.b64encode(buf.getvalue()).decode('utf-8')
    
    # 1. アップロードされた各種ファイルのバイナリ（データ）読み込み
    zumen_bytes = await zumen_file.read() if zumen_file else None
    madori_bytes = await madori_file.read() if madori_file else None
    empty_bytes = await empty_file.read() if empty_file else None
    map_bytes = await map_file.read() if map_file else None
    
    # 2. 【AI処理】販売図面のOCR解析（テキスト抽出）
    pdf_text = ""
    if zumen_bytes and gemini_client:
        print("🔍 販売図面をAI（OCR）で読み取り中...")
        mime_type = "application/pdf" if zumen_file.filename.lower().endswith(".pdf") else "image/jpeg"
        ocr_analysis = generate_with_retry(
            model_name='gemini-2.5-flash',
            prompt_contents=[
                "図面に記載されているすべてのテキスト情報を正確に抽出してください。特に「物件名」「所在地」「交通」「価格」「面積」「周辺施設」の情報は絶対に漏れなく抽出してください。Imagen生成用の地名（市区町村）も特定してください。",
                types.Part.from_bytes(data=zumen_bytes, mime_type=mime_type)
            ]
        )
        pdf_text = ocr_analysis.text if ocr_analysis else ""

    # 3. 【AI処理】ページ構成用JSONデータの生成（プロの不動産ライター風）
    extracted_info = {}
    if pdf_text and gemini_client:
        print("🧠 AIが物件情報、地域名、デザインテーマを詳細分析中...")
        ratio_text = "4:3（横長）" if orientation == "landscape" else "3:4（縦長）"
        
        prompt = f"""
        あなたはプロの不動産ライターです。提供された【補助データ】を隅々まで解析し、以下の情報をJSON形式（オブジェクト、または配列の最初の要素）で出力してください。
        必須キー: property_name_jp, property_name_en, city_town, station_info, price, price_jp, land_area, building_area, sub_copy, headline, sub_headline, main_text, access_info, life_info, company_name, license, address, tel
        出力は必ず純粋なJSON形式のみにしてください。
        比率: {ratio_text}
        【補助データ】: {pdf_text}
        """
        
        json_res = generate_with_retry(
            model_name='gemini-2.5-flash', 
            prompt_contents=prompt, 
            generation_config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        if json_res:
            raw_json = json_res.text.strip()
            if raw_json.startswith("```" + "json"): 
                raw_json = raw_json[7:-3].strip()
            elif raw_json.startswith("```"): 
                raw_json = raw_json[3:-3].strip()
            
            try:
                parsed_data = json.loads(raw_json)
                extracted_info = parsed_data[0] if isinstance(parsed_data, list) and len(parsed_data) > 0 else parsed_data
            except:
                extracted_info = {}

    # 4. 【画像生成処理】表紙（Cover）の3パターン自動生成ループ
    cover_images = []
    if "cover" in selected_pages and gemini_client:
        print("📸 表紙のデザイン案を3パターン（家族・リビング等）同時にImagenで生成中...")
        target_place = extracted_info.get("city_town", "Tokyo")
        
        prompts = [
            f"High-end luxury magazine photography. A happy Japanese family playing happily in a beautiful sunny park in {target_place}. Bright natural daylight, soft sunlight filtering through trees. Modern and sophisticated casual style. NO text.",
            f"High-end luxury lifestyle photography. A sophisticated Japanese man relaxing and drinking coffee in a modern, spacious luxury living room of a detached house in {target_place}. Premium interior design, close-up shot. NO text.",
            f"High-end luxury lifestyle photography. A happy Japanese family playing in a stylish, high-ceiling living room of a luxury modern apartment in {target_place}. Sophisticated interior design, bright natural light, warm family atmosphere. NO text."
        ]
        
        for idx, p in enumerate(prompts):
            for attempt in range(4):
                try:
                    img_res = gemini_client.models.generate_images(
                        model='imagen-4.0-generate-001',
                        prompt=p,
                        config=types.GenerateImagesConfig(
                            number_of_images=1, 
                            aspect_ratio="4:3" if orientation == "landscape" else "3:4"
                        )
                    )
                    cover_images.append(Image.open(BytesIO(img_res.generated_images[0].image.image_bytes)))
                    time.sleep(3)
                    break
                except Exception as img_e:
                    if "429" in str(img_e) and attempt < 3:
                        print(f"⏳ 画像生成制限（429）を検知。15秒後に自動試行します... (再試行 {attempt+1}/3)")
                        time.sleep(15)
                    else:
                        raise img_e

# 5. 【PowerPoint組み立て】
    print("📊 高級感のあるPowerPointスライドを1枚ずつ緻密に組み立て中...")
    prs = Presentation()
    if orientation == "landscape":
        prs.slide_width, prs.slide_height = Inches(10), Inches(7.5)
    else:
        prs.slide_width, prs.slide_height = Inches(7.5), Inches(10)

    width, height = (1024, 768) if orientation == "landscape" else (768, 1024)

    # ────────────────────────────────────────────────────────
    # 🌟 ① 表紙（Cover）の書き出し
    # ────────────────────────────────────────────────────────
    if "cover" in selected_pages:
        for idx, c_img in enumerate(cover_images if cover_images else [None]):
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            
            if c_img:
                img_io = BytesIO()
                c_img.save(img_io, format='PNG')
                img_io.seek(0)
                slide.shapes.add_picture(img_io, 0, 0, width=prs.slide_width, height=prs.slide_height)
                preview_list.append({"type": f"P.1 表紙 (案{idx+1})", "image": image_to_base64(c_img)})
            else:
                dummy = Image.new('RGB', (width, height), color=(40, 40, 45))
                preview_list.append({"type": "P.1 表紙", "image": image_to_base64(dummy)})
            
            sw, sh = prs.slide_width, prs.slide_height
            gold_color = RGBColor(215, 185, 140)
            
            top_bar_h = Inches(1.8) if orientation == "landscape" else Inches(2.2)
            top_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, sw, top_bar_h)
            top_bar.fill.solid()
            top_bar.fill.fore_color.rgb = RGBColor(20, 20, 20)
            try: top_bar.fill.transparency = 0.4
            except: pass
            top_bar.line.fill.background()
            
            tx_addr = slide.shapes.add_textbox(Inches(0.4), Inches(0.25), Inches(4.0), Inches(0.4))
            tx_addr.text_frame.paragraphs[0].text = extracted_info.get("city_town", "TOKYO")
            tx_addr.text_frame.paragraphs[0].font.size = Pt(13)
            tx_addr.text_frame.paragraphs[0].font.name = "游明朝"
            tx_addr.text_frame.paragraphs[0].font.color.rgb = RGBColor(230, 230, 230)
            
            prop_name = extracted_info.get("property_name_jp", "【物件名】")
            logo_font_size = Pt(36) if len(prop_name) > 15 else (Pt(48) if len(prop_name) > 10 else Pt(60))
            
            tx_logo = slide.shapes.add_textbox(Inches(0.35), Inches(0.6), sw - Inches(0.8), Inches(2.0))
            p_logo = tx_logo.text_frame.paragraphs[0]
            p_logo.text = prop_name
            p_logo.font.size = logo_font_size
            p_logo.font.bold = True
            p_logo.font.name = "游明朝"
            p_logo.font.color.rgb = gold_color

            bottom_bar_h = Inches(1.2) if orientation == "landscape" else Inches(1.5)
            bottom_bar_y = sh - bottom_bar_h
            bottom_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, bottom_bar_y, sw, bottom_bar_h)
            bottom_bar.fill.solid()
            bottom_bar.fill.fore_color.rgb = RGBColor(20, 20, 20)
            try: bottom_bar.fill.transparency = 0.4
            except: pass
            bottom_bar.line.fill.background()
            
            tx_sub = slide.shapes.add_textbox(Inches(1.5), bottom_bar_y + Inches(0.3), sw - Inches(1.8), Inches(1.0))
            p_sub = tx_sub.text_frame.paragraphs[0]
            p_sub.text = extracted_info.get("sub_copy", "都市の洗練と、静謐なるプライベートを纏う新邸。")
            p_sub.font.size = Pt(13)
            p_sub.font.name = "游明朝"
            p_sub.font.color.rgb = RGBColor(240, 240, 240)
            p_sub.alignment = PP_ALIGN.CENTER
            
            station_text = extracted_info.get("station_info", "最寄駅\n徒歩分数").replace('\\n', '\n')
            add_station_info_circle(slide, Inches(0.4), bottom_bar_y - Inches(0.5), Inches(0.55), station_text, color=(215, 185, 140))

    # ────────────────────────────────────────────────────────
    # 🌟 ② コンセプト（Concept / aerial_map）の書き出し
    # ────────────────────────────────────────────────────────
    if "aerial_map" in selected_pages:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(245, 240, 225)
        
        headline = "THE CONCEPT"
        sub_headline = extracted_info.get('sub_headline', '五感を満たす、静謐の邸宅。')
        main_text = extracted_info.get('main_text', '')
        bronze_rgb = RGBColor(215, 185, 140)
        
        concept_bg = Image.new('RGB', (width, height), color=(245, 240, 225))
        preview_list.append({"type": "P.2 コンセプト", "image": image_to_base64(concept_bg)})
        
        if orientation == "landscape":
            tx_box_head = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(4.5), Inches(0.6))
            line1 = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(1.3), Inches(4.5), Pt(1))
            line1.fill.solid()
            line1.fill.fore_color.rgb = bronze_rgb
            line1.line.color.rgb = bronze_rgb
            tx_box_sub = slide.shapes.add_textbox(Inches(0.5), Inches(1.6), Inches(4.5), Inches(0.6))
            tx_box_main = slide.shapes.add_textbox(Inches(0.5), Inches(2.5), Inches(4.0), Inches(3.0))
            
            add_placeholder_box(slide, Inches(4.5), Inches(0), Inches(5.5), Inches(7.5), "【 メイン画像 】")
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
            
            add_placeholder_box(slide, Inches(0), Inches(4.5), Inches(7.5), Inches(5.5), "【 メイン画像 】")
            add_placeholder_box(slide, Inches(4.5), Inches(3.5), Inches(2.5), Inches(2.0), "写真1")
            add_placeholder_box(slide, Inches(0.5), Inches(7.5), Inches(2.5), Inches(2.0), "写真2")

        p_head = tx_box_head.text_frame.paragraphs[0]
        p_head.text = headline
        p_head.font.name = "Arial"
        p_head.font.size = Pt(36)
        p_head.font.bold = True
        
        p_sub = tx_box_sub.text_frame.paragraphs[0]
        p_sub.text = sub_headline
        p_sub.font.name = "游ゴシック"
        p_sub.font.size = Pt(24)
        p_sub.font.bold = True
        p_sub.font.color.rgb = RGBColor(0,0,0)

        tf_main = tx_box_main.text_frame
        tf_main.word_wrap = True
        p_main = tf_main.paragraphs[0]
        p_main.text = main_text
        p_main.font.name = "游ゴシック"
        p_main.font.size = Pt(13)
        p_main.font.color.rgb = RGBColor(80,80,80)

    # ────────────────────────────────────────────────────────
    # 🌟 ③ MAP & ACCESS（アクセス・地図）の書き出し
    # ────────────────────────────────────────────────────────
    if "access" in selected_pages:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        acc_text = extracted_info.get('access_info', "交通情報がありません")
        if isinstance(acc_text, list): acc_text = "\n".join(str(x) for x in acc_text)
        
        life_text = extracted_info.get('life_info', "周辺施設情報がありません")
        if isinstance(life_text, list): life_text = "\n".join(str(x) for x in life_text)

        gold_color = RGBColor(180, 150, 80)
        navy_color = RGBColor(20, 30, 60)
        text_color_rgb = RGBColor(40, 40, 40)
        
        gen_map_io = None
        access_bg = Image.new('RGB', (width, height), color=(250, 250, 250))
        if map_bytes:
            print("🗺️ 地図画像をネイビー＆ゴールドの高級仕様に変換中...")
            try:
                map_img = Image.open(BytesIO(map_bytes)).convert("RGB")
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
                
                resized_map = final_map.resize((int(width * 0.7), int(height * 0.5)))
                access_bg.paste(resized_map, (int(width * 0.15), int(height * 0.2)))
            except Exception as e:
                print(f"地図変換エラー: {e}")
        preview_list.append({"type": "P.3 地図", "image": image_to_base64(access_bg)})

        if orientation == "landscape":
            tx_box_head = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(5.0), Inches(0.8))
            tx_box_sub = slide.shapes.add_textbox(Inches(0.5), Inches(1.1), Inches(5.0), Inches(0.4))
            line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(1.5), Inches(9.0), Pt(1.5))
            line.fill.solid()
            line.fill.fore_color.rgb = gold_color
            line.line.color.rgb = gold_color

            if gen_map_io:
                slide.shapes.add_picture(gen_map_io, Inches(0.5), Inches(1.7), width=Inches(9.0), height=Inches(4.2))
            else:
                add_placeholder_box(slide, Inches(0.5), Inches(1.7), Inches(9.0), Inches(4.2), "【 MAP画像 挿入枠 】\n※地図画像をアップロードすると自動で高級化されます")

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
                add_placeholder_box(slide, Inches(0.5), Inches(1.8), Inches(6.5), Inches(5.0), "【 MAP画像 挿入枠 】\n※地図画像をアップロードすると自動で高級化されます")
            
            tx_box_acc = slide.shapes.add_textbox(Inches(0.5), Inches(7.0), Inches(3.1), Inches(2.5))
            tx_box_life = slide.shapes.add_textbox(Inches(3.9), Inches(7.0), Inches(3.1), Inches(2.5))

        p_head = tx_box_head.text_frame.paragraphs[0]
        p_head.text = "MAP & ACCESS"
        p_head.font.size = Pt(40)
        p_head.font.bold = True
        p_head.font.color.rgb = navy_color
        p_head.font.name = "Arial"

        p_sub = tx_box_sub.text_frame.paragraphs[0]
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

    # ────────────────────────────────────────────────────────
    # 🌟 ④ 間取り（Floor Plan）の書き出し（修正版）
    # ────────────────────────────────────────────────────────
    if "floor_plan" in selected_pages:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        luxury_gold = RGBColor(185, 160, 110)
        
        print("🎨 間取り図ページの高級背景（木目グラデーション）をAIで生成中...")
        bg_prompt = (
            "A cinematic, high-end architectural background for a luxury property brochure. "
            "Top 20% area: dark charcoal gray slate stone with elegant natural texture. "
            "Bottom 80% area: rich, deep espresso luxury wood grain texture, vertical planks, "
            "with a subtle vertical gradient that gets progressively darker towards the bottom edge. "
            "High contrast, moody lighting, NO text, NO floor plans, NO logos."
        )
        
        try:
            image_result = gemini_client.models.generate_images(
                model='imagen-4.0-generate-001',
                prompt=bg_prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1, 
                    aspect_ratio="4:3" if orientation == "landscape" else "3:4"
                )
            )
            generated_bytes = image_result.generated_images[0].image.image_bytes
            fp_bg = Image.open(BytesIO(generated_bytes)).convert("RGB").resize((width, height))
        except Exception as e:
            print(f"4ページ目の背景生成エラー: {e}")
            fp_bg = Image.new('RGB', (width, height), color=(25, 20, 15))

        draw = ImageDraw.Draw(fp_bg)
        header_h = int(height * 0.20)

        # ゴールドの区切り線を立体的に描画
        gold_light = (215, 185, 140)
        gold_dark = (160, 130, 80)
        draw.rectangle([(0, header_h - 15), (width, header_h + 15)], fill=gold_light)
        draw.rectangle([(0, header_h - 2), (width, header_h + 2)], fill=gold_dark)

        # 間取り図を立体ゴールド額縁付きで合成
        if madori_bytes:
            try:
                m_img = Image.open(BytesIO(madori_bytes)).convert("RGB")
                frame_width = 15
                m_img_with_frame = Image.new('RGB', (m_img.width + frame_width*2, m_img.height + frame_width*2), gold_light)
                draw_frame = ImageDraw.Draw(m_img_with_frame)
                draw_frame.rectangle([(5, 5), (m_img_with_frame.width-5, m_img_with_frame.height-5)], outline=(100, 80, 40), width=3)
                m_img_with_frame.paste(m_img, (frame_width, frame_width))
                m_img_with_frame.thumbnail((width * 0.85, height * 0.70))
                
                p_x = (width - m_img_with_frame.width) // 2
                p_y = header_h + 40 + (height - header_h - 40 - m_img_with_frame.height) // 2
                fp_bg.paste(m_img_with_frame, (int(p_x), int(p_y)))
            except Exception as e:
                print(f"間取り図合成エラー: {e}")
        else:
            try:
                f_m = ImageFont.truetype(FONT_PATH, int(height * 0.025))
                draw.text((width/2, height/2), "間取り図がアップロードされていません", font=f_m, fill="white", anchor="mm")
            except: pass

        preview_list.append({"type": "P.4 間取り図", "image": image_to_base64(fp_bg)})

        # 背景画像貼り付け
        img_io_fp = BytesIO()
        fp_bg.save(img_io_fp, format='PNG')
        img_io_fp.seek(0)
        slide.shapes.add_picture(img_io_fp, 0, 0, width=prs.slide_width, height=prs.slide_height)

        # 【テキストボックスの配置最適化】
        if orientation == "landscape":
            tb_title = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(5.8), Inches(1.2))
            tb_area = slide.shapes.add_textbox(Inches(6.5), Inches(0.20), Inches(3.0), Inches(0.7))
            tb_price = slide.shapes.add_textbox(Inches(6.0), Inches(0.85), Inches(3.5), Inches(0.8))
        else:
            tb_title = slide.shapes.add_textbox(Inches(0.4), Inches(0.3), Inches(4.2), Inches(1.3))
            tb_area = slide.shapes.add_textbox(Inches(4.6), Inches(0.25), Inches(2.5), Inches(0.6))
            tb_price = slide.shapes.add_textbox(Inches(4.0), Inches(0.85), Inches(3.1), Inches(0.8))
            
        # ────────── 物件タイトル ──────────
        tf_title = tb_title.text_frame
        tf_title.word_wrap = True
        tf_title.margin_top = tf_title.margin_bottom = tf_title.margin_left = tf_title.margin_right = 0
        p_t = tf_title.paragraphs[0]
        p_t.text = extracted_info.get("property_name_jp", "物件名")
        
        name_len = len(p_t.text)
        if name_len > 20: p_t.font.size = Pt(20)
        elif name_len > 14: p_t.font.size = Pt(24)
        elif name_len > 10: p_t.font.size = Pt(28)
        else: p_t.font.size = Pt(32)
            
        p_t.font.name = "游明朝"
        p_t.font.bold = True
        p_t.font.color.rgb = luxury_gold
        try: p_t.font.shadow = True
        except: pass
        
        # ────────── 土地・建物面積（AIデータの自動クレンジング装置） ──────────
        import re
        tf_area = tb_area.text_frame
        tf_area.clear()
        tf_area.margin_top = tf_area.margin_bottom = tf_area.margin_left = tf_area.margin_right = 0
        
        p_l = tf_area.paragraphs[0]
        l_area = extracted_info.get("land_area")
        l_area_str = str(l_area).strip() if l_area is not None else ""
        
        if "所有権" in l_area_str or not re.search(r'\d', l_area_str):
            p_l.text = "土地 --- ㎡"
        else:
            if "土地" not in l_area_str: l_area_str = "土地 " + l_area_str
            if "㎡" not in l_area_str and "坪" not in l_area_str: l_area_str = l_area_str + "㎡"
            p_l.text = l_area_str
            
        p_l.font.size = Pt(14)
        p_l.font.color.rgb = luxury_gold
        p_l.alignment = PP_ALIGN.RIGHT
        try: p_l.font.shadow = True
        except: pass
        
        b_area = extracted_info.get("building_area")
        b_area_str = str(b_area).strip() if b_area is not None else ""
        
        if re.search(r'\d', b_area_str):
            p_b = tf_area.add_paragraph()
            if "建物" not in b_area_str: b_area_str = "建物 " + b_area_str
            if "㎡" not in b_area_str and "坪" not in b_area_str: b_area_str = b_area_str + "㎡"
            p_b.text = b_area_str
            p_b.font.size = Pt(14)
            p_b.font.color.rgb = luxury_gold
            p_b.alignment = PP_ALIGN.RIGHT
            try: p_b.font.shadow = True
            except: pass
            
        # ────────── 価格 ──────────
        tf_price = tb_price.text_frame
        tf_price.margin_top = tf_price.margin_bottom = tf_price.margin_left = tf_price.margin_right = 0
        p_p = tf_price.paragraphs[0]
        
        price_text = extracted_info.get("price_jp", "--- 万円")
        p_p.text = price_text
        p_p.font.name = "游明朝"
        p_p.font.bold = True
        p_p.font.color.rgb = luxury_gold
        p_p.alignment = PP_ALIGN.RIGHT
        try: p_p.font.shadow = True
        except: pass
        
        if len(price_text) > 12: p_p.font.size = Pt(24)
        elif len(price_text) > 8: p_p.font.size = Pt(30)
        else: p_p.font.size = Pt(36)

    # ────────────────────────────────────────────────────────
    # 🌟 ⑤ 内観生成（Interior HQ / バーチャルステージング）の書き出し
    # ────────────────────────────────────────────────────────
    if "interior_hq" in selected_pages:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        
        final_room_prompt = "A cinematic, high-end luxury living room interior, modern sophisticated design, bright natural light, luxury furniture, 8k resolution. NO text."
        if empty_bytes and gemini_client:
            print("🔍 空室写真を解析し、バーチャルステージング用のプロンプトを生成中...")
            try:
                analysis_img = generate_with_retry(
                    model_name='gemini-2.5-flash',
                    prompt_contents=[
                        "Analyze this empty room photo precisely. Generate a highly detailed English prompt for an Image Generation AI to recreate this EXACT room structure (same window placement, floor, wall) BUT add elegant luxury style furniture. Output ONLY the prompt string.",
                        types.Part.from_bytes(data=empty_bytes, mime_type="image/jpeg")
                    ]
                )
                if analysis_img and analysis_img.text:
                    final_room_prompt = analysis_img.text.strip()
            except Exception as e:
                print(f"空室解析エラー: {e}")

        bg_image = None
        if gemini_client:
            print("🎨 内観完成予想イメージをImagenで生成中...")
            for attempt in range(3):
                try:
                    image_result = gemini_client.models.generate_images(
                        model='imagen-4.0-generate-001',
                        prompt=final_room_prompt,
                        config=types.GenerateImagesConfig(
                            number_of_images=1, 
                            aspect_ratio="4:3" if orientation == "landscape" else "3:4"
                        )
                    )
                    generated_bytes = image_result.generated_images[0].image.image_bytes
                    bg_image = Image.open(BytesIO(generated_bytes)).convert("RGB")
                    break
                except Exception as e:
                    if "429" in str(e) and attempt < 2:
                        time.sleep(15)
                    else:
                        print(f"内観生成エラー: {e}")
                        break
        
        if bg_image:
            img_io = BytesIO()
            bg_image.save(img_io, format='PNG')
            img_io.seek(0)
            slide.shapes.add_picture(img_io, 0, 0, width=prs.slide_width, height=prs.slide_height)
            preview_list.append({"type": "P.5 内観完成予想", "image": image_to_base64(bg_image)})
        else:
            dummy = Image.new('RGB', (width, height), color=(240, 240, 240))
            preview_list.append({"type": "P.5 内観完成予想", "image": image_to_base64(dummy)})

        sw, sh = prs.slide_width, prs.slide_height
        bar_h = Inches(1.5)
        bar_y = sh - bar_h
        bottom_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, bar_y, sw, bar_h)
        bottom_bar.fill.solid()
        bottom_bar.fill.fore_color.rgb = RGBColor(0, 0, 0)
        try: bottom_bar.fill.transparency = 0.3
        except: pass
        bottom_bar.line.fill.background()
        
        gold_line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, bar_y, sw, Pt(4))
        gold_line.fill.solid()
        gold_line.fill.fore_color.rgb = RGBColor(185, 160, 110)
        gold_line.line.fill.background()
        
        tx_head = slide.shapes.add_textbox(sw * 0.05, bar_y + Inches(0.15), sw * 0.5, Inches(0.8))
        tf_head = tx_head.text_frame

        p_en = tf_head.paragraphs[0]
        p_en.text = "INTERIOR VISION"
        p_en.font.size = Pt(30)
        p_en.font.color.rgb = RGBColor(255, 255, 255)
        p_en.alignment = PP_ALIGN.LEFT

        p_jp = tf_head.add_paragraph()
        p_jp.text = "内観完成予想イメージ"
        p_jp.font.size = Pt(14)
        p_jp.font.name = "游明朝"
        p_jp.font.color.rgb = RGBColor(255, 255, 255)
        p_jp.alignment = PP_ALIGN.LEFT
        p_jp.space_before = Pt(4)

    # ────────────────────────────────────────────────────────
    # 🌟 ⑥ 内観ギャラリー（Gallery）の書き出し
    # ────────────────────────────────────────────────────────
    if "interior" in selected_pages:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        sw, sh = prs.slide_width, prs.slide_height
        luxury_gold = RGBColor(185, 160, 110)
        
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(20, 20, 25)
        
        gallery_bg = Image.new('RGB', (width, height), color=(20, 20, 25))
        preview_list.append({"type": "P.6 内観ギャラリー", "image": image_to_base64(gallery_bg)})

        if orientation == "landscape":
            en_y, jp_y, bar_y, main_y, main_h = Inches(0.2), Inches(0.7), Inches(1.4), Inches(1.6), Inches(2.5)
            sub1_y, sub2_y, sub_h = Inches(4.3), Inches(5.8), Inches(1.3)
            
            add_placeholder_box(slide, Inches(0.5), main_y, Inches(9.0), main_h, "【 メイン画像 】", luxury_gold, show_icon=True, label_text="MAIN SLOT")
            add_placeholder_box(slide, Inches(0.5), sub1_y, Inches(4.3), sub_h, "【 サブ画像1 】", luxury_gold, show_icon=True, label_text="SUB 1")
            add_placeholder_box(slide, Inches(5.2), sub1_y, Inches(4.3), sub_h, "【 サブ画像2 】", luxury_gold, show_icon=True, label_text="SUB 2")
            add_placeholder_box(slide, Inches(0.5), sub2_y, Inches(4.3), sub_h, "【 サブ画像3 】", luxury_gold, show_icon=True, label_text="SUB 3")
            add_placeholder_box(slide, Inches(5.2), sub2_y, Inches(4.3), sub_h, "【 サブ画像4 】", luxury_gold, show_icon=True, label_text="SUB 4")
        else:
            en_y, jp_y, bar_y, main_y, main_h = Inches(0.3), Inches(0.8), Inches(1.5), Inches(1.7), Inches(3.7)
            sub1_y, sub2_y, sub_h = Inches(5.6), Inches(7.6), Inches(1.8)
            
            add_placeholder_box(slide, Inches(0.5), main_y, Inches(6.5), main_h, "【 メイン画像 】", luxury_gold, show_icon=True, label_text="MAIN SLOT")
            add_placeholder_box(slide, Inches(0.5), sub1_y, Inches(3.1), sub_h, "【 サブ1 】", luxury_gold, show_icon=True, label_text="SUB 1")
            add_placeholder_box(slide, Inches(3.9), sub1_y, Inches(3.1), sub_h, "【 サブ2 】", luxury_gold, show_icon=True, label_text="SUB 2")
            add_placeholder_box(slide, Inches(0.5), sub2_y, Inches(3.1), sub_h, "【 サブ3 】", luxury_gold, show_icon=True, label_text="SUB 3")
            add_placeholder_box(slide, Inches(3.9), sub2_y, Inches(3.1), sub_h, "【 サブ4 】", luxury_gold, show_icon=True, label_text="SUB 4")

        gold_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, bar_y, sw, Pt(6))
        gold_bar.fill.solid()
        gold_bar.fill.fore_color.rgb = luxury_gold
        gold_bar.line.fill.background()

        tx_head_en = slide.shapes.add_textbox(sw * 0.05, en_y, sw * 0.5, Inches(0.5))
        tx_head_en.text_frame.paragraphs[0].text = "INTERIOR GALLERY"
        tx_head_en.text_frame.paragraphs[0].font.size, tx_head_en.text_frame.paragraphs[0].font.color.rgb = Pt(28), RGBColor(255, 255, 255)
        
        tx_head_jp = slide.shapes.add_textbox(sw * 0.05, jp_y, sw * 0.4, Inches(0.6))
        tx_head_jp.text_frame.paragraphs[0].text = "内観ギャラリー"
        tx_head_jp.text_frame.paragraphs[0].font.size, tx_head_jp.text_frame.paragraphs[0].font.name, tx_head_jp.text_frame.paragraphs[0].font.color.rgb = Pt(16), "游明朝", luxury_gold

    # ────────────────────────────────────────────────────────
    # 🌟 ⑦ 会社案内（Company）の書き出し
    # ────────────────────────────────────────────────────────
    if "company" in selected_pages:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        sw, sh = prs.slide_width, prs.slide_height
        luxury_gold = RGBColor(185, 160, 110)
        
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(20, 20, 25)
        
        company_bg = Image.new('RGB', (width, height), color=(20, 20, 25))
        preview_list.append({"type": "P.7 会社案内", "image": image_to_base64(company_bg)})

        if orientation == "landscape":
            main_y, main_h = Inches(0.4), Inches(4.2)
            sub_y, sub_h = Inches(4.8), Inches(2.1)
            sub_w = Inches(4.3)
            
            add_placeholder_box(slide, Inches(0.5), main_y, Inches(9.0), main_h, "【 会社案内 メイン画像 】", luxury_gold, show_icon=True, label_text="COMPANY MAIN")
            add_placeholder_box(slide, Inches(0.5), sub_y, sub_w, sub_h, "【 オフィス写真 】", luxury_gold, show_icon=True, label_text="OFFICE")
            add_placeholder_box(slide, Inches(5.2), sub_y, sub_w, sub_h, "【 スタッフ写真 】", luxury_gold, show_icon=True, label_text="STAFF")
        else:
            main_y, main_h = Inches(0.5), Inches(5.5)
            sub_y, sub_h = Inches(6.2), Inches(3.0)
            sub_w = Inches(3.1)
            
            add_placeholder_box(slide, Inches(0.5), main_y, Inches(6.5), main_h, "【 会社案内 メイン画像 】", luxury_gold, show_icon=True, label_text="COMPANY MAIN")
            add_placeholder_box(slide, Inches(0.5), sub_y, sub_w, sub_h, "【 オフィス写真 】", luxury_gold, show_icon=True, label_text="OFFICE")
            add_placeholder_box(slide, Inches(3.9), sub_y, sub_w, sub_h, "【 スタッフ写真 】", luxury_gold, show_icon=True, label_text="STAFF")

        tx_slogan = slide.shapes.add_textbox(0, sh * 0.94, sw, Inches(0.4))
        p_slogan = tx_slogan.text_frame.paragraphs[0]
        p_slogan.text = "「住まい」を通じて、お客様の人生に確かな価値を。"
        p_slogan.font.size, p_slogan.font.name = Pt(14), "游明朝"
        p_slogan.font.color.rgb = RGBColor(245, 240, 225)
        p_slogan.alignment = PP_ALIGN.CENTER

    # ────────────────────────────────────────────────────────
    # 🌟 ⑧ Contact & Thank you スライド（結び、共通で最後に追加）
    # ────────────────────────────────────────────────────────
    slide_thanks = prs.slides.add_slide(prs.slide_layouts[6]) 
    sw, sh = prs.slide_width, prs.slide_height
    gold_main = RGBColor(185, 160, 110)
    
    fill_thanks = slide_thanks.background.fill
    fill_thanks.solid()
    fill_thanks.fore_color.rgb = RGBColor(252, 248, 242)
    
    thanks_bg = Image.new('RGB', (width, height), color=(252, 248, 242))
    preview_list.append({"type": "P.8 結び", "image": image_to_base64(thanks_bg)})

    top_line = slide_thanks.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, sw, Pt(6))
    top_line.fill.solid()
    top_line.fill.fore_color.rgb = gold_main
    top_line.line.fill.background()

    tx_ty = slide_thanks.shapes.add_textbox(0, sh * 0.12, sw, Inches(1.0))
    p_ty = tx_ty.text_frame.paragraphs[0]
    p_ty.text = "THANK YOU"
    p_ty.font.size, p_ty.font.name, p_ty.alignment = Pt(48), "Arial", PP_ALIGN.CENTER

    map_box_w, map_box_h = Inches(5.5), Inches(2.2) 
    add_placeholder_box(slide_thanks, (sw - map_box_w) / 2, sh * 0.30, map_box_w, map_box_h, "店舗案内図（地図）")

    box_w, box_h, box_y = Inches(6.5), Inches(1.8), sh * 0.68 
    box = slide_thanks.shapes.add_shape(MSO_SHAPE.RECTANGLE, (sw - box_w) / 2, box_y, box_w, box_h)
    box.fill.solid()
    box.fill.fore_color.rgb = RGBColor(255, 255, 255)
    box.line.color.rgb = RGBColor(240, 240, 240)
    box.line.width = Pt(1)

    tx_contact = slide_thanks.shapes.add_textbox((sw - box_w) / 2, box_y, box_w, box_h)
    tf_contact = tx_contact.text_frame
    tf_contact.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf_contact.margin_top = tf_contact.margin_bottom = 0
    tf_contact.clear()
    
    tel_info = extracted_info.get("tel", "0120-000-000")
    lic_info = extracted_info.get("license", "東京都知事（〇）第〇〇〇号")
    adr_info = extracted_info.get("address", "東京都...")

    p_tel = tf_contact.add_paragraph()
    p_tel.text = f"フリーダイヤル：{tel_info}"
    p_tel.font.size, p_tel.font.bold, p_tel.font.color.rgb, p_tel.alignment = Pt(26), True, gold_main, PP_ALIGN.CENTER

    p_info = tf_contact.add_paragraph()
    p_info.text = f"{lic_info}  |  {adr_info}"
    p_info.font.size, p_info.font.color.rgb, p_info.alignment = Pt(10), RGBColor(120, 120, 120), PP_ALIGN.CENTER

    # 6. 完成したPowerPointファイルをバイナリ（データストリーム）としてBase64化
    pptx_io = BytesIO()
    prs.save(pptx_io)
    pptx_io.seek(0)
    pptx_base64 = base64.b64encode(pptx_io.getvalue()).decode('utf-8')

    print("✅ 【APB】すべてのAI解析・画像合成・パワポ作成がエラーなく完了しました！")
    return {
        "status": "success",
        "preview_images": preview_list,
        "pptx_base64": pptx_base64
    }