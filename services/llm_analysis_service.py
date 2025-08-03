import google.generativeai as genai
import os
import logging
import requests
import json
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
        else:
            self.model = None
            self.llm_available = False
            logger.warning("Gemini API key not set. LLM analysis will not be available.")
        
        self.alpha_vantage_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        self.logger = logger
    
    def analyze_stock(self, symbol: str) -> Dict:
        """
        Comprehensive stock analysis using LLM agents
        Returns recommendation with reasoning, sentiment, and technical analysis  
        """
        try:
            # Gather all data for analysis
            stock_data = self._get_stock_fundamental_data(symbol)
            news_data = self._get_recent_news(symbol)
            technical_data = self._get_technical_indicators(symbol)
            
            # Perform individual analyses
            news_sentiment = self._analyze_news_sentiment(symbol, news_data)
            technical_analysis = self._analyze_technical_indicators(symbol, technical_data)
            fundamental_analysis = self._analyze_fundamentals(symbol, stock_data)
            
            # Generate final recommendation
            final_recommendation = self._generate_final_recommendation(
                symbol, stock_data, news_sentiment, technical_analysis, fundamental_analysis
            )
            
            return {
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
            
        except Exception as e:
            self.logger.error(f"Error analyzing stock {symbol}: {str(e)}")
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
        """Analyze news sentiment using LLM"""
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
            
            prompt = f"""
            Analyze the sentiment of recent news for {symbol} stock. 
            
            Recent News:
            {news_summary}
            
            Based on this news, provide:
            1. A sentiment score from -1 (very negative) to +1 (very positive)
            2. Brief reasoning for the sentiment score
            
            Focus on news that could impact stock price and investor sentiment.
            Be objective and consider both positive and negative aspects.
            
            Respond in JSON format:
            {{
                "sentiment_score": <number between -1 and 1>,
                "reasoning": "<brief explanation>"
            }}
            """
            
            response = self.model.generate_content(prompt)
            result = json.loads(response.text)
            
            return {
                'score': result.get('sentiment_score', 0),
                'reasoning': result.get('reasoning', 'Analysis completed')
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
            2. Brief reasoning based on the technical indicators
            
            Consider:
            - RSI levels (overbought >70, oversold <30)
            - Price relative to moving averages
            - Momentum trends
            - Volume patterns
            
            Respond in JSON format:
            {{
                "technical_score": <number between -1 and 1>,
                "reasoning": "<brief technical analysis>"
            }}
            """
            
            response = self.model.generate_content(prompt)
            result = json.loads(response.text)
            
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
            - Market Cap: ${stock_data.get('market_cap', 'N/A'):,} if stock_data.get('market_cap') else 'N/A'
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
            2. Brief reasoning based on the fundamental analysis
            
            Consider:
            - Valuation metrics (P/E, PEG, P/B ratios)
            - Financial health (debt levels, ROE)
            - Growth prospects (revenue/earnings growth)
            - Dividend sustainability
            - Sector comparisons where relevant
            
            Respond in JSON format:
            {{
                "fundamental_score": <number between -1 and 1>,
                "reasoning": "<brief fundamental analysis>"
            }}
            """
            
            response = self.model.generate_content(prompt)
            result = json.loads(response.text)
            
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
            3. Detailed reasoning that synthesizes all three analyses
            
            Guidelines:
            - BUY: Strong positive signals across multiple analyses
            - HOLD: Mixed signals or modest positive/negative indicators
            - SELL: Strong negative signals or significant risk factors
            
            Consider the weight of each analysis type and how they complement or contradict each other.
            
            Respond in JSON format:
            {{
                "recommendation": "<BUY|HOLD|SELL>",
                "confidence": <number between 0 and 1>,
                "reasoning": "<detailed explanation combining all analyses>"
            }}
            """
            
            response = self.model.generate_content(prompt)
            
            result = json.loads(response.text)
            
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