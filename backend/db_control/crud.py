from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from . import models, schemas
import uuid
import os
from datetime import datetime
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

async def create_minutes(db: Session, user_id: str, filename: str = None) -> int:
    # ファイル名から拡張子を除去
    title = os.path.splitext(filename)[0] if filename else f"議事録_{func.now()}"
    
    db_minutes = models.Minutes(
        user_id=user_id,
        title=title
    )
    db.add(db_minutes)
    db.commit()
    db.refresh(db_minutes)
    return db_minutes.id

async def create_video(db: Session, minutes_id: int, video_url: str = None) -> int:
    db_video = models.Video(
        minutes_id=minutes_id,
        video_url=video_url,
        image_url=None,  # サムネイル画像はしばらく使用しない
        status="queued",
        progress=0
    )
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    return db_video.id

async def update_video_status(db: Session, minutes_id: int, status: str, progress: int = None):
    video = db.query(models.Video).filter(models.Video.minutes_id == minutes_id).first()
    if video:
        video.status = status
        if progress is not None:
            video.progress = progress
        db.commit()

async def create_transcript(db: Session, video_id: int, content: str) -> int:
    db_transcript = models.Transcript(
        video_id=video_id,
        content=content,
        is_summaried=False,
        is_embedded=False
    )
    db.add(db_transcript)
    db.commit()
    db.refresh(db_transcript)
    return db_transcript.id

async def create_transcript_chunk(db: Session, transcript_id: int, chunk_index: int, content: str) -> int:
    db_chunk = models.TranscriptChunk(
        transcript_id=transcript_id,
        chunk_index=chunk_index,
        content=content
    )
    db.add(db_chunk)
    db.commit()
    db.refresh(db_chunk)
    return db_chunk.id

async def create_vector_embedding(db: Session, chunk_id: int, embedding: str) -> int:
    db_embedding = models.VectorEmbedding(
        chunk_id=chunk_id,
        embedding=embedding
    )
    db.add(db_embedding)
    db.commit()
    db.refresh(db_embedding)
    return db_embedding.id

def get_minutes(db: Session, minutes_id: int):
    minutes = db.query(models.Minutes).filter(models.Minutes.id == minutes_id).first()
    if minutes:
        print(f"get_minutes - 取得したデータ: id={minutes.id}, user_id={minutes.user_id}, title={minutes.title}")
    else:
        print(f"get_minutes - データが見つかりません: minutes_id={minutes_id}")
    return minutes

def get_video(db: Session, minutes_id: int):
    return db.query(models.Video).filter(models.Video.minutes_id == minutes_id).first()

def get_transcript(db: Session, video_id: int):
    return db.query(models.Transcript).filter(models.Transcript.video_id == video_id).first()

async def update_video_progress(db: Session, minutes_id: int, progress: int) -> bool:
    """
    動画の処理進捗を更新する
    
    Args:
        db (Session): データベースセッション
        minutes_id (int): 議事録ID
        progress (int): 進捗状況（0-100）
        
    Returns:
        bool: 更新が成功したかどうか
    """
    try:
        video = db.query(models.Video).filter(models.Video.minutes_id == minutes_id).first()
        if not video:
            return False
        
        video.progress = progress
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"進捗更新中にエラーが発生: {str(e)}")
        return False

async def update_transcript_embedded(db: Session, transcript_id: int) -> bool:
    """
    文字起こしデータの埋め込み完了フラグを更新する
    
    Args:
        db (Session): データベースセッション
        transcript_id (int): 文字起こしID
        
    Returns:
        bool: 更新が成功したかどうか
    """
    try:
        transcript = db.query(models.Transcript).filter(models.Transcript.id == transcript_id).first()
        if not transcript:
            return False
        
        transcript.is_embedded = True
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"文字起こしの埋め込みフラグ更新中にエラーが発生: {str(e)}")
        return False

def get_summary_by_transcript_id(db: Session, transcript_id: str):
    """
    文字起こしIDからサマリーを取得
    """
    return db.query(models.Summary).filter(
        models.Summary.transcript_id == transcript_id
    ).first()

def create_summary(db: Session, transcript_id: str, content: str):
    """
    サマリーを作成し、文字起こしのis_summariedフラグを更新する
    """
    try:
        # 既存のサマリーを確認
        existing_summary = get_summary_by_transcript_id(db, transcript_id)
        if existing_summary:
            logger.info(f"既存のサマリーが見つかりました: summary_id={existing_summary.id}")
            return existing_summary

        # 文字起こしデータを取得してis_summariedフラグを更新
        transcript = get_transcript_by_id(db, transcript_id)
        if not transcript:
            logger.error(f"文字起こしデータが見つかりません: transcript_id={transcript_id}")
            raise ValueError(f"文字起こしデータが見つかりません: transcript_id={transcript_id}")
        
        transcript.is_summaried = True

        # 新しいサマリーを作成
        summary = models.Summary(
            transcript_id=transcript_id,
            content=content
        )
        db.add(summary)
        db.commit()
        db.refresh(summary)
        logger.info(f"新しいサマリーを作成し、is_summariedフラグを更新しました: summary_id={summary.id}")
        return summary
    except IntegrityError as e:
        db.rollback()
        logger.error(f"サマリーの作成中に整合性エラーが発生しました: {str(e)}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"サマリーの作成中にエラーが発生しました: {str(e)}")
        raise

def get_transcript_by_id(db: Session, transcript_id: int) -> models.Transcript:
    """
    文字起こしIDから文字起こしデータを取得する
    """
    return db.query(models.Transcript).filter(models.Transcript.id == transcript_id).first()

def get_transcript_by_video_id(db: Session, video_id: int) -> models.Transcript:
    """
    動画IDから文字起こしデータを取得する
    """
    return db.query(models.Transcript).filter(models.Transcript.video_id == video_id).first()

def get_video_by_minutes_id(db: Session, minutes_id: int) -> models.Video:
    """
    議事録IDから動画データを取得する
    
    Args:
        db (Session): データベースセッション
        minutes_id (int): 議事録ID
        
    Returns:
        models.Video: 動画データ
    """
    return db.query(models.Video).filter(models.Video.minutes_id == minutes_id).first()

def get_chat_session_by_minutes_and_transcript(db: Session, minutes_id: str, transcript_id: str):
    """
    議事録IDと文字起こしIDからチャットセッションを取得
    """
    return db.query(models.ChatSession).filter(
        models.ChatSession.minutes_id == minutes_id,
        models.ChatSession.transcript_id == transcript_id
    ).first()

def create_chat_session(db: Session, minutes_id: str, transcript_id: str):
    """
    チャットセッションを作成
    """
    try:
        # 既存のセッションを確認
        existing_session = get_chat_session_by_minutes_and_transcript(db, minutes_id, transcript_id)
        if existing_session:
            logger.info(f"既存のチャットセッションが見つかりました: session_id={existing_session.id}")
            return existing_session

        # 新しいセッションを作成
        chat_session = models.ChatSession(
            id=str(uuid.uuid4()),
            minutes_id=minutes_id,
            transcript_id=transcript_id
        )
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)
        logger.info(f"新しいチャットセッションを作成しました: session_id={chat_session.id}")
        return chat_session
    except IntegrityError as e:
        db.rollback()
        logger.error(f"チャットセッションの作成中に整合性エラーが発生しました: {str(e)}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"チャットセッションの作成中にエラーが発生しました: {str(e)}")
        raise

def get_chat_session(db: Session, session_id: str):
    """
    チャットセッションを取得
    """
    return db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()

def create_chat_message(db: Session, chat_session_id: str, role: str, content: str):
    """
    チャットメッセージを作成
    """
    try:
        chat_message = models.ChatMessage(
            id=str(uuid.uuid4()),
            chat_session_id=chat_session_id,
            role=role,
            content=content
        )
        db.add(chat_message)
        db.commit()
        db.refresh(chat_message)
        return chat_message
    except Exception as e:
        db.rollback()
        logger.error(f"チャットメッセージの作成中にエラーが発生しました: {str(e)}")
        raise

def get_chat_messages(db: Session, chat_session_id: str, skip: int = 0, limit: int = 100):
    """
    チャットメッセージを取得
    """
    return db.query(models.ChatMessage).filter(
        models.ChatMessage.chat_session_id == chat_session_id
    ).order_by(models.ChatMessage.created_at).offset(skip).limit(limit).all()

def update_summary(db: Session, transcript_id: int, content: str) -> models.Summary:
    """
    既存のサマリーを更新する
    
    Args:
        db (Session): データベースセッション
        transcript_id (int): 文字起こしID
        content (str): 更新する要約内容
        
    Returns:
        models.Summary: 更新されたサマリー
    """
    summary = db.query(models.Summary).filter(models.Summary.transcript_id == transcript_id).first()
    if summary:
        summary.content = content
        db.commit()
        db.refresh(summary)
    return summary

def get_all_minutes_by_user_id(db: Session, user_id: str):
    """
    ユーザーIDに紐づく全ての議事録を取得する
    
    Args:
        db (Session): データベースセッション
        user_id (str): ユーザーID
        
    Returns:
        List[Tuple[Minutes, str]]: 議事録とサムネイル画像URLのタプルのリスト
    """
    # 議事録と動画を結合して取得
    results = db.query(
        models.Minutes,
        models.Video.image_url
    ).outerjoin(
        models.Video,
        models.Minutes.id == models.Video.minutes_id
    ).filter(
        models.Minutes.user_id == user_id,
        models.Minutes.is_deleted == False
    ).order_by(
        models.Minutes.created_at.desc()
    ).all()
    
    return results

def get_minutes_detail(db: Session, minutes_id: int, user_id: str):
    """
    議事録の詳細情報を取得する
    
    Args:
        db (Session): データベースセッション
        minutes_id (int): 議事録ID
        user_id (str): ユーザーID
        
    Returns:
        Tuple[Video, Transcript, Summary, ChatSession, List[ChatMessage]]: 
            動画、文字起こし、要約、チャットセッション、チャットメッセージの情報
    """
    # 議事録の存在確認とアクセス権限チェック
    minutes = get_minutes(db, minutes_id)
    if not minutes:
        raise ValueError("議事録が見つかりません")
    if str(minutes.user_id) != str(user_id):
        raise ValueError("この議事録へのアクセス権限がありません")
    
    # 動画情報を取得
    video = get_video_by_minutes_id(db, minutes_id)
    if not video:
        raise ValueError("動画情報が見つかりません")
    
    # 文字起こし情報を取得
    transcript = get_transcript_by_video_id(db, video.id)
    if not transcript:
        raise ValueError("文字起こし情報が見つかりません")
    
    # 要約情報を取得
    summary = get_summary_by_transcript_id(db, transcript.id)
    
    # チャットセッションを取得
    chat_session = get_chat_session_by_minutes_and_transcript(db, minutes_id, transcript.id)
    
    # チャットメッセージを取得（作成日時の昇順）
    messages = []
    if chat_session:
        messages = db.query(models.ChatMessage).filter(
            models.ChatMessage.session_id == chat_session.id
        ).order_by(models.ChatMessage.created_at.asc()).all()
    
    return video, transcript, summary, chat_session, messages
