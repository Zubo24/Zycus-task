# LLM Client wrapper

import os
import json
import requests
from typing import Type, TypeVar
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

load_dotenv()

T = TypeVar('T', bound=BaseModel)

class LLMParseError(Exception):
    def __init__(self, message: str, raw_response: str):
        super().__init__(message)
        self.raw_response = raw_response

def _call_anthropic(system_prompt: str, user_prompt: str) -> str:
    import anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is missing. Please set it in .env to use the Anthropic provider.")
    
    model = os.getenv("LLM_MODEL", "claude-3-haiku-20240307")
    print(f"[LLM] Provider: anthropic | Model: {model}")
    
    client = anthropic.Anthropic(api_key=api_key)
    
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        temperature=0.0,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )
    return response.content[0].text

def _call_ollama(system_prompt: str, user_prompt: str) -> str:
    model = os.getenv("OLLAMA_MODEL", "gemma3:1b")
    print(f"[LLM] Provider: ollama | Model: {model}")
    
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.0
        }
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()["message"]["content"]
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Ollama API request failed: {e}")

def _parse_and_validate(raw_text: str, response_model: Type[T]) -> T:
    """Extract JSON from raw text and validate with Pydantic."""
    text = raw_text.strip()
    
    # Strip markdown code blocks if the LLM added them
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    data = json.loads(text)
    return response_model.model_validate(data)

def call_structured(system_prompt: str, user_prompt: str, response_model: Type[T]) -> T:
    """
    Public interface to call the configured LLM and return a strongly-typed Pydantic object.
    Automatically handles JSON prompting, parsing, and a single validation retry.
    """
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    
    def _build_simple_schema(model: Type[BaseModel]) -> dict:
        schema = {}
        for name, field in model.model_fields.items():
            from typing import get_args, get_origin
            import inspect
            
            origin = get_origin(field.annotation)
            args = get_args(field.annotation)
            
            if origin is list and args and inspect.isclass(args[0]) and issubclass(args[0], BaseModel):
                schema[name] = [_build_simple_schema(args[0])]
            elif inspect.isclass(field.annotation) and issubclass(field.annotation, BaseModel):
                schema[name] = _build_simple_schema(field.annotation)
            else:
                schema[name] = field.description or str(field.annotation)
        return schema
        
    # Inject a simplified schema representation for tiny models
    simple_schema = _build_simple_schema(response_model)
    schema_json = json.dumps(simple_schema, indent=2)
    
    sys_prompt = (
        f"{system_prompt}\n\n"
        "You must return ONLY a valid JSON object. "
        "Use exactly the JSON structure and keys shown below, and fill in the appropriate values:\n"
        f"{schema_json}"
    )
    
    def attempt_call(sys_p: str, user_p: str) -> str:
        if provider == "ollama":
            return _call_ollama(sys_p, user_p)
        else:
            return _call_anthropic(sys_p, user_p)

    raw_response = attempt_call(sys_prompt, user_prompt)
    print(f"\n[DEBUG] RAW First Attempt Response:\n{raw_response.encode('ascii', 'ignore').decode('ascii')}\n")
    
    try:
        res = _parse_and_validate(raw_response, response_model)
        print("[DEBUG] First Attempt Parse: SUCCESS\n")
        return res
    except (json.JSONDecodeError, ValidationError) as e:
        print(f"[DEBUG] First Attempt Parse: FAILED. Exception:\n{e}\n")
        print(f"[LLM] Parse/Validation failed on first attempt. Retrying once...")
        
        # Retry with an explicit correction prompt
        retry_sys = (
            "You must return valid JSON only, no other text. "
            f"It MUST strictly use these keys and contain the correct values:\n{schema_json}"
        )
        retry_user = (
            f"Your previous response failed validation:\n{str(e)}\n\n"
            f"Original prompt:\n{user_prompt}\n\n"
            "Return ONLY the raw JSON object."
        )
        
        raw_response_retry = attempt_call(retry_sys, retry_user)
        print(f"\n[DEBUG] RAW Retry Attempt Response:\n{raw_response_retry.encode('ascii', 'ignore').decode('ascii')}\n")
        
        try:
            res_retry = _parse_and_validate(raw_response_retry, response_model)
            print("[DEBUG] Retry Attempt Parse: SUCCESS\n")
            return res_retry
        except Exception as e2:
            print(f"[DEBUG] Retry Attempt Parse: FAILED. Exception:\n{e2}\n")
            raise LLMParseError(f"Failed to parse LLM output after retry: {e2}", raw_response)

def call_text(system_prompt: str, user_prompt: str) -> str:
    """Same as call_structured but returns raw text without JSON parsing."""
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    
    def attempt_call(sys_p, user_p):
        if provider == "ollama":
            return _call_ollama(sys_p, user_p)
        else:
            return _call_anthropic(sys_p, user_p)
            
    return attempt_call(system_prompt, user_prompt)

if __name__ == "__main__":
    # Optional quick local test (if OLLAMA is running)
    print("--- Sanity Check llm_client ---")
    class TestModel(BaseModel):
        answer: str
        confidence: float
        
    try:
        res = call_structured("You are a helpful assistant.", "What is 2+2? Answer with high confidence.", TestModel)
        print(f"Success! Output: {res}")
    except Exception as ex:
        print(f"Failed (expected if no API key / Ollama not running): {ex}")
