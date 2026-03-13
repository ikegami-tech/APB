import os
from pypdf import PdfReader
# ↓ 新しいAIの道具を読み込みます
from google import genai
from dotenv import load_dotenv

# ① 金庫（.envファイル）からAPIキーをこっそり取り出す
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# ② AIの準備（新しい書き方）
client = genai.Client(api_key=api_key)

file_path = "sample.pdf"
print(f"【{file_path}】の読み込みを開始します...\n")

try:
    # ③ PDFから文字を抽出する
    reader = PdfReader(file_path)
    page = reader.pages[0]
    text = page.extract_text()
    
    print("----- PDFから抽出した文字 -----")
    print(text)
    print("-------------------------------\n")
    
    # ④ 抽出した文字をAIに渡して、お願い事（プロンプト）をする！
    print("AIが情報を整理しています。数秒お待ちください...\n")
    prompt = f"""
    以下のテキストは、不動産の資料から読み取ったデータです。
    この中から、「物件名」「住所」「価格」「アピールポイント（キャッチコピーの種になりそうなもの）」を抜き出して、分かりやすく箇条書きで整理してください。

    【読み取ったデータ】
    {text}
    """
    
    # AIに答えを考えてもらう（最新の2.5モデルを指定）
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    
    print("✨----- AIの解析結果 -----✨")
    print(response.text)
    print("✨------------------------✨")

except Exception as e:
    print(f"エラーが発生しました: {e}")