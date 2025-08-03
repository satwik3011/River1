// Main JavaScript functionality for the finance app

class FinanceApp {
    constructor() {
        this.apiBaseUrl = '/api';
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupNotifications();
        this.initializeTheme();
    }

    setupEventListeners() {
        // Refresh button functionality
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshAllData());
        }

        // Theme toggle functionality
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
        }

        // Modal close functionality
        document.addEventListener('click', (e) => {
            if (e.target.matches('.modal-close') || e.target.closest('.modal-close')) {
                this.closeModal();
            }
            
            // Close modal when clicking outside
            if (e.target.matches('.modal')) {
                this.closeModal();
            }
        });

        // Notification close functionality
        document.addEventListener('click', (e) => {
            if (e.target.matches('.notification-close') || e.target.closest('.notification-close')) {
                this.hideNotification();
            }
        });

        // Escape key to close modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModal();
                this.hideNotification();
            }
        });

        // Modal analyze button
        const modalAnalyzeBtn = document.getElementById('modal-analyze-btn');
        if (modalAnalyzeBtn) {
            modalAnalyzeBtn.addEventListener('click', () => {
                this.reAnalyzeModalStock();
            });
        }
    }

    setupNotifications() {
        // Auto-hide notifications after 5 seconds
        const notification = document.getElementById('notification');
        if (notification) {
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                        if (!notification.classList.contains('hidden')) {
                            setTimeout(() => this.hideNotification(), 5000);
                        }
                    }
                });
            });
            observer.observe(notification, { attributes: true });
        }
    }

    // API methods
    async makeRequest(endpoint, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        const config = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(`${this.apiBaseUrl}${endpoint}`, config);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            this.showNotification('API request failed: ' + error.message, 'error');
            throw error;
        }
    }

    async getPortfolioOverview() {
        return this.makeRequest('/portfolio/overview');
    }

    async getAllStocks() {
        return this.makeRequest('/stocks');
    }

    async getTopChanges() {
        return this.makeRequest('/stocks/top-changes');
    }

    async analyzeStock(symbol) {
        return this.makeRequest(`/analyze/${symbol}`);
    }

    async refreshAllRecommendations() {
        return this.makeRequest('/refresh-all');
    }

    // UI helper methods
    showLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.remove('hidden');
        }
    }

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.add('hidden');
        }
    }

    showNotification(message, type = 'info') {
        const notification = document.getElementById('notification');
        const messageElement = notification?.querySelector('.notification-message');
        
        if (notification && messageElement) {
            messageElement.textContent = message;
            notification.className = `notification ${type}`;
            notification.classList.remove('hidden');
        }
    }

    hideNotification() {
        const notification = document.getElementById('notification');
        if (notification) {
            notification.classList.add('hidden');
        }
    }

    openModal(modalId = 'stock-modal') {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
        }
    }

    closeModal(modalId = 'stock-modal') {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('hidden');
            document.body.style.overflow = '';
        }
    }

    // Data refresh functionality
    async refreshAllData() {
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.disabled = true;
            const originalContent = refreshBtn.innerHTML;
            refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Refreshing...</span>';
        }

        this.showLoading();

        try {
            await this.refreshAllRecommendations();
            this.showNotification('Portfolio analysis completed successfully!', 'success');
            
            // Reload page data
            if (typeof window.dashboard !== 'undefined') {
                window.dashboard.loadData();
            }
            if (typeof window.stocksPage !== 'undefined') {
                window.stocksPage.loadStocks();
            }
        } catch (error) {
            this.showNotification('Failed to refresh portfolio data', 'error');
        } finally {
            this.hideLoading();
            if (refreshBtn) {
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> <span>Refresh</span>';
            }
        }
    }

    // Utility methods
    formatCurrency(value) {
        if (value === null || value === undefined) return '$0.00';
        
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
        }).format(value);
    }

    formatPercent(value) {
        if (value === null || value === undefined) return '0.00%';
        
        return new Intl.NumberFormat('en-US', {
            style: 'percent',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(value / 100);
    }

    formatDate(dateString) {
        if (!dateString) return 'N/A';
        
        return new Intl.DateTimeFormat('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        }).format(new Date(dateString));
    }

    getRecommendationClass(recommendation) {
        return recommendation ? recommendation.toLowerCase() : 'hold';
    }

    getScoreColor(score) {
        if (score > 0.3) return 'var(--success-color)';
        if (score < -0.3) return 'var(--danger-color)';
        return 'var(--warning-color)';
    }

    getGainLossClass(value) {
        if (value > 0) return 'positive';
        if (value < 0) return 'negative';
        return 'neutral';
    }

    updateLastUpdatedTime() {
        const element = document.getElementById('last-updated-time');
        if (element) {
            element.textContent = this.formatDate(new Date().toISOString());
        }
    }

    // Theme management
    initializeTheme() {
        const savedTheme = localStorage.getItem('theme');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const theme = savedTheme || (prefersDark ? 'dark' : 'light');
        
        this.setTheme(theme);
    }

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
    }

    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        
        const themeIcon = document.getElementById('theme-icon');
        if (themeIcon) {
            themeIcon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }
    }

    // Score visualization
    updateScoreBar(barElement, score, showLabel = false) {
        if (!barElement) return;

        const normalizedScore = (score + 1) / 2; // Convert -1 to 1 range to 0 to 1
        const percentage = Math.max(0, Math.min(100, normalizedScore * 100));
        
        barElement.style.width = `${percentage}%`;
        barElement.style.backgroundColor = this.getScoreColor(score);

        if (showLabel) {
            const valueElement = barElement.closest('.score-item')?.querySelector('.score-value');
            if (valueElement) {
                valueElement.textContent = score.toFixed(2);
            }
        }
    }

    updateConfidenceBar(barElement, confidence) {
        if (!barElement) return;

        const percentage = Math.max(0, Math.min(100, confidence * 100));
        barElement.style.width = `${percentage}%`;
    }

    // Unified Stock Modal Manager
    openStockModal(stock, companyName = null) {
        if (!stock) return;

        // Update modal title and company name
        const symbolEl = document.getElementById('modal-stock-symbol');
        const companyEl = document.getElementById('modal-company-name');
        if (symbolEl) symbolEl.textContent = stock.symbol;
        if (companyEl) companyEl.textContent = companyName || stock.company_name || stock.symbol;

        // Update price information
        this.updateModalPriceInfo(stock);
        
        // Update recommendation
        this.updateModalRecommendation(stock);
        
        // Update analysis scores
        this.updateModalAnalysisScores(stock);
        
        // Update reasoning
        this.updateModalReasoning(stock);
        
        // Update portfolio information
        this.updateModalPortfolioInfo(stock);

        // Store current stock symbol for re-analysis
        this.currentModalStock = stock.symbol;
        
        // Show modal
        this.openModal('stock-modal');
    }

    updateModalPriceInfo(stock) {
        const currentPriceEl = document.getElementById('modal-current-price');
        const priceChangeEl = document.getElementById('modal-price-change');

        if (currentPriceEl) {
            currentPriceEl.textContent = this.formatCurrency(stock.current_price);
        }

        if (priceChangeEl && stock.current_price && stock.previous_close) {
            const priceChange = stock.current_price - stock.previous_close;
            const changePercent = (priceChange / stock.previous_close) * 100;
            
            const changeValueEl = priceChangeEl.querySelector('.change-value');
            const changePercentEl = priceChangeEl.querySelector('.change-percent');
            
            if (changeValueEl) {
                changeValueEl.textContent = `${priceChange >= 0 ? '+' : ''}${this.formatCurrency(priceChange)}`;
                changeValueEl.className = `change-value ${this.getGainLossClass(priceChange)}`;
            }
            
            if (changePercentEl) {
                changePercentEl.textContent = `(${changePercent >= 0 ? '+' : ''}${changePercent.toFixed(2)}%)`;
                changePercentEl.className = `change-percent ${this.getGainLossClass(priceChange)}`;
            }
        }
    }

    updateModalRecommendation(stock) {
        const recommendation = stock.recommendation;
        if (!recommendation) return;

        // Update recommendation badge
        const badgeEl = document.getElementById('modal-recommendation');
        if (badgeEl) {
            badgeEl.textContent = recommendation.action;
            badgeEl.className = `recommendation-badge ${recommendation.action}`;
        }

        // Update confidence
        const confidenceBarEl = document.getElementById('modal-confidence-bar');
        const confidenceTextEl = document.getElementById('modal-confidence-text');
        
        if (confidenceBarEl) {
            this.updateConfidenceBar(confidenceBarEl, recommendation.confidence);
        }
        
        if (confidenceTextEl) {
            confidenceTextEl.textContent = `${(recommendation.confidence * 100).toFixed(0)}%`;
        }
    }

    updateModalAnalysisScores(stock) {
        const recommendation = stock.recommendation;
        if (!recommendation) return;

        const scores = [
            { 
                scoreId: 'modal-technical-score', 
                valueId: 'modal-technical-value', 
                score: recommendation.technical_score 
            },
            { 
                scoreId: 'modal-fundamental-score', 
                valueId: 'modal-fundamental-value', 
                score: recommendation.fundamental_score 
            },
            { 
                scoreId: 'modal-news-score', 
                valueId: 'modal-news-value', 
                score: recommendation.news_sentiment 
            }
        ];

        scores.forEach(({ scoreId, valueId, score }) => {
            const scoreEl = document.getElementById(scoreId);
            const valueEl = document.getElementById(valueId);
            
            if (scoreEl && valueEl && score !== null && score !== undefined) {
                this.updateScoreBar(scoreEl, score, false);
                valueEl.textContent = score.toFixed(2);
            }
        });
    }

    updateModalReasoning(stock) {
        const reasoningEl = document.getElementById('modal-reasoning');
        if (!reasoningEl || !stock.recommendation) return;

        const reasoning = stock.recommendation.reasoning || 'No reasoning available';
        
        // Check if reasoning contains bullet points
        if (reasoning.includes('•')) {
            // Split by bullet points and clean up
            const bulletPoints = reasoning
                .split('•')
                .map(point => point.trim())
                .filter(point => point.length > 0 && point !== '\n');
            
            // Create proper HTML list
            reasoningEl.innerHTML = '<ul>' + 
                bulletPoints.map(point => `<li>${point}</li>`).join('') + 
                '</ul>';
        } else {
            reasoningEl.textContent = reasoning;
        }
    }

    updateModalPortfolioInfo(stock) {
        const elements = {
            'modal-shares': stock.shares?.toString() || '0',
            'modal-avg-cost': this.formatCurrency(stock.avg_cost || 0),
            'modal-market-value': this.formatCurrency(stock.current_value || stock.market_value || 0),
            'modal-gain-loss': this.formatGainLoss(stock.gain_loss, stock.gain_loss_percent)
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
                
                // Apply gain/loss coloring
                if (id === 'modal-gain-loss') {
                    element.className = `portfolio-value gain-loss-value ${this.getGainLossClass(stock.gain_loss)}`;
                }
            }
        });
    }

    formatGainLoss(gainLoss, gainLossPercent) {
        const currency = this.formatCurrency(gainLoss || 0);
        const percent = gainLossPercent !== null && gainLossPercent !== undefined 
            ? `${gainLossPercent >= 0 ? '+' : ''}${gainLossPercent.toFixed(2)}%`
            : '0.00%';
        return `${currency} (${percent})`;
    }

    async reAnalyzeModalStock() {
        if (!this.currentModalStock) return;

        const analyzeBtn = document.getElementById('modal-analyze-btn');
        if (analyzeBtn) {
            analyzeBtn.disabled = true;
            const originalContent = analyzeBtn.innerHTML;
            analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';
        }

        try {
            await this.analyzeStock(this.currentModalStock);
            this.showNotification(`Analysis completed for ${this.currentModalStock}`, 'success');
            
            // Refresh data and update modal
            if (typeof window.dashboard !== 'undefined') {
                await window.dashboard.loadData();
                // Find updated stock data and refresh modal
                const updatedStock = window.dashboard.stocks?.find(s => s.symbol === this.currentModalStock);
                if (updatedStock) {
                    this.openStockModal(updatedStock);
                }
            }
            if (typeof window.stocksPage !== 'undefined') {
                await window.stocksPage.loadStocks();
                // Find updated stock data and refresh modal
                const updatedStock = window.stocksPage.stocks?.find(s => s.symbol === this.currentModalStock);
                if (updatedStock) {
                    this.openStockModal(updatedStock);
                }
            }
            
        } catch (error) {
            this.showNotification(`Failed to analyze ${this.currentModalStock}`, 'error');
        } finally {
            if (analyzeBtn) {
                analyzeBtn.disabled = false;
                analyzeBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Re-analyze Stock';
            }
        }
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.financeApp = new FinanceApp();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FinanceApp;
}