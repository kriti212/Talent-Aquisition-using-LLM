import requests
import json
import config

def query_llm(messages, temperature=0.2, json_mode=False, model_name=None):
    """
    Queries the custom Ollama API endpoint.
    If json_mode is True, it forces Ollama to return a JSON object.
    """
    model = model_name or config.LLM_MODEL
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature
        }
    }
    
    # Enforce deterministic greedy decoding parameters when temperature is 0.0
    if temperature == 0.0:
        payload["options"]["seed"] = 42
        payload["options"]["top_k"] = 1
        payload["options"]["top_p"] = 0.0
    
    # Ollama supports forcing JSON format output
    if json_mode:
        payload["format"] = "json"
        
    max_retries = 3
    retry_delay = 2
    for attempt in range(max_retries):
        try:
            response = requests.post(config.API_URL, json=payload, timeout=45)
            response.raise_for_status()
            res_json = response.json()
            content = res_json.get("message", {}).get("content", "")
            return content
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Error querying custom LLM API ({config.API_URL}) after {max_retries} attempts: {str(e)}")
                raise e
            print(f"LLM API query attempt {attempt + 1} failed: {str(e)}. Retrying in {retry_delay}s...")
            import time
            time.sleep(retry_delay)
            retry_delay *= 2

def get_available_models():
    """
    Queries the /api/tags endpoint of the Ollama server to fetch available models.
    """
    try:
        # Construct tags URL from the chat URL
        tags_url = config.API_URL.replace("/api/chat", "/api/tags")
        response = requests.get(tags_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = [item["name"] for item in data.get("models", [])]
            if models:
                return models
    except Exception as e:
        print(f"Could not fetch models from Ollama server, using fallbacks. Error: {str(e)}")
    
    # Standard fallback models if API is unreachable or fails
    return ["llama3:latest", "llama3", "mistral:latest", "gemma:latest", "phi3:latest"]
