"""
Setu Account Aggregator Service
Handles all interactions with Setu AA APIs for consent management and data fetching
"""

import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import os
from flask import current_app
from models import db, User, SetuConsentRequest, SetuHolding, Stock, Portfolio

logger = logging.getLogger(__name__)

class SetuAAService:
    """Service for interacting with Setu Account Aggregator APIs"""
    
    def __init__(self):
        # Setu AA API configuration
        self.base_url = os.getenv('SETU_AA_BASE_URL', 'https://demo-aa.setu.co')
        self.client_id = os.getenv('SETU_CLIENT_ID')
        self.client_secret = os.getenv('SETU_CLIENT_SECRET')
        self.redirect_uri = os.getenv('SETU_REDIRECT_URI', 'http://localhost:8000/auth/setu/callback')
        self.product_instance_id = os.getenv('SETU_PRODUCT_INSTANCE_ID', '169e9bf5-69d0-4994-9b46-dc77ce607fa7')
        
        # Default consent configuration
        self.default_consent_config = {
            "purpose": "Portfolio Holdings Analysis",
            "fiTypes": ["DEPOSIT", "MUTUAL_FUNDS", "EQUITY"],  # Types of financial data
            "dataLife": {
                "unit": "MONTH",
                "value": 12
            },
            "frequency": {
                "unit": "DAY", 
                "value": 1
            },
            "dataRange": {
                "from": (datetime.now() - timedelta(days=365)).isoformat(),
                "to": datetime.now().isoformat()
            }
        }
        
        if not all([self.client_id, self.client_secret]):
            logger.warning("Setu AA credentials not configured. Check environment variables.")
    
    def _get_headers(self, access_token: str = None, content_type: str = "application/json") -> Dict[str, str]:
        """Get standard headers for Setu AA API calls"""
        headers = {
            "Content-Type": content_type,
            "x-product-instance-id": self.product_instance_id
        }
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        return headers
    
    def get_auth_url(self, user_id: int, state: str = None) -> str:
        """
        Generate Setu AA OAuth authorization URL
        """
        if not state:
            state = f"user_{user_id}_{datetime.now().timestamp()}"
        
        auth_url = (
            f"{self.base_url}/oauth/authorize?"
            f"client_id={self.client_id}&"
            f"response_type=code&"
            f"scope=data&"
            f"redirect_uri={self.redirect_uri}&"
            f"state={state}"
        )
        
        logger.info(f"Generated Setu AA auth URL for user {user_id}")
        return auth_url
    
    def exchange_code_for_tokens(self, authorization_code: str) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for access and refresh tokens
        """
        try:
            token_url = f"{self.base_url}/oauth/token"
            
            payload = {
                "grant_type": "authorization_code",
                "code": authorization_code,
                "redirect_uri": self.redirect_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            headers = self._get_headers(content_type="application/x-www-form-urlencoded")
            
            response = requests.post(token_url, data=payload, headers=headers)
            response.raise_for_status()
            
            token_data = response.json()
            logger.info("Successfully exchanged authorization code for tokens")
            return token_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error exchanging code for tokens: {str(e)}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh access token using refresh token
        """
        try:
            token_url = f"{self.base_url}/oauth/token"
            
            payload = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            headers = self._get_headers(content_type="application/x-www-form-urlencoded")
            
            response = requests.post(token_url, data=payload, headers=headers)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error refreshing access token: {str(e)}")
            return None
    
    def create_consent_request(self, user: User, custom_config: Dict = None) -> Optional[SetuConsentRequest]:
        """
        Create a new consent request for the user
        """
        try:
            if not user.is_setu_token_valid:
                logger.error(f"Invalid Setu token for user {user.id}")
                return None
            
            consent_url = f"{self.base_url}/consents"
            config = custom_config or self.default_consent_config
            
            payload = {
                "detail": {
                    "consentStart": datetime.now().isoformat(),
                    "consentExpiry": (datetime.now() + timedelta(days=365)).isoformat(),
                    "Customer": {
                        "id": user.email
                    },
                    "FIDataRange": config["dataRange"],
                    "consentMode": "STORE",
                    "consentTypes": ["TRANSACTIONS", "PROFILE", "SUMMARY"],
                    "fetchType": "PERIODIC",
                    "Frequency": config["frequency"],
                    "DataLife": config["dataLife"],
                    "Purpose": {
                        "code": "101",
                        "refUri": "https://api.rebit.org.in/aa/purpose/101.xml",
                        "text": config["purpose"],
                        "Category": {
                            "type": "purpose"
                        }
                    },
                    "fiTypes": config["fiTypes"]
                }
            }
            
            headers = self._get_headers(access_token=user.setu_access_token)
            
            response = requests.post(consent_url, json=payload, headers=headers)
            response.raise_for_status()
            
            consent_data = response.json()
            
            # Create consent request record
            consent_request = SetuConsentRequest(
                user_id=user.id,
                consent_id=consent_data.get('ConsentId'),
                consent_handle=consent_data.get('ConsentHandle'),
                purpose=config["purpose"],
                data_life=config["dataLife"],
                frequency=config["frequency"],
                fi_types=config["fiTypes"],
                status='PENDING',
                consent_start=datetime.fromisoformat(payload["detail"]["consentStart"].replace('Z', '+00:00')),
                consent_expiry=datetime.fromisoformat(payload["detail"]["consentExpiry"].replace('Z', '+00:00'))
            )
            
            db.session.add(consent_request)
            db.session.commit()
            
            logger.info(f"Created consent request {consent_request.consent_id} for user {user.id}")
            return consent_request
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating consent request: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating consent request: {str(e)}")
            return None
    
    def check_consent_status(self, user: User, consent_id: str) -> Optional[str]:
        """
        Check the status of a consent request
        """
        try:
            if not user.is_setu_token_valid:
                logger.error(f"Invalid Setu token for user {user.id}")
                return None
            
            status_url = f"{self.base_url}/consents/{consent_id}"
            
            headers = self._get_headers(access_token=user.setu_access_token)
            
            response = requests.get(status_url, headers=headers)
            response.raise_for_status()
            
            status_data = response.json()
            consent_status = status_data.get('consentStatus')
            
            # Update local consent record
            consent_request = SetuConsentRequest.query.filter_by(
                consent_id=consent_id,
                user_id=user.id
            ).first()
            
            if consent_request:
                consent_request.status = consent_status
                consent_request.updated_at = datetime.utcnow()
                db.session.commit()
            
            logger.info(f"Consent {consent_id} status: {consent_status}")
            return consent_status
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error checking consent status: {str(e)}")
            return None
    
    def fetch_holdings_data(self, user: User, consent_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch holdings data for an approved consent
        """
        try:
            if not user.is_setu_token_valid:
                logger.error(f"Invalid Setu token for user {user.id}")
                return None
            
            # Check consent status first
            consent_status = self.check_consent_status(user, consent_id)
            if consent_status != 'ACTIVE':
                logger.warning(f"Cannot fetch data for consent {consent_id}. Status: {consent_status}")
                return None
            
            data_url = f"{self.base_url}/sessions"
            
            payload = {
                "consentId": consent_id,
                "DataRange": {
                    "from": (datetime.now() - timedelta(days=30)).isoformat(),
                    "to": datetime.now().isoformat()
                },
                "format": "json"
            }
            
            headers = self._get_headers(access_token=user.setu_access_token)
            
            # Create data session
            response = requests.post(data_url, json=payload, headers=headers)
            response.raise_for_status()
            
            session_data = response.json()
            session_id = session_data.get('sessionId')
            
            if not session_id:
                logger.error("No session ID returned from data request")
                return None
            
            # Fetch the actual data
            fetch_url = f"{self.base_url}/sessions/{session_id}"
            fetch_response = requests.get(fetch_url, headers=headers)
            fetch_response.raise_for_status()
            
            holdings_data = fetch_response.json()
            logger.info(f"Successfully fetched holdings data for consent {consent_id}")
            
            return holdings_data.get('data', [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching holdings data: {str(e)}")
            return None
    
    def sync_holdings_to_database(self, user: User, consent_id: str, holdings_data: List[Dict[str, Any]]) -> int:
        """
        Sync fetched holdings data to local database
        """
        try:
            synced_count = 0
            
            for fip_data in holdings_data:
                fip_id = fip_data.get('fipID')
                fip_name = fip_data.get('fipName', 'Unknown')
                
                for account in fip_data.get('accounts', []):
                    account_id = account.get('linkedAccRef')
                    account_type = account.get('type', 'UNKNOWN')
                    
                    for holding in account.get('holdings', []):
                        # Extract holding details
                        instrument_name = holding.get('description', '')
                        instrument_type = holding.get('type', 'EQUITY')
                        isin = holding.get('isin', '')
                        symbol = self._extract_symbol_from_holding(holding)
                        exchange = holding.get('exchange', '')
                        
                        units = float(holding.get('units', 0))
                        average_cost = float(holding.get('avgCost', 0))
                        current_value = float(holding.get('currentValue', 0))
                        market_price = float(holding.get('marketPrice', 0))
                        
                        # Create or update holding record
                        existing_holding = SetuHolding.query.filter_by(
                            user_id=user.id,
                            consent_id=consent_id,
                            fip_id=fip_id,
                            account_id=account_id,
                            symbol=symbol
                        ).first()
                        
                        if existing_holding:
                            # Update existing record
                            existing_holding.units = units
                            existing_holding.average_cost = average_cost
                            existing_holding.current_value = current_value
                            existing_holding.market_price = market_price
                            existing_holding.fetched_at = datetime.utcnow()
                            existing_holding.raw_data = holding
                        else:
                            # Create new record
                            new_holding = SetuHolding(
                                user_id=user.id,
                                consent_id=consent_id,
                                fip_id=fip_id,
                                fip_name=fip_name,
                                account_id=account_id,
                                account_type=account_type,
                                instrument_name=instrument_name,
                                instrument_type=instrument_type,
                                isin=isin,
                                symbol=symbol,
                                exchange=exchange,
                                units=units,
                                average_cost=average_cost,
                                current_value=current_value,
                                market_price=market_price,
                                holding_date=datetime.now().date(),
                                raw_data=holding
                            )
                            db.session.add(new_holding)
                        
                        synced_count += 1
                        
                        # Also sync to main portfolio if it's an equity
                        if instrument_type == 'EQUITY' and symbol:
                            self._sync_to_main_portfolio(user, symbol, units, average_cost)
            
            db.session.commit()
            
            # Update user's last sync time
            user.setu_last_sync = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"Synced {synced_count} holdings for user {user.id}")
            return synced_count
            
        except Exception as e:
            logger.error(f"Error syncing holdings to database: {str(e)}")
            db.session.rollback()
            return 0
    
    def _extract_symbol_from_holding(self, holding: Dict[str, Any]) -> str:
        """
        Extract stock symbol from holding data
        """
        # Try different fields that might contain the symbol
        symbol = holding.get('symbol', '')
        if not symbol:
            symbol = holding.get('ticker', '')
        if not symbol:
            # Try to extract from description or name
            desc = holding.get('description', '').upper()
            # Simple heuristic: look for patterns like "RELIANCE" or "TCS"
            words = desc.split()
            if words:
                symbol = words[0]  # Take first word as symbol
        
        return symbol.upper() if symbol else ''
    
    def _sync_to_main_portfolio(self, user: User, symbol: str, units: float, average_cost: float):
        """
        Sync Setu holdings to main portfolio table
        """
        try:
            # Find or create stock record
            stock = Stock.query.filter_by(symbol=symbol).first()
            if not stock:
                # Create basic stock record
                stock = Stock(
                    symbol=symbol,
                    company_name=symbol,  # Will be updated later with real data
                    sector='Unknown'
                )
                db.session.add(stock)
                db.session.flush()  # Get the ID
            
            # Find or create portfolio entry
            portfolio_entry = Portfolio.query.filter_by(
                user_id=user.id,
                stock_id=stock.id,
                is_active=True
            ).first()
            
            if portfolio_entry:
                # Update existing portfolio entry
                portfolio_entry.shares = units
                portfolio_entry.average_cost = average_cost
                portfolio_entry.updated_at = datetime.utcnow()
            else:
                # Create new portfolio entry
                portfolio_entry = Portfolio(
                    user_id=user.id,
                    stock_id=stock.id,
                    shares=units,
                    average_cost=average_cost,
                    purchase_date=datetime.now().date()
                )
                db.session.add(portfolio_entry)
            
            logger.debug(f"Synced {symbol} to main portfolio: {units} shares")
            
        except Exception as e:
            logger.error(f"Error syncing {symbol} to main portfolio: {str(e)}")
    
    def get_user_holdings_summary(self, user: User) -> Dict[str, Any]:
        """
        Get summary of user's holdings from Setu AA
        """
        try:
            holdings = SetuHolding.query.filter_by(user_id=user.id).all()
            
            total_value = sum(h.current_value or 0 for h in holdings)
            total_cost = sum((h.units or 0) * (h.average_cost or 0) for h in holdings)
            total_gain_loss = total_value - total_cost
            
            holdings_by_type = {}
            for holding in holdings:
                inst_type = holding.instrument_type or 'UNKNOWN'
                if inst_type not in holdings_by_type:
                    holdings_by_type[inst_type] = {
                        'count': 0,
                        'value': 0,
                        'holdings': []
                    }
                holdings_by_type[inst_type]['count'] += 1
                holdings_by_type[inst_type]['value'] += holding.current_value or 0
                holdings_by_type[inst_type]['holdings'].append({
                    'symbol': holding.symbol,
                    'name': holding.instrument_name,
                    'units': holding.units,
                    'current_value': holding.current_value,
                    'average_cost': holding.average_cost
                })
            
            return {
                'total_holdings': len(holdings),
                'total_value': total_value,
                'total_cost': total_cost,
                'total_gain_loss': total_gain_loss,
                'gain_loss_percent': (total_gain_loss / total_cost * 100) if total_cost > 0 else 0,
                'holdings_by_type': holdings_by_type,
                'last_sync': user.setu_last_sync.isoformat() if user.setu_last_sync else None
            }
            
        except Exception as e:
            logger.error(f"Error getting holdings summary: {str(e)}")
            return {}
    
    def revoke_consent(self, user: User, consent_id: str) -> bool:
        """
        Revoke a consent request
        """
        try:
            if not user.is_setu_token_valid:
                logger.error(f"Invalid Setu token for user {user.id}")
                return False
            
            revoke_url = f"{self.base_url}/consents/{consent_id}"
            
            headers = self._get_headers(access_token=user.setu_access_token)
            
            payload = {
                "status": "REVOKED"
            }
            
            response = requests.patch(revoke_url, json=payload, headers=headers)
            response.raise_for_status()
            
            # Update local record
            consent_request = SetuConsentRequest.query.filter_by(
                consent_id=consent_id,
                user_id=user.id
            ).first()
            
            if consent_request:
                consent_request.status = 'REVOKED'
                consent_request.updated_at = datetime.utcnow()
                db.session.commit()
            
            logger.info(f"Revoked consent {consent_id} for user {user.id}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error revoking consent: {str(e)}")
            return False