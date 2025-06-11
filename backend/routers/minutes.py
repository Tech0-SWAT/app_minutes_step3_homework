from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from typing import List
import asyncio
from db_control import crud, schemas
from utils.auth import get_current_user_id
from utils import transcription, storage, chunk, embedding
from sqlalchemy.orm import Session
from db_control.connect import get_db, SessionLocal
import tempfile
import os
from datetime import datetime
import uuid
import logging
from pydantic import BaseModel

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Minutes"])

ALLOWED_EXTENSIONS = {'mp4', 'mov'}

def validate_video_file(file: UploadFile) -> bool:
    return file.filename.split('.')[-1].lower() in ALLOWED_EXTENSIONS

@router.post("/api/upload_video", response_model=schemas.VideoUploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    # ファイル形式のバリデーション
    if not validate_video_file(file):
        raise HTTPException(
            status_code=400,
            detail="無効なファイル形式です。mp4またはmov形式のファイルをアップロードしてください。"
        )
    
    try:
        # minutes_idの生成とDBへの保存（ファイル名を渡す）
        minutes_id = await crud.create_minutes(db, user_id=user_id, filename=file.filename)
        
        # 動画データをDBに保存（status: queued）
        video_id = await crud.create_video(db, minutes_id, None)
        
        # 一時ファイルに保存
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1])
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
        
        # バックグラウンドタスクとして処理を開始
        background_tasks.add_task(process_video, temp_file.name, minutes_id, db)
        
        return schemas.VideoUploadResponse(
            minutes_id=minutes_id,
            status="queued"
        )
        
    except Exception as e:
        # エラー発生時の処理
        error_message = f"動画のアップロード中にエラーが発生しました: {str(e)}"
        logger.error(error_message)  # ログ出力
        raise HTTPException(
            status_code=500,
            detail=error_message
        )

async def process_video(file_path: str, minutes_id: int, db: Session):
    """
    動画の処理を行う関数
    """
    try:
        # 処理開始を通知
        await crud.update_video_status(db, minutes_id, "processing")
        await crud.update_video_progress(db, minutes_id, 0)
        
        # 1. 動画をAzure Blob Storageにアップロード
        with open(file_path, 'rb') as f:
            video_url = await storage.upload_video(f, minutes_id)
        if not video_url:
            raise Exception("動画のアップロードに失敗しました")
        
        # 2. 動画データのURLを更新
        video = crud.get_video(db, minutes_id)
        if not video:
            raise Exception("動画データが見つかりません")
        video.video_url = video_url
        db.commit()
        
        # 動画保存完了（30%）
        await crud.update_video_progress(db, minutes_id, 30)
        
        # 3. 文字起こしの実行
        transcript_content = await transcription.transcribe_video(video_url)
        if not transcript_content:
            raise Exception("文字起こしに失敗しました")
        
        # 文字起こし完了（60%）
        await crud.update_video_progress(db, minutes_id, 60)
        
        # 4. 文字起こしデータの保存
        transcript_id = await crud.create_transcript(db, video.id, transcript_content)
        if not transcript_id:
            raise Exception("文字起こしデータの保存に失敗しました")
        
        # 5. チャンク分割
        chunks = chunk.split_into_chunks(transcript_content)
        if not chunks:
            raise Exception("チャンク分割に失敗しました")
        
        # チャンク分割完了（80%）
        await crud.update_video_progress(db, minutes_id, 80)
        
        # 6. チャンクの保存とベクトル化
        total_chunks = len(chunks)
        for i, chunk_content in enumerate(chunks):
            # 各チャンク処理ごとに新しいデータベースセッションを作成
            chunk_db = SessionLocal()
            try:
                chunk_id = await crud.create_transcript_chunk(chunk_db, transcript_id, i, chunk_content)
                if not chunk_id:
                    raise Exception("チャンクの保存に失敗しました")
                    
                embedding_vector = await embedding.generate_embedding(chunk_content)
                if not embedding_vector:
                    raise Exception("ベクトル化に失敗しました")
                    
                await crud.create_vector_embedding(chunk_db, chunk_id, embedding_vector)
                chunk_db.commit()
                
                # Embedding生成の進捗を更新（80-95%）
                progress = 80 + int((i + 1) / total_chunks * 15)
                await crud.update_video_progress(db, minutes_id, progress)
            finally:
                chunk_db.close()
        
        # すべてのチャンクのEmbedding生成が完了したら、is_embeddedを更新
        await crud.update_transcript_embedded(db, transcript_id)
        
        # 7. 処理完了の更新
        await crud.update_video_status(db, minutes_id, "completed")
        await crud.update_video_progress(db, minutes_id, 100)
        
    except Exception as e:
        # エラー発生時の処理
        error_message = f"動画処理中にエラーが発生しました: {str(e)}"
        logger.error(error_message)
        try:
            db.rollback()  # トランザクションをロールバック
            await crud.update_video_status(db, minutes_id, "failed")
            # エラー発生時の進捗を保持（最後に更新された進捗を維持）
        except Exception as update_error:
            logger.error(f"ステータス更新中にエラーが発生: {str(update_error)}")
        raise Exception(error_message)
    finally:
        # 一時ファイルの削除
        try:
            os.unlink(file_path)
        except Exception as e:
            logger.error(f"一時ファイルの削除に失敗: {str(e)}")

@router.get("/api/upload_status", response_model=schemas.VideoUploadStatusResponse)
def get_upload_status(
    minutes_id: int,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    動画のアップロードと処理状況を取得する
    
    Args:
        minutes_id (int): 議事録ID
        user_id (str): 認証されたユーザーID
        db (Session): データベースセッション
        
    Returns:
        VideoUploadStatusResponse: アップロード状況
    """
    try:
        # 議事録データを取得してユーザーIDを確認
        minutes = crud.get_minutes(db, minutes_id)
        if not minutes:
            raise HTTPException(
                status_code=404,
                detail="指定された議事録IDのデータが見つかりません"
            )
        
        # ユーザーIDの比較（文字列として比較）
        if str(minutes.user_id) != str(user_id):
            raise HTTPException(
                status_code=403,
                detail="この議事録へのアクセス権限がありません"
            )
        
        # 動画データを取得
        video = crud.get_video(db, minutes_id)
        if not video:
            raise HTTPException(
                status_code=404,
                detail="指定された議事録IDの動画が見つかりません"
            )
        
        return schemas.VideoUploadStatusResponse(
            minutes_id=minutes_id,
            status=video.status,
            progress=video.progress
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_message = f"アップロード状況の取得中にエラーが発生しました: {str(e)}"
        logger.error(error_message)  # ログ出力
        raise HTTPException(
            status_code=500,
            detail=error_message
        )

@router.get("/api/upload_result", response_model=schemas.VideoUploadResultResponse)
def get_upload_result(
    minutes_id: int,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    動画のアップロードと処理結果を取得する
    
    Args:
        minutes_id (int): 議事録ID
        user_id (str): 認証されたユーザーID
        db (Session): データベースセッション
        
    Returns:
        VideoUploadResultResponse: アップロード結果
    """
    try:
        # 議事録データを取得してユーザーIDを確認
        minutes = crud.get_minutes(db, minutes_id)
        if not minutes:
            raise HTTPException(
                status_code=404,
                detail="指定された議事録IDのデータが見つかりません"
            )
        
        # ユーザーIDの比較（文字列として比較）
        if str(minutes.user_id) != str(user_id):
            raise HTTPException(
                status_code=403,
                detail="この議事録へのアクセス権限がありません"
            )
        
        # 動画データを取得
        video = crud.get_video(db, minutes_id)
        if not video:
            raise HTTPException(
                status_code=404,
                detail="指定された議事録IDの動画が見つかりません"
            )
        
        # 処理が完了していない場合はエラー
        if video.status != "completed":
            raise HTTPException(
                status_code=400,
                detail="動画の処理が完了していません"
            )
        
        # 文字起こしデータを取得
        transcript = crud.get_transcript(db, video.id)
        if not transcript:
            raise HTTPException(
                status_code=404,
                detail="文字起こしデータが見つかりません"
            )
        
        # 動画URLをSAS URLに変換
        try:
            video_url = storage.generate_sas_url(video.video_url, storage.container_name_video)
        except Exception as e:
            logger.error(f"動画URLのSAS URL生成中にエラーが発生: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="動画URLの生成中にエラーが発生しました"
            )
        
        return schemas.VideoUploadResultResponse(
            minutes_id=minutes_id,
            title=minutes.title,
            video_url=video_url,
            transcript=[
                schemas.TranscriptResponse(
                    transcript_id=transcript.id,
                    transcript_content=transcript.content
                )
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_message = f"アップロード結果の取得中にエラーが発生しました: {str(e)}"
        logger.error(error_message)  # ログ出力
        raise HTTPException(
            status_code=500,
            detail=error_message
        )

@router.get("/api/get_all_minutes", response_model=schemas.MinutesListResponse)
async def get_all_minutes(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    ユーザーが作成した全ての議事録一覧を取得する
    
    Args:
        user_id (str): 認証されたユーザーID
        db (Session): データベースセッション
        
    Returns:
        MinutesListResponse: 議事録一覧（各議事録に紐づく画像URLを含む）
    """
    try:
        # 議事録一覧を取得
        results = crud.get_all_minutes_by_user_id(db, user_id)
        
        # レスポンス用のデータを整形
        minutes_list = []
        
        for minutes, video_image_url in results:
            # 画像URLをSAS URLに変換
            image_url = None
            if video_image_url:
                try:
                    image_url = storage.generate_sas_url(video_image_url, storage.container_name_video)
                except Exception as e:
                    logger.error(f"画像URLのSAS URL生成中にエラーが発生: {str(e)}")
            
            minutes_list.append(schemas.MinutesListItem(
                minutes_id=minutes.id,
                title=minutes.title,
                image_url=image_url,
                created_at=minutes.created_at
            ))
        
        return schemas.MinutesListResponse(
            minutes=minutes_list
        )
        
    except Exception as e:
        error_message = f"議事録一覧の取得中にエラーが発生しました: {str(e)}"
        logger.error(error_message)
        raise HTTPException(
            status_code=500,
            detail=error_message
        )

@router.get("/api/get_minutes_list", response_model=schemas.MinutesDetailResponse)
async def get_minutes_detail(
    minutes_id: int,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    議事録の詳細情報を取得する
    """
    try:
        # 議事録の詳細情報を取得
        video, transcript, summary, chat_session, messages = crud.get_minutes_detail(
            db, minutes_id, user_id
        )
        
        # 動画URLをSAS URLに変換
        try:
            video_url = storage.generate_sas_url(video.video_url, storage.container_name_video)
        except Exception as e:
            logger.error(f"動画URLのSAS URL生成中にエラーが発生: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="動画URLの生成中にエラーが発生しました"
            )
        
        # チャットメッセージをレスポンス用に整形
        message_items = None
        if messages:
            message_items = [
                schemas.ChatMessageItem(
                    message_id=msg.id,
                    role=msg.role,
                    message=msg.message,
                    created_at=msg.created_at
                ) for msg in messages
            ]
        
        return schemas.MinutesDetailResponse(
            video_url=video_url,
            transcript_content=transcript.content,
            summary=summary.content if summary else None,
            session_id=chat_session.id if chat_session else None,
            messages=message_items
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        error_message = f"議事録詳細の取得中にエラーが発生しました: {str(e)}"
        logger.error(error_message)
        raise HTTPException(
            status_code=500,
            detail=error_message
        )
