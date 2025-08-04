from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import logging
import traceback

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///river.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Session configuration for OAuth state persistence
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize extensions
from models import db
db.init_app(app)
CORS(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access River portfolio.'

# Configure logging with detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Initialize database first
with app.app_context():
    # Import models after app context
    from models import User, Stock, Recommendation, Portfolio, RecommendationHistory
    db.create_all()
    logger.info("Database tables created successfully")

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Import services after models
from services.portfolio_service import PortfolioService
from services.llm_analysis_service import LLMAnalysisService
from services.recommendation_service import RecommendationService
from services.upstox_service import UpstoxService

# Initialize services
portfolio_service = PortfolioService()
llm_service = LLMAnalysisService()
recommendation_service = RecommendationService()
upstox_service = UpstoxService()

@app.route('/')
@login_required
def home():
    """Home page with portfolio overview and top changes"""
    return render_template('index.html')

@app.route('/api/portfolio/overview')
@login_required
def get_portfolio_overview():
    """Get portfolio overview data"""
    try:
        overview = portfolio_service.get_portfolio_overview(current_user.id)
        return jsonify(overview)
    except Exception as e:
        logger.error(f"Error getting portfolio overview: {str(e)}")
        return jsonify({'error': 'Failed to fetch portfolio overview'}), 500

@app.route('/api/stocks')
@login_required
def get_all_stocks():
    """Get all stocks with current recommendations"""
    try:
        stocks = recommendation_service.get_all_stocks_with_recommendations()
        return jsonify(stocks)
    except Exception as e:
        logger.error(f"Error getting stocks: {str(e)}")
        return jsonify({'error': 'Failed to fetch stocks'}), 500

@app.route('/api/stocks/top-changes')
@login_required
def get_top_changes():
    """Get stocks with recent recommendation changes"""
    try:
        changes = recommendation_service.get_top_recommendation_changes()
        return jsonify(changes)
    except Exception as e:
        logger.error(f"Error getting top changes: {str(e)}")
        return jsonify({'error': 'Failed to fetch top changes'}), 500

@app.route('/api/analyze/<symbol>')
@login_required
def analyze_stock(symbol):
    """Trigger LLM analysis for a specific stock and save to database"""
    try:
        # Use recommendation service to analyze and save to database
        result = recommendation_service.create_recommendation_for_stock(symbol.upper())
        
        if result:
            logger.info(f"✅ Analysis saved for {symbol}: {result['recommendation']} (confidence: {result['confidence_score']:.2f})")
            return jsonify({
                'success': True,
                'symbol': symbol.upper(),
                'message': f'Analysis completed for {symbol.upper()}',
                'recommendation': result['recommendation'],
                'confidence': result['confidence_score'],
                'timestamp': result['created_at']
            })
        else:
            logger.error(f"Failed to create recommendation for {symbol}")
            return jsonify({'error': f'Failed to analyze stock {symbol}'}), 500
            
    except Exception as e:
        logger.error(f"Error analyzing stock {symbol}: {str(e)}")
        return jsonify({'error': f'Failed to analyze stock {symbol}'}), 500

@app.route('/api/refresh-all')
@login_required
def refresh_all_recommendations():
    """Refresh recommendations for all portfolio stocks"""
    try:
        result = recommendation_service.refresh_all_recommendations()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error refreshing recommendations: {str(e)}")
        return jsonify({'error': 'Failed to refresh recommendations'}), 500

@app.route('/api/sync-portfolio')
@login_required
def sync_portfolio():
    """Sync portfolio from Upstox"""
    try:
        if not current_user.upstox_access_token:
            return jsonify({'error': 'Upstox account not connected'}), 400
        
        if not current_user.is_upstox_token_valid:
            return jsonify({'error': 'Upstox token expired. Please reconnect your account'}), 401
        
        result = upstox_service.sync_portfolio_to_database(current_user)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error syncing portfolio: {str(e)}")
        return jsonify({'error': 'Failed to sync portfolio'}), 500

@app.route('/stocks')
@login_required
def stocks_page():
    """Stocks list page"""
    return render_template('stocks.html')

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page - now primarily for Upstox OAuth"""
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    # Simple bypass for development/demo (keeping for backward compatibility)
    if request.method == 'POST':
        email = request.form.get('email')
        if email:
            # Create or get user
            user = User.query.filter_by(email=email).first()
            if not user:
                user = User(
                    google_id=f"demo_{email}",  # Keeping for backward compatibility
                    email=email,
                    name=email.split('@')[0].title(),
                    picture=''
                )
                db.session.add(user)
                db.session.commit()
                logger.info(f"Demo user created: {user.email}")
                
                # Auto-populate demo holdings for new demo users
                try:
                    from services.portfolio_service import PortfolioService
                    from datetime import datetime, timedelta
                    
                    portfolio_service = PortfolioService()
                    
                    # Sample holdings for demo users
                    demo_holdings = [
                        {'symbol': 'META', 'shares': 35, 'average_cost': 185.90, 'days_ago': 75},
                        {'symbol': 'GOOGL', 'shares': 25, 'average_cost': 125.50, 'days_ago': 120},
                        {'symbol': 'MSFT', 'shares': 60, 'average_cost': 280.75, 'days_ago': 200},
                        {'symbol': 'TSLA', 'shares': 40, 'average_cost': 220.15, 'days_ago': 90},
                        {'symbol': 'NVDA', 'shares': 15, 'average_cost': 420.80, 'days_ago': 150}
                    ]
                    
                    holdings_added = 0
                    for holding in demo_holdings:
                        try:
                            purchase_date = (datetime.now() - timedelta(days=holding['days_ago'])).date()
                            success = portfolio_service.add_stock_to_portfolio(
                                symbol=holding['symbol'],
                                shares=holding['shares'],
                                average_cost=holding['average_cost'],
                                user_id=user.id,
                                purchase_date=purchase_date
                            )
                            if success:
                                holdings_added += 1
                        except Exception as e:
                            logger.warning(f"Failed to add demo holding {holding['symbol']}: {str(e)}")
                    
                    logger.info(f"Added {holdings_added} demo holdings for {user.email}")
                    
                except Exception as e:
                    logger.error(f"Error creating demo holdings: {str(e)}")
            
            login_user(user)
            return redirect(url_for('home'))
    
    return render_template('login.html')

@app.route('/auth/upstox')
def upstox_login():
    """Initiate Upstox OAuth login"""
    try:
        # Generate state parameter for security
        state = os.urandom(16).hex()
        session['oauth_state'] = state
        
        # Get authorization URL
        auth_url = upstox_service.get_authorization_url(state)
        
        logger.info("🚀 Redirecting to Upstox OAuth...")
        return redirect(auth_url)
        
    except Exception as e:
        logger.error(f"Error initiating Upstox OAuth: {str(e)}")
        flash('Failed to connect to Upstox. Please try again.', 'error')
        return redirect(url_for('login'))

@app.route('/auth/upstox/callback')
def upstox_callback():
    """Handle Upstox OAuth callback"""
    try:
        # Check for errors from Upstox
        if 'error' in request.args:
            error = request.args.get('error')
            error_description = request.args.get('error_description', 'No description')
            logger.error(f"Upstox OAuth error: {error} - {error_description}")
            flash('Authorization was denied or failed. Please try again.', 'error')
            return redirect(url_for('login'))
        
        # Verify state parameter (with more lenient validation)
        returned_state = request.args.get('state')
        stored_state = session.get('oauth_state')
        
        logger.info(f"🔍 OAuth callback debug - Returned state: {returned_state}, Stored state: {stored_state}")
        
        # Only validate state if both exist (more lenient for development)
        if returned_state and stored_state and returned_state != stored_state:
            logger.error(f"OAuth state mismatch - returned: {returned_state}, stored: {stored_state}")
            flash('Security error. Please try again.', 'error')
            return redirect(url_for('login'))
        elif not stored_state:
            logger.warning("No stored OAuth state found - session may have expired, continuing anyway")
        
        # Get authorization code
        code = request.args.get('code')
        if not code:
            logger.error("No authorization code received from Upstox")
            flash('Authentication failed. Please try again.', 'error')
            return redirect(url_for('login'))
        
        logger.info(f"✅ OAuth callback validation passed - Code: {code[:10]}...")
        
        # Exchange code for token and user data
        logger.info("🔄 Processing Upstox OAuth callback...")
        user_data = upstox_service.exchange_code_for_token(code)
        
        # Create or update user
        user = upstox_service.create_or_update_user(user_data)
        
        # Log in user
        login_user(user)
        
        # Clean up session
        session.pop('oauth_state', None)
        
        # Sync portfolio in background (non-blocking)
        try:
            logger.info("🔄 Starting initial portfolio sync...")
            sync_result = upstox_service.sync_portfolio_to_database(user)
            if sync_result['success']:
                flash(f"Welcome! Synced {sync_result['synced_count']} holdings from your Upstox account.", 'success')
            else:
                flash("Welcome! Portfolio sync will happen in the background.", 'info')
        except Exception as sync_error:
            logger.error(f"Portfolio sync error: {str(sync_error)}")
            flash("Welcome! Portfolio sync will happen in the background.", 'info')
        
        # Redirect to home page
        next_page = session.get('next') or url_for('home')
        session.pop('next', None)
        return redirect(next_page)
        
    except Exception as e:
        logger.error(f"Error during Upstox authentication: {str(e)}")
        logger.error(traceback.format_exc())
        flash('Authentication failed. Please try again.', 'error')
        return redirect(url_for('login'))

# Legacy Google OAuth routes (keeping for backward compatibility)
@app.route('/auth/google')
def google_login():
    """Legacy Google OAuth - redirect to Upstox"""
    flash('Please use Upstox login to connect your trading account.', 'info')
    return redirect(url_for('upstox_login'))

@app.route('/auth/google/callback')
def google_callback():
    """Legacy Google OAuth callback - redirect to login"""
    flash('Google login is no longer supported. Please use Upstox login.', 'info')
    return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

# API route to check Upstox connection status
@app.route('/api/upstox/status')
@login_required
def upstox_status():
    """Check Upstox connection status"""
    try:
        status = {
            'connected': bool(current_user.upstox_access_token),
            'token_valid': current_user.is_upstox_token_valid,
            'user_id': current_user.upstox_user_id,
            'last_sync': current_user.upstox_last_sync.isoformat() if current_user.upstox_last_sync else None,
            'expires_at': current_user.upstox_token_expires_at.isoformat() if current_user.upstox_token_expires_at else None
        }
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error checking Upstox status: {str(e)}")
        return jsonify({'error': 'Failed to check status'}), 500

# Debug route for OAuth testing
@app.route('/debug/oauth')
def debug_oauth():
    """Debug OAuth session state"""
    if app.debug:
        # Test session functionality
        if 'test_counter' not in session:
            session['test_counter'] = 0
        session['test_counter'] += 1
        
        return jsonify({
            'session_working': True,
            'test_counter': session['test_counter'],
            'oauth_state': session.get('oauth_state', 'no oauth state'),
            'session_keys': list(session.keys()),
            'request_args': dict(request.args),
            'cookies': dict(request.cookies)
        })
    else:
        return jsonify({'error': 'Debug mode only'}), 403

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)