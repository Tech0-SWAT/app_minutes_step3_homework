from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db_control import schemas
from db_control.connect import get_db
from utils.auth import get_current_user_id
from utils.summarize import process_summary_generation
import logging

router = APIRouter(tags=["summary"])
logger = logging.getLogger(__name__)

@router.post("/api/generate_summary", response_model=schemas.SummaryResponse)
async def generate_summary_endpoint(
    request: schemas.SummaryRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    文字起こし文章から要約を生成する
    
    Args:
        request (SummaryRequest): 文字起こしIDを含むリクエスト
        user_id (str): 認証されたユーザーID
        db (Session): データベースセッション
        
    Returns:
        SummaryResponse: 生成された要約
    """
    try:
        summary_content = process_summary_generation(db, request.transcript_id, user_id)
        return {"summary": summary_content}
    except HTTPException:
        raise
    except Exception as e:
        error_message = f"要約の生成中にエラーが発生しました: {str(e)}"
        logger.error(error_message)
        raise HTTPException(
            status_code=500,
            detail=error_message
        )
