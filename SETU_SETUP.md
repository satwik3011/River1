# Setu Account Aggregator Setup Guide

This guide will help you set up Setu Account Aggregator integration for fetching user holdings in River.

## 1. Environment Variables

Add the following environment variables to your `.env` file:

```bash
# Setu Account Aggregator Configuration
SETU_AA_BASE_URL=https://aa-sandbox.setu.co
SETU_CLIENT_ID=your-setu-client-id
SETU_CLIENT_SECRET=your-setu-client-secret
SETU_REDIRECT_URI=http://localhost:8000/auth/setu/callback

# For production, use:
# SETU_AA_BASE_URL=https://aa.setu.co
```

## 2. Setu Dashboard Configuration

Based on the screenshot you provided, here's what you need to configure in your Setu app:

### Redirect URL
Set this in your Setu app configuration:
```
http://localhost:8000/auth/setu/callback
```

For production, update to your domain:
```
https://yourdomain.com/auth/setu/callback
```

### Data Fetching Options
In the Setu dashboard, enable these options:

1. **Automatically fetch periodic data from FIPs**: ✅ Enable
   - This allows automatic data sync without manual intervention

2. **Allow partial fetch of data, in data fetch sessions**: ✅ Enable  
   - This improves reliability by allowing partial data retrieval

### FI Types (Financial Information Types)
Enable these data types in your Setu app:
- ✅ DEPOSIT (Bank accounts)
- ✅ MUTUAL_FUNDS (Mutual fund holdings)
- ✅ EQUITY (Stock holdings)

### Consent Configuration
The app automatically configures consent requests with:
- **Purpose**: Portfolio Holdings Analysis
- **Data Life**: 12 months
- **Frequency**: Daily updates
- **Data Range**: Last 12 months of data

## 3. Integration Flow

### User Journey:
1. User clicks "Connect Demat Account" on login page (shows info modal)
2. User logs in with email/Google
3. User clicks "Connect Demat" button on dashboard
4. User is redirected to Setu OAuth flow
5. User authorizes access to their financial data
6. User is redirected back to River dashboard
7. Consent request is automatically created
8. User approves consent request through their AA app
9. User can sync holdings data using "Sync Holdings" button

### API Endpoints Created:
- `GET /auth/setu` - Initiate Setu OAuth flow
- `GET /auth/setu/callback` - Handle OAuth callback
- `POST /api/setu/consent/create` - Create consent request
- `GET /api/setu/consent/{id}/status` - Check consent status
- `POST /api/setu/holdings/sync` - Sync holdings data
- `GET /api/setu/holdings/summary` - Get holdings summary
- `POST /api/setu/consent/{id}/revoke` - Revoke consent

## 4. Database Tables Created

The integration adds these new tables:
- `setu_consent_requests` - Track consent requests and their status
- `setu_holdings` - Store fetched holdings data
- Additional columns in `users` table for Setu tokens

## 5. Testing

### Sandbox Testing:
1. Use Setu's sandbox environment for testing
2. Create test consent requests
3. Use mock FIP data to test data fetching
4. Verify holdings sync to local database

### Production Checklist:
- [ ] Update `SETU_AA_BASE_URL` to production URL
- [ ] Update redirect URI in Setu dashboard
- [ ] Test with real bank/broker connections
- [ ] Verify consent flow with actual AA apps
- [ ] Monitor sync performance and error handling

## 6. Security Considerations

- All tokens are stored encrypted in the database
- Consent requests follow RBI AA guidelines
- User data is only accessed with explicit consent
- Tokens have expiration and refresh mechanisms
- All API calls use HTTPS in production

## 7. Troubleshooting

### Common Issues:
1. **OAuth redirect mismatch**: Ensure redirect URI matches exactly
2. **Token expiration**: Implement proper token refresh logic
3. **Consent not approved**: Guide users through AA app approval
4. **Data sync failures**: Check FIP connectivity and consent status

### Logs to Monitor:
- OAuth flow completion
- Consent request creation
- Token refresh attempts  
- Holdings sync success/failure
- API rate limiting

## 8. Next Steps

After basic setup:
1. Implement automatic token refresh
2. Add consent status monitoring
3. Set up periodic holdings sync
4. Add user notifications for consent expiry
5. Implement data reconciliation with existing portfolio

## Support

For Setu-specific issues:
- Documentation: https://docs.setu.co/data/account-aggregator/
- Support: aa@setu.co

For River integration issues:
- Check application logs
- Verify environment variables
- Test with Setu sandbox first