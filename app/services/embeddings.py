import openai
from app.config import settings
from typing import List

class EmbeddingService:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        if self.provider == "openai":
            self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        elif self.provider == "gemini":
            from google import genai
            self.genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def get_embedding(self, text: str) -> List[float]:
        text = text.replace("\n", " ")
        if self.provider == "openai":
            if not settings.OPENAI_API_KEY:
                return [0.1] * 1536
            response = self.client.embeddings.create(
                input=[text],
                model=settings.OPENAI_EMBEDDING_MODEL
            )
            return response.data[0].embedding
        elif self.provider == "gemini":
            if not settings.GEMINI_API_KEY:
                return [0.1] * 768
            from google import genai
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            response = client.models.embed_content(
                model=settings.GEMINI_EMBEDDING_MODEL,
                contents=text,
            )
            return response.embeddings[0].values
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

