import json
import logging
import os
from typing import Dict, List

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class LLMProcessor:
    def __init__(self, model: str = "gemini-2.0-flash"):
        self.model = model
        api_key = os.getenv("API_KEY")
        if not api_key:
            logger.error("API_KEY env var is not set – LLM calls will fail")
        self.client = genai.Client(api_key=api_key)

    def prompt_builder(self, document_type: str, fields: List[str], hints: Dict, text: str) -> str:
        field_list = "\n".join([f"- {f}" for f in fields])

        return f"""
        You are extracting structured data from a {document_type}.
        Extract ONLY the requested fields.
        Return ONLY valid JSON.
        If a field is missing, return null.
        FIELDS TO EXTRACT:
        {field_list}
        CANDIDATE ENTITIES:
        {json.dumps(hints, indent=2)}
        DOCUMENT TEXT:
        {text}
        """

    def call_model(self, prompt: str) -> str:
        logger.info("LLM call_model: sending request to %s", self.model)
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                top_p=1.0,
                top_k=40,
                max_output_tokens=1024,
                response_mime_type="application/json",
            ),
        )
        logger.info("LLM call_model: received response (%s chars)", len(response.text) if response.text else 0)
        return response.text

    def parse_json(self, text: str) -> Dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            cleaned = (
                text.strip()
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )
            return json.loads(cleaned)    

    def extract(
        self,
        document_type: str,
        fields: List[str],
        text: str,
        hints: Dict,
    ) -> Dict:
        prompt = self.prompt_builder(
            document_type=document_type,
            fields=fields,
            text=text,
            hints=hints,
        )

        raw_response = self.call_model(prompt)
        parsed = self.parse_json(raw_response)

        # LLM may return a single object or a list of objects (e.g. multiple totals/rows)
        if isinstance(parsed, list):
            return parsed
        # single object: ensure requested fields exist
        return {field: parsed.get(field) for field in fields}