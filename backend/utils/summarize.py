from fastapi import HTTPException
from sqlalchemy.orm import Session
from db_control import crud
from openai import AzureOpenAI
import os
import logging

logger = logging.getLogger(__name__)

# Azure OpenAIの設定
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION_CHAT", "2025-01-01-preview"),
    azure_endpoint=os.getenv("AZURE_OPENAI_BASE_URL")
)

def validate_access_permissions(db: Session, transcript_id: int, user_id: str) -> None:
    """
    文字起こしへのアクセス権限を検証する
    
    Args:
        db (Session): データベースセッション
        transcript_id (int): 文字起こしID
        user_id (str): ユーザーID
        
    Raises:
        HTTPException: アクセス権限がない場合
    """
    transcript = crud.get_transcript_by_id(db, transcript_id)
    if not transcript:
        logger.error(f"文字起こしデータが見つかりません: transcript_id={transcript_id}")
        raise HTTPException(
            status_code=404,
            detail="指定された文字起こしIDのデータが見つかりません"
        )
    
    # 動画を取得
    video = crud.get_video_by_id(db, transcript.video_id)
    if not video:
        raise HTTPException(
            status_code=404,
            detail="動画が見つかりません"
        )
    
    # 議事録を取得
    minutes = crud.get_minutes(db, video.minutes_id)
    if not minutes:
        logger.error(f"議事録データが見つかりません: minutes_id={video.minutes_id}")
        raise HTTPException(
            status_code=404,
            detail="議事録データが見つかりません"
        )
    
    if str(minutes.user_id) != str(user_id):
        logger.error(f"アクセス権限がありません: minutes_user_id={minutes.user_id}, request_user_id={user_id}")
        raise HTTPException(
            status_code=403,
            detail="この議事録へのアクセス権限がありません"
        )

def generate_summary_content(transcript_content: str) -> str:
    """
    Azure OpenAIを使用して要約を生成する
    
    Args:
        transcript_content (str): 文字起こしの内容
        
    Returns:
        str: 生成された要約
        
    Raises:
        HTTPException: 要約生成中にエラーが発生した場合
    """
    try:
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_CHAT", "gpt-4.1"),
            messages=[
                {"role": "system", "content": "あなたは会議の議事録を要約する専門家です。与えられた文字起こし文章を、重要なポイントを漏らさず、簡潔にマークダウン記法で要約してください。見出しには`### を使ってください。それ以上の大きな見出し # や ## は使わないでください。"},
                {"role": "user", "content": f"以下の会議の文字起こしを要約してください：\n\n{transcript_content}"}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        error_message = f"要約の生成中にエラーが発生しました: {str(e)}"
        logger.error(error_message)
        raise HTTPException(
            status_code=500,
            detail=error_message
        )

def process_summary_generation(db: Session, transcript_id: str, user_id: str) -> str:
    """
    要約生成の一連の処理を実行する
    
    Args:
        db (Session): データベースセッション
        transcript_id (str): 文字起こしID
        user_id (str): ユーザーID
        
    Returns:
        str: 生成された要約の内容
        
    Raises:
        HTTPException: 処理中にエラーが発生した場合
    """
    try:
        logger.info(f"要約生成リクエスト: transcript_id={transcript_id}, user_id={user_id}")
        
        # アクセス権限の検証
        validate_access_permissions(db, transcript_id, user_id)
        
        # 文字起こしデータを取得
        transcript = crud.get_transcript_by_id(db, transcript_id)
        transcript_content = transcript.content if hasattr(transcript, 'content') else transcript.text
        
        # 要約を生成
        summary_content = generate_summary_content(transcript_content)
        logger.info("要約の生成が完了しました")
        
        # 要約を保存
        summary = crud.create_summary(db, transcript_id, summary_content)
        logger.info(f"サマリーを作成/更新しました: summary_id={summary.id}")
        
        return summary.content
        
    except HTTPException:
        raise
    except Exception as e:
        error_message = f"要約の生成中にエラーが発生しました: {str(e)}"
        logger.error(error_message)
        raise HTTPException(
            status_code=500,
            detail=error_message
        ) 