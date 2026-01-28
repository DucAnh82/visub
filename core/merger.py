"""
VietDub Solo - Video Merger Module
Sử dụng FFmpeg để ghép audio dubbed vào video gốc
"""

import subprocess
import os
import tempfile
from typing import List, Dict, Optional
from pydub import AudioSegment


def create_dubbed_audio(
    segments: List[Dict],
    total_duration: float,
    original_audio_path: Optional[str] = None,
    original_volume: float = 0.1,
    dubbed_volume: float = 1.0
) -> str:
    """
    Ghép các audio segments thành một file audio hoàn chỉnh
    
    Args:
        segments: List segments với audio_path
        total_duration: Tổng duration của video (seconds)
        original_audio_path: Audio gốc (optional, để mix)
        original_volume: Volume của audio gốc (0.0 - 1.0)
        dubbed_volume: Volume của audio dubbed
    
    Returns:
        Đường dẫn file audio đã ghép
    """
    # Tạo audio rỗng với duration đúng
    total_ms = int(total_duration * 1000)
    combined = AudioSegment.silent(duration=total_ms)
    
    # Overlay từng segment vào đúng vị trí
    for seg in segments:
        if not seg.get("audio_path") or not os.path.exists(seg["audio_path"]):
            continue
        
        try:
            audio = AudioSegment.from_file(seg["audio_path"])
            start_ms = int(seg["start"] * 1000)
            
            # Adjust volume
            if dubbed_volume != 1.0:
                audio = audio + (20 * (dubbed_volume - 1))  # dB adjustment
            
            combined = combined.overlay(audio, position=start_ms)
            
        except Exception as e:
            print(f"Error overlaying segment {seg['id']}: {e}")
    
    # Mix với audio gốc nếu có
    if original_audio_path and os.path.exists(original_audio_path) and original_volume > 0:
        try:
            original = AudioSegment.from_file(original_audio_path)
            
            # Giảm volume audio gốc
            original = original - (20 * (1 - original_volume))  # Reduce by dB
            
            # Ensure same length
            if len(original) > len(combined):
                original = original[:len(combined)]
            elif len(original) < len(combined):
                silence = AudioSegment.silent(duration=len(combined) - len(original))
                original = original + silence
            
            combined = combined.overlay(original)
            
        except Exception as e:
            print(f"Error mixing original audio: {e}")
    
    # Export
    output_path = tempfile.mktemp(suffix=".mp3")
    combined.export(output_path, format="mp3")
    
    return output_path


def create_srt_file(segments: List[Dict], output_path: Optional[str] = None) -> str:
    """
    Tạo file SRT từ segments
    
    Args:
        segments: List segments
        output_path: Đường dẫn output
    
    Returns:
        Đường dẫn file SRT
    """
    if output_path is None:
        output_path = tempfile.mktemp(suffix=".srt")
    
    def format_srt_time(seconds: float) -> str:
        """Convert seconds to SRT format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, seg in enumerate(segments):
            text = seg.get("vietnamese") or seg.get("text", "")
            
            f.write(f"{i + 1}\n")
            f.write(f"{format_srt_time(seg['start'])} --> {format_srt_time(seg['end'])}\n")
            f.write(f"{text}\n\n")
    
    return output_path


def merge_video_audio(
    video_path: str,
    audio_path: str,
    output_path: str,
    subtitle_path: Optional[str] = None,
    burn_subtitles: bool = True
) -> bool:
    """
    Ghép video với audio mới và (optional) hardsub
    
    Args:
        video_path: Đường dẫn video gốc
        audio_path: Đường dẫn audio dubbed
        output_path: Đường dẫn output
        subtitle_path: Đường dẫn file SRT (optional)
        burn_subtitles: Có burn subtitles vào video không
    
    Returns:
        True nếu thành công
    """
    try:
        # Build FFmpeg command
        cmd = ["ffmpeg", "-y"]
        
        # Input files
        cmd.extend(["-i", video_path])
        cmd.extend(["-i", audio_path])
        
        if burn_subtitles and subtitle_path and os.path.exists(subtitle_path):
            # Complex filter để burn subtitles
            # Escape special characters trong path
            escaped_sub_path = subtitle_path.replace("\\", "\\\\").replace(":", "\\:")
            
            cmd.extend([
                "-filter_complex",
                f"[0:v]subtitles='{escaped_sub_path}':force_style='FontSize=24,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=2'[v]",
                "-map", "[v]",
                "-map", "1:a"
            ])
        else:
            # Simple merge
            cmd.extend([
                "-map", "0:v",
                "-map", "1:a"
            ])
        
        # Output settings
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path
        ])
        
        # Run FFmpeg
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )
        
        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr}")
            return False
        
        return True
        
    except subprocess.TimeoutExpired:
        print("FFmpeg timeout")
        return False
    except Exception as e:
        print(f"Merge error: {e}")
        return False


def export_video(
    video_path: str,
    segments: List[Dict],
    output_path: str,
    original_audio_path: Optional[str] = None,
    original_volume: float = 0.1,
    dubbed_volume: float = 1.0,
    burn_subtitles: bool = True,
    progress_callback=None
) -> bool:
    """
    Pipeline hoàn chỉnh để export video dubbed
    
    Args:
        video_path: Video gốc
        segments: Segments với audio
        output_path: Output path
        original_audio_path: Audio gốc để mix
        original_volume: Volume audio gốc
        dubbed_volume: Volume audio dubbed
        burn_subtitles: Có burn sub không
        progress_callback: Progress callback
    
    Returns:
        True nếu thành công
    """
    from moviepy.editor import VideoFileClip
    
    if progress_callback:
        progress_callback("Đang tạo audio dubbed...")
    
    # Get total duration
    video = VideoFileClip(video_path)
    total_duration = video.duration
    video.close()
    
    # Create dubbed audio
    dubbed_audio = create_dubbed_audio(
        segments,
        total_duration,
        original_audio_path,
        original_volume,
        dubbed_volume
    )
    
    if progress_callback:
        progress_callback("Đang tạo file subtitles...")
    
    # Create SRT
    srt_path = None
    if burn_subtitles:
        srt_path = create_srt_file(segments)
    
    if progress_callback:
        progress_callback("Đang render video...")
    
    # Merge
    success = merge_video_audio(
        video_path,
        dubbed_audio,
        output_path,
        srt_path,
        burn_subtitles
    )
    
    # Cleanup temp files
    for path in [dubbed_audio, srt_path]:
        if path and os.path.exists(path):
            os.remove(path)
    
    return success


def check_ffmpeg_installed() -> bool:
    """Kiểm tra FFmpeg đã được cài chưa"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False
