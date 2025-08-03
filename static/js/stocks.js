// Stocks page JavaScript functionality

class StocksPage {
    constructor() {
        this.app = window.financeApp;
        this.stocks = [];
        this.filteredStocks = [];
        this.currentFilter = 'all';
        this.currentSort = 'value';
        this.init();
    }

    init() {
        this.loadStocks();
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Filter buttons
        const filterButtons = document.querySelectorAll('.filter-btn');
        filterButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.setFilter(e.target.dataset.filter);
            });
        });

        // Sort dropdown
        const sortSelect = document.getElementById('sort-select');
        if (sortSelect) {
            sortSelect.addEventListener('change', (e) => {
                this.setSortCriteria(e.target.value);
            });
        }

        // Stock card clicks for modal
        document.addEventListener('click', (e) => {
            const stockCard = e.target.closest('.stock-card');
            if (stockCard) {
                const symbol = stockCard.dataset.symbol;
                this.openStockModal(symbol);
            }
        });
    }

    async loadStocks() {
        try {
            this.stocks = await this.app.getAllStocks();
            this.filteredStocks = [...this.stocks];
            this.renderStocks();
        } catch (error) {
            console.error('Error loading stocks:', error);
            this.renderErrorState();
        }
    }

    setFilter(filter) {
        this.currentFilter = filter;
        
        // Update active filter button
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.filter === filter);
        });

        this.applyFiltersAndSort();
    }

    setSortCriteria(sortBy) {
        this.currentSort = sortBy;
        this.applyFiltersAndSort();
    }

    applyFiltersAndSort() {
        // Apply filter
        if (this.currentFilter === 'all') {
            this.filteredStocks = [...this.stocks];
        } else {
            this.filteredStocks = this.stocks.filter(stock => 
                stock.recommendation.action === this.currentFilter
            );
        }

        // Apply sort
        this.filteredStocks.sort((a, b) => {
            switch (this.currentSort) {
                case 'symbol':
                    return a.symbol.localeCompare(b.symbol);
                case 'recommendation':
                    const order = { 'BUY': 0, 'HOLD': 1, 'SELL': 2 };
                    return order[a.recommendation.action] - order[b.recommendation.action];
                case 'change':
                    const changeA = ((a.current_price - a.previous_close) / a.previous_close) * 100;
                    const changeB = ((b.current_price - b.previous_close) / b.previous_close) * 100;
                    return changeB - changeA;
                case 'gain_loss':
                    return b.gain_loss_percent - a.gain_loss_percent;
                case 'value':
                default:
                    return b.current_value - a.current_value;
            }
        });

        this.renderStocks();
    }

    renderStocks() {
        const container = document.getElementById('stocks-grid');
        if (!container) return;

        if (!this.filteredStocks || this.filteredStocks.length === 0) {
            container.innerHTML = `
                <div class="loading-placeholder">
                    <i class="fas fa-chart-pie"></i>
                    <p>No stocks found matching the current filter.</p>
                </div>
            `;
            return;
        }

        const stocksHtml = this.filteredStocks.map(stock => this.createStockCard(stock)).join('');
        container.innerHTML = stocksHtml;
    }

    createStockCard(stock) {
        const recommendation = stock.recommendation;
        const priceChange = stock.current_price && stock.previous_close ? 
            ((stock.current_price - stock.previous_close) / stock.previous_close) * 100 : 0;
        
        return `
            <div class="stock-card" data-symbol="${stock.symbol}">
                <div class="stock-header">
                    <div class="stock-info">
                        <h3>${stock.symbol}</h3>
                        <p>${stock.company_name}</p>
                    </div>
                    <div class="stock-price">
                        <div class="current-price">${this.app.formatCurrency(stock.current_price)}</div>
                        <div class="price-change ${this.app.getGainLossClass(priceChange)}">
                            ${priceChange > 0 ? '+' : ''}${priceChange.toFixed(2)}%
                        </div>
                    </div>
                </div>
                
                <div class="stock-metrics">
                    <div class="metric">
                        <span class="metric-label">Shares</span>
                        <span class="metric-value">${stock.shares}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Current Value</span>
                        <span class="metric-value">${this.app.formatCurrency(stock.current_value)}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Gain/Loss</span>
                        <span class="metric-value ${this.app.getGainLossClass(stock.gain_loss)}">
                            ${this.app.formatCurrency(stock.gain_loss)}
                        </span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Gain/Loss %</span>
                        <span class="metric-value ${this.app.getGainLossClass(stock.gain_loss_percent)}">
                            ${stock.gain_loss_percent > 0 ? '+' : ''}${stock.gain_loss_percent.toFixed(2)}%
                        </span>
                    </div>
                </div>
                
                <div class="stock-recommendation">
                    <div class="recommendation-badge ${recommendation.action}">
                        ${recommendation.action}
                    </div>
                    <div class="confidence-score">
                        <span>Confidence:</span>
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: ${(recommendation.confidence * 100)}%"></div>
                        </div>
                        <span>${(recommendation.confidence * 100).toFixed(0)}%</span>
                    </div>
                </div>
            </div>
        `;
    }

    openStockModal(symbol) {
        const stock = this.stocks.find(s => s.symbol === symbol);
        if (stock && this.app) {
            this.app.openStockModal(stock);
        }
    }

    renderErrorState() {
        const container = document.getElementById('stocks-grid');
        if (container) {
            container.innerHTML = `
                <div class="loading-placeholder">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Error loading stocks data</p>
                </div>
            `;
        }
    }
}

// Initialize stocks page when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Wait for main app to be initialized
    const initStocksPage = () => {
        if (window.financeApp) {
            window.stocksPage = new StocksPage();
        } else {
            setTimeout(initStocksPage, 100);
        }
    };
    
    initStocksPage();
});