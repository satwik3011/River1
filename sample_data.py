#!/usr/bin/env python3
"""
Sample data script to populate the database with initial portfolio holdings.
Run this script to add some sample stocks to your portfolio for testing.
"""

import os
import sys
from datetime import datetime, timedelta
from app import app, db
from models import User, Stock, Portfolio, Recommendation
from services.portfolio_service import PortfolioService

# Sample portfolio holdings - More diverse portfolio for demo
SAMPLE_HOLDINGS = [
    {
        'symbol': 'AAPL',
        'shares': 50,
        'average_cost': 145.30,
        'purchase_date': datetime.now() - timedelta(days=180)
    },
    {
        'symbol': 'META',
        'shares': 35,
        'average_cost': 185.90,
        'purchase_date': datetime.now() - timedelta(days=75)
    },
    {
        'symbol': 'GOOGL',
        'shares': 25,
        'average_cost': 125.50,
        'purchase_date': datetime.now() - timedelta(days=120)
    },
    {
        'symbol': 'MSFT',
        'shares': 60,
        'average_cost': 280.75,
        'purchase_date': datetime.now() - timedelta(days=200)
    },
    {
        'symbol': 'TSLA',
        'shares': 40,
        'average_cost': 220.15,
        'purchase_date': datetime.now() - timedelta(days=90)
    },
    {
        'symbol': 'NVDA',
        'shares': 15,
        'average_cost': 420.80,
        'purchase_date': datetime.now() - timedelta(days=150)
    }
]

def create_sample_portfolio():
    """Create sample portfolio holdings"""
    with app.app_context():
        portfolio_service = PortfolioService()
        
        # Create or get specific user
        target_user = User.query.filter_by(email='satwikdudeja@gmail.com').first()
        if not target_user:
            target_user = User(
                google_id='satwik_demo_user_001',
                email='satwikdudeja@gmail.com',
                name='Satwik Dudeja',
                picture=''
            )
            db.session.add(target_user)
            db.session.commit()
            print("✓ Created demo user: satwikdudeja@gmail.com")
        else:
            print("✓ Using existing demo user: satwikdudeja@gmail.com")
        
        print("Creating sample portfolio...")
        
        for holding in SAMPLE_HOLDINGS:
            try:
                success = portfolio_service.add_stock_to_portfolio(
                    symbol=holding['symbol'],
                    shares=holding['shares'],
                    average_cost=holding['average_cost'],
                    user_id=target_user.id,
                    purchase_date=holding['purchase_date'].date()
                )
                
                if success:
                    print(f"✓ Added {holding['symbol']}: {holding['shares']} shares @ ${holding['average_cost']}")
                else:
                    print(f"✗ Failed to add {holding['symbol']}")
                    
            except Exception as e:
                print(f"✗ Error adding {holding['symbol']}: {str(e)}")
        
        print(f"\nSample portfolio created with {len(SAMPLE_HOLDINGS)} stocks!")
        print("You can now run the Flask app and see your portfolio.")
        print("\nTo get LLM recommendations, make sure to:")
        print("1. Set your GEMINI_API_KEY in the .env file")
        print("2. Click the 'Refresh' button in the web interface")

def clear_existing_data():
    """Clear existing portfolio data"""
    with app.app_context():
        try:
            # Clear all tables (order matters due to foreign keys)
            Recommendation.query.delete()
            Portfolio.query.delete()
            Stock.query.delete()
            User.query.delete()
            db.session.commit()
            print("✓ Cleared existing data")
        except Exception as e:
            print(f"✗ Error clearing data: {str(e)}")
            db.session.rollback()

def main():
    """Main function to set up sample data"""
    if len(sys.argv) > 1 and sys.argv[1] == '--clear':
        print("Clearing existing data...")
        clear_existing_data()
        return
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("Warning: .env file not found. Please create one with your API keys.")
        print("Make sure to set GEMINI_API_KEY with your Google AI API key.")
        print()
    
    create_sample_portfolio()

if __name__ == '__main__':
    main()