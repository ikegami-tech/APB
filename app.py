import streamlit as st
import os
import json
from pypdf import PdfReader
from google import genai
from dotenv import load_dotenv
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# 金庫から鍵を取り出す
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

st.title("🏡 AI Pamphlet Builder (APB)")
st.write("販売図面から、AIが背景画像とキャッチコピーを考えて、プロ仕様の雑誌風パンフレット（画像）を自動生成します！")

# 準備：フォントと画像のパス（プロジェクトフォルダに置いてください）
FONT_PATH = './NotoSansCJKjp-Bold.ttf' # 日本語フォント
LOGO_PATH = './logo.png'             # ロゴ画像
BARCODE_PATH = './barcode.png'       # バーコード画像

uploaded_file = st.file_uploader("販売図面のPDFをドラッグ＆ドロップ", type="pdf")

if uploaded_file is not None:
    st.info("① AIが物件の魅力とキャッチコピー、そして背景画像のプロンプトを考えています...")
    
    try:
        reader = PdfReader(uploaded_file)
        text = "".join([page.extract_text() for page in reader.pages])
        
        # クライアントの初期化（Gemini）
        client = genai.Client(api_key=gemini_api_key)
        
        # 1. テキストと画像生成用プロンプトの作成
        prompt = f"""
        以下の不動産データから、雑誌風パンフレットの表紙を作成するためのコンテンツを考えてください。
        1. ターゲット層（30代夫婦）に響く、雑誌風のコピー3種類。
        2. 画像生成AI向けの、ターゲット層が入ったスタイリッシュなLDKの英語プロンプト。

        出力はMarkdownのブロック等を含めず、以下の純粋なJSON形式のみにしてください。
        {{
          "main_copy": "（15文字以内。中央の大きなコピー）",
          "side_copy_1": "（20文字以内。左下の小さなコピー1）",
          "side_copy_2": "（20文字以内。左下の小さなコピー2）",
          "image_prompt": "（ターゲット層、雰囲気、LDKの内装を英語で詳細に記述。テキストやロゴは絶対に含めないこと。人物入りのモダンなLDK）"
        }}
        【データ】{text}
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        # JSONを安全に読み込むための処理（```json などの余分な文字を消す）
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:-3]
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:-3]
            
        ai_data = json.loads(raw_text.strip())
        
        st.subheader("✨ AIが考えた表紙コピー")
        st.write(f"**メイン**: {ai_data['main_copy']}")
        st.write(f"**サブ1**: {ai_data['side_copy_1']}")
        st.write(f"**サブ2**: {ai_data['side_copy_2']}")
        
        # --- 段階1：画像生成（Gemini Imagen 3を使用） ---
        st.info("② Geminiが背景画像を生成しています（少し時間がかかります）...")
        
        image_result = client.models.generate_images(
            model='imagen-3.0-generate-001',
            prompt=ai_data['image_prompt'],
            config=dict(
                number_of_images=1,
                aspect_ratio="9:16", # 雑誌風の縦長サイズ
                output_mime_type="image/jpeg"
            )
        )
        
        # 生成された画像データをPillowで読み込む
        generated_image_bytes = image_result.generated_images[0].image.image_bytes
        bg_image = Image.open(BytesIO(generated_image_bytes))
        
        st.subheader("🖼️ 生成された背景画像")
        st.image(bg_image, caption="Gemini (Imagen 3) が生成した背景画像")
        
        # --- 段階2：テキスト・ロゴの合成 ---
        st.info("③ 生成された画像に、テキスト、ロゴ、バーコードを合成しています...")
        
        width, height = bg_image.size
        draw = ImageDraw.Draw(bg_image)
        
        # フォントの読み込み（エラーハンドリング付き）
        try:
            # 画像の解像度（Imagen 3は少し小さめ）に合わせてフォントサイズを調整
            font_title = ImageFont.truetype(FONT_PATH, int(width * 0.12))
            font_subtitle = ImageFont.truetype(FONT_PATH, int(width * 0.04))
            font_main = ImageFont.truetype(FONT_PATH, int(width * 0.06))
            font_side = ImageFont.truetype(FONT_PATH, int(width * 0.04))
            font_bottom = ImageFont.truetype(FONT_PATH, int(width * 0.03))
        except Exception as e:
            st.warning("⚠️ フォントファイルが見つかりません。デフォルトフォントを使用します（日本語が文字化けする可能性があります）。")
            font_title = font_subtitle = font_main = font_side = font_bottom = ImageFont.load_default()

        # 固定テキストの描画
        draw.text((width/2, height * 0.05), "THE HERITAGE", font=font_title, fill="white", anchor="ms")
        draw.text((width/2, height * 0.15), "THE NERIMA COLLECTIVE", font=font_subtitle, fill="white", anchor="ms")
        draw.text((width * 0.95, height * 0.95), "特別号 | VOL. 01 | ¥1,000", font=font_bottom, fill="white", anchor="re")

        # AIが考えたコピーの描画（影付きで見やすく）
        main_x, main_y = width * 0.1, height * 0.4
        draw.text((main_x + 2, main_y + 2), ai_data['main_copy'], font=font_main, fill="black") # 影
        draw.text((main_x, main_y), ai_data['main_copy'], font=font_main, fill="white")

        side_x, side_y1, side_y2 = width * 0.1, height * 0.75, height * 0.82
        draw.text((side_x + 2, side_y1 + 2), ai_data['side_copy_1'], font=font_side, fill="black")
        draw.text((side_x, side_y1), ai_data['side_copy_1'], font=font_side, fill="white")
        
        draw.text((side_x + 2, side_y2 + 2), ai_data['side_copy_2'], font=font_side, fill="black")
        draw.text((side_x, side_y2), ai_data['side_copy_2'], font=font_side, fill="white")

        # ロゴ、バーコード画像の合成
        try:
            logo_img = Image.open(LOGO_PATH)
            logo_img = logo_img.resize((int(width * 0.3), int((width * 0.3) * logo_img.height / logo_img.width)))
            bg_image.paste(logo_img, (int(width * 0.05), int(height * 0.9)), logo_img if logo_img.mode == 'RGBA' else None)
        except:
            pass # ロゴがなければスキップ

        try:
            barcode_img = Image.open(BARCODE_PATH)
            barcode_img = barcode_img.resize((int(width * 0.2), int((width * 0.2) * barcode_img.height / barcode_img.width)))
            bg_image.paste(barcode_img, (int(width * 0.75), int(height * 0.85)), barcode_img if barcode_img.mode == 'RGBA' else None)
        except:
            pass # バーコードがなければスキップ

        st.subheader("🎉 完成したパンフレット")
        st.image(bg_image, caption="AIが作成したオリジナル表紙")
        
        # ダウンロード用のデータ化
        output_stream = BytesIO()
        bg_image.save(output_stream, format='JPEG', quality=95)
        output_stream.seek(0)
        
        st.success("処理がすべて完了しました！")
        st.download_button(
            label="📥 完成した画像（JPEG）をダウンロード",
            data=output_stream,
            file_name="AI_Pamphlet_Cover.jpg",
            mime="image/jpeg"
        )
        st.balloons()

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")