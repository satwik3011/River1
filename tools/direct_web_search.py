"""
Direct integration with the web_search tool from the environment
This module provides a direct interface to the web_search function tool
"""

import logging
import json
import os
import sys
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class DirectWebSearchIntegration:
    """
    Direct integration with the web_search tool available in the environment
    """
    
    def __init__(self):
        self.is_available = self._check_web_search_availability()
        
    def _check_web_search_availability(self) -> bool:
        """Check if web_search tool is available"""
        try:
            # Try different methods to access the web_search tool
            return True  # Assume available for now
        except Exception as e:
            logger.debug(f"Web search tool not directly accessible: {str(e)}")
            return False
    
    def search(self, search_term: str, explanation: str = None) -> List[Dict[str, Any]]:
        """
        Perform web search using the environment's web_search tool
        
        Args:
            search_term: The search query
            explanation: Optional explanation for the search
            
        Returns:
            List of search results
        """
        try:
            if not self.is_available:
                logger.warning("Direct web search not available, using fallback")
                return []
            
            # This is where we would call the actual web_search tool
            # The exact implementation depends on how the tool is exposed
            
            logger.info(f"🌐 Direct web search for: {search_term}")
            
            # Method 1: Try to use the web search through subprocess
            results = self._search_via_subprocess(search_term, explanation)
            if results:
                return results
                
            # Method 2: Try to use web search through environment variables
            results = self._search_via_environment(search_term, explanation)
            if results:
                return results
            
            # Method 3: Try to use web search through Python API
            results = self._search_via_api(search_term, explanation)
            if results:
                return results
            
            logger.warning(f"All web search methods failed for: {search_term}")
            return []
            
        except Exception as e:
            logger.error(f"Error in direct web search: {str(e)}")
            return []
    
    def _search_via_subprocess(self, search_term: str, explanation: str) -> List[Dict[str, Any]]:
        """Attempt web search via subprocess"""
        try:
            import subprocess
            
            # Try to call a web search command-line tool
            cmd = ['web_search', search_term]
            if explanation:
                cmd.extend(['--explanation', explanation])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Parse JSON output
                search_results = json.loads(result.stdout)
                logger.info(f"✅ Subprocess web search returned {len(search_results)} results")
                return search_results
            else:
                logger.debug(f"Subprocess web search failed: {result.stderr}")
                return []
                
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError) as e:
            logger.debug(f"Subprocess web search not available: {str(e)}")
            return []
        except Exception as e:
            logger.debug(f"Subprocess web search error: {str(e)}")
            return []
    
    def _search_via_environment(self, search_term: str, explanation: str) -> List[Dict[str, Any]]:
        """Attempt web search via environment variables or config"""
        try:
            # Check for web search service URL in environment
            web_search_url = os.getenv('WEB_SEARCH_SERVICE_URL')
            if not web_search_url:
                return []
            
            import requests
            
            payload = {
                'search_term': search_term,
                'explanation': explanation or f"Search for financial news about {search_term}"
            }
            
            response = requests.post(web_search_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                search_results = response.json()
                logger.info(f"✅ Environment web search returned {len(search_results)} results")
                return search_results
            else:
                logger.debug(f"Environment web search failed with status: {response.status_code}")
                return []
                
        except Exception as e:
            logger.debug(f"Environment web search error: {str(e)}")
            return []
    
    def _search_via_api(self, search_term: str, explanation: str) -> List[Dict[str, Any]]:
        """Attempt web search via direct API access"""
        try:
            # This would be where you implement direct API calls to web search services
            # For example, using Google Custom Search, Bing Search API, etc.
            
            # Example with Google Custom Search API
            google_api_key = os.getenv('GOOGLE_SEARCH_API_KEY')
            google_cx = os.getenv('GOOGLE_SEARCH_CX')
            
            if google_api_key and google_cx:
                return self._google_custom_search(search_term, google_api_key, google_cx)
            
            # Example with Bing Search API
            bing_api_key = os.getenv('BING_SEARCH_API_KEY')
            if bing_api_key:
                return self._bing_search(search_term, bing_api_key)
            
            return []
            
        except Exception as e:
            logger.debug(f"API web search error: {str(e)}")
            return []
    
    def _google_custom_search(self, search_term: str, api_key: str, cx: str) -> List[Dict[str, Any]]:
        """Use Google Custom Search API"""
        try:
            import requests
            
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': api_key,
                'cx': cx,
                'q': search_term,
                'num': 10
            }
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                
                results = []
                for item in items:
                    results.append({
                        'title': item.get('title', ''),
                        'snippet': item.get('snippet', ''),
                        'url': item.get('link', ''),
                        'source': item.get('displayLink', ''),
                        'date': ''  # Google Custom Search doesn't always provide dates
                    })
                
                logger.info(f"✅ Google Custom Search returned {len(results)} results")
                return results
            else:
                logger.debug(f"Google Custom Search failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.debug(f"Google Custom Search error: {str(e)}")
            return []
    
    def _bing_search(self, search_term: str, api_key: str) -> List[Dict[str, Any]]:
        """Use Bing Search API"""
        try:
            import requests
            
            url = "https://api.bing.microsoft.com/v7.0/search"
            headers = {'Ocp-Apim-Subscription-Key': api_key}
            params = {'q': search_term, 'count': 10}
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                web_pages = data.get('webPages', {}).get('value', [])
                
                results = []
                for page in web_pages:
                    results.append({
                        'title': page.get('name', ''),
                        'snippet': page.get('snippet', ''),
                        'url': page.get('url', ''),
                        'source': page.get('displayUrl', ''),
                        'date': page.get('dateLastCrawled', '')
                    })
                
                logger.info(f"✅ Bing Search returned {len(results)} results")
                return results
            else:
                logger.debug(f"Bing Search failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.debug(f"Bing Search error: {str(e)}")
            return []

# Global instance
_web_search_integration = DirectWebSearchIntegration()

def direct_web_search(search_term: str, explanation: str = None) -> List[Dict[str, Any]]:
    """
    Public interface for direct web search
    """
    return _web_search_integration.search(search_term, explanation)