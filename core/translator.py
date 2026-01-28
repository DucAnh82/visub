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
        raise ValueError("Vui lòng nhập OpenRouter API Key trong Sidebar!")
    
    # Chia thành batches
    batches = [segments[i:i + batch_size] for i in range(0, len(segments), batch_size)]
    
    for batch in batches:
        try:
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
                    
                    if not translations:
                        # Nếu parse không được gì, fallback
                        raise ValueError("Không thể parse response từ AI")
                    
                    for seg in batch:
                        seg_id = seg["id"]
                        # Thử nhiều cách match id
                        if seg_id in translations:
                            seg["vietnamese"] = translations[seg_id]
                        elif str(seg_id) in translations:
                            seg["vietnamese"] = translations[str(seg_id)]
                        else:
                            # Fallback nếu không tìm thấy
                            if not seg.get("vietnamese"):
                                seg["vietnamese"] = seg["text"]
                                
                except Exception as parse_error:
                    print(f"Error parsing translation: {parse_error}")
                    print(f"Raw response: {response[:500] if response else 'None'}")
                    # Fallback: giữ nguyên text gốc
                    for seg in batch:
                        if not seg.get("vietnamese"):
                            seg["vietnamese"] = seg["text"]
            else:
                # Nếu API không trả về gì, fallback
                for seg in batch:
                    if not seg.get("vietnamese"):
                        seg["vietnamese"] = seg["text"]
                        
        except Exception as batch_error:
            print(f"Error processing batch: {batch_error}")
            # Fallback cho cả batch
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
    import re
    
    # Tìm JSON trong response
    # LLM có thể trả về với text bổ sung
    
    # Thử tìm trong code block trước
    if '```json' in response:
        match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
        if match:
            response = match.group(1)
    elif '```' in response:
        match = re.search(r'```\s*([\s\S]*?)\s*```', response)
        if match:
            response = match.group(1)
    else:
        # Tìm JSON array
        start = response.find('[')
        end = response.rfind(']') + 1
        if start != -1 and end > 0:
            response = response[start:end]
    
    try:
        translations = json.loads(response.strip())
    except json.JSONDecodeError:
        # Thử sửa JSON bị lỗi
        response = response.strip()
        if not response.startswith('['):
            response = '[' + response
        if not response.endswith(']'):
            response = response + ']'
        translations = json.loads(response)
    
    result = {}
    for item in translations:
        # Hỗ trợ nhiều format: id có thể là int hoặc string
        item_id = item.get("id") or item.get("ID") or item.get("Id")
        vietnamese = item.get("vietnamese") or item.get("Vietnamese") or item.get("vi") or item.get("translation")
        
        if item_id is not None and vietnamese:
            # Chuyển id sang int nếu có thể
            try:
                item_id = int(item_id)
            except (ValueError, TypeError):
                pass
            result[item_id] = vietnamese
    
    return result


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
        "openai/gpt-oss-120b:free": 0.0,  # Free model
        "google/gemini-2.0-flash-exp": 0.0,  # Free tier
        "deepseek/deepseek-chat": 0.14,
        "openai/gpt-4o-mini": 0.15,
        "openai/gpt-4o": 2.50,
        "anthropic/claude-3.5-sonnet": 3.00
    }
    
    rate = pricing.get(model, 1.0)
    cost = (estimated_tokens / 1_000_000) * rate
    
    return round(cost, 4)
