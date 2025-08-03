import yfinance as yf
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from models import Stock, Portfolio, db

logger = logging.getLogger(__name__)

class PortfolioService:
    """Service for managing portfolio data and stock information"""
    
    def __init__(self):
        self.logger = logger
    
    def get_portfolio_overview(self, user_id: int) -> Dict:
        """Get portfolio overview with total value, gain/loss, and performance metrics"""
        try:
            portfolio_stocks = Portfolio.query.filter_by(user_id=user_id, is_active=True).join(Stock).all()
            
            if not portfolio_stocks:
                return {
                    'total_value': 0,
                    'total_cost': 0,
                    'total_gain_loss': 0,
                    'total_gain_loss_percent': 0,
                    'stock_count': 0,
                    'holdings': []
                }
            
            total_value = 0
            total_cost = 0
            holdings = []
            
            for holding in portfolio_stocks:
                # Update stock price if needed
                self._update_stock_price_if_needed(holding.stock)
                
                holding_data = {
                    'symbol': holding.stock.symbol,
                    'company_name': holding.stock.company_name,
                    'shares': holding.shares,
                    'current_price': holding.stock.current_price,
                    'current_value': holding.current_value,
                    'total_cost': holding.total_cost,
                    'gain_loss': holding.unrealized_gain_loss,
                    'gain_loss_percent': holding.unrealized_gain_loss_percent
                }
                
                holdings.append(holding_data)
                total_value += holding.current_value
                total_cost += holding.total_cost
            
            total_gain_loss = total_value - total_cost
            total_gain_loss_percent = (total_gain_loss / total_cost * 100) if total_cost > 0 else 0
            
            return {
                'total_value': round(total_value, 2),
                'total_cost': round(total_cost, 2),
                'total_gain_loss': round(total_gain_loss, 2),
                'total_gain_loss_percent': round(total_gain_loss_percent, 2),
                'stock_count': len(holdings),
                'holdings': holdings
            }
            
        except Exception as e:
            self.logger.error(f"Error getting portfolio overview: {str(e)}")
            raise
    
    def add_stock_to_portfolio(self, symbol: str, shares: float, average_cost: float, user_id: int, purchase_date: Optional[datetime] = None) -> bool:
        """Add a stock to the portfolio"""
        try:
            symbol = symbol.upper()
            
            # Get or create stock
            stock = self._get_or_create_stock(symbol)
            if not stock:
                return False
            
            # Check if stock already exists in user's portfolio
            existing_holding = Portfolio.query.filter_by(stock_id=stock.id, user_id=user_id, is_active=True).first()
            
            if existing_holding:
                # Update existing holding (average cost calculation)
                total_shares = existing_holding.shares + shares
                total_cost = (existing_holding.shares * existing_holding.average_cost) + (shares * average_cost)
                new_average_cost = total_cost / total_shares
                
                existing_holding.shares = total_shares
                existing_holding.average_cost = new_average_cost
                existing_holding.updated_at = datetime.utcnow()
            else:
                # Create new holding
                new_holding = Portfolio(
                    stock_id=stock.id,
                    user_id=user_id,
                    shares=shares,
                    average_cost=average_cost,
                    purchase_date=purchase_date or datetime.utcnow().date()
                )
                db.session.add(new_holding)
            
            db.session.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding stock {symbol} to portfolio: {str(e)}")
            db.session.rollback()
            return False
    
    def _get_or_create_stock(self, symbol: str) -> Optional[Stock]:
        """Get existing stock or create new one from Yahoo Finance"""
        try:
            # Check if stock already exists
            stock = Stock.query.filter_by(symbol=symbol).first()
            if stock:
                return stock
            
            # Fetch stock data from Yahoo Finance
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info or 'longName' not in info:
                self.logger.error(f"Could not fetch data for symbol {symbol}")
                return None
            
            # Create new stock
            stock = Stock(
                symbol=symbol,
                company_name=info.get('longName', symbol),
                sector=info.get('sector'),
                current_price=info.get('currentPrice'),
                previous_close=info.get('previousClose'),
                market_cap=info.get('marketCap'),
                pe_ratio=info.get('trailingPE')
            )
            
            db.session.add(stock)
            db.session.commit()
            
            return stock
            
        except Exception as e:
            self.logger.error(f"Error creating stock {symbol}: {str(e)}")
            db.session.rollback()
            return None
    
    def _update_stock_price_if_needed(self, stock: Stock) -> bool:
        """Update stock price if data is stale (older than 15 minutes)"""
        try:
            if not stock.last_updated or datetime.utcnow() - stock.last_updated > timedelta(minutes=15):
                ticker = yf.Ticker(stock.symbol)
                info = ticker.info
                
                if info and 'currentPrice' in info:
                    stock.current_price = info.get('currentPrice')
                    stock.previous_close = info.get('previousClose')
                    stock.market_cap = info.get('marketCap')
                    stock.pe_ratio = info.get('trailingPE')
                    stock.last_updated = datetime.utcnow()
                    
                    db.session.commit()
                    return True
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating stock price for {stock.symbol}: {str(e)}")
            return False
    
    def get_stock_price_history(self, symbol: str, period: str = "1mo") -> Dict:
        """Get historical price data for a stock"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            
            if hist.empty:
                return {}
            
            # Convert to format suitable for frontend charts
            history_data = []
            for date, row in hist.iterrows():
                history_data.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'open': round(row['Open'], 2),
                    'high': round(row['High'], 2),
                    'low': round(row['Low'], 2),
                    'close': round(row['Close'], 2),
                    'volume': int(row['Volume'])
                })
            
            return {
                'symbol': symbol,
                'period': period,
                'data': history_data
            }
            
        except Exception as e:
            self.logger.error(f"Error getting price history for {symbol}: {str(e)}")
            return {}