"""
VietDub Solo - Configuration Constants
"""

# Whisper Models
WHISPER_MODELS = {
    "tiny": "Tiny (Nhanh nhất, kém chính xác)",
    "base": "Base (Cân bằng - Khuyên dùng)",
    "small": "Small (Tốt hơn, chậm hơn)",
    "medium": "Medium (Rất tốt, cần GPU)",
    "large-v3": "Large V3 (Tốt nhất, cần GPU mạnh)"
}

# Translation Models via OpenRouter
TRANSLATION_MODELS = {
    "meta-llama/llama-3.3-70b-instruct:free": "Llama 3.3 70B (Free - Khuyên dùng)",
    "allenai/molmo-2-8b:free": "Molmo 2 8B (Free)",
    "openai/gpt-oss-120b:free": "GPT-OSS 120B (Free)",
    "google/gemini-2.0-flash-exp": "Gemini 2.0 Flash (Free)",
    "deepseek/deepseek-chat": "DeepSeek Chat (Rẻ nhất)",
    "openai/gpt-4o-mini": "GPT-4o Mini (Cân bằng)",
    "openai/gpt-4o": "GPT-4o (Tốt nhất)",
    "anthropic/claude-3.5-sonnet": "Claude 3.5 Sonnet (Rất tốt)"
}

# TTS Providers
TTS_PROVIDERS = {
    "fpt": "FPT.AI (Giọng Việt tốt nhất)",
    "elevenlabs": "ElevenLabs (Multilingual)",
    "openai": "OpenAI TTS (Dễ dùng)"
}

# FPT.AI Voices
FPT_VOICES = {
    "banmai": "Ban Mai (Nữ Bắc)",
    "leminh": "Lê Minh (Nam Bắc)",
    "thuminh": "Thu Minh (Nữ Bắc)",
    "giahuy": "Gia Huy (Nam Bắc)",
    "myan": "Mỹ An (Nữ Nam)",
    "lannhi": "Lan Nhi (Nữ Nam)",
    "linhsan": "Linh San (Nữ Trung)",
    "minhquang": "Minh Quang (Nam Trung)"
}

# ElevenLabs Voices (Vietnamese support)
ELEVENLABS_VOICES = {
    "21m00Tcm4TlvDq8ikWAM": "Rachel (Female)",
    "AZnzlk1XvdvUeBnXmlld": "Domi (Female)", 
    "EXAVITQu4vr4xnSDxMaL": "Bella (Female)",
    "ErXwobaYiN019PkySvjV": "Antoni (Male)",
    "MF3mGyEYCl7XYWbV9V6O": "Elli (Female)",
    "TxGEqnHWrfWFTfGW9XjX": "Josh (Male)"
}

# OpenAI TTS Voices
OPENAI_VOICES = {
    "alloy": "Alloy (Neutral)",
    "echo": "Echo (Male)",
    "fable": "Fable (British)",
    "onyx": "Onyx (Male Deep)",
    "nova": "Nova (Female)",
    "shimmer": "Shimmer (Female)"
}

# Default Values
DEFAULTS = {
    "whisper_model": "tiny",
    "translation_model": "meta-llama/llama-3.3-70b-instruct:free",
    "tts_provider": "fpt",
    "voice": "banmai",
    "speed": 1.0,
    "original_volume": 0.1,
    "dubbing_volume": 1.0
}

# Translation Prompt Template
TRANSLATION_PROMPT = """Bạn là dịch giả chuyên nghiệp. Dịch các câu sau từ tiếng Anh sang tiếng Việt tự nhiên, phù hợp với ngữ cảnh video.

Quy tắc:
1. Giữ nguyên ý nghĩa và cảm xúc của câu gốc
2. Dịch tự nhiên như người Việt nói, không dịch word-by-word
3. Giữ ngắn gọn để phù hợp với thời lượng
4. Giữ nguyên các tên riêng, thuật ngữ chuyên ngành

Trả về JSON array với format: [{"id": 1, "vietnamese": "bản dịch"}]

Các câu cần dịch:
{segments}
"""
