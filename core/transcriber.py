"""
VietDub Solo - Transcriber Module
Sử dụng OpenAI Whisper để transcribe audio thành text với timestamps
"""

import whisper
import torch
import os
from typing import List, Dict, Optional
import tempfile
from moviepy.editor import VideoFileClip


def get_available_device() -> str:
    """Kiểm tra GPU availability"""
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        return "mps"  # Apple Silicon
    return "cpu"


def extract_audio(video_path: str, output_path: Optional[str] = None) -> str:
    """
    Trích xuất audio từ video file
    
    Args:
        video_path: Đường dẫn đến video
        output_path: Đường dẫn output (optional)
    
    Returns:
        Đường dẫn file audio
    """
    if output_path is None:
        output_path = tempfile.mktemp(suffix=".mp3")
    
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(output_path, verbose=False, logger=None)
    video.close()
    
    return output_path


def transcribe_audio(
    audio_path: str,
    model_name: str = "base",
    language: str = "en"
) -> List[Dict]:
    """
    Transcribe audio thành text với timestamps
    
    Args:
        audio_path: Đường dẫn file audio
        model_name: Tên model Whisper (tiny, base, small, medium, large-v3)
        language: Ngôn ngữ của audio
    
    Returns:
        List các segments với format:
        [{"id": 1, "start": 0.0, "end": 5.0, "text": "Hello world"}, ...]
    """
    device = get_available_device()
    
    # Load model
    model = whisper.load_model(model_name, device=device)
    
    # Transcribe
    result = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=False,
        verbose=False
    )
    
    # Format segments
    segments = []
    for i, seg in enumerate(result["segments"]):
        segments.append({
            "id": i + 1,
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "text": seg["text"].strip(),
            "vietnamese": "",  # Sẽ điền sau khi dịch
            "audio_path": ""   # Sẽ điền sau khi TTS
        })
    
    # Merge segments ngắn để tối ưu cho dubbing
    segments = merge_short_segments(segments, min_duration=1.5)
    
    # Re-index IDs
    for i, seg in enumerate(segments):
        seg["id"] = i + 1
        
    return segments


def merge_short_segments(segments: List[Dict], min_duration: float = 1.5) -> List[Dict]:
    """
    Gộp các segments quá ngắn vào segment tiếp theo để tránh voice chồng chéo
    
    Args:
        segments: List segments gốc
        min_duration: Duration tối thiểu (seconds)
        
    Returns:
        List segments đã merge
    """
    if not segments:
        return []
        
    merged = []
    current_seg = segments[0]
    
    for next_seg in segments[1:]:
        # Tính duration của segment hiện tại
        duration = current_seg["end"] - current_seg["start"]
        
        # Kiểm tra điều kiện merge:
        # 1. Segment hiện tại quá ngắn (< min_duration)
        # 2. Hoặc khoảng cách với segment tiếp theo quá gần (< 0.5s)
        gap = next_seg["start"] - current_seg["end"]
        
        if duration < min_duration or gap < 0.5:
            # Merge với next_seg
            current_seg["end"] = next_seg["end"]
            current_seg["text"] += " " + next_seg["text"]
            # Giữ start time của current, end time của next
        else:
            # Segment hiện tại đã đủ tốt, đẩy vào list
            merged.append(current_seg)
            current_seg = next_seg
            
    # Đừng quên segment cuối cùng
    merged.append(current_seg)
    
    return merged


def transcribe_video(
    video_path: str,
    model_name: str = "base",
    language: str = "en",
    progress_callback=None
) -> List[Dict]:
    """
    Pipeline hoàn chỉnh: Video -> Audio -> Transcription
    
    Args:
        video_path: Đường dẫn video
        model_name: Model Whisper
        language: Ngôn ngữ
        progress_callback: Callback để update progress
    
    Returns:
        List segments
    """
    if progress_callback:
        progress_callback("Đang trích xuất audio từ video...")
    
    # Extract audio
    audio_path = extract_audio(video_path)
    
    if progress_callback:
        progress_callback(f"Đang transcribe với model {model_name}...")
    
    # Transcribe
    segments = transcribe_audio(audio_path, model_name, language)
    
    # Cleanup temp file
    if os.path.exists(audio_path):
        os.remove(audio_path)
    
    if progress_callback:
        progress_callback(f"Hoàn tất! Tìm thấy {len(segments)} đoạn.")
    
    return segments


def format_timecode(seconds: float) -> str:
    """Chuyển seconds thành format MM:SS"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def format_timecode_range(start: float, end: float) -> str:
    """Format timecode range"""
    return f"{format_timecode(start)} - {format_timecode(end)}"
