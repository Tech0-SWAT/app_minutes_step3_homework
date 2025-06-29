# 📝 議事録アプリ

## 💡 概要
このアプリケーションは、効率的な講義理解を実現するためのWebアプリケーションです。講義動画をアップロードすると、文字起こし、要約、AIチャットボット機能を用いて講義内容を効率的に理解できます。

## デモ動画
https://github.com/user-attachments/assets/9e8fa3ce-3506-4bf0-a0ae-06df67fd6604

## 🚀 主な機能
- ユーザー認証
- 動画のアップロード
- 文字起こし機能
- 要約
- AIチャット機能（文字起こしデータを元にRAGを作成）

## 🏗️ 技術スタック

### バックエンド
- **フレームワーク**: FastAPI
- **データベース**: Supabase（PostgreSQL）
- **ストレージ**: Azure Blob Storage
- **AIモデル**: Azure AI Foundry 
- **ORM**: SQLAlchemy
- **認証**: JWT
- **その他**: Python 3.8+

### フロントエンド
- **フレームワーク**: Next.js
- **言語**: TypeScript
- **スタイリング**: Tailwind CSS
- **状態管理**: React Context
- **その他**: Node.js 18+

## 📁 プロジェクト構造
```
議事録アプリ/
├── backend/
│   ├── app.py             # FastAPIアプリケーションのメインファイル
│   ├── requirements.txt   # Python依存関係
│   ├── routers/           # APIルーター
│   │   ├── minutes.py     # 議事録関連のエンドポイント
│   │   ├── chat.py        # チャット関連のエンドポイント
│   │   └── summary.py     # 要約生成関連のエンドポイント
│   ├── db_control/        # データベース関連
│   └── utils/             # ユーティリティ関数
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.jsアプリケーション
│   │   ├── components/    # Reactコンポーネント
│   │   ├── contexts/      # Reactコンテキスト
│   │   ├── hooks/         # カスタムフック
│   │   └── lib/           # ユーティリティ関数
│   ├── public/
│   ├── package.json       # npm依存関係
│   └── next.config.mjs    # Next.js設定
├── README.md
└── .gitignore
```

## 🛠️ セットアップ手順

### 前提条件
- Python 3.8以上
- Node.js 18以上
- PostgreSQL

### 各種外部リソースのセットアップ
1. Supabaseでプロジェクト作成
    - 公式サイト
        - https://supabase.com/
    - 選定理由
        - 無料プランかつ、pgvector拡張ベクターデータが扱えて、Auth機能が簡単に実装できるから
    - 今回のER図
        - https://dbdiagram.io/d/app_minutes_step3_homework-6839a559bd74709cb74a4557
2. Azure Blob Storage内にvideoコンテナを作成
    - 公式サイト
        - https://azure.microsoft.com/ja-jp/products/storage/blobs
    - 選定利用
        Supabase Storageは無料プランでは1GBまでだが、Azure Blob Storageは無料枠で月あたり5GBまで使えるため
3. Azure AI Foundryにモデル構築
    - 汎用モデル、エンベディング用モデル、文字起こし用モデルの3つを立ち上げる

### 動画処理に用いるライブラリのインストール
所要時間：10分程度
ターミナルで実行
```bash
brew install ffmpeg
```

### バックエンドのセットアップ
1. バックエンドディレクトリに移動
```bash
cd backend
```

2. 仮想環境の作成と有効化
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 依存関係のインストール
```bash
pip install -r requirements.txt
```

4. 環境変数の設定
backendに`.env`ファイルを作成し、以下の変数を設定：
```
# SupabaseDB接続用
DATABASE_URL="your_supabase_connect_url"（ヘッダーの「Connect」をクリックしてURIをコピー）

# Supabase認証用
SUPABASE_URL="your_supabase_url"（「Project Settings」の「Data API」のProjectURLをコピー）
SUPABASE_API_KEY="your_supabase_key"（「Project Settings」の「API Keys」のanon public keyをコピー）

# ストレージ
AZURE_STORAGE_ACCOUNT_NAME="your_name"
AZURE_STORAGE_ACCOUNT_KEY="your_key"
AZURE_STORAGE_CONTAINER_VIDEO=video

# Azure OpenAI 各種モデル
# 共通
AZURE_OPENAI_API_KEY="your_key"
AZURE_OPENAI_BASE_URL="your_url"

# APIバージョン（用途ごとに）
AZURE_OPENAI_API_VERSION_CHAT="chat用AIのAPIバージョン名"
AZURE_OPENAI_API_VERSION_EMBED="embedding用AIのAPIバージョン名"
AZURE_OPENAI_API_VERSION_WHISPER="文字起こし用AIのAPIバージョン名"

# デプロイ名（modelの区別）
AZURE_OPENAI_DEPLOYMENT_CHAT="chat用AIモデルのデプロイ名"
AZURE_OPENAI_DEPLOYMENT_EMBED="embedding用AIモデルのデプロイ名"
AZURE_OPENAI_DEPLOYMENT_WHISPER="文字起こし用AIモデルのデプロイ名"
```

5. サーバーの起動
```bash
uvicorn app:app --reload
```

6. 接続先のDBにテーブル作成
```bash
python db_control/init_db.py
```

### フロントエンドのセットアップ
1. フロントエンドディレクトリに移動
```bash
cd frontend
```

2. 依存関係のインストール
```bash
npm install
```
3. 環境変数の設定
frontendに`.env`ファイルを作成し、以下の変数を設定：
```
NEXT_PUBLIC_SUPABASE_URL="your_supabase_url"
NEXT_PUBLIC_SUPABASE_ANON_KEY=”your_supabase_key”
FASTAPI_URL=http://127.0.0.1:8000
```

4. 開発サーバーの起動
```bash
npm run dev
```

## 🔍 APIエンドポイント

### 動画アップロード・管理
- `POST /api/upload_video` - 講義動画のアップロード（mp4, mov形式）
- `GET /api/upload_status` - 動画のアップロードと処理状況の取得
- `GET /api/upload_result` - 動画の処理結果（文字起こし、埋め込み状態など）の取得
- `GET /api/get_all_minutes` - ユーザーの全議事録一覧の取得
- `GET /api/get_minutes_list` - 特定の議事録の詳細情報の取得

### 要約機能
- `POST /api/generate_summary` - 文字起こし文章からの要約生成

### チャット機能
- `POST /api/start_chat` - チャットセッションの開始
- `POST /api/send_chat` - チャットメッセージの送信
- `GET /api/reference` - チャットメッセージに関連する参照情報の取得

## 文字起こし（SST）モデル比較
- https://artificialanalysis.ai/speech-to-text
- <img width="1310" alt="スクリーンショット 2025-06-22 12 25 23" src="https://github.com/user-attachments/assets/c3458d51-a5a9-40c8-8a8d-0f676b6fb015" />
