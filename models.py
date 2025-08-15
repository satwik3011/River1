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
    
    # Setu Account Aggregator fields
    setu_user_id = db.Column(db.String(100), unique=True, nullable=True, index=True)
    setu_access_token = db.Column(db.Text, nullable=True)  # Setu access token
    setu_refresh_token = db.Column(db.Text, nullable=True)  # Setu refresh token
    setu_token_expires_at = db.Column(db.DateTime, nullable=True)  # Token expiry
    is_setu_active = db.Column(db.Boolean, default=False)
    setu_last_sync = db.Column(db.DateTime)  # Last portfolio sync time
    
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
    
    @property
    def is_setu_token_valid(self):
        """Check if the Setu access token is still valid"""
        if not self.setu_access_token or not self.setu_token_expires_at:
            return False
        return datetime.utcnow() < self.setu_token_expires_at
    
    def update_upstox_tokens(self, access_token, extended_token=None, expires_at=None):
        """Update Upstox tokens"""
        self.upstox_access_token = access_token
        if extended_token:
            self.upstox_extended_token = extended_token
        if expires_at:
            self.upstox_token_expires_at = expires_at
        db.session.commit()
    
    def update_setu_tokens(self, access_token, refresh_token=None, expires_at=None):
        """Update Setu AA tokens"""
        self.setu_access_token = access_token
        if refresh_token:
            self.setu_refresh_token = refresh_token
        if expires_at:
            self.setu_token_expires_at = expires_at
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

class SetuConsentRequest(db.Model):
    """Model for tracking Setu AA consent requests"""
    __tablename__ = 'setu_consent_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    consent_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    consent_handle = db.Column(db.String(100), nullable=True)
    
    # Consent details
    purpose = db.Column(db.String(200), default='Portfolio Holdings')
    data_life = db.Column(db.JSON)  # Data life period
    frequency = db.Column(db.JSON)  # Data fetch frequency
    fi_types = db.Column(db.JSON)   # Financial Information types requested
    
    # Status tracking
    status = db.Column(db.Enum('PENDING', 'ACTIVE', 'PAUSED', 'REVOKED', 'EXPIRED', name='consent_status'), 
                      default='PENDING', nullable=False, index=True)
    consent_start = db.Column(db.DateTime)
    consent_expiry = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='setu_consents')
    
    def __repr__(self):
        return f'<SetuConsentRequest {self.consent_id}: {self.status}>'

class SetuHolding(db.Model):
    """Model for storing holdings fetched from Setu AA"""
    __tablename__ = 'setu_holdings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    consent_id = db.Column(db.String(100), db.ForeignKey('setu_consent_requests.consent_id'), nullable=False)
    
    # Financial Information Provider details
    fip_id = db.Column(db.String(50), nullable=False)  # Bank/Broker ID
    fip_name = db.Column(db.String(100))
    account_id = db.Column(db.String(100))
    account_type = db.Column(db.String(50))  # DEMAT, TRADING, etc.
    
    # Holding details
    instrument_name = db.Column(db.String(200))
    instrument_type = db.Column(db.String(50))  # EQUITY, MUTUAL_FUND, etc.
    isin = db.Column(db.String(20), index=True)
    symbol = db.Column(db.String(20), index=True)
    exchange = db.Column(db.String(20))
    
    # Quantity and value
    units = db.Column(db.Float)
    average_cost = db.Column(db.Float)
    current_value = db.Column(db.Float)
    market_price = db.Column(db.Float)
    
    # Additional metadata
    raw_data = db.Column(db.JSON)  # Store complete response for debugging
    
    # Timestamps
    holding_date = db.Column(db.Date)  # Date of the holding record
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='setu_holdings')
    consent = db.relationship('SetuConsentRequest', backref='holdings')
    
    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_user_symbol', 'user_id', 'symbol'),
        Index('idx_user_holding_date', 'user_id', 'holding_date'),
    )
    
    def __repr__(self):
        return f'<SetuHolding {self.symbol}: {self.units} units>'