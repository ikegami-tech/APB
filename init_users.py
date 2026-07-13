import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# 👤 ユーザー（社員）テーブルの設計図
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(100), unique=True, nullable=False) # ログインID（メールアドレス）
    name = Column(String(50), nullable=False)                # 氏名
    password = Column(String(100), nullable=False)           # パスワード
    branch_key = Column(String(50), nullable=False)          # 所属店舗（"練馬"など）
    # 🌟 ここがポイント！ユーザーが最後に選んだフッターデザインを記憶するカラム
    footer_design_num = Column(String(10), default="1")      

Base.metadata.create_all(bind=engine)

Session = sessionmaker(bind=engine)
session = Session()

# 画像から読み取った練馬店の皆様のデータ
# （パスワードはすべて「th-nerima」、所属は「練馬」で統一します）
USER_DATA = [
    {"email": "17uketsuke@toho-nerima.co.jp", "name": "柳楽 彩乃"},
    {"email": "iwasaki@toho-nerima.co.jp", "name": "岩崎 亮"},
    {"email": "kozawa@toho-nerima.co.jp", "name": "小澤 聖輝"},
    {"email": "yonezawa@toho-nerima.co.jp", "name": "米澤 璃子"},
    {"email": "nakazato@toho-nerima.co.jp", "name": "中里 光貴"},
    {"email": "akutsu@toho-nerima.co.jp", "name": "阿久津 美菜"},
    {"email": "kato@toho-nerima.co.jp", "name": "加藤 敦士"},
    {"email": "kuroda@toho-nerima.co.jp", "name": "黒田 聡"},
    {"email": "furukawa@toho-nerima.co.jp", "name": "古川 雷太"},
    {"email": "y.kawasaki@toho-nerima.co.jp", "name": "川崎 祐稀"},
    {"email": "asano@toho-nerima.co.jp", "name": "浅野 勝一"},
    {"email": "komata@toho-nerima.co.jp", "name": "駒田 優人"},
    {"email": "s.hiyoriyama@toho-nerima.co.jp", "name": "日和山 翔"},
    {"email": "yamada@toho-nerima.co.jp", "name": "山田 哲也"},
    {"email": "itai@toho-nerima.co.jp", "name": "板井 悠里奈"},
    {"email": "nakao@toho-nerima.co.jp", "name": "中尾 智美"},
    {"email": "machida@toho-nerima.co.jp", "name": "町田 俊太"},
    {"email": "nagata@toho-nerima.co.jp", "name": "永田 涼"},
    {"email": "horikiri@toho-nerima.co.jp", "name": "堀切 葵"},
    {"email": "kawano@toho-nerima.co.jp", "name": "河野 拓也"},
    {"email": "yoshitome@toho-nerima.co.jp", "name": "吉留 将"},
    {"email": "masui@toho-nerima.co.jp", "name": "増井 翔大"},
    {"email": "sato@toho-nerima.co.jp", "name": "佐藤 聡俊"},
    {"email": "sengoku@toho-nerima.co.jp", "name": "千石 栄次"},
    {"email": "kurosawa@toho-nerima.co.jp", "name": "黒澤 亮太朗"},
    {"email": "kawagoe@toho-nerima.co.jp", "name": "川越 尚輝"},
    {"email": "takahashi@toho-nerima.co.jp", "name": "高橋 虎太"},
    {"email": "aiyoshi@toho-nerima.co.jp", "name": "相吉 雄太"},
    {"email": "hasemi@toho-nerima.co.jp", "name": "長谷見 有紀"},
    {"email": "onuma@toho-nerima.co.jp", "name": "小沼 雅嗣"},
    {"email": "ishikawa@toho-nerima.co.jp", "name": "石川 巧"},
    {"email": "sakuda@toho-nerima.co.jp", "name": "佐久田 真稔"},
    {"email": "ito@toho-nerima.co.jp", "name": "伊藤 温規"},
    {"email": "nishiyama@toho-nerima.co.jp", "name": "西山 正志"},
    {"email": "sinozaki@toho-nerima.co.jp", "name": "篠崎 玲治"}
]

# データをDBに流し込む
for data in USER_DATA:
    existing_user = session.query(User).filter_by(email=data["email"]).first()
    if not existing_user:
        new_user = User(
            email=data["email"],
            name=data["name"],
            password="th-nerima",      # パスワードは統一
            branch_key="練馬",         # 所属店舗を紐づけ
            footer_design_num="1"      # デフォルトのデザイン番号
        )
        session.add(new_user)
        print(f"✅ {data['name']} さんのアカウントを作成しました！")
    else:
        print(f"⚠️ {data['name']} さんのアカウントは既に存在します。")

session.commit()
session.close()
print("🎉 ユーザーデータのDB移行が完了しました！")