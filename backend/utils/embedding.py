from openai import AzureOpenAI
import os
from dotenv import load_dotenv
import json
import httpx

load_dotenv(override=True)
http_client = httpx.Client(timeout=60.0)

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION_EMBED"),
    azure_endpoint=os.getenv("AZURE_OPENAI_BASE_URL"),
    http_client=http_client
)

async def generate_embedding(text: str) -> str:
    """
    Azure OpenAIのtext-embedding-ada-002モデルを使用してテキストをベクトル化する
    
    Args:
        text (str): ベクトル化するテキスト
        
    Returns:
        str: ベクトルデータ（JSON文字列）
    """
    try:
        # テキストをベクトル化
        response = client.embeddings.create(
            input=text,
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_EMBED")
        )
        
        # ベクトルデータをJSON文字列に変換
        embedding_vector = response.data[0].embedding
        return json.dumps(embedding_vector)
        
    except Exception as e:
        raise Exception(f"ベクトル化処理中にエラーが発生しました: {str(e)}")
