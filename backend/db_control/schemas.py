from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class VideoUploadResponse(BaseModel):
    minutes_id: int
    status: str

class VideoUploadStatusResponse(BaseModel):
    minutes_id: int
    status: str
    progress: int

class MinutesBase(BaseModel):
    user_id: str
    title: str

class MinutesCreate(MinutesBase):
    pass

class Minutes(MinutesBase):
    id: int
    created_at: datetime
    is_deleted: bool = False

    class Config:
        from_attributes = True

class VideoBase(BaseModel):
    minutes_id: int
    video_url: Optional[str] = None
    image_url: Optional[str] = None
    status: str
    progress: Optional[int] = None

class VideoCreate(VideoBase):
    pass

class Video(VideoBase):
    id: int
    created_at: datetime
    recorded_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TranscriptBase(BaseModel):
    video_id: int
    content: str
    is_summaried: bool = False
    is_embedded: bool = False

class TranscriptCreate(TranscriptBase):
    pass

class Transcript(TranscriptBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class TranscriptChunkBase(BaseModel):
    transcript_id: int
    chunk_index: int
    content: str

class TranscriptChunkCreate(TranscriptChunkBase):
    pass

class TranscriptChunk(TranscriptChunkBase):
    id: int

    class Config:
        from_attributes = True

class VectorEmbeddingBase(BaseModel):
    chunk_id: int
    embedding: str

class VectorEmbeddingCreate(VectorEmbeddingBase):
    pass

class VectorEmbedding(VectorEmbeddingBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class TranscriptResponse(BaseModel):
    transcript_id: int
    transcript_content: str

class VideoUploadResultResponse(BaseModel):
    minutes_id: int
    title: str
    video_url: str
    transcript: List[TranscriptResponse]

class SummaryRequest(BaseModel):
    transcript_id: int

class SummaryResponse(BaseModel):
    summary: str

class ChatStartRequest(BaseModel):
    minutes_id: int

class ChatStartResponse(BaseModel):
    is_embedded: bool
    session_id: Optional[str] = None

class MinutesListItem(BaseModel):
    minutes_id: int
    title: str
    image_url: Optional[str] = None
    created_at: datetime

class MinutesListResponse(BaseModel):
    minutes: List[MinutesListItem]

class ChatMessageItem(BaseModel):
    message_id: int
    role: str
    message: str
    created_at: datetime

class MinutesDetailResponse(BaseModel):
    video_url: str
    transcript_content: str
    summary: Optional[str] = None
    session_id: Optional[int] = None
    messages: Optional[List[ChatMessageItem]] = None
