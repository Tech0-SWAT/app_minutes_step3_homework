from openai import AzureOpenAI
import os
from dotenv import load_dotenv
import tempfile
import requests
import mimetypes
import logging
import subprocess
import shutil
import aiohttp
import asyncio
from typing import List, Tuple
import httpx

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(override=True)
http_client = httpx.Client(timeout=60.0)

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION_WHISPER"),
    azure_endpoint=os.getenv("AZURE_OPENAI_BASE_URL"),
    http_client=http_client
)

MAX_SIZE = 25 * 1024 * 1024  # 25MB in bytes
MAX_DURATION = 10 * 60  # 10分（秒）

async def get_video_duration(file_path: str) -> float:
    """動画の長さを取得する関数"""
    command = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        file_path
    ]
    
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        raise Exception(f"動画の長さ取得に失敗しました: {stderr.decode()}")
    
    return float(stdout.decode().strip())

async def compress_video(input_path: str, output_path: str) -> None:
    """動画を圧縮する関数"""
    command = [
        'ffmpeg', '-i', input_path,
        '-c:v', 'libx264',
        '-crf', '28',  # より高い圧縮率
        '-preset', 'medium',
        '-vf', 'scale=1280:720',  # 720pに解像度を下げる
        '-r', '24',  # フレームレートを24fpsに下げる
        '-c:a', 'aac',
        '-b:a', '96k',  # 音声ビットレートを96kに下げる
        '-y', output_path
    ]
    
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        raise Exception(f"動画の圧縮に失敗しました: {stderr.decode()}")

async def split_video(input_path: str, output_dir: str, segment_duration: int = 600) -> List[str]:
    """動画を分割する関数"""
    command = [
        'ffmpeg', '-i', input_path,
        '-c:v', 'libx264',
        '-crf', '28',
        '-preset', 'medium',
        '-vf', 'scale=1280:720',
        '-r', '24',
        '-c:a', 'aac',
        '-b:a', '96k',
        '-f', 'segment',
        '-segment_time', str(segment_duration),
        '-reset_timestamps', '1',
        '-y',
        os.path.join(output_dir, 'segment_%03d.mp4')
    ]
    
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        raise Exception(f"動画の分割に失敗しました: {stderr.decode()}")
    
    # 分割されたファイルのリストを取得
    segments = sorted([f for f in os.listdir(output_dir) if f.startswith('segment_')])
    return [os.path.join(output_dir, segment) for segment in segments]

async def transcribe_video(video_url: str) -> str:
    """動画の文字起こしを行う関数"""
    temp_dir = None
    try:
        # 一時ディレクトリの作成
        temp_dir = tempfile.mkdtemp()
        temp_input = os.path.join(temp_dir, 'input.mp4')
        temp_output = os.path.join(temp_dir, 'output.mp4')
        
        # 動画のダウンロード
        async with aiohttp.ClientSession() as session:
            async with session.get(video_url) as response:
                if response.status != 200:
                    raise Exception(f"動画のダウンロードに失敗しました: {response.status}")
                content = await response.read()
                with open(temp_input, 'wb') as f:
                    f.write(content)
        
        # 動画の長さを取得
        duration = await get_video_duration(temp_input)
        logger.info(f"動画の長さ: {duration}秒")
        
        # 動画の圧縮
        logger.info("動画の圧縮を開始")
        await compress_video(temp_input, temp_output)
        
        # 圧縮後のファイルサイズをチェック
        compressed_size = os.path.getsize(temp_output)
        logger.info(f"圧縮後のファイルサイズ: {compressed_size} bytes")
        
        if compressed_size <= MAX_SIZE:
            # 圧縮後のファイルが制限内の場合、そのまま文字起こし
            logger.info("圧縮後のファイルが制限内のため、そのまま文字起こしを実行")
            with open(temp_output, 'rb') as audio_file:
                response = client.audio.transcriptions.create(
                    model=os.getenv("AZURE_OPENAI_DEPLOYMENT_WHISPER"),
                    file=audio_file,
                    response_format="text"
                )
            return response
        else:
            # 圧縮後のファイルが制限を超える場合、分割して処理
            logger.info("圧縮後のファイルが制限を超えるため、分割して処理")
            segments = await split_video(temp_input, temp_dir)
            transcriptions = []
            
            for i, segment in enumerate(segments):
                logger.info(f"セグメント {i+1}/{len(segments)} の文字起こしを開始")
                with open(segment, 'rb') as audio_file:
                    response = client.audio.transcriptions.create(
                        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_WHISPER"),
                        file=audio_file,
                        response_format="text"
                    )
                transcriptions.append(response)
            
            # 文字起こし結果を結合
            return " ".join(transcriptions)
            
    except Exception as e:
        logger.error(f"エラーが発生: {str(e)}")
        raise Exception(f"文字起こし処理中にエラーが発生しました: {str(e)}")
    finally:
        # 一時ファイルの削除
        if temp_dir and os.path.exists(temp_dir):
            try:
                for file in os.listdir(temp_dir):
                    os.unlink(os.path.join(temp_dir, file))
                os.rmdir(temp_dir)
                logger.info(f"一時ディレクトリを削除: {temp_dir}")
            except Exception as e:
                logger.error(f"一時ファイルの削除に失敗: {str(e)}")
