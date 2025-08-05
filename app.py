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

# Import services after app context is established
from services.portfolio_service import PortfolioService
from services.llm_analysis_service import LLMAnalysisService  
from services.recommendation_service import RecommendationService

# Initialize services
portfolio_service = PortfolioService()
llm_service = LLMAnalysisService()
recommendation_service = RecommendationService()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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

@app.route('/stocks')
@login_required
def stocks_page():
    """Stocks list page"""
    return render_template('stocks.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page with demo and Google OAuth options"""
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
    """Google OAuth login"""
    # TODO: Implement proper Google OAuth
    flash('Google OAuth not yet implemented. Use demo login for now.', 'info')
    return redirect(url_for('login'))

@app.route('/auth/google/callback')
def google_callback():
    """Google OAuth callback"""
    # TODO: Implement proper Google OAuth callback
    flash('Google OAuth not yet implemented. Use demo login for now.', 'info')
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    """Logout user"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Debug route for testing
@app.route('/debug/oauth')
def debug_oauth():
    """Debug OAuth session state"""
    return jsonify({
        'session_working': True,
        'test_counter': session.get('test_counter', 0),
        'oauth_state': session.get('oauth_state', 'no oauth state'),
        'session_keys': list(session.keys()),
        'request_args': dict(request.args),
        'cookies': dict(request.cookies)
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)