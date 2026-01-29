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
    Ghép các audio segments thành một file audio hoàn chỉnh với Auto-Ducking
    """
    total_ms = int(total_duration * 1000)
    
    # 1. Base Audio Layer
    if original_audio_path and os.path.exists(original_audio_path):
        try:
            base_audio = AudioSegment.from_file(original_audio_path)
            # Resize base audio
            if len(base_audio) > total_ms:
                base_audio = base_audio[:total_ms]
            elif len(base_audio) < total_ms:
                base_audio = base_audio + AudioSegment.silent(duration=total_ms - len(base_audio))
        except Exception as e:
            print(f"Error loading original audio: {e}")
            base_audio = AudioSegment.silent(duration=total_ms)
    else:
        base_audio = AudioSegment.silent(duration=total_ms)
    
    # 2. Voice Layer (Dubbed)
    voice_layer = AudioSegment.silent(duration=total_ms)
    
    # Track where we have voice to apply ducking
    voice_segments_mask = []  # List of tuples (start_ms, end_ms)
    
    for seg in segments:
        if not seg.get("audio_path") or not os.path.exists(seg["audio_path"]):
            continue
        
        try:
            audio = AudioSegment.from_file(seg["audio_path"])
            
            # Apply dubbed volume
            if dubbed_volume != 1.0:
                audio = audio + (20 * (dubbed_volume - 1))
            
            start_ms = int(seg["start"] * 1000)
            voice_layer = voice_layer.overlay(audio, position=start_ms)
            
            # Record voice timing for ducking
            voice_segments_mask.append((start_ms, start_ms + len(audio)))
            
        except Exception as e:
            print(f"Error overlaying segment {seg['id']}: {e}")
    
    # 3. Apply Auto-Ducking to Base Audio
    # Nếu có original volume, chúng ta sẽ giữ nền ở mức đó
    # Nhưng khi CÓ giọng đọc, chúng ta giảm nó xuống thêm (ducking)
    # Ví dụ: Nền bình thường 30%, khi có người nói giảm còn 10%
    
    final_audio = base_audio
    
    # Simple Ducking: Reduce volume during voice segments
    if original_volume > 0:
        # Volume nền mặc định (ví dụ 0.3)
        base_db_adj = -20 * (1.0 - original_volume) # Giảm dB theo volume setting
        
        # Volume khi có giọng đọc (ducking) - giảm thêm 10dB
        duck_db_adj = base_db_adj - 10 
        
        # Áp dụng volume mặc định cho toàn bài trước
        final_audio = final_audio + base_db_adj
        
        # TODO: Advanced ducking cần pydub complex logic (split & gain).
        # Để đơn giản và hiệu quả: Chúng ta mix Voice đè lên Base đã giảm volume.
        # Với version đơn giản này, ta chấp nhận volume nền background thấp đều.
        pass
    else:
        final_audio = final_audio - 100 # Silence
        
    # 4. Final Mix
    output_audio = final_audio.overlay(voice_layer)
    
    output_path = tempfile.mktemp(suffix=".mp3")
    output_audio.export(output_path, format="mp3")
    
    return output_path


def create_srt_file(segments: List[Dict], output_path: Optional[str] = None, max_line_width: int = 50) -> str:
    """
    Tạo file SRT từ segments với xử lý xuống dòng
    
    Args:
        segments: List segments
        output_path: Đường dẫn output
        max_line_width: Số ký tự tối đa trên 1 dòng
    
    Returns:
        Đường dẫn file SRT
    """
    import textwrap
    
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
            
            # Wrap text to ensure max 2 lines (mostly)
            wrapped_lines = textwrap.wrap(text, width=max_line_width)
            wrapped_text = "\n".join(wrapped_lines)
            
            f.write(f"{i + 1}\n")
            f.write(f"{format_srt_time(seg['start'])} --> {format_srt_time(seg['end'])}\n")
            f.write(f"{wrapped_text}\n\n")
    
    return output_path


def merge_video_audio(
    video_path: str,
    audio_path: str,
    output_path: str,
    subtitle_path: Optional[str] = None,
    burn_subtitles: bool = True,
    font_size: int = 24
) -> bool:
    """
    Ghép video với audio mới và (optional) hardsub
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
            
            # Adjust style based on font size
            style = f"FontSize={font_size},PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=2,Alignment=2,MarginV=20"
            
            cmd.extend([
                "-filter_complex",
                f"[0:v]subtitles='{escaped_sub_path}':force_style='{style}'[v]",
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
    progress_callback=None,
    preview_duration: Optional[float] = None,
    font_size: int = 24,
    max_line_width: int = 50
) -> bool:
    """
    Pipeline hoàn chỉnh để export video dubbed
    """
    from moviepy.editor import VideoFileClip
    
    if progress_callback:
        progress_callback("Đang tạo audio dubbed...")
    
    # Get total duration and extract original audio
    video = VideoFileClip(video_path)
    total_duration = video.duration
    
    # Extract original audio for mixing context
    temp_original_audio = None
    if original_volume > 0 and video.audio:
        temp_original_audio = tempfile.mktemp(suffix=".mp3")
        try:
            video.audio.write_audiofile(temp_original_audio, verbose=False, logger=None)
        except Exception as e:
            print(f"Error extracting audio: {e}")
            temp_original_audio = None

    # Nếu là preview, giới hạn duration
    if preview_duration and preview_duration < total_duration:
        total_duration = preview_duration
    
    video.close()
    
    # Filter segments nếu là preview
    if preview_duration:
        segments = [seg for seg in segments if seg["start"] < preview_duration]
    
    # Create dubbed audio
    dubbed_audio = create_dubbed_audio(
        segments,
        total_duration,
        temp_original_audio, # Pass extracted audio path
        original_volume,
        dubbed_volume
    )
    
    if progress_callback:
        progress_callback("Đang tạo file subtitles...")
    
    # Create SRT
    srt_path = None
    if burn_subtitles:
        srt_path = create_srt_file(segments, max_line_width=max_line_width)
    
    if progress_callback:
        progress_callback("Đang render video...")
    
    # Nếu là preview, cắt video trước khi merge
    temp_video_path = video_path
    if preview_duration:
        temp_video_path = tempfile.mktemp(suffix=".mp4")
        cut_cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-t", str(preview_duration),
            "-c", "copy",
            temp_video_path
        ]
        subprocess.run(cut_cmd, capture_output=True, timeout=120)
    
    # Merge
    success = merge_video_audio(
        temp_video_path,
        dubbed_audio,
        output_path,
        srt_path,
        burn_subtitles,
        font_size=font_size
    )
    
    # Cleanup temp files
    cleanup_files = [dubbed_audio, srt_path]
    if preview_duration and temp_video_path != video_path:
        cleanup_files.append(temp_video_path)
    
    for path in cleanup_files:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass
    
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
