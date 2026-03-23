import streamlit as st
import os
import json
import urllib.parse
import fitz  # PyMuPDF
from google import genai
from dotenv import load_dotenv
from io import BytesIO
import requests
from PIL import Image, ImageDraw, ImageFont
from google.genai import types

# --- 1. 環境設定 ---
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

st.set_page_config(page_title="AI Pamphlet Builder", layout="centered")
st.title("🏡 AI Pamphlet Builder (APB)")
st.write("最新の Gemini 3 Flash が、図面を読み取ってプロ仕様のパンフレットを自動生成します。")

# フォントとロゴのパス
FONT_PATH = './NotoSansCJKjp-Bold.ttf' 
LOGO_PATH = './logo.png' 

# --- 2. メモリ（セッション状態）の初期化 ---
if "finished_image" not in st.session_state:
    st.session_state.finished_image = None
if "ai_data" not in st.session_state:
    st.session_state.ai_data = None
if "current_file" not in st.session_state:
    st.session_state.current_file = None

# --- 3. ファイルアップロード ---
uploaded_file = st.file_uploader("販売図面のPDFをドラッグ＆ドロップ", type="pdf")

# 新しいファイルがアップロードされたらメモリをリセット
if uploaded_file is not None and uploaded_file.name != st.session_state.current_file:
    st.session_state.finished_image = None
    st.session_state.ai_data = None
    st.session_state.current_file = uploaded_file.name

# --- 4. メイン処理（メモリに完成品がない場合だけ実行） ---
if uploaded_file is not None:
    
    if st.session_state.finished_image is None:
        with st.status("🎨 パンフレットを作成中...（約30秒）", expanded=True) as status:
            try:
                # 4-1. PDFを画像に変換
                st.write("PDF図面を解析中...")
                pdf_bytes = uploaded_file.read()
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                page = doc.load_page(0)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                pdf_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                pdf_text = page.get_text()
                
                # 4-2. Gemini 3 でコピー生成
                st.write("AIがキャッチコピーを考案中...")
                gemini_client = genai.Client(api_key=gemini_api_key)
                prompt = f"""
                不動産図面を解析して、雑誌風パンフレットのコピーを作成してください。
                出力は以下のJSON形式のみにしてください。
                {{
                  "main_copy": "（15文字以内）",
                  "side_copy_1": "（20文字以内）",
                  "side_copy_2": "（20文字以内）",
                  "image_prompt": "（高級なLDKの英語プロンプト。人物入り）"
                }}
                【補助データ】: {pdf_text}
                """
                response = gemini_client.models.generate_content(
                    model='gemini-3-flash-preview', 
                    contents=[prompt, pdf_image], 
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                st.session_state.ai_data = json.loads(response.text)
                
                # 4-3. 背景画像の生成 (Imagen 3優先)
                st.write("背景画像を生成中...")
                bg_image = None
                try:
                    image_response = gemini_client.models.generate_image(
                        model='imagen-3.0-generate-001', 
                        prompt=st.session_state.ai_data['image_prompt'][:200],
                        config=types.GenerateImageConfig(number_of_images=1, aspect_ratio="9:16", add_watermark=False)
                    )
                    bg_image = image_response.generated_images[0].image
                except:
                    # 失敗時は予備のストックフォトを使用
                    fallback_url = "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?q=80&w=1024&h=1792&auto=format&fit=crop"
                    bg_image = Image.open(BytesIO(requests.get(fallback_url).content))

                # 4-4. デザイン合成
                st.write("デザインを仕上げ中...")
                width, height = bg_image.size
                draw = ImageDraw.Draw(bg_image)
                
                try:
                    font_title = ImageFont.truetype(FONT_PATH, int(width * 0.12))
                    font_main = ImageFont.truetype(FONT_PATH, int(width * 0.065))
                    font_side = ImageFont.truetype(FONT_PATH, int(width * 0.045))
                except:
                    font_title = font_main = font_side = ImageFont.load_default()

                # 文字描画（影付き）
                m_x, m_y = width * 0.1, height * 0.45
                draw.text((width/2, height * 0.1), "THE RESIDENCE", font=font_title, fill="white", anchor="ms")
                
                # メイン
                draw.text((m_x+3, m_y+3), st.session_state.ai_data['main_copy'], font=font_main, fill="black")
                draw.text((m_x, m_y), st.session_state.ai_data['main_copy'], font=font_main, fill="white")
                
                # サブ
                s_y1, s_y2 = height * 0.78, height * 0.84
                draw.text((m_x+2, s_y1+2), st.session_state.ai_data['side_copy_1'], font=font_side, fill="black")
                draw.text((m_x, s_y1), st.session_state.ai_data['side_copy_1'], font=font_side, fill="white")
                draw.text((m_x+2, s_y2+2), st.session_state.ai_data['side_copy_2'], font=font_side, fill="black")
                draw.text((m_x, s_y2), st.session_state.ai_data['side_copy_2'], font=font_side, fill="white")

                # ロゴ合成（RGBA対策）
                try:
                    logo_img = Image.open(LOGO_PATH).convert("RGBA")
                    logo_w = int(width * 0.3)
                    logo_h = int(logo_w * logo_img.height / logo_img.width)
                    logo_img = logo_img.resize((logo_w, logo_h))
                    bg_image.paste(logo_img, (int(width * 0.05), int(height * 0.88)), logo_img)
                except:
                    pass

                # メモリに保存！
                st.session_state.finished_image = bg_image
                status.update(label="✅ パンフレットが完成しました！", state="complete", expanded=False)

            except Exception as e:
                st.error(f"作成中にエラーが発生しました: {e}")
                st.stop()

    # --- 5. 画面表示（メモリから読み出すので暗転しない！） ---
    if st.session_state.finished_image:
        st.subheader("✨ AIが考えた表紙コピー")
        st.write(f"**メイン**: {st.session_state.ai_data['main_copy']}")
        
        st.subheader("🎉 完成したパンフレット")
        st.image(st.session_state.finished_image, use_container_width=True)
        
        # JPEG保存（RGBAをRGBに変換して暗転を完全に防止）
        out = BytesIO()
        final_rgb = st.session_state.finished_image.convert("RGB")
        final_rgb.save(out, format='JPEG', quality=95)
        
        st.download_button(
            label="📥 完成画像をダウンロードする",
            data=out.getvalue(),
            file_name=f"APB_{st.session_state.current_file}.jpg",
            mime="image/jpeg"
        )
        
        if st.button("🔄 最初からやり直す"):
            st.session_state.finished_image = None
            st.rerun()