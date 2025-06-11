from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Float, DateTime, Enum, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum
import datetime

# Baseクラスを作成
Base = declarative_base()

# 議事録（minutes）テーブル：ユーザーが作成した議事録情報を格納
class Minutes(Base):
    __tablename__ = "minutes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)  # Supabaseのauth.users.id（uuid）
    title = Column(String, nullable=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    videos = relationship("Video", back_populates="minutes")
    chat_session = relationship("ChatSession", back_populates="minutes")

# 動画（video）テーブル：議事録に紐づくアップロード動画の情報を格納
class Video(Base):
    __tablename__ = "video"

    id = Column(Integer, primary_key=True, autoincrement=True)
    minutes_id = Column(Integer, ForeignKey("minutes.id"), nullable=False)
    video_url = Column(String, nullable=False)
    image_url = Column(String)
    status = Column(String, nullable=False)
    progress = Column(Integer, default=0)
    recorded_at = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    minutes = relationship("Minutes", back_populates="videos")
    transcript = relationship("Transcript", back_populates="video", uselist=False)

# 文字起こし（transcript）テーブル：動画から生成された文字起こしの本文を格納
class Transcript(Base):
    __tablename__ = "transcript"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(Integer, ForeignKey("video.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_embedded = Column(Boolean, default=False, nullable=False)
    is_summaried = Column(Boolean, default=False, nullable=False)  # 要約が生成されたかどうかのフラグ
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    video = relationship("Video", back_populates="transcript", uselist=False)
    transcript_chunks = relationship("TranscriptChunk", back_populates="transcript")
    summary = relationship("Summary", back_populates="transcript", uselist=False)
    chat_session = relationship("ChatSession", back_populates="transcript")

# 文字起こしチャンク（transcript_chunk）テーブル：長文の文字起こしを分割して格納
class TranscriptChunk(Base):
    __tablename__ = "transcript_chunk"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transcript_id = Column(Integer, ForeignKey("transcript.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(String, nullable=False)

    transcript = relationship("Transcript", back_populates="transcript_chunks")
    vector_embedding = relationship("VectorEmbedding", back_populates="transcript_chunk")
    references = relationship("Reference", back_populates="transcript_chunk")

# ベクトル埋め込み（vector_embedding）テーブル：文字起こしチャンクのベクトル情報を格納
class VectorEmbedding(Base):
    __tablename__ = "vector_embedding"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chunk_id = Column(Integer, ForeignKey("transcript_chunk.id"), nullable=False)
    embedding = Column(String)  # SQLAlchemyではfloat配列が扱いづらいため、一旦Stringで保持
    created_at = Column(DateTime, default=func.now())

    transcript_chunk = relationship("TranscriptChunk", back_populates="vector_embedding")

# 要約（summary）テーブル：文字起こしの要約を格納
class Summary(Base):
    __tablename__ = "summary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transcript_id = Column(Integer, ForeignKey("transcript.id"), unique=True, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    transcript = relationship("Transcript", back_populates="summary", uselist=False)

# チャットセッション（chat_session）テーブル：1議事録あたりのチャットセッションを格納
class ChatSession(Base):
    __tablename__ = "chat_session"

    id = Column(Integer, primary_key=True, autoincrement=True)
    minutes_id = Column(Integer, ForeignKey("minutes.id"), nullable=False)
    transcript_id = Column(Integer, ForeignKey("transcript.id"), nullable=False)
    started_at = Column(DateTime, default=func.now())

    minutes = relationship("Minutes", back_populates="chat_session")
    transcript = relationship("Transcript", back_populates="chat_session")
    chat_messages = relationship("ChatMessage", back_populates="chat_session")

    # minutes_idとtranscript_idの組み合わせにユニーク制約を追加
    __table_args__ = (
        UniqueConstraint('minutes_id', 'transcript_id', name='uix_minutes_transcript'),
    )

# チャットメッセージ（chat_message）テーブル：ユーザーとアシスタントのメッセージログを格納
class ChatMessage(Base):
    __tablename__ = "chat_message"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("chat_session.id"), nullable=False)
    role = Column(String, nullable=False)
    message = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())

    chat_session = relationship("ChatSession", back_populates="chat_messages")
    references = relationship("Reference", back_populates="chat_message")

# 参照情報（reference）テーブル：チャットメッセージに関連付けられた文字起こしチャンク情報
class Reference(Base):
    __tablename__ = "reference"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_message_id = Column(Integer, ForeignKey("chat_message.id"), nullable=False)
    transcript_chunk_id = Column(Integer, ForeignKey("transcript_chunk.id"), nullable=False)
    rank = Column(Integer, nullable=False)

    chat_message = relationship("ChatMessage", back_populates="references")
    transcript_chunk = relationship("TranscriptChunk", back_populates="references")
