from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()
from datetime import datetime
from sqlalchemy import Index

class User(UserMixin, db.Model):
    """Model for user authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Google OAuth fields (keeping for backward compatibility)
    google_id = db.Column(db.String(100), unique=True, nullable=True, index=True)
    
    # Upstox OAuth fields
    upstox_user_id = db.Column(db.String(100), unique=True, nullable=True, index=True)
    upstox_access_token = db.Column(db.Text, nullable=True)  # Current access token
    upstox_extended_token = db.Column(db.Text, nullable=True)  # Long-term token
    upstox_token_expires_at = db.Column(db.DateTime, nullable=True)  # Token expiry
    
    # User profile data
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    picture = db.Column(db.String(200))
    
    # Upstox specific user data
    broker = db.Column(db.String(50), default='UPSTOX')
    user_type = db.Column(db.String(20), default='individual')
    exchanges = db.Column(db.JSON)  # List of enabled exchanges
    products = db.Column(db.JSON)   # List of enabled products
    order_types = db.Column(db.JSON)  # List of enabled order types
    is_upstox_active = db.Column(db.Boolean, default=False)
    poa = db.Column(db.Boolean, default=False)  # Power of Attorney
    
    # General fields
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    upstox_last_sync = db.Column(db.DateTime)  # Last portfolio sync time
    
    # Relationships
    portfolios = db.relationship('Portfolio', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.email}: {self.name}>'
    
    @property
    def is_upstox_token_valid(self):
        """Check if the Upstox access token is still valid"""
        if not self.upstox_access_token or not self.upstox_token_expires_at:
            return False
        return datetime.utcnow() < self.upstox_token_expires_at
    
    def update_upstox_tokens(self, access_token, extended_token=None, expires_at=None):
        """Update Upstox tokens"""
        self.upstox_access_token = access_token
        if extended_token:
            self.upstox_extended_token = extended_token
        if expires_at:
            self.upstox_token_expires_at = expires_at
        db.session.commit()

class Stock(db.Model):
    """Model for stock information"""
    __tablename__ = 'stocks'
    
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), unique=True, nullable=False, index=True)
    company_name = db.Column(db.String(200), nullable=False)
    sector = db.Column(db.String(100))
    current_price = db.Column(db.Float)
    previous_close = db.Column(db.Float)
    market_cap = db.Column(db.BigInteger)
    pe_ratio = db.Column(db.Float)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to recommendations
    recommendations = db.relationship('Recommendation', backref='stock', lazy=True, cascade='all, delete-orphan')
    portfolio_entries = db.relationship('Portfolio', backref='stock', lazy=True)
    
    def __repr__(self):
        return f'<Stock {self.symbol}: {self.company_name}>'

class Recommendation(db.Model):
    """Model for stock recommendations"""
    __tablename__ = 'recommendations'
    
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False)
    recommendation = db.Column(db.Enum('BUY', 'HOLD', 'SELL', name='recommendation_type'), nullable=False)
    confidence_score = db.Column(db.Float)  # 0-1 confidence in the recommendation
    reasoning = db.Column(db.Text)  # LLM reasoning for the recommendation
    
    # Analysis components
    news_sentiment = db.Column(db.Float)  # -1 to 1 sentiment score
    technical_score = db.Column(db.Float)  # -1 to 1 technical analysis score
    fundamental_score = db.Column(db.Float)  # -1 to 1 fundamental analysis score
    
    # News and analysis data
    recent_news = db.Column(db.JSON)  # Store recent news headlines and summaries
    technical_indicators = db.Column(db.JSON)  # Store technical analysis data
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Index for efficient queries
    __table_args__ = (
        Index('idx_stock_created', 'stock_id', 'created_at'),
    )
    
    def __repr__(self):
        return f'<Recommendation {self.stock.symbol if self.stock else "Unknown"}: {self.recommendation}>'

class Portfolio(db.Model):
    """Model for user's portfolio holdings"""
    __tablename__ = 'portfolio'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False)
    shares = db.Column(db.Float, nullable=False)
    average_cost = db.Column(db.Float, nullable=False)
    purchase_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def current_value(self):
        """Calculate current value of the holding"""
        if self.stock and self.stock.current_price:
            return self.shares * self.stock.current_price
        return 0
    
    @property
    def total_cost(self):
        """Calculate total cost basis"""
        return self.shares * self.average_cost
    
    @property
    def unrealized_gain_loss(self):
        """Calculate unrealized gain/loss"""
        return self.current_value - self.total_cost
    
    @property
    def unrealized_gain_loss_percent(self):
        """Calculate unrealized gain/loss percentage"""
        if self.total_cost > 0:
            return (self.unrealized_gain_loss / self.total_cost) * 100
        return 0
    
    def __repr__(self):
        return f'<Portfolio {self.stock.symbol if self.stock else "Unknown"}: {self.shares} shares>'

class RecommendationHistory(db.Model):
    """Model for tracking recommendation changes over time"""
    __tablename__ = 'recommendation_history'
    
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False)
    previous_recommendation = db.Column(db.Enum('BUY', 'HOLD', 'SELL', name='recommendation_type'))
    new_recommendation = db.Column(db.Enum('BUY', 'HOLD', 'SELL', name='recommendation_type'), nullable=False)
    change_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationship to stock
    stock = db.relationship('Stock', backref='recommendation_changes')
    
    def __repr__(self):
        return f'<RecommendationHistory {self.stock.symbol if self.stock else "Unknown"}: {self.previous_recommendation} -> {self.new_recommendation}>'