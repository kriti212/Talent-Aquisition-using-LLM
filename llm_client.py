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
        
    try:
        response = requests.post(config.API_URL, json=payload, timeout=60)
        response.raise_for_status()
        res_json = response.json()
        content = res_json.get("message", {}).get("content", "")
        return content
    except Exception as e:
        print(f"Error querying custom LLM API ({config.API_URL}): {str(e)}")
        raise e

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
