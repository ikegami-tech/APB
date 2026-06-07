from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles # 🌟 ここを追加
import os
from io import BytesIO
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

app = FastAPI(title="らくらく販売図面 APIサーバー")

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
@app.get("/", response_class=HTMLResponse)
def read_login():
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

# (これより下の @app.post("/generate_zumen") などのプログラムは一切消さずにそのまま残してください)

@app.post("/generate_zumen_file")
async def generate_zumen_file(
    title: str = Form(...),
    price: str = Form("---"),
    address: str = Form("---"),
    main_image: UploadFile = File(None)
):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(10), Inches(7.5)
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    tx_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9.0), Inches(1.5))
    tf = tx_box.text_frame
    
    p_title = tf.paragraphs[0]
    p_title.text = f"【物件名】 {title}\n【価格】 {price} 万円\n【住所】 {address}"
    p_title.font.size = Pt(24)
    p_title.font.name = "游明朝"
    p_title.font.bold = True
    p_title.font.color.rgb = RGBColor(30, 45, 61)

    if main_image and main_image.filename:
        image_data = await main_image.read()
        img_stream = BytesIO(image_data)
        try:
            slide.shapes.add_picture(img_stream, Inches(0.5), Inches(2.5), width=Inches(5.0))
        except:
            pass

    pptx_io = BytesIO()
    prs.save(pptx_io)
    pptx_io.seek(0)

    return StreamingResponse(
        pptx_io,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f"attachment; filename=Zumen_{title}.pptx"}
    )
# --- ここから APB（パンフレット自動作成）用の裏方処理 ---
@app.post("/generate_apb")
async def generate_apb(
    zumen_file: UploadFile = File(None),
    madori_file: UploadFile = File(None),
    empty_file: UploadFile = File(None),
    map_file: UploadFile = File(None),
    orientation: str = Form("portrait")
):
    """
    とりあえず今回は「画面からちゃんとデータが届いたか」を確認するテスト用の処理です。
    次回、ここにGeminiとパワポ生成のコードを移植します。
    """
    zumen_name = zumen_file.filename if zumen_file else "なし"
    
    return {
        "status": "success", 
        "message": f"🎉 通信大成功！\n受け取った図面: {zumen_name}\nスライドの向き: {orientation}\n\nこの通信に乗せて、次回Geminiの処理を動かします！"
    }