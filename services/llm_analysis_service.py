import google.generativeai as genai
import os
import logging
import requests
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import yfinance as yf

logger = logging.getLogger(__name__)

class LLMAnalysisService:
    """Service for LLM-powered stock analysis using Google Gemini"""
    
    def __init__(self):
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        if gemini_api_key and gemini_api_key != 'your-gemini-api-key-here':
            genai.configure(api_key=gemini_api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.llm_available = True
            logger.info("✅ Gemini API configured successfully")
        else:
            self.model = None
            self.llm_available = False
            logger.warning("❌ Gemini API key not set. LLM analysis will not be available.")
        
        self.alpha_vantage_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        self.logger = logger
        
        # API call tracking (no rate limiting needed)
        self.gemini_call_count = 0
        self.max_parallel_calls = 10  # Max concurrent API calls
    
    def _call_gemini_optimized(self, prompt: str, operation_name: str) -> Dict:
        """
        Make a Gemini API call optimized for parallel execution
        """
        if not self.llm_available:
            self.logger.warning(f"🚫 Gemini API not available for {operation_name}")
            return {"error": "Gemini API not configured"}
        
        self.gemini_call_count += 1
        
        # Simplified logging for parallel execution
        self.logger.info(f"🤖 GEMINI API CALL #{self.gemini_call_count}: {operation_name}")
        
        try:
            # Make the API call (no artificial delays)
            response = self.model.generate_content(prompt)
            
            # Parse JSON
            result = self._parse_llm_json_response(response.text)
            self.logger.info(f"✅ {operation_name} completed successfully")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ GEMINI API ERROR in {operation_name}: {str(e)}")
            return {"error": str(e)}
    
    def _parse_llm_json_response(self, response_text: str) -> Dict:
        """
        Parse JSON from LLM response, handling markdown code fences
        """
        try:
            # Remove markdown code fences if present
            text = response_text.strip()
            if text.startswith('```json'):
                text = text[7:]  # Remove ```json
            if text.startswith('```'):
                text = text[3:]   # Remove ```
            if text.endswith('```'):
                text = text[:-3]  # Remove trailing ```
            
            # Clean up any remaining whitespace
            text = text.strip()
            
            # Parse JSON
            return json.loads(text)
        
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing error: {str(e)}")
            self.logger.error(f"Raw response: {response_text[:200]}...")
            raise
    
    def analyze_stock(self, symbol: str) -> Dict:
        """
        Comprehensive stock analysis using PARALLEL LLM execution
        Returns recommendation with reasoning, sentiment, and technical analysis  
        """
        self.logger.info(f"🚀 STARTING PARALLEL ANALYSIS for {symbol}")
        self.logger.info(f"{'='*80}")
        
        try:
            # Gather all data for analysis (sequential - data collection)
            self.logger.info(f"📊 Step 1: Gathering data for {symbol}...")
            stock_data = self._get_stock_fundamental_data(symbol)
            news_data = self._get_recent_news_with_websearch(symbol)  # Use web search for real-time news
            technical_data = self._get_technical_indicators(symbol)
            
            self.logger.info(f"   📰 Found {len(news_data) if news_data else 0} news articles")
            self.logger.info(f"   📈 Technical indicators calculated")
            self.logger.info(f"   📊 Fundamental data retrieved")
            
            # PARALLEL EXECUTION: Run 3 independent analyses simultaneously
            self.logger.info(f"⚡ PARALLEL LLM ANALYSIS for {symbol} (3 concurrent API calls)...")
            
            with ThreadPoolExecutor(max_workers=3) as executor:
                # Submit all 3 independent analyses
                future_to_analysis = {
                    executor.submit(self._analyze_news_sentiment, symbol, news_data): 'news_sentiment',
                    executor.submit(self._analyze_technical_indicators, symbol, technical_data): 'technical_analysis',
                    executor.submit(self._analyze_fundamentals, symbol, stock_data): 'fundamental_analysis'
                }
                
                # Collect results as they complete
                results = {}
                for future in as_completed(future_to_analysis):
                    analysis_type = future_to_analysis[future]
                    try:
                        results[analysis_type] = future.result()
                        self.logger.info(f"   ✅ {analysis_type} completed")
                    except Exception as e:
                        self.logger.error(f"   ❌ {analysis_type} failed: {str(e)}")
                        results[analysis_type] = {'score': 0, 'reasoning': f'Error: {str(e)}'}
            
            # Extract results
            news_sentiment = results.get('news_sentiment', {'score': 0, 'reasoning': 'News analysis failed'})
            technical_analysis = results.get('technical_analysis', {'score': 0, 'reasoning': 'Technical analysis failed'})
            fundamental_analysis = results.get('fundamental_analysis', {'score': 0, 'reasoning': 'Fundamental analysis failed'})
            
            # Generate final recommendation (depends on the 3 parallel analyses)
            self.logger.info(f"🎯 Final recommendation synthesis for {symbol}...")
            final_recommendation = self._generate_final_recommendation(
                symbol, stock_data, news_sentiment, technical_analysis, fundamental_analysis
            )
            
            result = {
                'symbol': symbol,
                'recommendation': final_recommendation['recommendation'],
                'confidence_score': final_recommendation['confidence'],
                'reasoning': final_recommendation['reasoning'],
                'news_sentiment': news_sentiment['score'],
                'technical_score': technical_analysis['score'],
                'fundamental_score': fundamental_analysis['score'],
                'recent_news': news_data[:5],  # Top 5 news items
                'technical_indicators': technical_data,
                'analysis_timestamp': datetime.utcnow().isoformat()
            }
            
            self.logger.info(f"🎉 PARALLEL ANALYSIS COMPLETE for {symbol}")
            self.logger.info(f"   Final Recommendation: {result['recommendation']} (confidence: {result['confidence_score']:.2f})")
            self.logger.info(f"   Total Gemini API calls: {self.gemini_call_count}")
            self.logger.info(f"{'='*80}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in parallel analysis for {symbol}: {str(e)}")
            raise
    
    def _get_stock_fundamental_data(self, symbol: str) -> Dict:
        """Get fundamental stock data from Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Get key fundamental metrics
            fundamentals = {
                'symbol': symbol,
                'company_name': info.get('longName', 'N/A'),
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'current_price': info.get('currentPrice', 0),
                'previous_close': info.get('previousClose', 0),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'peg_ratio': info.get('pegRatio'),
                'price_to_book': info.get('priceToBook'),
                'debt_to_equity': info.get('debtToEquity'),
                'roe': info.get('returnOnEquity'),
                'revenue_growth': info.get('revenueGrowth'),
                'earnings_growth': info.get('earningsGrowth'),
                'dividend_yield': info.get('dividendYield'),
                'beta': info.get('beta'),
                'target_price': info.get('targetMeanPrice'),
                'recommendation': info.get('recommendationMean')
            }
            
            return fundamentals
            
        except Exception as e:
            self.logger.error(f"Error getting fundamental data for {symbol}: {str(e)}")
            return {'symbol': symbol, 'error': str(e)}
    
    def _get_recent_news(self, symbol: str) -> List[Dict]:
        """Get recent news for the stock"""
        try:
            ticker = yf.Ticker(symbol)
            news = ticker.news
            
            processed_news = []
            for item in news[:10]:  # Get last 10 news items
                processed_news.append({
                    'title': item.get('title', ''),
                    'summary': item.get('summary', ''),
                    'source': item.get('publisher', ''),
                    'published_date': datetime.fromtimestamp(item.get('providerPublishTime', 0)).isoformat() if item.get('providerPublishTime') else None,
                    'url': item.get('link', '')
                })
            
            return processed_news
            
        except Exception as e:
            self.logger.error(f"Error getting news for {symbol}: {str(e)}")
            return []
    
    def _get_recent_news_with_websearch(self, symbol: str) -> List[Dict]:
        """Get recent news using web search for more current information"""
        try:
            self.logger.info(f"🌐 Fetching real-time news for {symbol} using web search...")
            
            # Construct targeted financial search queries
            search_queries = [
                f"{symbol} stock news today earnings financial results",
                f"{symbol} analyst upgrade downgrade price target",
                f"{symbol} company breaking news announcement merger"
            ]
            
            all_news = []
            
            for query in search_queries:
                try:
                    self.logger.info(f"🔍 Web search query: {query}")
                    
                    # Use the web_search tool - this will make an actual web search
                    from tools.web_search import web_search  # Import the web search function
                    search_results = web_search(query)
                    
                    # Process search results
                    for result in search_results[:5]:  # Top 5 per query
                        if self._is_relevant_financial_news(result, symbol):
                            processed_news = {
                                'title': result.get('title', ''),
                                'summary': result.get('snippet', result.get('description', '')),
                                'source': result.get('source', result.get('domain', 'Web')),
                                'url': result.get('url', ''),
                                'published_date': result.get('date', ''),
                                'relevance_score': self._calculate_news_relevance(result, symbol)
                            }
                            all_news.append(processed_news)
                    
                except Exception as e:
                    self.logger.error(f"Error in web search for query '{query}': {str(e)}")
                    continue
            
            # Sort by relevance and deduplicate
            all_news = self._deduplicate_news(all_news)
            all_news.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            self.logger.info(f"📰 Found {len(all_news)} relevant real-time news articles for {symbol}")
            
            # If web search fails or returns no results, fall back to Yahoo Finance
            if not all_news:
                self.logger.warning(f"No web search results for {symbol}, falling back to Yahoo Finance")
                return self._get_recent_news(symbol)
            
            return all_news[:10]  # Return top 10 most relevant
            
        except ImportError:
            self.logger.warning("Web search tool not available, falling back to Yahoo Finance")
            return self._get_recent_news(symbol)
        except Exception as e:
            self.logger.error(f"Error getting news with web search for {symbol}: {str(e)}")
            return self._get_recent_news(symbol)  # Fallback
    
    def _is_relevant_financial_news(self, result: Dict, symbol: str) -> bool:
        """Filter for financially relevant news about the stock"""
        title = result.get('title', '').lower()
        snippet = result.get('snippet', result.get('description', '')).lower()
        
        # Must contain the stock symbol
        contains_symbol = (symbol.lower() in title or symbol.lower() in snippet)
        
        # Financial keywords that indicate relevance
        financial_keywords = [
            'earnings', 'revenue', 'profit', 'loss', 'analyst', 'upgrade', 'downgrade',
            'price target', 'merger', 'acquisition', 'partnership', 'sec filing',
            'dividend', 'split', 'buyback', 'guidance', 'forecast', 'outlook',
            'quarterly', 'annual', 'financial results', 'stock', 'shares'
        ]
        
        contains_financial_terms = any(keyword in title or keyword in snippet 
                                     for keyword in financial_keywords)
        
        return contains_symbol and contains_financial_terms
    
    def _calculate_news_relevance(self, result: Dict, symbol: str) -> float:
        """Calculate relevance score for news item"""
        score = 0.0
        title = result.get('title', '').lower()
        snippet = result.get('snippet', result.get('description', '')).lower()
        
        # Higher score for symbol in title
        if symbol.lower() in title:
            score += 2.0
        elif symbol.lower() in snippet:
            score += 1.0
        
        # Score for high-impact financial keywords
        high_impact_keywords = ['earnings', 'merger', 'acquisition', 'upgrade', 'downgrade', 'price target']
        medium_impact_keywords = ['revenue', 'partnership', 'analyst', 'guidance', 'outlook']
        low_impact_keywords = ['stock', 'financial', 'quarterly', 'annual']
        
        for keyword in high_impact_keywords:
            if keyword in title:
                score += 1.5
            elif keyword in snippet:
                score += 1.0
        
        for keyword in medium_impact_keywords:
            if keyword in title:
                score += 1.0
            elif keyword in snippet:
                score += 0.7
        
        for keyword in low_impact_keywords:
            if keyword in title:
                score += 0.5
            elif keyword in snippet:
                score += 0.3
        
        return score
    
    def _deduplicate_news(self, news_list: List[Dict]) -> List[Dict]:
        """Remove duplicate news articles based on title similarity"""
        if not news_list:
            return []
        
        unique_news = []
        seen_titles = set()
        
        for news_item in news_list:
            title = news_item.get('title', '').lower().strip()
            # Simple deduplication - check if very similar title exists
            title_words = set(title.split())
            
            is_duplicate = False
            for seen_title in seen_titles:
                seen_words = set(seen_title.split())
                # If 80% of words are the same, consider it a duplicate
                overlap = len(title_words.intersection(seen_words))
                if overlap / max(len(title_words), len(seen_words), 1) > 0.8:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_news.append(news_item)
                seen_titles.add(title)
        
        return unique_news
    
    def _get_technical_indicators(self, symbol: str) -> Dict:
        """Calculate technical indicators for the stock"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="3mo")  # 3 months of data
            
            if hist.empty:
                return {}
            
            # Calculate technical indicators
            current_price = hist['Close'].iloc[-1]
            
            # Moving averages
            ma_20 = hist['Close'].rolling(window=20).mean().iloc[-1]
            ma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
            
            # RSI calculation
            rsi = self._calculate_rsi(hist['Close'])
            
            # Price relative to MAs
            price_vs_ma20 = ((current_price - ma_20) / ma_20) * 100 if ma_20 else 0
            price_vs_ma50 = ((current_price - ma_50) / ma_50) * 100 if ma_50 else 0
            
            # Volume analysis
            avg_volume = hist['Volume'].rolling(window=20).mean().iloc[-1]
            recent_volume = hist['Volume'].iloc[-1]
            volume_ratio = recent_volume / avg_volume if avg_volume else 1
            
            # Price momentum
            price_1w_ago = hist['Close'].iloc[-5] if len(hist) >= 5 else current_price
            price_1m_ago = hist['Close'].iloc[-20] if len(hist) >= 20 else current_price
            
            momentum_1w = ((current_price - price_1w_ago) / price_1w_ago) * 100 if price_1w_ago else 0
            momentum_1m = ((current_price - price_1m_ago) / price_1m_ago) * 100 if price_1m_ago else 0
            
            return {
                'current_price': round(current_price, 2),
                'ma_20': round(ma_20, 2) if ma_20 else None,
                'ma_50': round(ma_50, 2) if ma_50 else None,
                'rsi': round(rsi, 2) if rsi else None,
                'price_vs_ma20_percent': round(price_vs_ma20, 2),
                'price_vs_ma50_percent': round(price_vs_ma50, 2),
                'volume_ratio': round(volume_ratio, 2),
                'momentum_1w_percent': round(momentum_1w, 2),
                'momentum_1m_percent': round(momentum_1m, 2)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating technical indicators for {symbol}: {str(e)}")
            return {}
    
    def _calculate_rsi(self, prices, period=14):
        """Calculate RSI (Relative Strength Index)"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.iloc[-1]
        except:
            return None
    
    def _analyze_news_sentiment(self, symbol: str, news_data: List[Dict]) -> Dict:
        """Analyze news sentiment using LLM with optional web search enhancement"""
        if not news_data:
            return {'score': 0, 'reasoning': 'No recent news available'}
        
        if not self.llm_available:
            return {'score': 0, 'reasoning': 'Gemini API key not configured'}
        
        try:
            # Prepare news summary for LLM
            news_summary = "\n".join([
                f"- {item['title']}: {item['summary'][:200]}..."
                for item in news_data[:5]
            ])
            
            # Enhanced prompt that could use web search data
            prompt = f"""
            Analyze the sentiment of recent news for {symbol} stock. 
            
            Recent News Sources:
            {news_summary}
            
            ENHANCED ANALYSIS INSTRUCTIONS:
            You are analyzing real-time financial news sentiment. Consider:
            1. Market-moving events (earnings, partnerships, regulatory changes)
            2. Analyst upgrades/downgrades and price target changes
            3. Industry trends and competitive positioning
            4. Macroeconomic factors affecting the sector
            5. Management changes and strategic initiatives
            
            Based on this news, provide:
            1. A sentiment score from -1 (very negative) to +1 (very positive)
            2. Brief reasoning in bullet points for easy understanding
            3. Confidence level in your analysis
            
            Focus on news that could impact stock price and investor sentiment.
            Be objective and consider both positive and negative aspects.
            
            Respond in JSON format:
            {{
                "sentiment_score": <number between -1 and 1>,
                "reasoning": "• Market impact: How news affects stock outlook\n• Investor sentiment: Key emotional drivers\n• Timeline: Short vs long-term implications\n• Overall assessment: Net positive/negative view",
                "confidence": <number between 0 and 1>
            }}
            
            NOTE: This analysis could be enhanced with real-time web search for breaking news.
            """
            
            result = self._call_gemini_optimized(prompt, f"Enhanced News Sentiment Analysis - {symbol}")
            
            if "error" in result:
                return {'score': 0, 'reasoning': f'Error in sentiment analysis: {result["error"]}'}
            
            return {
                'score': result.get('sentiment_score', 0),
                'reasoning': result.get('reasoning', 'Analysis completed'),
                'confidence': result.get('confidence', 0.7)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing news sentiment for {symbol}: {str(e)}")
            return {'score': 0, 'reasoning': f'Error in sentiment analysis: {str(e)}'}
    
    def _analyze_technical_indicators(self, symbol: str, technical_data: Dict) -> Dict:
        """Analyze technical indicators using LLM"""
        if not technical_data:
            return {'score': 0, 'reasoning': 'No technical data available'}
        
        if not self.llm_available:
            return {'score': 0, 'reasoning': 'Gemini API key not configured'}
        
        try:
            prompt = f"""
            Analyze the technical indicators for {symbol} stock:
            
            Technical Data:
            - Current Price: ${technical_data.get('current_price', 'N/A')}
            - 20-day MA: ${technical_data.get('ma_20', 'N/A')}
            - 50-day MA: ${technical_data.get('ma_50', 'N/A')}
            - RSI: {technical_data.get('rsi', 'N/A')}
            - Price vs 20-day MA: {technical_data.get('price_vs_ma20_percent', 'N/A')}%
            - Price vs 50-day MA: {technical_data.get('price_vs_ma50_percent', 'N/A')}%
            - Volume Ratio: {technical_data.get('volume_ratio', 'N/A')}
            - 1-week Momentum: {technical_data.get('momentum_1w_percent', 'N/A')}%
            - 1-month Momentum: {technical_data.get('momentum_1m_percent', 'N/A')}%
            
            Provide:
            1. A technical score from -1 (very bearish) to +1 (very bullish)
            2. Brief reasoning in bullet points that anyone can understand
            
            Consider:
            - RSI levels (overbought >70, oversold <30)
            - Price relative to moving averages
            - Momentum trends
            - Volume patterns
            
            Respond in JSON format:
            {{
                "technical_score": <number between -1 and 1>,
                "reasoning": "• Price trend: Above/below key averages\n• RSI signal: Oversold/overbought condition\n• Momentum: Recent performance direction\n• Overall: Technical outlook summary"
            }}
            """
            
            result = self._call_gemini_optimized(prompt, f"Technical Indicators Analysis - {symbol}")
            
            if "error" in result:
                return {'score': 0, 'reasoning': f'Error in technical analysis: {result["error"]}'}
            
            return {
                'score': result.get('technical_score', 0),
                'reasoning': result.get('reasoning', 'Technical analysis completed')
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing technical indicators for {symbol}: {str(e)}")
            return {'score': 0, 'reasoning': f'Error in technical analysis: {str(e)}'}
    
    def _analyze_fundamentals(self, symbol: str, stock_data: Dict) -> Dict:
        """Analyze fundamental data using LLM"""
        if not stock_data or 'error' in stock_data:
            return {'score': 0, 'reasoning': 'No fundamental data available'}
        
        if not self.llm_available:
            return {'score': 0, 'reasoning': 'Gemini API key not configured'}
        
        try:
            prompt = f"""
            Analyze the fundamental metrics for {symbol} ({stock_data.get('company_name', 'N/A')}):
            
            Fundamental Data:
            - Sector: {stock_data.get('sector', 'N/A')}
            - Market Cap: {f"${stock_data.get('market_cap'):,}" if isinstance(stock_data.get('market_cap'), (int, float)) else 'N/A'}
            - P/E Ratio: {stock_data.get('pe_ratio', 'N/A')}
            - Forward P/E: {stock_data.get('forward_pe', 'N/A')}
            - PEG Ratio: {stock_data.get('peg_ratio', 'N/A')}
            - Price to Book: {stock_data.get('price_to_book', 'N/A')}
            - Debt to Equity: {stock_data.get('debt_to_equity', 'N/A')}
            - ROE: {stock_data.get('roe', 'N/A')}
            - Revenue Growth: {stock_data.get('revenue_growth', 'N/A')}
            - Earnings Growth: {stock_data.get('earnings_growth', 'N/A')}
            - Dividend Yield: {stock_data.get('dividend_yield', 'N/A')}
            - Beta: {stock_data.get('beta', 'N/A')}
            
            Provide:
            1. A fundamental score from -1 (poor fundamentals) to +1 (strong fundamentals)
            2. Brief reasoning in bullet points for easy understanding
            
            Consider:
            - Valuation metrics (P/E, PEG, P/B ratios)
            - Financial health (debt levels, ROE)
            - Growth prospects (revenue/earnings growth)
            - Dividend sustainability
            - Sector comparisons where relevant
            
            Respond in JSON format:
            {{
                "fundamental_score": <number between -1 and 1>,
                "reasoning": "• Valuation: Fair/expensive/cheap compared to peers\n• Growth: Revenue and earnings trends\n• Financial health: Debt levels and profitability\n• Overall: Long-term investment appeal"
            }}
            """
            
            result = self._call_gemini_optimized(prompt, f"Fundamental Analysis - {symbol}")
            
            if "error" in result:
                return {'score': 0, 'reasoning': f'Error in fundamental analysis: {result["error"]}'}
            
            return {
                'score': result.get('fundamental_score', 0),
                'reasoning': result.get('reasoning', 'Fundamental analysis completed')
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing fundamentals for {symbol}: {str(e)}")
            return {'score': 0, 'reasoning': f'Error in fundamental analysis: {str(e)}'}
    
    def _generate_final_recommendation(self, symbol: str, stock_data: Dict, 
                                     news_sentiment: Dict, technical_analysis: Dict, 
                                     fundamental_analysis: Dict) -> Dict:
        """Generate final BUY/HOLD/SELL recommendation using LLM"""
        if not self.llm_available:
            return {
                'recommendation': 'HOLD',
                'confidence': 0.5,
                'reasoning': 'Gemini API key not configured. Please add your API key to get AI-powered recommendations.'
            }
        
        try:
            prompt = f"""
            Generate a final investment recommendation for {symbol} ({stock_data.get('company_name', 'N/A')}) 
            based on comprehensive analysis:
            
            Analysis Summary:
            - News Sentiment Score: {news_sentiment['score']} 
              Reasoning: {news_sentiment['reasoning']}
            
            - Technical Analysis Score: {technical_analysis['score']}
              Reasoning: {technical_analysis['reasoning']}
            
            - Fundamental Analysis Score: {fundamental_analysis['score']}
              Reasoning: {fundamental_analysis['reasoning']}
            
            Current Price: ${stock_data.get('current_price', 'N/A')}
            
            Based on this comprehensive analysis, provide:
            1. Final recommendation: BUY, HOLD, or SELL
            2. Confidence score from 0 to 1 (how confident you are in this recommendation)
            3. Brief reasoning in bullet points that anyone can understand
            
            Guidelines:
            - BUY: Strong positive signals across multiple analyses
            - HOLD: Mixed signals or modest positive/negative indicators
            - SELL: Strong negative signals or significant risk factors
            
            Consider the weight of each analysis type and how they complement or contradict each other.
            
            Respond in JSON format:
            {{
                "recommendation": "<BUY|HOLD|SELL>",
                "confidence": <number between 0 and 1>,
                "reasoning": "• Technical outlook: Short-term price trend summary\n• Fundamental value: Long-term investment attractiveness\n• News impact: Recent events affecting stock\n• Final verdict: Why this recommendation makes sense now"
            }}
            """
            
            result = self._call_gemini_optimized(prompt, f"Final Recommendation - {symbol}")
            
            if "error" in result:
                return {
                    'recommendation': 'HOLD',
                    'confidence': 0.3,
                    'reasoning': f'Error in final analysis: {result["error"]}'
                }
            
            return {
                'recommendation': result.get('recommendation', 'HOLD'),
                'confidence': result.get('confidence', 0.5),
                'reasoning': result.get('reasoning', 'Comprehensive analysis completed')
            }
            
        except Exception as e:
            self.logger.error(f"Error generating final recommendation for {symbol}: {str(e)}")
            return {
                'recommendation': 'HOLD',
                'confidence': 0.3,
                'reasoning': f'Error in final analysis: {str(e)}'
            }