import streamlit as st
import os
from pypdf import PdfReader
from google import genai
from dotenv import load_dotenv

# 金庫（.env）から鍵を取り出す
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# アプリのタイトルと説明
st.title("🏡 AI Pamphlet Builder (APB)")
st.write("販売図面（PDF）をアップロードするだけで、AIが物件の魅力を自動解析します！")

# ファイルのアップロード画面を作る
uploaded_file = st.file_uploader("販売図面のPDFをここにドラッグ＆ドロップしてください", type="pdf")

# もしファイルがアップロードされたら、以下の処理を実行する
if uploaded_file is not None:
    st.info("PDFを読み込んでいます...")
    
    try:
        # PDFから文字を抽出する
        reader = PdfReader(uploaded_file)
        text = ""
        # 全てのページから文字を抜き出す
        for page in reader.pages:
            text += page.extract_text()
        
        # 抽出した文字を少しだけ画面に見せる（確認用）
        with st.expander("読み取った生データ（クリックで展開）"):
            st.write(text)
            
        st.success("PDFの読み込みが完了しました！AIに解析を依頼します...")
        
        # AIの準備
        client = genai.Client(api_key=api_key)
        
        # AIへのお願い事（プロンプト）
        prompt = f"""
        以下のテキストは、不動産の販売図面から読み取ったデータです。
        この中から、「物件名」「住所」「価格」「アピールポイント（キャッチコピーの種になりそうなもの）」を抜き出して、分かりやすく箇条書きで整理してください。

        【読み取ったデータ】
        {text}
        """
        
        # ぐるぐる回るマークを出して待つ
        with st.spinner('AIが物件の魅力を引き出しています...'):
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            
        # AIの結果を画面にドーンと表示！
        st.subheader("✨ AIの解析結果")
        st.write(response.text)
        
        st.balloons() # 成功したら風船を飛ばす！

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")