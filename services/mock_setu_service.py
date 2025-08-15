"""
Mock Setu AA Service for testing when sandbox is down
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import current_app
from models import db, User, SetuConsentRequest, SetuHolding, Stock, Portfolio

logger = logging.getLogger(__name__)

class MockSetuAAService:
    """Mock service for testing Setu AA integration when sandbox is down"""
    
    def __init__(self):
        self.base_url = "https://mock-setu.local"
        self.client_id = "mock_client_id"
        self.client_secret = "mock_client_secret"
        self.redirect_uri = "https://river-62s6.onrender.com/auth/setu/callback"
        
    def get_auth_url(self, user_id: int, state: str) -> str:
        """Generate mock OAuth URL that redirects back with mock code"""
        return f"https://river-62s6.onrender.com/auth/setu/callback?code=mock_auth_code_123&state={state}"
    
    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Mock token exchange"""
        if code == "mock_auth_code_123":
            return {
                "access_token": "mock_access_token_123",
                "refresh_token": "mock_refresh_token_123",
                "expires_in": 3600,
                "token_type": "Bearer"
            }
        return None
    
    def create_consent_request(self, user: User) -> Optional[SetuConsentRequest]:
        """Create mock consent request"""
        try:
            consent_request = SetuConsentRequest(
                user_id=user.id,
                consent_id=f"mock_consent_{user.id}_{datetime.now().timestamp()}",
                status="ACTIVE",
                purpose="Portfolio Holdings Analysis - Mock",
                fi_types=["DEPOSIT", "MUTUAL_FUNDS", "EQUITY"],
                data_life_value=12,
                data_life_unit="MONTH",
                frequency_value=1,
                frequency_unit="DAY",
                data_range_from=datetime.now() - timedelta(days=365),
                data_range_to=datetime.now(),
                created_at=datetime.utcnow()
            )
            
            db.session.add(consent_request)
            db.session.commit()
            
            logger.info(f"✅ Mock consent request created: {consent_request.consent_id}")
            return consent_request
            
        except Exception as e:
            logger.error(f"Error creating mock consent request: {str(e)}")
            return None
    
    def check_consent_status(self, user: User, consent_id: str) -> Optional[str]:
        """Mock consent status check"""
        return "ACTIVE"
    
    def fetch_holdings_data(self, user: User, consent_id: str) -> Optional[List[Dict]]:
        """Mock holdings data"""
        return [
            {
                "account_id": "mock_account_1",
                "fip_id": "MOCK_BANK",
                "account_type": "EQUITY",
                "holdings": [
                    {
                        "symbol": "RELIANCE",
                        "isin": "INE002A01018",
                        "quantity": 100,
                        "current_value": 250000,
                        "average_price": 2400
                    },
                    {
                        "symbol": "TCS",
                        "isin": "INE467B01029", 
                        "quantity": 50,
                        "current_value": 200000,
                        "average_price": 3800
                    }
                ]
            }
        ]
    
    def sync_holdings_to_database(self, user: User, consent_id: str, holdings_data: List[Dict]) -> int:
        """Sync mock holdings to database"""
        try:
            synced_count = 0
            
            for account_data in holdings_data:
                for holding in account_data.get('holdings', []):
                    # Create or update holding record
                    existing_holding = SetuHolding.query.filter_by(
                        user_id=user.id,
                        consent_id=consent_id,
                        symbol=holding['symbol']
                    ).first()
                    
                    if existing_holding:
                        # Update existing
                        existing_holding.quantity = holding['quantity']
                        existing_holding.current_value = holding['current_value']
                        existing_holding.average_price = holding['average_price']
                        existing_holding.last_updated = datetime.utcnow()
                    else:
                        # Create new
                        new_holding = SetuHolding(
                            user_id=user.id,
                            consent_id=consent_id,
                            account_id=account_data['account_id'],
                            fip_id=account_data['fip_id'],
                            symbol=holding['symbol'],
                            isin=holding['isin'],
                            quantity=holding['quantity'],
                            current_value=holding['current_value'],
                            average_price=holding['average_price'],
                            account_type=account_data['account_type'],
                            last_updated=datetime.utcnow()
                        )
                        db.session.add(new_holding)
                    
                    synced_count += 1
            
            db.session.commit()
            logger.info(f"✅ Mock sync completed: {synced_count} holdings")
            return synced_count
            
        except Exception as e:
            logger.error(f"Error syncing mock holdings: {str(e)}")
            return 0
    
    def get_user_holdings_summary(self, user: User) -> Dict[str, Any]:
        """Get mock holdings summary"""
        holdings = SetuHolding.query.filter_by(user_id=user.id).all()
        
        total_value = sum(h.current_value for h in holdings)
        total_holdings = len(holdings)
        
        return {
            "total_value": total_value,
            "total_holdings": total_holdings,
            "last_sync": datetime.utcnow().isoformat() if holdings else None,
            "status": "active",
            "holdings": [
                {
                    "symbol": h.symbol,
                    "quantity": h.quantity,
                    "current_value": h.current_value,
                    "average_price": h.average_price
                }
                for h in holdings
            ]
        }
    
    def revoke_consent(self, user: User, consent_id: str) -> bool:
        """Mock consent revocation"""
        consent = SetuConsentRequest.query.filter_by(
            user_id=user.id,
            consent_id=consent_id
        ).first()
        
        if consent:
            consent.status = "REVOKED"
            db.session.commit()
            return True
        return False