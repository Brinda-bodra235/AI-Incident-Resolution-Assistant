import json
import openai
from typing import List, Tuple
from app.config import settings
from app.prompts.root_cause_prompt import ROOT_CAUSE_PROMPT
from app.prompts.solution_prompt import SOLUTION_PROMPT

class LLMAgent:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        if self.provider == "openai":
            self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        elif self.provider == "gemini":
            from google import genai
            self.genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def _call_llm(self, prompt: str) -> str:
        if self.provider == "openai":
            if not settings.OPENAI_API_KEY:
                # Mock response for testing
                return json.dumps({
                    "root_cause": "Mock root cause due to missing API key.",
                    "confidence_score": 0.90,
                    "steps": ["Mock step 1", "Mock step 2"]
                })
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content
        elif self.provider == "gemini":
            if not settings.GEMINI_API_KEY:
                # Mock response for testing
                return json.dumps({
                    "root_cause": "Mock root cause due to missing API key.",
                    "confidence_score": 0.90,
                    "steps": ["Mock step 1", "Mock step 2"]
                })
            from google.genai import types as genai_types
            response = self.genai_client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            return response.text
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def analyze_root_cause(self, parsed_summary: str, similar_incidents: List[dict]) -> Tuple[str, float]:
        past_incidents_str = ""
        if not similar_incidents:
            past_incidents_str = "No similar resolved incidents found."
        for idx, inc in enumerate(similar_incidents):
            past_incidents_str += f"\nIncident {idx+1}:\n"
            past_incidents_str += f"- Root Cause: {inc.get('root_cause', 'Unknown')}\n"
            past_incidents_str += f"- Tags: {', '.join(inc.get('tags', []))}\n"

        prompt = ROOT_CAUSE_PROMPT.format(
            parsed_summary=parsed_summary,
            past_incidents=past_incidents_str
        )
        
        response_text = self._call_llm(prompt)
        try:
            data = json.loads(response_text)
            root_cause = data.get("root_cause", "Unable to determine root cause.")
            confidence_score = float(data.get("confidence_score", 0.5))
            return root_cause, confidence_score
        except Exception as e:
            print(f"Error parsing Root Cause LLM response: {e}")
            return f"Raw Response: {response_text}", 0.5

    def generate_solution(self, root_cause: str, past_resolutions: List[List[str]]) -> List[str]:
        past_resolutions_str = ""
        if not past_resolutions:
            past_resolutions_str = "No past resolutions found."
        for idx, res in enumerate(past_resolutions):
            steps_formatted = "\n".join(f"  {i+1}. {step}" for i, step in enumerate(res))
            past_resolutions_str += f"\nResolution {idx+1}:\n{steps_formatted}\n"

        prompt = SOLUTION_PROMPT.format(
            root_cause=root_cause,
            past_resolutions=past_resolutions_str
        )
        
        response_text = self._call_llm(prompt)
        try:
            data = json.loads(response_text)
            return data.get("steps", ["Standard check of configuration", "Check services dependency status"])
        except Exception as e:
            print(f"Error parsing Solution LLM response: {e}")
            return ["Review application logs manually.", "Verify database connections.", "Check service status."]
