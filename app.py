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
    from models import User, Stock, Recommendation, Portfolio, RecommendationHistory, SetuConsentRequest, SetuHolding
    db.create_all()
    logger.info("Database tables created successfully")

# Import services after app context is established
from services.portfolio_service import PortfolioService
from services.llm_analysis_service import LLMAnalysisService  
from services.recommendation_service import RecommendationService
from services.setu_aa_service import SetuAAService

# Initialize services
portfolio_service = PortfolioService()
llm_service = LLMAnalysisService()
recommendation_service = RecommendationService()
setu_service = SetuAAService()

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

# Setu Account Aggregator routes
@app.route('/auth/setu')
@login_required
def setu_connect():
    """Initiate Setu AA OAuth flow"""
    try:
        state = f"user_{current_user.id}_{datetime.now().timestamp()}"
        session['setu_oauth_state'] = state
        
        auth_url = setu_service.get_auth_url(current_user.id, state)
        return redirect(auth_url)
        
    except Exception as e:
        logger.error(f"Error initiating Setu OAuth: {str(e)}")
        flash('Failed to connect to Setu. Please try again.', 'error')
        return redirect(url_for('login'))

@app.route('/auth/setu/callback')
@login_required
def setu_callback():
    """Handle Setu AA OAuth callback"""
    try:
        # Verify state parameter
        state = request.args.get('state')
        stored_state = session.get('setu_oauth_state')
        
        if not state or state != stored_state:
            flash('Invalid OAuth state. Please try again.', 'error')
            return redirect(url_for('home'))
        
        # Get authorization code
        code = request.args.get('code')
        error = request.args.get('error')
        
        if error:
            flash(f'Setu authorization failed: {error}', 'error')
            return redirect(url_for('home'))
        
        if not code:
            flash('No authorization code received from Setu.', 'error')
            return redirect(url_for('home'))
        
        # Exchange code for tokens
        token_data = setu_service.exchange_code_for_tokens(code)
        if not token_data:
            flash('Failed to get access token from Setu.', 'error')
            return redirect(url_for('home'))
        
        # Update user with Setu tokens
        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')
        expires_in = token_data.get('expires_in', 3600)  # Default 1 hour
        
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        current_user.update_setu_tokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at
        )
        current_user.is_setu_active = True
        db.session.commit()
        
        # Create initial consent request
        consent_request = setu_service.create_consent_request(current_user)
        if consent_request:
            flash('Successfully connected to Setu! Please approve the consent request to fetch your holdings.', 'success')
        else:
            flash('Connected to Setu, but failed to create consent request. You can try again from your dashboard.', 'warning')
        
        # Clear session state
        session.pop('setu_oauth_state', None)
        
        return redirect(url_for('home'))
        
    except Exception as e:
        logger.error(f"Error in Setu callback: {str(e)}")
        flash('An error occurred during Setu authorization. Please try again.', 'error')
        return redirect(url_for('home'))

@app.route('/api/setu/consent/create', methods=['POST'])
@login_required
def create_setu_consent():
    """Create a new Setu consent request"""
    try:
        if not current_user.is_setu_active or not current_user.is_setu_token_valid:
            return jsonify({'error': 'Setu not connected or token expired'}), 401
        
        consent_request = setu_service.create_consent_request(current_user)
        if consent_request:
            return jsonify({
                'success': True,
                'consent_id': consent_request.consent_id,
                'status': consent_request.status,
                'message': 'Consent request created successfully'
            })
        else:
            return jsonify({'error': 'Failed to create consent request'}), 500
            
    except Exception as e:
        logger.error(f"Error creating Setu consent: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/setu/consent/<consent_id>/status')
@login_required
def check_setu_consent_status(consent_id):
    """Check status of a Setu consent request"""
    try:
        if not current_user.is_setu_active or not current_user.is_setu_token_valid:
            return jsonify({'error': 'Setu not connected or token expired'}), 401
        
        status = setu_service.check_consent_status(current_user, consent_id)
        if status:
            return jsonify({
                'consent_id': consent_id,
                'status': status
            })
        else:
            return jsonify({'error': 'Failed to check consent status'}), 500
            
    except Exception as e:
        logger.error(f"Error checking Setu consent status: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/setu/holdings/sync', methods=['POST'])
@login_required
def sync_setu_holdings():
    """Sync holdings from Setu AA"""
    try:
        if not current_user.is_setu_active or not current_user.is_setu_token_valid:
            return jsonify({'error': 'Setu not connected or token expired'}), 401
        
        # Get active consent
        active_consent = current_user.setu_consents.filter_by(status='ACTIVE').first()
        if not active_consent:
            return jsonify({'error': 'No active consent found. Please create and approve a consent request first.'}), 400
        
        # Fetch holdings data
        holdings_data = setu_service.fetch_holdings_data(current_user, active_consent.consent_id)
        if not holdings_data:
            return jsonify({'error': 'Failed to fetch holdings data'}), 500
        
        # Sync to database
        synced_count = setu_service.sync_holdings_to_database(
            current_user, 
            active_consent.consent_id, 
            holdings_data
        )
        
        return jsonify({
            'success': True,
            'synced_count': synced_count,
            'message': f'Successfully synced {synced_count} holdings'
        })
        
    except Exception as e:
        logger.error(f"Error syncing Setu holdings: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/setu/holdings/summary')
@login_required
def get_setu_holdings_summary():
    """Get summary of user's Setu holdings"""
    try:
        if not current_user.is_setu_active:
            return jsonify({'error': 'Setu not connected'}), 401
        
        summary = setu_service.get_user_holdings_summary(current_user)
        return jsonify(summary)
        
    except Exception as e:
        logger.error(f"Error getting Setu holdings summary: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/setu/consent/<consent_id>/revoke', methods=['POST'])
@login_required
def revoke_setu_consent(consent_id):
    """Revoke a Setu consent request"""
    try:
        if not current_user.is_setu_active or not current_user.is_setu_token_valid:
            return jsonify({'error': 'Setu not connected or token expired'}), 401
        
        success = setu_service.revoke_consent(current_user, consent_id)
        if success:
            return jsonify({
                'success': True,
                'message': 'Consent revoked successfully'
            })
        else:
            return jsonify({'error': 'Failed to revoke consent'}), 500
            
    except Exception as e:
        logger.error(f"Error revoking Setu consent: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

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
    # Run HTTP server - we'll use ngrok for HTTPS tunneling
    print("🚀 Starting HTTP server on port 8000...")
    print("💡 Use ngrok for HTTPS: 'ngrok http 8000'")
    app.run(debug=True, host='0.0.0.0', port=8000)