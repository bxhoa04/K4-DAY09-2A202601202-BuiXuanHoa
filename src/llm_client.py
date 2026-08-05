"""
src/llm_client.py
Client gửi prompt tới Ollama server local.
"""

import json
import urllib.request
from src.config import OLLAMA_MODEL_NAME, OLLAMA_BASE_URL


class LocalLLMClient:
    def __init__(self, model_name: str = OLLAMA_MODEL_NAME, base_url: str = OLLAMA_BASE_URL):
        self.model_name = model_name
        self.api_url = f"{base_url}/api/generate"

    def generate_response(self, prompt: str, system_prompt: str = "") -> str:
        """Gửi prompt tới Ollama local và nhận văn bản trả về."""
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.0  # Đặt bằng 0 để kết quả ra nhất quán, chính xác
            }
        }
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.api_url, 
            data=data, 
            headers={"Content-Type": "application/json"}
        )
        
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("response", "").strip()
        except Exception as e:
            print(f"⚠️ Lỗi kết nối Ollama: {e}")
            return ""