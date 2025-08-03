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
        return '';
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
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.financeApp = new FinanceApp();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FinanceApp;
}