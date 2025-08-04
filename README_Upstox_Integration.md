# Upstox OAuth Integration Setup

This document explains how to set up and configure the Upstox OAuth integration for River Portfolio Management.

## Overview

River now uses Upstox OAuth as the primary authentication method, allowing users to:
- Securely connect their Upstox trading accounts
- Auto-sync portfolio holdings from Upstox
- Get AI-powered analysis of their actual holdings
- View real-time portfolio performance

## Prerequisites

1. **Upstox Trading Account**: Users need an active Upstox trading account
2. **Upstox Developer App**: You need to create an app on Upstox Developer Portal
3. **API Credentials**: Get API Key and API Secret from your Upstox app

## Environment Variables

Add these variables to your `.env` file:

```env
# Required for Upstox OAuth
UPSTOX_API_KEY=your-upstox-api-key-here
UPSTOX_API_SECRET=your-upstox-api-secret-here
UPSTOX_REDIRECT_URI=http://localhost:8000/auth/upstox/callback

# Required for AI analysis
GEMINI_API_KEY=your-gemini-api-key-here

# Optional
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///river.db
```

## Upstox App Configuration

When creating your Upstox app, use these settings:

### App Details
- **App Name**: `River1 Portfolio Management`
- **Redirect URL**: `http://localhost:8000/auth/upstox/callback` (development)
- **Redirect URL**: `https://yourdomain.com/auth/upstox/callback` (production)
- **Primary IP**: Leave blank (optional)
- **Secondary IP**: Leave blank (optional)
- **Postback URL**: Leave blank (not needed for portfolio sync)
- **Notifier webhook endpoint**: Leave blank (not needed)

### Description
```
Personal portfolio management application that integrates Upstox holdings data with AI-powered stock analysis and recommendations using Google Gemini.
```

## Architecture

### New Components

1. **UpstoxService** (`services/upstox_service.py`):
   - Handles OAuth authentication flow
   - Fetches user profile and portfolio data
   - Syncs holdings to local database

2. **Updated User Model** (`models.py`):
   - Added Upstox-specific fields
   - Token management and validation
   - Portfolio sync tracking

3. **Updated Authentication Routes** (`app.py`):
   - `/auth/upstox` - Initiate OAuth flow
   - `/auth/upstox/callback` - Handle OAuth callback
   - `/api/sync-portfolio` - Manual portfolio sync
   - `/api/upstox/status` - Check connection status

### Authentication Flow

1. User clicks "Connect Upstox Account"
2. Redirected to Upstox OAuth consent screen
3. User grants permissions
4. Upstox redirects back with authorization code
5. Server exchanges code for access token and user profile
6. User account is created/updated with Upstox data
7. Portfolio holdings are automatically synced
8. User is logged in and redirected to dashboard

## API Endpoints Used

### Upstox APIs
- **Authorization**: `https://api.upstox.com/v2/login/authorization/dialog`
- **Token Exchange**: `https://api.upstox.com/v2/login/authorization/token`
- **Holdings**: `https://api.upstox.com/v2/portfolio/long-term-holdings`
- **Positions**: `https://api.upstox.com/v2/portfolio/short-term-positions`

### New Application APIs
- `GET /api/upstox/status` - Check Upstox connection status
- `POST /api/sync-portfolio` - Manually sync portfolio
- `GET /auth/upstox` - Start OAuth flow
- `GET /auth/upstox/callback` - OAuth callback handler

## Token Management

### Access Token
- **Validity**: Until 3:30 AM next day (Indian time)
- **Storage**: Encrypted in database
- **Auto-refresh**: Not available, user must re-authenticate

### Extended Token
- **Validity**: 1 year (if available)
- **Purpose**: Read-only access for portfolio data
- **Note**: Available only for multi-client applications

## Security Features

1. **OAuth 2.0 Flow**: Standard secure authentication
2. **State Parameter**: CSRF protection during OAuth
3. **Token Validation**: Automatic token expiry checking
4. **Read-Only Access**: Only portfolio data, no trading permissions
5. **Secure Storage**: Tokens encrypted in database

## Database Schema Changes

New User model fields:
```sql
-- Upstox OAuth fields
upstox_user_id VARCHAR(100) UNIQUE
upstox_access_token TEXT
upstox_extended_token TEXT  
upstox_token_expires_at DATETIME

-- Upstox user data
broker VARCHAR(50) DEFAULT 'UPSTOX'
user_type VARCHAR(20) DEFAULT 'individual'
exchanges JSON
products JSON  
order_types JSON
is_upstox_active BOOLEAN DEFAULT FALSE
poa BOOLEAN DEFAULT FALSE
upstox_last_sync DATETIME
```

## Error Handling

Common scenarios and responses:

1. **Token Expired**: User redirected to re-authenticate
2. **API Rate Limits**: Automatic retry with exponential backoff
3. **Invalid Holdings**: Logged but don't block sync process
4. **Network Errors**: Graceful fallback to cached data

## Development Setup

1. **Clone and Install**:
   ```bash
   git clone <repository>
   cd River1
   pip install -r requirements.txt
   ```

2. **Environment Variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Database Migration**:
   ```bash
   python app.py  # Auto-creates tables
   ```

4. **Run Development Server**:
   ```bash
   python3 app.py
   # Visit http://localhost:8000
   ```

## Production Considerations

1. **HTTPS Required**: Upstox requires HTTPS for production redirects
2. **Domain Verification**: Register actual domain in Upstox app
3. **Token Storage**: Consider encryption at rest for tokens
4. **Rate Limits**: Monitor API usage and implement caching
5. **Error Monitoring**: Set up logging for OAuth failures

## Troubleshooting

### Common Issues

1. **"Invalid Credentials" Error**:
   - Check API Key and Secret in .env
   - Verify redirect URI matches exactly
   - Ensure response_type is 'code'

2. **"Token Exchange Failed"**:
   - Authorization code is single-use only
   - Check network connectivity
   - Verify API Secret is correct

3. **"No Holdings Found"**:
   - User may not have any holdings
   - Check if account segments are active
   - Verify API permissions

4. **Portfolio Sync Issues**:
   - Check token validity
   - Verify holdings API response format
   - Review error logs for specific symbols

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Migration from Google OAuth

For existing users with Google OAuth:
1. Google authentication still works (backward compatibility)
2. Users prompted to connect Upstox for portfolio features
3. Email-based demo login still available
4. Gradual migration approach recommended

## Support

- Upstox Developer Documentation: https://upstox.com/developer/
- API Community: https://community.upstox.com/
- Technical Issues: Check logs and error messages first

## License

This integration follows the same license as the main River application. 