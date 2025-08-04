import requests
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote
from models import User, Stock, Portfolio, db

logger = logging.getLogger(__name__)

class UpstoxService:
    """Service for Upstox OAuth authentication and API interactions"""
    
    def __init__(self):
        self.client_id = os.getenv('UPSTOX_API_KEY')
        self.client_secret = os.getenv('UPSTOX_API_SECRET')
        self.redirect_uri = os.getenv('UPSTOX_REDIRECT_URI', 'http://localhost:8000/auth/upstox/callback')
        
        # API endpoints
        self.base_url = 'https://api.upstox.com/v2'
        self.auth_url = 'https://api.upstox.com/v2/login/authorization/dialog'
        self.token_url = 'https://api.upstox.com/v2/login/authorization/token'
        
        self.logger = logger
        
        if not self.client_id or not self.client_secret:
            self.logger.warning("❌ Upstox API credentials not configured")
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Generate Upstox authorization URL"""
        try:
            params = {
                'response_type': 'code',
                'client_id': self.client_id,
                'redirect_uri': self.redirect_uri,
            }
            
            if state:
                params['state'] = state
            
            # Build URL with proper encoding
            query_string = '&'.join([f"{k}={quote(str(v))}" for k, v in params.items()])
            auth_url = f"{self.auth_url}?{query_string}"
            
            self.logger.info(f"🔗 Generated Upstox authorization URL")
            return auth_url
            
        except Exception as e:
            self.logger.error(f"Error generating authorization URL: {str(e)}")
            raise
    
    def exchange_code_for_token(self, authorization_code: str) -> Dict:
        """Exchange authorization code for access token and user profile"""
        try:
            data = {
                'code': authorization_code,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'redirect_uri': self.redirect_uri,
                'grant_type': 'authorization_code'
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
            
            self.logger.info("🔄 Exchanging authorization code for access token...")
            response = requests.post(self.token_url, data=data, headers=headers)
            
            if response.status_code == 200:
                token_data = response.json()
                self.logger.info("✅ Successfully obtained access token and user profile")
                return token_data
            else:
                self.logger.error(f"❌ Token exchange failed: {response.status_code} - {response.text}")
                raise Exception(f"Token exchange failed: {response.text}")
                
        except Exception as e:
            self.logger.error(f"Error exchanging code for token: {str(e)}")
            raise
    
    def create_or_update_user(self, user_data: Dict) -> User:
        """Create or update user with Upstox data"""
        try:
            upstox_user_id = user_data.get('user_id')
            email = user_data.get('email')
            
            if not upstox_user_id or not email:
                raise ValueError("Missing required user data (user_id or email)")
            
            # Look for existing user by Upstox user ID or email
            user = User.query.filter(
                (User.upstox_user_id == upstox_user_id) | 
                (User.email == email)
            ).first()
            
            if user:
                # Update existing user
                user.upstox_user_id = upstox_user_id
                user.email = email
                user.name = user_data.get('user_name', user.name)
                self.logger.info(f"📝 Updated existing user: {user.email}")
            else:
                # Create new user
                user = User(
                    upstox_user_id=upstox_user_id,
                    email=email,
                    name=user_data.get('user_name', email.split('@')[0].title()),
                    picture=''  # Upstox doesn't provide profile pictures
                )
                db.session.add(user)
                self.logger.info(f"👤 Created new user: {user.email}")
            
            # Update Upstox-specific fields
            user.broker = user_data.get('broker', 'UPSTOX')
            user.user_type = user_data.get('user_type', 'individual')
            user.exchanges = user_data.get('exchanges', [])
            user.products = user_data.get('products', [])
            user.order_types = user_data.get('order_types', [])
            user.is_upstox_active = user_data.get('is_active', True)
            user.poa = user_data.get('poa', False)
            user.last_login = datetime.utcnow()
            
            # Store tokens
            access_token = user_data.get('access_token')
            extended_token = user_data.get('extended_token')
            
            if access_token:
                # Upstox tokens expire at 3:30 AM next day
                tomorrow = datetime.utcnow().date() + timedelta(days=1)
                expires_at = datetime.combine(tomorrow, datetime.min.time().replace(hour=3, minute=30))
                user.update_upstox_tokens(access_token, extended_token, expires_at)
            
            db.session.commit()
            return user
            
        except Exception as e:
            self.logger.error(f"Error creating/updating user: {str(e)}")
            db.session.rollback()
            raise
    
    def get_holdings(self, access_token: str) -> List[Dict]:
        """Fetch user's long-term holdings from Upstox"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            url = f"{self.base_url}/portfolio/long-term-holdings"
            self.logger.info("📊 Fetching long-term holdings from Upstox...")
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                holdings = data.get('data', [])
                self.logger.info(f"✅ Fetched {len(holdings)} holdings")
                return holdings
            else:
                self.logger.error(f"❌ Failed to fetch holdings: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error fetching holdings: {str(e)}")
            return []
    
    def get_positions(self, access_token: str) -> List[Dict]:
        """Fetch user's short-term positions from Upstox"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            url = f"{self.base_url}/portfolio/short-term-positions"
            self.logger.info("📈 Fetching short-term positions from Upstox...")
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                positions = data.get('data', [])
                self.logger.info(f"✅ Fetched {len(positions)} positions")
                return positions
            else:
                self.logger.error(f"❌ Failed to fetch positions: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error fetching positions: {str(e)}")
            return []
    
    def sync_portfolio_to_database(self, user: User) -> Dict:
        """Sync user's Upstox portfolio to local database"""
        try:
            if not user.is_upstox_token_valid:
                self.logger.warning(f"⚠️ Upstox token expired for user {user.email}")
                return {'success': False, 'error': 'Token expired'}
            
            # Fetch holdings and positions
            holdings = self.get_holdings(user.upstox_access_token)
            positions = self.get_positions(user.upstox_access_token)
            
            # Combine holdings and positions for portfolio sync
            all_positions = holdings + positions
            
            synced_count = 0
            errors = []
            
            for position in all_positions:
                try:
                    # Extract stock information
                    instrument_key = position.get('instrument_key', '')
                    trading_symbol = position.get('trading_symbol', '')
                    
                    if not trading_symbol:
                        continue
                    
                    # Convert to standard stock symbol (remove exchange prefix if present)
                    symbol = self._extract_symbol_from_trading_symbol(trading_symbol)
                    
                    if not symbol:
                        continue
                    
                    # Get or create stock
                    stock = self._get_or_create_stock_from_upstox(symbol, position)
                    
                    if not stock:
                        continue
                    
                    # Extract position data
                    quantity = float(position.get('quantity', 0))
                    average_price = float(position.get('average_price', 0))
                    
                    if quantity <= 0:
                        continue
                    
                    # Update or create portfolio entry
                    self._update_portfolio_entry(user.id, stock.id, quantity, average_price)
                    synced_count += 1
                    
                except Exception as e:
                    error_msg = f"Error syncing position {position.get('trading_symbol', 'unknown')}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
            
            # Update last sync time
            user.upstox_last_sync = datetime.utcnow()
            db.session.commit()
            
            result = {
                'success': True,
                'synced_count': synced_count,
                'total_positions': len(all_positions),
                'errors': errors
            }
            
            self.logger.info(f"🔄 Portfolio sync completed for {user.email}: {synced_count}/{len(all_positions)} positions synced")
            return result
            
        except Exception as e:
            self.logger.error(f"Error syncing portfolio for user {user.email}: {str(e)}")
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def _extract_symbol_from_trading_symbol(self, trading_symbol: str) -> Optional[str]:
        """Extract clean stock symbol from Upstox trading symbol"""
        try:
            # Upstox trading symbols are usually just the symbol for equities
            # For derivatives, they have additional info which we'll ignore for now
            symbol = trading_symbol.split(' ')[0]  # Take first part before any space
            return symbol.upper() if symbol else None
        except:
            return None
    
    def _get_or_create_stock_from_upstox(self, symbol: str, position_data: Dict) -> Optional[Stock]:
        """Get or create stock entry from Upstox position data"""
        try:
            # Check if stock already exists
            stock = Stock.query.filter_by(symbol=symbol).first()
            
            if stock:
                return stock
            
            # Create new stock from Upstox data
            # Note: Upstox doesn't provide detailed company info in portfolio APIs
            # We'll need to use yfinance for additional data
            stock = Stock(
                symbol=symbol,
                company_name=position_data.get('instrument_name', symbol),
                current_price=position_data.get('last_price', 0),
                last_updated=datetime.utcnow()
            )
            
            db.session.add(stock)
            db.session.commit()
            
            self.logger.info(f"📊 Created new stock: {symbol}")
            return stock
            
        except Exception as e:
            self.logger.error(f"Error creating stock {symbol}: {str(e)}")
            db.session.rollback()
            return None
    
    def _update_portfolio_entry(self, user_id: int, stock_id: int, quantity: float, average_price: float):
        """Update or create portfolio entry"""
        try:
            # Check for existing entry
            portfolio_entry = Portfolio.query.filter_by(
                user_id=user_id, 
                stock_id=stock_id, 
                is_active=True
            ).first()
            
            if portfolio_entry:
                # Update existing entry
                portfolio_entry.shares = quantity
                portfolio_entry.average_cost = average_price
                portfolio_entry.updated_at = datetime.utcnow()
            else:
                # Create new entry
                portfolio_entry = Portfolio(
                    user_id=user_id,
                    stock_id=stock_id,
                    shares=quantity,
                    average_cost=average_price,
                    purchase_date=datetime.utcnow().date()
                )
                db.session.add(portfolio_entry)
            
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error updating portfolio entry: {str(e)}")
            db.session.rollback()
            raise 