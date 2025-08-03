# River - Smart Portfolio Analytics

A modern web application that analyzes your stock portfolio using AI-powered recommendations. River connects to your portfolio, runs Gemini AI analysis on each stock to determine recent news sentiment, technical analysis, and fundamental analysis to predict **Buy**, **Hold**, or **Sell** recommendations.

## Features

- **Portfolio Overview**: Real-time portfolio value, gain/loss tracking, and performance metrics
- **AI-Powered Analysis**: Uses Google Gemini AI for comprehensive stock analysis including:
  - News sentiment analysis
  - Technical indicator analysis  
  - Fundamental analysis
- **Smart Recommendations**: Get Buy/Hold/Sell recommendations with confidence scores
- **Change Tracking**: Monitor recommendation changes over time
- **Clean Minimal UI**: Modern, responsive design for optimal user experience
- **Real-time Data**: Fetches live stock prices and news from Yahoo Finance

## Tech Stack

- **Backend**: Flask, SQLAlchemy, Python
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Database**: SQLite (configurable to PostgreSQL/MySQL)
- **APIs**: Google Gemini AI, Yahoo Finance (yfinance)
- **Styling**: Custom CSS with modern design system

## Quick Start

### 1. Clone and Install

```bash
git clone <repository-url>
cd River
pip install -r requirements.txt
```

### 2. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your API keys
GEMINI_API_KEY=your-gemini-api-key-here
SECRET_KEY=your-secret-key-here
```

### 3. Initialize Database and Sample Data

```bash
# Add sample portfolio (optional)
python sample_data.py

# Or clear existing data and start fresh
python sample_data.py --clear
```

### 4. Run the Application

```bash
python app.py
```

Visit `http://localhost:5000` in your browser.

## Usage

### Home Page
- **Portfolio Overview**: See your total portfolio value, gain/loss, and stock count
- **Top Holdings**: Quick view of your largest positions with current recommendations  
- **Recent Changes**: Track stocks that changed recommendations in the last 7 days

### All Stocks Page
- **Complete Portfolio**: View all your stocks with current recommendations
- **Filtering**: Filter by Buy/Hold/Sell recommendations
- **Sorting**: Sort by value, symbol, recommendation, price change, or gain/loss
- **Detailed Analysis**: Click any stock for detailed analysis and reasoning

### AI Analysis
- **Comprehensive Scoring**: Each stock gets scored on news sentiment (-1 to +1), technical analysis (-1 to +1), and fundamental analysis (-1 to +1)
- **Final Recommendation**: AI synthesizes all scores into Buy/Hold/Sell with confidence level
- **Detailed Reasoning**: Get explanation for each recommendation
- **Real-time Updates**: Click "Refresh" to update all recommendations

## API Endpoints

- `GET /api/portfolio/overview` - Portfolio summary statistics
- `GET /api/stocks` - All stocks with recommendations  
- `GET /api/stocks/top-changes` - Recent recommendation changes
- `GET /api/analyze/<symbol>` - Analyze a specific stock
- `GET /api/refresh-all` - Refresh all recommendations

## Adding Your Own Stocks

You can add stocks to your portfolio programmatically:

```python
from app import app
from services.portfolio_service import PortfolioService

with app.app_context():
    portfolio_service = PortfolioService()
    
    # Add a stock holding
    portfolio_service.add_stock_to_portfolio(
        symbol='AAPL',
        shares=50,
        average_cost=150.00,
        purchase_date=datetime(2023, 1, 15).date()
    )
```

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required for AI analysis)
- `SECRET_KEY`: Flask secret key for sessions
- `DATABASE_URL`: Database connection string (defaults to SQLite)
- `ALPHA_VANTAGE_API_KEY`: Optional, for additional financial data

### Database

The app uses SQLite by default. For production, set `DATABASE_URL`:

```bash
DATABASE_URL=postgresql://user:password@localhost/finance_db
```

## LLM Analysis Process

1. **Data Gathering**: Fetches stock fundamentals, recent news, and price history
2. **News Sentiment**: Analyzes recent news headlines and summaries for market sentiment
3. **Technical Analysis**: Calculates RSI, moving averages, momentum, and volume indicators  
4. **Fundamental Analysis**: Evaluates P/E ratios, growth metrics, debt levels, and financial health
5. **Final Recommendation**: Synthesizes all analyses into actionable Buy/Hold/Sell recommendation

## Screenshots

### Home Dashboard
![Dashboard showing portfolio overview and top holdings]

### Stock Analysis  
![Detailed stock analysis with AI reasoning and scores]

### All Stocks View
![Complete portfolio view with filtering and sorting options]

## Development

### Project Structure
```
River/
├── app.py                 # Main Flask application
├── models.py             # Database models  
├── requirements.txt      # Python dependencies
├── sample_data.py        # Sample data generator
├── services/             # Business logic services
│   ├── portfolio_service.py      # Portfolio management
│   ├── llm_analysis_service.py   # AI analysis engine
│   └── recommendation_service.py # Recommendation logic
├── templates/            # HTML templates
│   ├── base.html        # Base template
│   ├── index.html       # Home page
│   └── stocks.html      # Stocks page
└── static/              # Static assets
    ├── css/style.css    # Main stylesheet
    └── js/              # JavaScript files
```

### Adding New Features

1. **New Analysis Metrics**: Extend `LLMAnalysisService` to include additional analysis
2. **Different LLM Providers**: Modify `LLMAnalysisService` to support Claude, Gemini, etc.
3. **Additional Data Sources**: Integrate more financial APIs in `PortfolioService`
4. **Mobile App**: The API endpoints are ready for mobile app integration

## Troubleshooting

### Common Issues

1. **No recommendations showing**: Check your `OPENAI_API_KEY` is set correctly
2. **Stock prices not updating**: Yahoo Finance API might be rate-limited, wait a few minutes
3. **Database errors**: Delete `finance_app.db` and restart to reset database

### Logs

Check the console output for detailed error messages and API call information.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable  
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- Check the console logs for error details
- Ensure all API keys are properly configured
- Verify your internet connection for external API calls

---

Built with ❤️ for smart portfolio management