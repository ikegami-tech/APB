import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# 🎨 テーマ（themes）テーブルの設計図
class Theme(Base):
    __tablename__ = 'themes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    theme_key = Column(String(50), unique=True, nullable=False) # "luxury", "family" など
    name = Column(String(100), nullable=False)
    bg_color = Column(String(50), nullable=False)       # RGBをカンマ区切りの文字列で保存 (例: "40,40,45")
    text_color = Column(String(50), nullable=False)     # "white" または "black"
    accent_color = Column(String(50), nullable=False)   # (例: "180,150,80")

Base.metadata.create_all(bind=engine)

Session = sessionmaker(bind=engine)
session = Session()

# 移行する元データ（RGBのタプルはカンマ区切りの文字列に変換して保存します）
THEMES_DATA = {
    "luxury":       {"name": "1 高級・ラグジュアリー", "bg_color": "40,40,45", "text_color": "white", "accent_color": "180,150,80"},
    "family":       {"name": "2 ファミリー・温もり", "bg_color": "255,245,235", "text_color": "black", "accent_color": "240,130,50"},
    "modern":       {"name": "3 スタイリッシュ・モダン", "bg_color": "240,245,255", "text_color": "black", "accent_color": "50,100,180"},
    "wa_modern":    {"name": "4 和モダン・伝統美", "bg_color": "230,225,215", "text_color": "black", "accent_color": "100,120,80"},
    "casual":       {"name": "5 カジュアル・ポップ", "bg_color": "255,250,220", "text_color": "black", "accent_color": "250,100,130"},
    "other":        {"name": "6 その他（自由入力スタイル）", "bg_color": "240,240,240", "text_color": "black", "accent_color": "100,100,100"}
}

# データを流し込む
for key, data in THEMES_DATA.items():
    existing_theme = session.query(Theme).filter_by(theme_key=key).first()
    if not existing_theme:
        new_theme = Theme(
            theme_key=key,
            name=data["name"],
            bg_color=data["bg_color"],
            text_color=data["text_color"],
            accent_color=data["accent_color"]
        )
        session.add(new_theme)
        print(f"✅ テーマ '{key}' をDBに追加しました！")
    else:
        print(f"⚠️ テーマ '{key}' は既に存在します。")

session.commit()
session.close()
print("🎉 テーマデータのDB移行が完了しました！")