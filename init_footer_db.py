import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# 🖼️ 帯（フッター）履歴テーブルの設計図
class FooterHistory(Base):
    __tablename__ = 'footer_history'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String(100), nullable=False)     # 誰がアップロードしたか
    image_filename = Column(String(200), nullable=False) # サーバー上のファイル名
    created_at = Column(DateTime, default=datetime.now)  # アップロードした日時

Base.metadata.create_all(bind=engine)
print("🎉 フッター履歴（footer_history）テーブルの作成が完了しました！")