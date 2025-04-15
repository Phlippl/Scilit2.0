# Backend/api/query.py
"""
Blueprint for Query API endpoints with improved performance and reliability
"""
import os
import json
import logging
import uuid
import time
import functools
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app, Response, stream_with_context
import requests
import re
from typing import Dict, List, Any, Optional, Union, Callable

# Import services
from Backend.services.vector_db import search_documents
from Backend.services.citation_service import format_citation

logger = logging.getLogger(__name__)

# Create Blueprint for Query API
query_bp = Blueprint('query', __name__, url_prefix='/api/query')

# Configuration for LLM integration
LLM_API_URL = os.environ.get('LLM_API_URL', 'https://api.openai.com/v1/chat/completions')
LLM_API_KEY = os.environ.get('LLM_API_KEY', '')
LLM_MODEL = os.environ.get('LLM_MODEL', 'gpt-3.5-turbo')
LLM_TIMEOUT = int(os.environ.get('LLM_TIMEOUT', 60))  # Timeout in seconds

# Supported citation styles
CITATION_STYLES = [
    {"id": "apa", "name": "APA 7th Edition"},
    {"id": "chicago", "name": "Chicago 18th Edition"},
    {"id": "harvard", "name": "Harvard"}
]

# Simple in-memory query cache (in a real app, use Redis)
query_cache = {}
CACHE_TTL = 60 * 60  # 1 hour cache TTL


def cache_results(func):
    """
    Decorator for caching query results
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Get request data
        if request.method == 'POST':
            data = request.get_json()
            user_id = request.headers.get('X-User-ID', 'default_user')
            
            # Create cache key
            cache_key = f"{user_id}:{json.dumps(data, sort_keys=True)}"
            
            # Check cache
            if cache_key in query_cache:
                cached_item = query_cache[cache_key]
                # Check if cache is still valid
                if time.time() - cached_item['timestamp'] < CACHE_TTL:
                    logger.info(f"Using cached result for query: {data.get('query', '')[:50]}...")
                    return cached_item['result']
            
            # Call the original function
            result = func(*args, **kwargs)
            
            # Cache the result
            query_cache[cache_key] = {
                'result': result,
                'timestamp': time.time()
            }
            
            # Clean cache if too large (keep most recent 100 items)
            if len(query_cache) > 100:
                # Sort by timestamp and keep newest 100
                sorted_cache = sorted(
                    query_cache.items(), 
                    key=lambda x: x[1]['timestamp'],
                    reverse=True
                )
                
                query_cache.clear()
                for k, v in sorted_cache[:100]:
                    query_cache[k] = v
            
            return result
        else:
            # For non-POST requests, don't cache
            return func(*args, **kwargs)
    
    return wrapper


@query_bp.route('', methods=['POST'])
@cache_results
def query_documents_api():
    """
    Query documents and use LLM for answers with streaming support
    """
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        
        # Check required parameters
        if 'query' not in data or not data['query'].strip():
            return jsonify({"error": "Query text is required"}), 400
        
        # Extract parameters
        query_text = data['query'].strip()
        citation_style = data.get('citation_style', 'apa')
        document_ids = data.get('document_ids', None)
        n_results = int(data.get('n_results', 5))
        use_direct_quotes = data.get('use_direct_quotes', True)
        include_page_numbers = data.get('include_page_numbers', True)
        streaming = data.get('streaming', False)  # New parameter for streaming responses
        
        # TODO: User authentication
        user_id = request.headers.get('X-User-ID', 'default_user')
        
        # Filters for documents
        filters = {}
        if document_ids:
            filters['document_ids'] = document_ids
        
        # Search for relevant documents
        start_time = time.time()
        search_results = search_documents(
            query=query_text,
            user_id=user_id,
            filters=filters,
            n_results=n_results * 2,  # Get more results for better LLM context
            include_metadata=True
        )
        
        search_time = time.time() - start_time
        logger.info(f"Search completed in {search_time:.2f}s")
        
        if not search_results or len(search_results) == 0:
            return jsonify({
                "results": [],
                "bibliography": [],
                "query": query_text,
                "search_time": search_time
            })
        
        # Format results with citation style and page numbers
        formatted_results = []
        bibliography_entries = []
        documents_for_bibliography = {}
        
        for result in search_results:
            # Extract metadata
            metadata = result.get('metadata', {})
            document_id = metadata.get('document_id')
            
            # Create citation for this result
            formatted_results.append({
                "text": result.get('text', ''),
                "source": result.get('source', ''),
                "metadata": metadata,
                "document_id": document_id
            })
            
            # For each unique document, create a full citation
            if document_id not in documents_for_bibliography:
                documents_for_bibliography[document_id] = metadata
        
        # Create bibliography
        for doc_metadata in documents_for_bibliography.values():
            citation = format_citation(doc_metadata, citation_style)
            if citation and citation not in bibliography_entries:
                bibliography_entries.append(citation)
        
        # If LLM key is available, generate LLM response
        llm_results = None
        if LLM_API_KEY:
            if streaming:
                # Return a streaming response
                def generate_streaming_response():
                    yield json.dumps({
                        "type": "search_results",
                        "data": {
                            "search_time": search_time,
                            "result_count": len(search_results)
                        }
                    }) + '\n'
                    
                    # Stream LLM response
                    for chunk in stream_llm_response(
                        query_text=query_text,
                        search_results=formatted_results[:n_results],
                        citation_style=citation_style,
                        use_direct_quotes=use_direct_quotes,
                        include_page_numbers=include_page_numbers
                    ):
                        yield json.dumps({
                            "type": "llm_chunk",
                            "data": chunk
                        }) + '\n'
                    
                    # Send bibliography at the end
                    yield json.dumps({
                        "type": "bibliography",
                        "data": bibliography_entries
                    }) + '\n'
                
                return Response(
                    stream_with_context(generate_streaming_response()),
                    content_type='application/x-ndjson'
                )
            else:
                # Generate standard LLM response
                llm_start_time = time.time()
                llm_results = generate_llm_response(
                    query_text=query_text,
                    search_results=formatted_results[:n_results],
                    citation_style=citation_style,
                    use_direct_quotes=use_direct_quotes,
                    include_page_numbers=include_page_numbers
                )
                llm_time = time.time() - llm_start_time
                logger.info(f"LLM response generated in {llm_time:.2f}s")
                
                # If LLM response was successful, use it
                if llm_results:
                    return jsonify({
                        "results": llm_results,
                        "bibliography": bibliography_entries,
                        "query": query_text,
                        "search_time": search_time,
                        "llm_time": llm_time
                    })
        
        # Standard response without LLM or as fallback
        # Limited to the requested number of results
        return jsonify({
            "results": formatted_results[:n_results],
            "bibliography": bibliography_entries,
            "query": query_text,
            "search_time": search_time
        })
    
    except Exception as e:
        logger.error(f"Error querying documents: {e}")
        return jsonify({"error": f"Failed to query documents: {str(e)}"}), 500


def generate_llm_response(
    query_text: str, 
    search_results: List[Dict[str, Any]], 
    citation_style: str = 'apa', 
    use_direct_quotes: bool = True,
    include_page_numbers: bool = True
) -> Optional[List[Dict[str, Any]]]:
    """
    Use LLM for answer generation with citations
    
    Args:
        query_text: Query text
        search_results: Search results from vector database
        citation_style: Citation style
        use_direct_quotes: Use direct quotes
        include_page_numbers: Include page numbers
    
    Returns:
        list: LLM response with results and citations
    """
    try:
        # If no API key or URL, return a simulated response
        if not LLM_API_KEY or LLM_API_URL == '':
            logger.warning("No LLM API configuration, using search results directly")
            return search_results
        
        # Prepare context for the LLM
        context_items = []
        
        for i, result in enumerate(search_results):
            context_items.append(f"Information #{i+1}: {result['text']}")
            context_items.append(f"Citation #{i+1}: {result['source']}")
        
        context = "\n".join(context_items)
        
        # Instructions for citation style and direct quotes
        citation_instructions = f"Use {citation_style.upper()} citation style."
        if not use_direct_quotes:
            citation_instructions += " Avoid direct quotes, paraphrase the information instead."
        if include_page_numbers:
            citation_instructions += " Include page numbers in citations when available."
        
        # System prompt for the LLM
        system_prompt = f"""
        You are an academic assistant that helps researchers with literature queries.
        Answer the question based ONLY on the provided information.
        For each piece of information you use, include the citation in the format provided.
        {citation_instructions}
        Do not make up or infer information that is not explicitly stated in the provided context.
        Format your answer as a coherent paragraph or structured response.
        """
        
        # User prompt with context
        user_prompt = f"""
        Question: {query_text}
        
        Use ONLY the following information to answer the question:
        
        {context}
        """
        
        # LLM request with timeout
        response = requests.post(
            LLM_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {LLM_API_KEY}"
            },
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,  # Low temperature for more precise answers
                "max_tokens": 1000
            },
            timeout=LLM_TIMEOUT
        )
        
        # Process response
        if response.status_code == 200:
            llm_data = response.json()
            llm_text = llm_data['choices'][0]['message']['content']
            
            # Split LLM response into paragraphs
            paragraphs = re.split(r'\n\s*\n', llm_text)
            
            # Create structured results
            structured_results = []
            
            for paragraph in paragraphs:
                if not paragraph.strip():
                    continue
                
                # Look for citations (pattern: Text (Author, Year, p. X))
                citation_matches = list(re.finditer(r'\((?:[^()]+,\s*)?[^()]+(?:,\s*S\.\s*\d+)?\)', paragraph))
                
                if citation_matches:
                    # Split text and citation
                    last_match = citation_matches[-1]
                    text = paragraph[:last_match.start()].strip()
                    source = last_match.group(0)
                    
                    structured_results.append({
                        "text": text,
                        "source": source
                    })
                else:
                    # If no citation found, use the whole paragraph
                    structured_results.append({
                        "text": paragraph,
                        "source": ""
                    })
            
            return structured_results
        else:
            logger.error(f"LLM API error: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error("LLM request timed out")
        return None
    except Exception as e:
        logger.error(f"Error generating LLM response: {e}")
        return None


def stream_llm_response(
    query_text: str, 
    search_results: List[Dict[str, Any]], 
    citation_style: str = 'apa', 
    use_direct_quotes: bool = True,
    include_page_numbers: bool = True
):
    """
    Stream LLM response chunks for faster perceived response time
    
    Args:
        query_text: Query text
        search_results: Search results from vector database
        citation_style: Citation style
        use_direct_quotes: Use direct quotes
        include_page_numbers: Include page numbers
    
    Yields:
        dict: Chunks of LLM response
    """
    try:
        # If no API key or URL, return a simulated response
        if not LLM_API_KEY or LLM_API_URL == '':
            logger.warning("No LLM API configuration, using search results directly")
            for result in search_results:
                yield {
                    "text": result['text'],
                    "source": result['source'],
                    "complete": False
                }
            yield {"complete": True}
            return
        
        # Prepare context for the LLM
        context_items = []
        
        for i, result in enumerate(search_results):
            context_items.append(f"Information #{i+1}: {result['text']}")
            context_items.append(f"Citation #{i+1}: {result['source']}")
        
        context = "\n".join(context_items)
        
        # Instructions for citation style and direct quotes
        citation_instructions = f"Use {citation_style.upper()} citation style."
        if not use_direct_quotes:
            citation_instructions += " Avoid direct quotes, paraphrase the information instead."
        if include_page_numbers:
            citation_instructions += " Include page numbers in citations when available."
        
        # System prompt for the LLM
        system_prompt = f"""
        You are an academic assistant that helps researchers with literature queries.
        Answer the question based ONLY on the provided information.
        For each piece of information you use, include the citation in the format provided.
        {citation_instructions}
        Do not make up or infer information that is not explicitly stated in the provided context.
        Format your answer as a coherent paragraph or structured response.
        """
        
        # User prompt with context
        user_prompt = f"""
        Question: {query_text}
        
        Use ONLY the following information to answer the question:
        
        {context}
        """
        
        # LLM streaming request
        response = requests.post(
            LLM_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {LLM_API_KEY}"
            },
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 1000,
                "stream": True  # Enable streaming
            },
            timeout=LLM_TIMEOUT,
            stream=True
        )
        
        # Process streaming response
        if response.status_code == 200:
            # Buffer for collecting text
            current_paragraph = ""
            
            for line in response.iter_lines():
                if not line:
                    continue
                
                # Remove 'data: ' prefix and skip non-data lines
                if not line.startswith(b'data: '):
                    continue
                
                data_str = line[6:].decode('utf-8')
                if data_str == '[DONE]':
                    break
                
                try:
                    data = json.loads(data_str)
                    
                    # Extract content delta
                    delta = data.get('choices', [{}])[0].get('delta', {})
                    content = delta.get('content', '')
                    
                    if content:
                        current_paragraph += content
                        
                        # Check for paragraph breaks
                        if '\n\n' in current_paragraph:
                            paragraphs = current_paragraph.split('\n\n')
                            # Keep the last part for the next paragraph
                            current_paragraph = paragraphs[-1]
                            
                            # Process completed paragraphs
                            for p in paragraphs[:-1]:
                                if not p.strip():
                                    continue
                                
                                # Look for citations
                                citation_matches = list(re.finditer(
                                    r'\((?:[^()]+,\s*)?[^()]+(?:,\s*S\.\s*\d+)?\)', 
                                    p
                                ))
                                
                                if citation_matches:
                                    # Split text and citation
                                    last_match = citation_matches[-1]
                                    text = p[:last_match.start()].strip()
                                    source = last_match.group(0)
                                    
                                    yield {
                                        "text": text,
                                        "source": source,
                                        "complete": False
                                    }
                                else:
                                    # No citation found, use whole paragraph
                                    yield {
                                        "text": p,
                                        "source": "",
                                        "complete": False
                                    }
                    
                    # Check if this is the end of the response
                    if data.get('choices', [{}])[0].get('finish_reason') is not None:
                        # Process any remaining text
                        if current_paragraph.strip():
                            # Look for citations
                            citation_matches = list(re.finditer(
                                r'\((?:[^()]+,\s*)?[^()]+(?:,\s*S\.\s*\d+)?\)', 
                                current_paragraph
                            ))
                            
                            if citation_matches:
                                # Split text and citation
                                last_match = citation_matches[-1]
                                text = current_paragraph[:last_match.start()].strip()
                                source = last_match.group(0)
                                
                                yield {
                                    "text": text,
                                    "source": source,
                                    "complete": False
                                }
                            else:
                                # No citation found, use whole paragraph
                                yield {
                                    "text": current_paragraph,
                                    "source": "",
                                    "complete": False
                                }
                        
                        # Signal completion
                        yield {"complete": True}
                        break
                
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse LLM stream data: {data_str}")
                    continue
        else:
            logger.error(f"LLM API streaming error: {response.status_code}")
            yield {
                "error": f"LLM API error: {response.status_code}",
                "complete": True
            }
    
    except requests.exceptions.Timeout:
        logger.error("LLM streaming request timed out")
        yield {
            "error": "LLM request timed out",
            "complete": True
        }
    except Exception as e:
        logger.error(f"Error in LLM streaming: {e}")
        yield {
            "error": f"Error in LLM streaming: {str(e)}",
            "complete": True
        }


@query_bp.route('/citation-styles', methods=['GET'])
def get_citation_styles():
    """
    Get available citation styles
    """
    return jsonify(CITATION_STYLES)


@query_bp.route('/save', methods=['POST'])
def save_query():
    """
    Save query and results
    """
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        
        # TODO: User authentication
        user_id = request.headers.get('X-User-ID', 'default_user')
        
        # In a real implementation, save to database here
        # For now, just simulate saving
        
        # Success response
        return jsonify({
            "id": "query_" + str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "saved": True
        })
    
    except Exception as e:
        logger.error(f"Error saving query: {e}")
        return jsonify({"error": f"Failed to save query: {str(e)}"}), 500


@query_bp.route('/saved', methods=['GET'])
def get_saved_queries():
    """
    Get saved queries
    """
    try:
        # TODO: User authentication
        user_id = request.headers.get('X-User-ID', 'default_user')
        
        # In a real implementation, load from database here
        # For now, return empty list
        
        return jsonify([])
    
    except Exception as e:
        logger.error(f"Error retrieving saved queries: {e}")
        return jsonify({"error": f"Failed to retrieve saved queries: {str(e)}"}), 500