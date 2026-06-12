"""
Azure OpenAI service — generates multiple-choice questions from lecture text.

Reads config from environment:
  AZURE_OPENAI_KEY
  AZURE_OPENAI_ENDPOINT
  AZURE_OPENAI_DEPLOYMENT      (e.g. gpt-4.1)
  AZURE_OPENAI_API_VERSION     (e.g. 2025-01-01-preview)

The service is OPTIONAL: if the package or config is missing, it stays
disabled and callers receive an empty result instead of crashing.
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional

try:
    from openai import AsyncAzureOpenAI
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False
    print("⚠️ openai package not installed — AI question generation disabled.")


# Map the AI's difficulty rating to your engagement clusters.
DIFFICULTY_TO_CLUSTER = {
    "easy": "passive",      # struggling / low-engagement students
    "medium": "moderate",   # average students
    "hard": "active",       # advanced / highly-engaged students
}


class AzureOpenAIService:
    def __init__(self):
        self.api_key = os.getenv("AZURE_OPENAI_KEY", "")
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
        self.enabled = bool(_OPENAI_AVAILABLE and self.api_key and self.endpoint)

        self._client: Optional["AsyncAzureOpenAI"] = None
        if self.enabled:
            try:
                self._client = AsyncAzureOpenAI(
                    api_key=self.api_key,
                    azure_endpoint=self.endpoint,
                    api_version=self.api_version,
                )
                print(f"✅ Azure OpenAI service initialized (deployment={self.deployment})")
            except Exception as e:
                self.enabled = False
                print(f"⚠️ Azure OpenAI init failed: {e}")
        else:
            print("⚠️ Azure OpenAI not configured — AI question generation disabled.")

    def is_enabled(self) -> bool:
        return self.enabled and self._client is not None

    async def generate_questions_for_slide(
        self,
        slide_text: str,
        slide_number: int,
        count: int = 1,
        topic: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Generate `count` MCQ questions from one slide's text.
        Returns a list of dicts (may be empty if the slide is too thin or on error):
          {
            "question": str,
            "options": [str, str, str, str],
            "correctAnswer": int,        # 0-based index
            "difficulty": "easy"|"medium"|"hard",
            "explanation": str
          }
        """
        if not self.is_enabled():
            return []

        # Skip slides with almost no usable content.
        cleaned = (slide_text or "").strip()
        if len(cleaned) < 25:
            return []

        system_prompt = (
            "You are an expert exam author. You create clear, factual "
            "multiple-choice questions strictly from the provided lecture "
            "content. Never invent facts that are not supported by the text."
        )

        user_prompt = f"""Create exactly {count} multiple-choice question(s) based ONLY on the
lecture content below.

Rules for every question:
- Exactly 4 options.
- Exactly one correct option.
- "correctAnswer" is the 0-based index of the correct option.
- Rate "difficulty" as "easy", "medium", or "hard".
- Keep the question self-contained and unambiguous.
- If the content cannot support a good question, return an empty "questions" array.

Topic (optional context): {topic or "N/A"}

Lecture content:
\"\"\"
{cleaned[:4000]}
\"\"\"

Return STRICT JSON in exactly this shape:
{{
  "questions": [
    {{
      "question": "string",
      "options": ["string", "string", "string", "string"],
      "correctAnswer": 0,
      "difficulty": "easy",
      "explanation": "short reason the answer is correct"
    }}
  ]
}}"""

        try:
            resp = await self._client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content or "{}"
            data = json.loads(raw)
            questions = data.get("questions", [])
            return [
                self._normalize(q, slide_number)
                for q in questions
                if self._is_valid(q)
            ]
        except Exception as e:
            print(f"⚠️ Azure OpenAI generation failed for slide {slide_number}: {e}")
            return []

    @staticmethod
    def _is_valid(q: Dict[str, Any]) -> bool:
        opts = q.get("options")
        return (
            isinstance(q.get("question"), str)
            and isinstance(opts, list)
            and len(opts) == 4
            and isinstance(q.get("correctAnswer"), int)
            and 0 <= q["correctAnswer"] < 4
        )

    @staticmethod
    def _normalize(q: Dict[str, Any], slide_number: int) -> Dict[str, Any]:
        difficulty = str(q.get("difficulty", "medium")).lower()
        if difficulty not in DIFFICULTY_TO_CLUSTER:
            difficulty = "medium"
        return {
            "question": str(q["question"]).strip(),
            "options": [str(o).strip() for o in q["options"]],
            "correctAnswer": int(q["correctAnswer"]),
            "difficulty": difficulty,
            "suggestedCluster": DIFFICULTY_TO_CLUSTER[difficulty],
            "explanation": str(q.get("explanation", "")).strip(),
            "sourceSlide": slide_number,
        }


# Singleton instance
azure_openai_service = AzureOpenAIService()
