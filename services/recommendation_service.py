import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy import desc, and_
from models import Stock, Recommendation, Portfolio, RecommendationHistory, db
from services.llm_analysis_service import LLMAnalysisService
from services.portfolio_service import PortfolioService

logger = logging.getLogger(__name__)

class RecommendationService:
    """Service for managing stock recommendations and tracking changes"""
    
    def __init__(self):
        self.llm_service = LLMAnalysisService()
        self.portfolio_service = PortfolioService()
        self.logger = logger
    
    def get_all_stocks_with_recommendations(self) -> List[Dict]:
        """Get all portfolio stocks with their latest recommendations"""
        try:
            # Get all active portfolio stocks
            portfolio_stocks = (Portfolio.query
                              .filter_by(is_active=True)
                              .join(Stock)
                              .all())
            
            stocks_with_recommendations = []
            
            for holding in portfolio_stocks:
                stock = holding.stock
                
                # Get latest recommendation
                latest_recommendation = (Recommendation.query
                                       .filter_by(stock_id=stock.id)
                                       .order_by(desc(Recommendation.created_at))
                                       .first())
                
                # Update stock price if needed
                self.portfolio_service._update_stock_price_if_needed(stock)
                
                stock_data = {
                    'symbol': stock.symbol,
                    'company_name': stock.company_name,
                    'current_price': stock.current_price,
                    'previous_close': stock.previous_close,
                    'price_change_percent': self._calculate_price_change_percent(stock),
                    'shares': holding.shares,
                    'current_value': holding.current_value,
                    'gain_loss': holding.unrealized_gain_loss,
                    'gain_loss_percent': holding.unrealized_gain_loss_percent,
                    'recommendation': {
                        'action': latest_recommendation.recommendation if latest_recommendation else 'HOLD',
                        'confidence': latest_recommendation.confidence_score if latest_recommendation else 0.5,
                        'reasoning': latest_recommendation.reasoning if latest_recommendation else 'No analysis available',
                        'last_updated': latest_recommendation.created_at.isoformat() if latest_recommendation else None,
                        'news_sentiment': latest_recommendation.news_sentiment if latest_recommendation else 0,
                        'technical_score': latest_recommendation.technical_score if latest_recommendation else 0,
                        'fundamental_score': latest_recommendation.fundamental_score if latest_recommendation else 0
                    }
                }
                
                stocks_with_recommendations.append(stock_data)
            
            # Sort by current value (largest holdings first)
            stocks_with_recommendations.sort(key=lambda x: x['current_value'], reverse=True)
            
            return stocks_with_recommendations
            
        except Exception as e:
            self.logger.error(f"Error getting stocks with recommendations: {str(e)}")
            raise
    
    def get_top_recommendation_changes(self, days_back: int = 7) -> List[Dict]:
        """Get stocks with recent recommendation changes"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Get recent recommendation changes
            recent_changes = (RecommendationHistory.query
                            .filter(RecommendationHistory.change_date >= cutoff_date)
                            .join(Stock)
                            .order_by(desc(RecommendationHistory.change_date))
                            .all())
            
            changes_data = []
            
            for change in recent_changes:
                stock = change.stock
                
                # Get current portfolio holding info
                holding = Portfolio.query.filter_by(stock_id=stock.id, is_active=True).first()
                
                if holding:  # Only include stocks in current portfolio
                    # Get latest recommendation
                    latest_recommendation = (Recommendation.query
                                           .filter_by(stock_id=stock.id)
                                           .order_by(desc(Recommendation.created_at))
                                           .first())
                    
                    change_data = {
                        'symbol': stock.symbol,
                        'company_name': stock.company_name,
                        'current_price': stock.current_price,
                        'previous_recommendation': change.previous_recommendation,
                        'new_recommendation': change.new_recommendation,
                        'change_date': change.change_date.isoformat(),
                        'current_value': holding.current_value,
                        'confidence': latest_recommendation.confidence_score if latest_recommendation else 0.5,
                        'reasoning': latest_recommendation.reasoning if latest_recommendation else 'No reasoning available'
                    }
                    
                    changes_data.append(change_data)
            
            return changes_data
            
        except Exception as e:
            self.logger.error(f"Error getting top recommendation changes: {str(e)}")
            raise
    
    def refresh_all_recommendations(self) -> Dict:
        """Refresh recommendations for all portfolio stocks using PARALLEL processing"""
        try:
            portfolio_stocks = Portfolio.query.filter_by(is_active=True).join(Stock).all()
            
            if not portfolio_stocks:
                return {
                    'success': True,
                    'updated_count': 0,
                    'changed_count': 0,
                    'total_stocks': 0,
                    'errors': [],
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            self.logger.info(f"🚀 STARTING PARALLEL PORTFOLIO REFRESH for {len(portfolio_stocks)} stocks")
            
            updated_count = 0
            changed_count = 0
            errors = []
            
            # Define function to analyze a single stock
            def analyze_single_stock(holding):
                try:
                    stock = holding.stock
                    self.logger.info(f"🔍 Analyzing {stock.symbol}...")
                    
                    # Get LLM analysis (already parallelized internally)
                    analysis_result = self.llm_service.analyze_stock(stock.symbol)
                    
                    return {
                        'success': True,
                        'stock': stock,
                        'analysis_result': analysis_result,
                        'holding': holding
                    }
                    
                except Exception as e:
                    error_msg = f"Error analyzing {holding.stock.symbol}: {str(e)}"
                    self.logger.error(error_msg)
                    return {
                        'success': False,
                        'error': error_msg,
                        'stock': holding.stock,
                        'holding': holding
                    }
            
            # PARALLEL EXECUTION: Analyze all stocks concurrently
            max_workers = min(len(portfolio_stocks), 5)  # Limit concurrent API calls
            self.logger.info(f"⚡ Running {len(portfolio_stocks)} stock analyses with {max_workers} parallel workers")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all stock analyses
                future_to_stock = {
                    executor.submit(analyze_single_stock, holding): holding.stock.symbol
                    for holding in portfolio_stocks
                }
                
                # Process completed analyses
                for future in as_completed(future_to_stock):
                    symbol = future_to_stock[future]
                    try:
                        result = future.result()
                        
                        if result['success']:
                            # Process successful analysis
                            stock = result['stock']
                            analysis_result = result['analysis_result']
                            
                            # Get previous recommendation
                            previous_recommendation = (Recommendation.query
                                                     .filter_by(stock_id=stock.id)
                                                     .order_by(desc(Recommendation.created_at))
                                                     .first())
                            
                            # Create new recommendation
                            new_recommendation = Recommendation(
                                stock_id=stock.id,
                                recommendation=analysis_result['recommendation'],
                                confidence_score=analysis_result['confidence_score'],
                                reasoning=analysis_result['reasoning'],
                                news_sentiment=analysis_result['news_sentiment'],
                                technical_score=analysis_result['technical_score'],
                                fundamental_score=analysis_result['fundamental_score'],
                                recent_news=analysis_result['recent_news'],
                                technical_indicators=analysis_result['technical_indicators']
                            )
                            
                            db.session.add(new_recommendation)
                            
                            # Check if recommendation changed
                            if (previous_recommendation and 
                                previous_recommendation.recommendation != analysis_result['recommendation']):
                                
                                # Record the change
                                change_record = RecommendationHistory(
                                    stock_id=stock.id,
                                    previous_recommendation=previous_recommendation.recommendation,
                                    new_recommendation=analysis_result['recommendation']
                                )
                                
                                db.session.add(change_record)
                                changed_count += 1
                                
                                self.logger.info(f"📈 {stock.symbol}: {previous_recommendation.recommendation} -> {analysis_result['recommendation']}")
                            
                            updated_count += 1
                            self.logger.info(f"✅ {symbol} analysis completed successfully")
                            
                        else:
                            # Handle failed analysis
                            errors.append(result['error'])
                            
                    except Exception as e:
                        error_msg = f"Error processing result for {symbol}: {str(e)}"
                        self.logger.error(error_msg)
                        errors.append(error_msg)
            
            # Commit all changes at once
            db.session.commit()
            
            self.logger.info(f"🎉 PARALLEL PORTFOLIO REFRESH COMPLETE!")
            self.logger.info(f"   Updated: {updated_count}/{len(portfolio_stocks)} stocks")
            self.logger.info(f"   Changed recommendations: {changed_count}")
            self.logger.info(f"   Errors: {len(errors)}")
            
            return {
                'success': True,
                'updated_count': updated_count,
                'changed_count': changed_count,
                'total_stocks': len(portfolio_stocks),
                'errors': errors,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error in parallel portfolio refresh: {str(e)}")
            raise
    
    def get_recommendation_for_stock(self, symbol: str) -> Optional[Dict]:
        """Get the latest recommendation for a specific stock"""
        try:
            stock = Stock.query.filter_by(symbol=symbol.upper()).first()
            if not stock:
                return None
            
            latest_recommendation = (Recommendation.query
                                   .filter_by(stock_id=stock.id)
                                   .order_by(desc(Recommendation.created_at))
                                   .first())
            
            if not latest_recommendation:
                return None
            
            return {
                'symbol': stock.symbol,
                'company_name': stock.company_name,
                'recommendation': latest_recommendation.recommendation,
                'confidence_score': latest_recommendation.confidence_score,
                'reasoning': latest_recommendation.reasoning,
                'news_sentiment': latest_recommendation.news_sentiment,
                'technical_score': latest_recommendation.technical_score,
                'fundamental_score': latest_recommendation.fundamental_score,
                'created_at': latest_recommendation.created_at.isoformat(),
                'recent_news': latest_recommendation.recent_news,
                'technical_indicators': latest_recommendation.technical_indicators
            }
            
        except Exception as e:
            self.logger.error(f"Error getting recommendation for {symbol}: {str(e)}")
            return None
    
    def create_recommendation_for_stock(self, symbol: str) -> Optional[Dict]:
        """Create a new recommendation for a stock using LLM analysis"""
        try:
            stock = Stock.query.filter_by(symbol=symbol.upper()).first()
            if not stock:
                # Try to create the stock first
                stock = self.portfolio_service._get_or_create_stock(symbol.upper())
                if not stock:
                    return None
            
            # Get LLM analysis
            analysis_result = self.llm_service.analyze_stock(stock.symbol)
            
            # Get previous recommendation for change tracking
            previous_recommendation = (Recommendation.query
                                     .filter_by(stock_id=stock.id)
                                     .order_by(desc(Recommendation.created_at))
                                     .first())
            
            # Create new recommendation
            new_recommendation = Recommendation(
                stock_id=stock.id,
                recommendation=analysis_result['recommendation'],
                confidence_score=analysis_result['confidence_score'],
                reasoning=analysis_result['reasoning'],
                news_sentiment=analysis_result['news_sentiment'],
                technical_score=analysis_result['technical_score'],
                fundamental_score=analysis_result['fundamental_score'],
                recent_news=analysis_result['recent_news'],
                technical_indicators=analysis_result['technical_indicators']
            )
            
            db.session.add(new_recommendation)
            
            # Track recommendation change if applicable
            if (previous_recommendation and 
                previous_recommendation.recommendation != analysis_result['recommendation']):
                
                change_record = RecommendationHistory(
                    stock_id=stock.id,
                    previous_recommendation=previous_recommendation.recommendation,
                    new_recommendation=analysis_result['recommendation']
                )
                
                db.session.add(change_record)
            
            db.session.commit()
            
            return {
                'symbol': stock.symbol,
                'recommendation': new_recommendation.recommendation,
                'confidence_score': new_recommendation.confidence_score,
                'reasoning': new_recommendation.reasoning,
                'created_at': new_recommendation.created_at.isoformat()
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error creating recommendation for {symbol}: {str(e)}")
            return None
    
    def _calculate_price_change_percent(self, stock: Stock) -> float:
        """Calculate price change percentage from previous close"""
        if not stock.current_price or not stock.previous_close:
            return 0.0
        
        return ((stock.current_price - stock.previous_close) / stock.previous_close) * 100