"""OpenAI-compatible LLM client. Works with GPT-4o, Ollama, Groq, Together, etc."""

import os
import json
import time
from openai import OpenAI


class LLMClient:
    def __init__(self, base_url=None, api_key=None, model=None):
        self.base_url = base_url or os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
        self.api_key = api_key or os.environ.get('LLM_API_KEY', '')
        self.model = model or os.environ.get('LLM_MODEL', 'gpt-4o')

        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        self.call_count = 0
        self.total_tokens = 0

    def chat(self, system_prompt, user_prompt, temperature=0.7, max_tokens=4096):
        """Single-turn chat completion. Returns the response text."""
        self.call_count += 1

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        usage = response.usage
        if usage:
            self.total_tokens += usage.total_tokens

        return response.choices[0].message.content

    def chat_json(self, system_prompt, user_prompt, temperature=0.4, max_tokens=4096):
        """Chat completion that returns parsed JSON. Retries once on parse failure."""
        text = self.chat(system_prompt, user_prompt, temperature, max_tokens)

        # Strip markdown code fences if present
        text = text.strip()
        if text.startswith('```'):
            lines = text.split('\n')
            # Remove first and last lines (```json and ```)
            lines = [l for l in lines if not l.strip().startswith('```')]
            text = '\n'.join(lines)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Retry with stricter prompt
            retry_prompt = (
                f"Your previous response was not valid JSON. "
                f"Please respond with ONLY valid JSON, no markdown or explanation.\n\n"
                f"Original request:\n{user_prompt}"
            )
            text = self.chat(system_prompt, retry_prompt, temperature=0.2, max_tokens=max_tokens)
            text = text.strip()
            if text.startswith('```'):
                lines = text.split('\n')
                lines = [l for l in lines if not l.strip().startswith('```')]
                text = '\n'.join(lines)
            return json.loads(text)

    def extract_code(self, text):
        """Extract Python code from LLM response (handles markdown fences)."""
        text = text.strip()

        # Look for python code block
        if '```python' in text:
            start = text.index('```python') + len('```python')
            end = text.index('```', start)
            return text[start:end].strip()
        elif '```' in text:
            start = text.index('```') + 3
            # Skip language identifier on same line
            if text[start] != '\n':
                start = text.index('\n', start) + 1
            end = text.index('```', start)
            return text[start:end].strip()

        return text

    def get_stats(self):
        return {
            'calls': self.call_count,
            'total_tokens': self.total_tokens,
            'model': self.model,
        }
