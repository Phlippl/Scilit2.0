# Backend/services/ollama_embeddings.py
import requests
import numpy as np
import logging
from chromadb.api.types import Documents, EmbeddingFunction

logger = logging.getLogger(__name__)

class OllamaEmbeddingFunction(EmbeddingFunction):
    def __init__(self, base_url="http://localhost:11434", model="llama3"):
        self.base_url = base_url
        self.model = model
        # Test connection
        try:
            logger.info(f"Testing connection to Ollama API at {self.base_url}")
            response = requests.get(f"{self.base_url}/api/version")
            if response.status_code == 200:
                logger.info(f"Successfully connected to Ollama: {response.json()}")
            else:
                logger.warning(f"Ollama API not responding correctly: {response.status_code}")
        except Exception as e:
            logger.warning(f"Could not connect to Ollama API: {e}")

    def __call__(self, texts: Documents) -> list:
        embeddings = []
        for text in texts:
            try:
                # For long texts, truncate to avoid overwhelming the API
                truncated_text = text[:8000] if len(text) > 8000 else text
                
                response = requests.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": truncated_text}
                )
                
                if response.status_code == 200:
                    embedding = response.json().get("embedding", [])
                    embeddings.append(embedding)
                else:
                    # Fallback to zeros if API fails
                    logger.error(f"Error getting embedding from Ollama: {response.text}")
                    embeddings.append([0.0] * 4096)  # Typical embedding size for Llama models
            except Exception as e:
                logger.error(f"Exception when calling Ollama API: {e}")
                embeddings.append([0.0] * 4096)
        
        return embeddings