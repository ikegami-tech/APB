import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

# 環境変数の読み込み
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ エラー: .envファイルにDATABASE_URLが設定されていません。")
    exit()

# データベースエンジンの作成
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# 🏢 店舗（branches）テーブルの設計図
class Branch(Base):
    __tablename__ = 'branches'
    id = Column(Integer, primary_key=True, autoincrement=True)
    branch_key = Column(String(50), unique=True, nullable=False) # "練馬"、"国分寺"などのキー
    full_name = Column(String(100), nullable=False)
    license = Column(String(100), nullable=False)
    address = Column(String(200), nullable=False)
    tel = Column(String(20), nullable=False)
    login_id = Column(String(50), nullable=False)
    password = Column(String(100), nullable=False)

# データベースに設計図通りにテーブルを作成！
Base.metadata.create_all(bind=engine)

# 初期データの流し込み処理
Session = sessionmaker(bind=engine)
session = Session()

# 移行する元データ
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

# データを1件ずつ確認しながら追加
for key, data in BRANCH_DATA.items():
    existing_branch = session.query(Branch).filter_by(branch_key=key).first()
    if not existing_branch:
        new_branch = Branch(
            branch_key=key,
            full_name=data["full_name"],
            license=data["license"],
            address=data["address"],
            tel=data["tel"],
            login_id=data["login_id"],
            password=data["password"]
        )
        session.add(new_branch)
        print(f"✅ {key}店のデータを追加しました！")
    else:
        print(f"⚠️ {key}店のデータは既に存在します。")

session.commit()
session.close()
print("🎉 データベースの初期セットアップとデータ移行が完了しました！")