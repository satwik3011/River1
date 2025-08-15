// Dashboard-specific JavaScript functionality

class Dashboard {
    constructor() {
        this.app = window.financeApp;
        this.init();
    }

    init() {
        this.loadData();
        this.setupEventListeners();
        this.checkSetuStatus();
    }

    setupEventListeners() {
        // Make holding cards clickable
        document.addEventListener('click', (e) => {
            const holdingCard = e.target.closest('.holding-card');
            if (holdingCard) {
                const symbol = holdingCard.dataset.symbol;
                if (symbol) {
                    this.openStockModal(symbol);
                }
            }
        });
    }

    openStockModal(symbol) {
        const stock = this.stocks?.find(s => s.symbol === symbol);
        if (stock && this.app) {
            this.app.openStockModal(stock);
        }
    }

    async loadData() {
        try {
            // Load all data in parallel
            const [overview, stocks, topChanges] = await Promise.all([
                this.app.getPortfolioOverview(),
                this.app.getAllStocks(),
                this.app.getTopChanges()
            ]);

            this.renderOverview(overview);
            this.renderTopHoldings(stocks.slice(0, 6)); // Show top 6 holdings
            this.renderTopChanges(topChanges);
            this.app.updateLastUpdatedTime();
            
            // Store stocks data for modal access
            this.stocks = stocks;

        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.renderErrorState();
        }
    }

    renderOverview(data) {
        // Update total value
        const totalValueEl = document.getElementById('total-value');
        if (totalValueEl) {
            totalValueEl.textContent = this.app.formatCurrency(data.total_value);
        }

        // Update total gain/loss
        const gainLossEl = document.getElementById('total-gain-loss');
        const gainLossPercentEl = document.getElementById('total-gain-loss-percent');
        
        if (gainLossEl) {
            gainLossEl.textContent = this.app.formatCurrency(data.total_gain_loss);
            gainLossEl.className = `value ${this.app.getGainLossClass(data.total_gain_loss)}`;
        }
        
        if (gainLossPercentEl) {
            gainLossPercentEl.textContent = this.app.formatPercent(data.total_gain_loss_percent);
            gainLossPercentEl.className = `percentage ${this.app.getGainLossClass(data.total_gain_loss)}`;
        }

        // Update stock count
        const stockCountEl = document.getElementById('stock-count');
        if (stockCountEl) {
            stockCountEl.textContent = data.stock_count.toString();
        }
    }

    renderTopHoldings(holdings) {
        const container = document.getElementById('top-holdings');
        if (!container) return;

        if (!holdings || holdings.length === 0) {
            container.innerHTML = `
                <div class="loading-placeholder">
                    <i class="fas fa-chart-pie"></i>
                    <p>No holdings found. Add stocks to your portfolio to get started.</p>
                </div>
            `;
            return;
        }

        const holdingsHtml = holdings.map(holding => this.createHoldingCard(holding)).join('');
        container.innerHTML = holdingsHtml;
    }

    createHoldingCard(holding) {
        const recommendation = holding.recommendation;
        const priceChange = holding.previous_close ? ((holding.current_price - holding.previous_close) / holding.previous_close) * 100 : 0;
        
        return `
            <div class="holding-card" data-symbol="${holding.symbol}" style="cursor: pointer;">
                <div class="holding-header">
                    <div>
                        <div class="stock-symbol">${holding.symbol}</div>
                        <div class="company-name">${holding.company_name}</div>
                    </div>
                    <div class="recommendation-badge ${recommendation.action}">
                        ${recommendation.action}
                    </div>
                </div>
                
                <div class="holding-details">
                    <div class="detail-item">
                        <span class="detail-label">Current Price</span>
                        <span class="detail-value">${this.app.formatCurrency(holding.current_price)}</span>
                        <span class="detail-value ${this.app.getGainLossClass(priceChange)}">
                            ${priceChange > 0 ? '+' : ''}${priceChange.toFixed(2)}%
                        </span>
                    </div>
                    
                    <div class="detail-item">
                        <span class="detail-label">Shares</span>
                        <span class="detail-value">${holding.shares}</span>
                    </div>
                    
                    <div class="detail-item">
                        <span class="detail-label">Current Value</span>
                        <span class="detail-value">${this.app.formatCurrency(holding.current_value)}</span>
                    </div>
                    
                    <div class="detail-item">
                        <span class="detail-label">Gain/Loss</span>
                        <span class="detail-value ${this.app.getGainLossClass(holding.gain_loss)}">
                            ${this.app.formatCurrency(holding.gain_loss)}
                        </span>
                        <span class="detail-value ${this.app.getGainLossClass(holding.gain_loss_percent)}">
                            (${holding.gain_loss_percent > 0 ? '+' : ''}${holding.gain_loss_percent.toFixed(2)}%)
                        </span>
                    </div>
                </div>
                
                <div class="confidence-info">
                    <span class="confidence-label">Confidence:</span>
                    <div class="confidence-bar">
                        <div class="confidence-fill" style="width: ${(recommendation.confidence * 100)}%"></div>
                    </div>
                    <span class="confidence-text">${(recommendation.confidence * 100).toFixed(0)}%</span>
                </div>
            </div>
        `;
    }

    renderTopChanges(changes) {
        const container = document.getElementById('top-changes');
        if (!container) return;

        if (!changes || changes.length === 0) {
            container.innerHTML = `
                <div class="loading-placeholder">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>No recent recommendation changes found.</p>
                </div>
            `;
            return;
        }

        const changesHtml = changes.map(change => this.createChangeItem(change)).join('');
        container.innerHTML = changesHtml;
    }

    createChangeItem(change) {
        const changeDate = this.app.formatDate(change.change_date);
        
        return `
            <div class="change-item" data-symbol="${change.symbol}">
                <div class="change-info">
                    <div>
                        <div class="change-symbol">${change.symbol}</div>
                        <div class="change-company">${change.company_name}</div>
                    </div>
                    
                    <div class="change-arrow">
                        <span class="recommendation-badge ${change.previous_recommendation}">
                            ${change.previous_recommendation}
                        </span>
                        <i class="fas fa-arrow-right"></i>
                        <span class="recommendation-badge ${change.new_recommendation}">
                            ${change.new_recommendation}
                        </span>
                    </div>
                </div>
                
                <div class="change-meta">
                    <div class="change-date">${changeDate}</div>
                    <div class="confidence-score">
                        <span>Confidence:</span>
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: ${(change.confidence * 100)}%"></div>
                        </div>
                        <span>${(change.confidence * 100).toFixed(0)}%</span>
                    </div>
                </div>
            </div>
        `;
    }

    renderErrorState() {
        const containers = [
            'top-holdings', 
            'top-changes',
            'total-value',
            'total-gain-loss', 
            'stock-count'
        ];

        containers.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                if (id.includes('top-')) {
                    element.innerHTML = `
                        <div class="loading-placeholder">
                            <i class="fas fa-exclamation-triangle"></i>
                            <p>Error loading data</p>
                        </div>
                    `;
                } else {
                    element.textContent = 'Error';
                }
            }
        });
    }

    // Setu Account Aggregator methods
    async checkSetuStatus() {
        try {
            const response = await fetch('/api/setu/holdings/summary');
            if (response.status === 401) {
                // User not connected to Setu
                document.getElementById('connect-demat-btn').style.display = 'inline-flex';
            } else if (response.ok) {
                // User connected to Setu
                document.getElementById('sync-holdings-btn').style.display = 'inline-flex';
                const summary = await response.json();
                this.updateSetuHoldingsDisplay(summary);
            }
        } catch (error) {
            console.error('Error checking Setu status:', error);
            document.getElementById('connect-demat-btn').style.display = 'inline-flex';
        }
    }

    updateSetuHoldingsDisplay(summary) {
        if (summary.last_sync) {
            const lastSync = new Date(summary.last_sync);
            const syncElement = document.getElementById('last-updated-time');
            if (syncElement) {
                syncElement.textContent = `Setu sync: ${lastSync.toLocaleString()}`;
            }
        }
    }

    async connectDemat() {
        try {
            // Redirect to Setu OAuth flow
            window.location.href = '/auth/setu';
        } catch (error) {
            console.error('Error connecting to Setu:', error);
            this.app.showNotification('Failed to connect to Setu. Please try again.', 'error');
        }
    }

    async syncHoldings() {
        const syncBtn = document.getElementById('sync-holdings-btn');
        const originalText = syncBtn.innerHTML;
        
        try {
            // Show loading state
            syncBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Syncing...';
            syncBtn.disabled = true;
            
            const response = await fetch('/api/setu/holdings/sync', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                this.app.showNotification(`Successfully synced ${result.synced_count} holdings`, 'success');
                // Reload dashboard data
                await this.loadData();
            } else {
                this.app.showNotification(result.error || 'Failed to sync holdings', 'error');
            }
        } catch (error) {
            console.error('Error syncing holdings:', error);
            this.app.showNotification('Failed to sync holdings. Please try again.', 'error');
        } finally {
            // Restore button state
            syncBtn.innerHTML = originalText;
            syncBtn.disabled = false;
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Wait for main app to be initialized
    const initDashboard = () => {
        if (window.financeApp) {
            window.dashboard = new Dashboard();
        } else {
            setTimeout(initDashboard, 100);
        }
    };
    
    initDashboard();
});

// Global functions for HTML onclick handlers
function connectDemat() {
    if (window.dashboard) {
        window.dashboard.connectDemat();
    }
}

function syncHoldings() {
    if (window.dashboard) {
        window.dashboard.syncHoldings();
    }
}