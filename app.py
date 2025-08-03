from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
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

# Initialize extensions
from models import db
db.init_app(app)
CORS(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access River portfolio.'

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OAuth
oauth = OAuth(app)

# Use manual Google OAuth configuration (more reliable than auto-discovery)
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url=None,  # Disable auto-discovery
    authorize_url='https://accounts.google.com/oauth2/v2/auth',
    access_token_url='https://oauth2.googleapis.com/token',
    userinfo_endpoint='https://www.googleapis.com/oauth2/v2/userinfo',
    client_kwargs={
        'scope': 'openid email profile'
    }
)
logger.info("Google OAuth configured with manual endpoints")

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

# Initialize services
portfolio_service = PortfolioService()
llm_service = LLMAnalysisService()
recommendation_service = RecommendationService()

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
    """Trigger LLM analysis for a specific stock"""
    try:
        result = llm_service.analyze_stock(symbol.upper())
        return jsonify(result)
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

@app.route('/stocks')
@login_required
def stocks_page():
    """Stocks list page"""
    return render_template('stocks.html')

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    # Simple bypass for development/demo
    if request.method == 'POST':
        email = request.form.get('email')
        if email:
            # Create or get user
            user = User.query.filter_by(email=email).first()
            if not user:
                user = User(
                    google_id=f"demo_{email}",
                    email=email,
                    name=email.split('@')[0].title(),
                    picture=''
                )
                db.session.add(user)
                db.session.commit()
                logger.info(f"Demo user created: {user.email}")
            
            login_user(user)
            return redirect(url_for('home'))
    
    return render_template('login.html')

@app.route('/auth/google')
def google_login():
    """Initiate Google OAuth login"""
    # Force localhost instead of 127.0.0.1 for redirect URI
    redirect_uri = url_for('google_callback', _external=True).replace('127.0.0.1', 'localhost')
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        # Check if there's an error parameter from Google
        if 'error' in request.args:
            error = request.args.get('error')
            error_description = request.args.get('error_description', 'No description')
            logger.error(f"Google OAuth error: {error} - {error_description}")
            return redirect(url_for('login'))
        
        token = google.authorize_access_token()
        
        # Get user info from Google's userinfo endpoint
        user_info = google.parse_id_token(token)
        if not user_info:
            # Fallback: fetch user info directly
            resp = google.get('userinfo', token=token)
            user_info = resp.json()
        
        if user_info and 'email' in user_info:
            # Check if user exists
            google_id = user_info.get('sub') or user_info.get('id')
            user = User.query.filter_by(google_id=google_id).first()
            
            if not user:
                # Create new user
                user = User(
                    google_id=google_id,
                    email=user_info['email'],
                    name=user_info.get('name', user_info['email']),
                    picture=user_info.get('picture', '')
                )
                db.session.add(user)
                db.session.commit()
                logger.info(f"New user created: {user.email}")
            else:
                # Update existing user info
                user.name = user_info.get('name', user.name)
                user.picture = user_info.get('picture', user.picture)
                user.last_login = datetime.utcnow()
                db.session.commit()
                logger.info(f"User logged in: {user.email}")
            
            # Log in user
            login_user(user)
            
            # Redirect to originally requested page or home
            next_page = session.get('next') or url_for('home')
            session.pop('next', None)
            return redirect(next_page)
        else:
            logger.error("Failed to get user info from Google")
            return redirect(url_for('login'))
            
    except Exception as e:
        logger.error(f"Error during Google authentication: {str(e)}")
        return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)