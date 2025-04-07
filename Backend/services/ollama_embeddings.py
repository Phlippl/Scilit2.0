# Backend/services/ollama_embeddings.py
import requests
import numpy as np
import logging
import time
from typing import List, Optional
from chromadb.api.types import Documents, EmbeddingFunction

logger = logging.getLogger(__name__)

class OllamaEmbeddingFunction(EmbeddingFunction):
    """
    ChromaDB-compatible embedding function that uses Ollama API.
    Includes robust error handling, retries, and fallback mechanisms.
    """
    def __init__(
        self, 
        base_url: str = "http://localhost:11434", 
        model: str = "llama3",
        fallback_dimension: int = 3072,  # Updated default for Llama3
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 30.0
    ):
        self.base_url = base_url
        self.model = model
        self.fallback_dimension = fallback_dimension
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self._embedding_size = None  # Will be determined on first successful call
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self) -> None:
        """Test the connection to Ollama API and log the result."""
        try:
            logger.info(f"Testing connection to Ollama API at {self.base_url}")
            response = requests.get(
                f"{self.base_url}/api/version", 
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully connected to Ollama: {response.json()}")
            else:
                logger.warning(
                    f"Ollama API not responding correctly: Status {response.status_code}"
                )
        except Exception as e:
            logger.warning(f"Could not connect to Ollama API: {str(e)}")
    
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get embedding for a single text with retries.
        
        Args:
            text: The text to embed
            
        Returns:
            List of embedding values or None if all retries failed
        """
        # For long texts, truncate to avoid overwhelming the API
        truncated_text = text[:8000] if len(text) > 8000 else text
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": truncated_text},
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    embedding = response.json().get("embedding", [])
                    
                    # Store embedding size for future fallbacks
                    if embedding and self._embedding_size is None:
                        self._embedding_size = len(embedding)
                        logger.info(f"Detected embedding size: {self._embedding_size}")
                    
                    return embedding
                else:
                    logger.error(f"Ollama API error: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"Exception when calling Ollama API (attempt {attempt+1}): {str(e)}")
            
            # Wait before retry (except on last attempt)
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
        
        return None

    def __call__(self, texts: Documents) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of text documents to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        
        for text in texts:
            embedding = self._get_embedding(text)
            
            if embedding:
                embeddings.append(embedding)
            else:
                # Use fallback dimensions. Prioritize:
                # 1. Previously detected embedding size
                # 2. Configured fallback dimension
                dim = self._embedding_size or self.fallback_dimension
                logger.warning(f"Using zero fallback embedding with dimension {dim}")
                embeddings.append([0.0] * dim)
        
        return embeddings