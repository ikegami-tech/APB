import os
import fitz  # PyMuPDF
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from openai import OpenAI
from dotenv import load_dotenv

# 設定の読み込み
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_pdf_text(pdf_path):
    """PDFからテキストを抽出する"""
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

def get_ai_marketing_copy(property_info):
    """AIに雑誌風のコピーを作らせる"""
    # 実際はここにGPT-4oへのプロンプトを書きます
    # 「みほんPDF」のような情報を元に「THE HERITAGE」風のコピーを生成
    # 例: 府中市美好町  -> 「緑の街・府中で暮らす」
    prompt = f"以下の物件情報から、高級雑誌の表紙のようなキャッチコピーを3つ作成して。\n{property_info}"
    
    # 簡易的なダミー返却（本来はclient.chat.completions.createを使用）
    return {
        "title": "THE HERITAGE",
        "sub_title": "THE FUCHU COLLECTIVE",
        "main_copy": "「府中」で、理想の暮らしをデザインする。",
        "desc_copy": "30代夫婦が選ぶ、洗練された週末の風景。"
    }

def create_ppt_cover(copy_data, output_path):
    """パワポの表紙スライドを作成する"""
    prs = Presentation()
    # A4サイズ（スライドサイズを設定）
    prs.slide_width = Inches(8.27)
    prs.slide_height = Inches(11.69)
    
    slide_layout = prs.slide_layouts[6]  # 空白レイアウト
    slide = prs.slides.add_slide(slide_layout)

    # 1. メインタイトル (THE HERITAGE風)
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(7.27), Inches(1))
    tf = title_box.text_frame
    p = tf.paragraphs[0]
    p.text = copy_data["title"]
    p.font.size = Pt(60)
    p.font.bold = True
    p.alignment = PP_ALIGN.CENTER

    # 2. メインコピーの挿入
    copy_box = slide.shapes.add_textbox(Inches(0.5), Inches(4), Inches(7.27), Inches(2))
    tf = copy_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = copy_data["main_copy"]
    p.font.size = Pt(36)
    p.font.color.rgb = RGBColor(0, 0, 0)
    p.alignment = PP_ALIGN.CENTER

    prs.save(output_path)
    print(f"Saved: {output_path}")

# 実行テスト
if __name__ == "__main__":
    # PDFパスは実際の「みほんPDF」を指定してください
    pdf_text = "所在地:府中市美好町 4380万円" 
    copy = get_ai_marketing_copy(pdf_text)
    create_ppt_cover(copy, "test_output.pptx")
