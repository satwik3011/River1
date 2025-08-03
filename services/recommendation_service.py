import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
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
        """Refresh recommendations for all portfolio stocks"""
        try:
            portfolio_stocks = Portfolio.query.filter_by(is_active=True).join(Stock).all()
            
            updated_count = 0
            changed_count = 0
            errors = []
            
            for holding in portfolio_stocks:
                try:
                    stock = holding.stock
                    self.logger.info(f"Analyzing {stock.symbol}...")
                    
                    # Get LLM analysis
                    analysis_result = self.llm_service.analyze_stock(stock.symbol)
                    
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
                        
                        self.logger.info(f"{stock.symbol}: {previous_recommendation.recommendation} -> {analysis_result['recommendation']}")
                    
                    updated_count += 1
                    
                except Exception as e:
                    error_msg = f"Error analyzing {holding.stock.symbol}: {str(e)}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)
            
            db.session.commit()
            
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
            self.logger.error(f"Error refreshing all recommendations: {str(e)}")
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