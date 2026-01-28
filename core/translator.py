"""
VietDub Solo - Translator Module
Sử dụng OpenRouter API để dịch text sang tiếng Việt
"""

import requests
import json
from typing import List, Dict, Optional
from config import TRANSLATION_PROMPT


OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


def translate_segments(
    segments: List[Dict],
    api_key: str,
    model: str = "google/gemini-2.0-flash-exp",
    batch_size: int = 20
) -> List[Dict]:
    """
    Dịch các segments sang tiếng Việt
    
    Args:
        segments: List segments với text tiếng Anh
        api_key: OpenRouter API key
        model: Model để dịch
        batch_size: Số câu dịch mỗi batch
    
    Returns:
        Segments với trường 'vietnamese' đã được điền
    """
    if not api_key:
        raise ValueError("OpenRouter API key is required")
    
    # Chia thành batches
    batches = [segments[i:i + batch_size] for i in range(0, len(segments), batch_size)]
    
    for batch in batches:
        # Chuẩn bị text để dịch
        text_to_translate = json.dumps([
            {"id": seg["id"], "english": seg["text"]}
            for seg in batch
        ], ensure_ascii=False, indent=2)
        
        prompt = TRANSLATION_PROMPT.format(segments=text_to_translate)
        
        # Gọi API
        response = call_openrouter(api_key, model, prompt)
        
        if response:
            # Parse response và cập nhật segments
            try:
                translations = parse_translation_response(response)
                for seg in batch:
                    if seg["id"] in translations:
                        seg["vietnamese"] = translations[seg["id"]]
            except Exception as e:
                print(f"Error parsing translation: {e}")
                # Fallback: giữ nguyên text gốc
                for seg in batch:
                    if not seg.get("vietnamese"):
                        seg["vietnamese"] = seg["text"]
    
    return segments


def call_openrouter(
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int = 4096
) -> Optional[str]:
    """
    Gọi OpenRouter API
    
    Args:
        api_key: API key
        model: Model ID
        prompt: Prompt text
        max_tokens: Max tokens trong response
    
    Returns:
        Response text hoặc None nếu lỗi
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://vietdub-solo.local",
        "X-Title": "VietDub Solo"
    }
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Bạn là translator chuyên nghiệp Anh-Việt. Luôn trả về JSON hợp lệ."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3  # Low temperature để dịch chính xác
    }
    
    try:
        response = requests.post(
            OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        
        data = response.json()
        return data["choices"][0]["message"]["content"]
        
    except requests.exceptions.RequestException as e:
        print(f"OpenRouter API error: {e}")
        return None


def parse_translation_response(response: str) -> Dict[int, str]:
    """
    Parse JSON response từ LLM
    
    Args:
        response: Raw response string
    
    Returns:
        Dict mapping id -> vietnamese text
    """
    # Tìm JSON trong response
    # LLM có thể trả về với text bổ sung
    start = response.find('[')
    end = response.rfind(']') + 1
    
    if start == -1 or end == 0:
        # Thử tìm trong code block
        if '```json' in response:
            start = response.find('```json') + 7
            end = response.find('```', start)
            response = response[start:end]
        elif '```' in response:
            start = response.find('```') + 3
            end = response.find('```', start)
            response = response[start:end]
    else:
        response = response[start:end]
    
    translations = json.loads(response)
    
    return {
        item["id"]: item["vietnamese"]
        for item in translations
    }


def translate_single(
    text: str,
    api_key: str,
    model: str = "google/gemini-2.0-flash-exp"
) -> str:
    """
    Dịch một câu đơn lẻ
    
    Args:
        text: Text tiếng Anh
        api_key: API key
        model: Model ID
    
    Returns:
        Text tiếng Việt
    """
    prompt = f"Dịch câu sau sang tiếng Việt tự nhiên, chỉ trả về bản dịch:\n\n{text}"
    
    response = call_openrouter(api_key, model, prompt, max_tokens=500)
    
    return response.strip() if response else text


def estimate_cost(segments: List[Dict], model: str) -> float:
    """
    Ước tính chi phí dịch thuật
    
    Args:
        segments: List segments
        model: Model ID
    
    Returns:
        Chi phí ước tính (USD)
    """
    # Đếm tokens (ước tính rough: 1 word ≈ 1.3 tokens)
    total_words = sum(len(seg["text"].split()) for seg in segments)
    estimated_tokens = int(total_words * 1.3 * 2)  # x2 for input + output
    
    # Pricing (approximate, per 1M tokens)
    pricing = {
        "google/gemini-2.0-flash-exp": 0.0,  # Free tier
        "deepseek/deepseek-chat": 0.14,
        "openai/gpt-4o-mini": 0.15,
        "openai/gpt-4o": 2.50,
        "anthropic/claude-3.5-sonnet": 3.00
    }
    
    rate = pricing.get(model, 1.0)
    cost = (estimated_tokens / 1_000_000) * rate
    
    return round(cost, 4)
