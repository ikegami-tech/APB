from pypdf import PdfReader

# 用意したPDFファイルの名前
file_path = "sample.pdf"

print(f"【{file_path}】の読み込みを開始します...\n")

try:
    # PDFを読み込む
    reader = PdfReader(file_path)
    
    # 最初のページ（0ページ目）を取得
    page = reader.pages[0]
    
    # テキストを抽出
    text = page.extract_text()
    
    print("----- 抽出結果 -----")
    print(text)
    print("--------------------")

except Exception as e:
    print(f"エラーが発生しました: {e}")