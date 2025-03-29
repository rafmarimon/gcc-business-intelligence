/**
 * GCC Business Intelligence Platform Dashboard
 * JavaScript functionality for the enhanced dashboard experience
 */

// State management
let state = {
    reports: [],
    allReports: [],
    filteredReports: [],
    currentPage: 1,
    totalPages: 1,
    reportsPerPage: 6,
    analytics: null,
    preferences: {
        showAnalytics: true,
        showChatbot: true,
        gridView: false,
        receiveNotifications: true,
        darkMode: false
    },
    isLoading: false,
    reportFilters: {
        client: 'general',
        frequency: 'daily',
        date: null,
        searchTerm: '',
        sortBy: 'date-desc'
    }
};

// DOM Elements - will be initialized in the document ready function
let elements = {
    // Report generation
    generateReportBtn: null,
    footerGenerateBtn: null,
    reportModal: null,
    closeBtn: null,
    generateReportForm: null,
    generateAlert: null,
    generatingLoading: null,
    
    // Reports listing
    reportsList: null,
    reportsLoading: null,
    reportsAlert: null,
    
    // Filters and sorting
    clientFilter: null,
    frequencyFilter: null,
    dateFilter: null,
    sortCriteria: null,
    applyFilters: null,
    resetFilters: null,
    reportSearch: null,
    
    // Pagination
    prevPage: null,
    nextPage: null,
    pageIndicator: null,
    
    // Chatbot
    chatbotToggle: null,
    chatbotPanel: null,
    chatbotClose: null,
    chatbotMessages: null,
    chatbotInput: null,
    chatbotSend: null,
    
    // Preferences
    preferencesBtn: null,
    widgetPreferences: null,
    preferencesClose: null,
    savePreferences: null,
    showAnalytics: null,
    showChatbot: null,
    gridView: null,
    receiveNotifications: null,
    darkMode: null,
    
    // Notifications
    notificationsBtn: null,
    notificationCenter: null,
    closeNotifications: null,
    markAllRead: null,
    notificationBadge: null,
    
    // Analytics
    analyticsPanel: null
};

/**
 * Initialize the dashboard
 */
function initDashboard() {
    // Initialize DOM elements
    initializeElements();
    
    // Setup event listeners
    setupEventListeners();
    
    // Load user preferences
    loadPreferences();
    
    // Load initial data
    loadReports(state.reportFilters.client, state.reportFilters.frequency);
    
    // Load dashboard analytics
    loadDashboardAnalytics();
    
    // Update notification badge
    updateNotificationBadge();
}

/**
 * Initialize all DOM elements
 */
function initializeElements() {
    // Report generation elements
    elements.generateReportBtn = document.getElementById('generateReportBtn');
    elements.footerGenerateBtn = document.getElementById('footerGenerateBtn');
    elements.reportModal = document.getElementById('reportModal');
    elements.closeBtn = document.querySelector('.close');
    elements.generateReportForm = document.getElementById('generateReportForm');
    elements.generateAlert = document.getElementById('generateAlert');
    elements.generatingLoading = document.getElementById('generatingLoading');
    
    // Reports listing elements
    elements.reportsList = document.getElementById('reportsList');
    elements.reportsLoading = document.getElementById('reportsLoading');
    elements.reportsAlert = document.getElementById('reportsAlert');
    
    // Filters and sorting elements
    elements.clientFilter = document.getElementById('clientFilter');
    elements.frequencyFilter = document.getElementById('frequencyFilter');
    elements.dateFilter = document.getElementById('dateFilter');
    elements.sortCriteria = document.getElementById('sortCriteria');
    elements.applyFilters = document.getElementById('applyFilters');
    elements.resetFilters = document.getElementById('resetFilters');
    elements.reportSearch = document.getElementById('reportSearch');
    
    // Pagination elements
    elements.prevPage = document.getElementById('prevPage');
    elements.nextPage = document.getElementById('nextPage');
    elements.pageIndicator = document.getElementById('pageIndicator');
    
    // Chatbot elements
    elements.chatbotToggle = document.getElementById('chatbotToggle');
    elements.chatbotPanel = document.getElementById('chatbotPanel');
    elements.chatbotClose = document.getElementById('chatbotClose');
    elements.chatbotMessages = document.getElementById('chatbotMessages');
    elements.chatbotInput = document.getElementById('chatbotInput');
    elements.chatbotSend = document.getElementById('chatbotSend');
    
    // Preferences elements
    elements.preferencesBtn = document.getElementById('preferencesBtn');
    elements.widgetPreferences = document.getElementById('widgetPreferences');
    elements.preferencesClose = document.querySelector('.preferences-close');
    elements.savePreferences = document.getElementById('savePreferences');
    elements.showAnalytics = document.getElementById('showAnalytics');
    elements.showChatbot = document.getElementById('showChatbot');
    elements.gridView = document.getElementById('gridView');
    elements.receiveNotifications = document.getElementById('receiveNotifications');
    elements.darkMode = document.getElementById('darkMode');
    
    // Notification elements
    elements.notificationsBtn = document.getElementById('notificationsBtn');
    elements.notificationCenter = document.getElementById('notificationCenter');
    elements.closeNotifications = document.getElementById('closeNotifications');
    elements.markAllRead = document.getElementById('markAllRead');
    elements.notificationBadge = document.getElementById('notificationBadge');
    
    // Analytics elements
    elements.analyticsPanel = document.getElementById('analyticsPanel');
}

/**
 * Setup all event listeners
 */
function setupEventListeners() {
    // Modal controls
    if (elements.generateReportBtn) {
        elements.generateReportBtn.addEventListener('click', openModal);
    }
    
    if (elements.footerGenerateBtn) {
        elements.footerGenerateBtn.addEventListener('click', openModal);
    }
    
    if (elements.closeBtn) {
        elements.closeBtn.addEventListener('click', closeModal);
    }
    
    window.addEventListener('click', (event) => {
        if (event.target === elements.reportModal) {
            closeModal();
        }
    });
    
    // Filter controls
    if (elements.applyFilters) {
        elements.applyFilters.addEventListener('click', applyReportFilters);
    }
    
    if (elements.resetFilters) {
        elements.resetFilters.addEventListener('click', resetReportFilters);
    }
    
    if (elements.reportSearch) {
        elements.reportSearch.addEventListener('input', debounce(applyReportFilters, 300));
    }
    
    // Pagination controls
    if (elements.prevPage) {
        elements.prevPage.addEventListener('click', () => changePage(-1));
    }
    
    if (elements.nextPage) {
        elements.nextPage.addEventListener('click', () => changePage(1));
    }
    
    // Chatbot controls
    if (elements.chatbotToggle) {
        elements.chatbotToggle.addEventListener('click', toggleChatbot);
    }
    
    if (elements.chatbotClose) {
        elements.chatbotClose.addEventListener('click', toggleChatbot);
    }
    
    if (elements.chatbotSend) {
        elements.chatbotSend.addEventListener('click', sendChatbotMessage);
    }
    
    if (elements.chatbotInput) {
        elements.chatbotInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendChatbotMessage();
            }
        });
    }
    
    // Preferences controls
    if (elements.preferencesBtn) {
        elements.preferencesBtn.addEventListener('click', togglePreferences);
    }
    
    if (elements.preferencesClose) {
        elements.preferencesClose.addEventListener('click', togglePreferences);
    }
    
    if (elements.savePreferences) {
        elements.savePreferences.addEventListener('click', saveUserPreferences);
    }
    
    // Notification controls
    if (elements.notificationsBtn) {
        elements.notificationsBtn.addEventListener('click', toggleNotifications);
    }
    
    if (elements.closeNotifications) {
        elements.closeNotifications.addEventListener('click', toggleNotifications);
    }
    
    if (elements.markAllRead) {
        elements.markAllRead.addEventListener('click', markAllNotificationsRead);
    }
    
    // Report generation form
    if (elements.generateReportForm) {
        elements.generateReportForm.addEventListener('submit', generateReport);
    }
}

/**
 * Open the report generation modal
 */
function openModal() {
    if (elements.reportModal) {
        elements.reportModal.style.display = 'block';
    }
}

/**
 * Close the report generation modal
 */
function closeModal() {
    if (elements.reportModal) {
        elements.reportModal.style.display = 'none';
    }
}

/**
 * Load reports from the API
 * @param {string} client - Client identifier
 * @param {string} frequency - Report frequency
 */
async function loadReports(client = 'general', frequency = 'daily') {
    try {
        state.isLoading = true;
        if (elements.reportsLoading) {
            elements.reportsLoading.style.display = 'block';
        }
        
        if (elements.reportsAlert) {
            elements.reportsAlert.style.display = 'none';
        }
        
        if (elements.reportsList) {
            elements.reportsList.innerHTML = '';
        }
        
        const response = await fetch(`/api/reports?client=${client}&frequency=${frequency}`);
        const data = await response.json();
        
        if (elements.reportsLoading) {
            elements.reportsLoading.style.display = 'none';
        }
        
        state.isLoading = false;
        
        if (data.error) {
            if (elements.reportsAlert) {
                elements.reportsAlert.textContent = `Error: ${data.error}`;
                elements.reportsAlert.style.display = 'block';
            }
            return;
        }
        
        if (!data.reports || data.reports.length === 0) {
            if (elements.reportsList) {
                elements.reportsList.innerHTML = `<div class="no-reports-message">No reports available for ${client} (${frequency}). Generate your first report!</div>`;
            }
            return;
        }
        
        // Store reports in state
        state.reports = data.reports;
        state.allReports = [...data.reports];
        state.filteredReports = [...data.reports];
        
        // Update pagination
        state.totalPages = Math.ceil(state.filteredReports.length / state.reportsPerPage);
        state.currentPage = 1;
        updatePaginationControls();
        
        // Display paginated reports
        displayPaginatedReports();
    } catch (error) {
        if (elements.reportsLoading) {
            elements.reportsLoading.style.display = 'none';
        }
        
        state.isLoading = false;
        
        if (elements.reportsAlert) {
            elements.reportsAlert.textContent = `Failed to load reports: ${error.message}`;
            elements.reportsAlert.style.display = 'block';
        }
    }
}

/**
 * Load all available reports across clients and frequencies
 * @returns {Promise<Array>} - Array of report objects
 */
async function loadAllReports() {
    try {
        elements.reportsLoading.style.display = 'block';
        state.isLoading = true;
        
        // Load reports for all client and frequency combinations
        const clients = ['general', 'google', 'nestle'];
        const frequencies = ['daily', 'weekly', 'monthly', 'quarterly'];
        
        state.allReports = [];
        
        for (const client of clients) {
            for (const frequency of frequencies) {
                const response = await fetch(`/api/reports?client=${client}&frequency=${frequency}`);
                const data = await response.json();
                
                if (!data.error && data.reports && data.reports.length > 0) {
                    state.allReports = [...state.allReports, ...data.reports];
                }
            }
        }
        
        // Remove duplicates by timestamp
        const reportMap = new Map();
        state.allReports.forEach(report => {
            reportMap.set(report.timestamp, report);
        });
        
        state.allReports = Array.from(reportMap.values());
        elements.reportsLoading.style.display = 'none';
        state.isLoading = false;
        
        return state.allReports;
    } catch (error) {
        elements.reportsLoading.style.display = 'none';
        state.isLoading = false;
        elements.reportsAlert.textContent = `Failed to load reports: ${error.message}`;
        elements.reportsAlert.style.display = 'block';
        return [];
    }
}

/**
 * Generate a new report
 * @param {Event} event - Form submit event
 */
async function generateReport(event) {
    event.preventDefault();
    
    const client = document.getElementById('clientSelect').value;
    const reportType = document.getElementById('reportType').value;
    const collectNews = document.getElementById('collectNews').checked;
    
    try {
        // Reset alerts and show loading
        elements.generateAlert.style.display = 'none';
        elements.generatingLoading.style.display = 'block';
        
        const response = await fetch('/api/generate-report', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                client: client,
                report_type: reportType,
                collect_news: collectNews
            })
        });
        
        const data = await response.json();
        
        elements.generatingLoading.style.display = 'none';
        
        if (!data.success) {
            elements.generateAlert.textContent = data.message || 'Failed to generate report';
            elements.generateAlert.className = 'alert alert-danger';
            elements.generateAlert.style.display = 'block';
            return;
        }
        
        // Show success message
        elements.generateAlert.textContent = data.message;
        elements.generateAlert.className = 'alert alert-success';
        elements.generateAlert.style.display = 'block';
        
        // Add notification
        addNotification(`New report generated for ${client}`);
        
        // Reload reports after a delay
        setTimeout(() => {
            loadReports(client, reportType);
            closeModal();
        }, 3000);
        
    } catch (error) {
        elements.generatingLoading.style.display = 'none';
        elements.generateAlert.textContent = `Error: ${error.message}`;
        elements.generateAlert.className = 'alert alert-danger';
        elements.generateAlert.style.display = 'block';
    }
}

/**
 * Reset all filters to default values
 */
function resetReportFilters() {
    elements.clientFilter.value = 'general';
    elements.frequencyFilter.value = 'daily';
    elements.dateFilter.value = '';
    elements.sortCriteria.value = 'date-desc';
    elements.reportSearch.value = '';
    state.currentPage = 1;
    
    // Update state
    state.reportFilters = {
        client: 'general',
        frequency: 'daily',
        date: null,
        searchTerm: '',
        sortBy: 'date-desc'
    };
    
    // Load reports with default values
    loadReports('general', 'daily');
}

/**
 * Apply filters and sorting to reports
 */
function applyReportFilters() {
    const client = elements.clientFilter.value;
    const frequency = elements.frequencyFilter.value;
    const date = elements.dateFilter.value ? new Date(elements.dateFilter.value) : null;
    const searchTerm = elements.reportSearch.value.toLowerCase();
    const sortBy = elements.sortCriteria.value;
    
    // Update state
    state.reportFilters = {
        client,
        frequency,
        date,
        searchTerm,
        sortBy
    };
    
    // Reset pagination
    state.currentPage = 1;
    
    // If client and frequency are specific (not "all"), load from API
    if (client !== 'all' && frequency !== 'all' && !date && !searchTerm) {
        loadReports(client, frequency);
        return;
    }
    
    // If we already have reports loaded, filter them
    if (state.allReports.length > 0) {
        filterAndDisplayReports();
    } else {
        // If we don't have reports yet, load all reports first
        loadAllReports().then(() => {
            filterAndDisplayReports();
        });
    }
}

/**
 * Filter and display reports based on current filter settings
 */
function filterAndDisplayReports() {
    const { client, frequency, date, searchTerm, sortBy } = state.reportFilters;
    
    // Filter reports
    state.filteredReports = state.allReports.filter(report => {
        // Client filter
        if (client !== 'all' && report.client.toLowerCase() !== client) {
            return false;
        }
        
        // Frequency filter
        if (frequency !== 'all' && report.frequency !== frequency) {
            return false;
        }
        
        // Date filter
        if (date) {
            const reportDate = new Date(report.date);
            // Reset time portion to compare dates only
            reportDate.setHours(0, 0, 0, 0);
            date.setHours(0, 0, 0, 0);
            
            if (reportDate.getTime() !== date.getTime()) {
                return false;
            }
        }
        
        // Search filter
        if (searchTerm) {
            const title = report.title.toLowerCase();
            const description = report.description.toLowerCase();
            const clientName = report.client.toLowerCase();
            
            return title.includes(searchTerm) || 
                   description.includes(searchTerm) || 
                   clientName.includes(searchTerm);
        }
        
        return true;
    });
    
    // Sort reports
    state.filteredReports.sort((a, b) => {
        switch (sortBy) {
            case 'date-asc':
                return new Date(a.date) - new Date(b.date);
            case 'date-desc':
                return new Date(b.date) - new Date(a.date);
            case 'client':
                return a.client.localeCompare(b.client);
            case 'type':
                return a.frequency.localeCompare(b.frequency);
            default:
                return new Date(b.date) - new Date(a.date);
        }
    });
    
    // Update pagination
    state.totalPages = Math.ceil(state.filteredReports.length / state.reportsPerPage);
    if (state.currentPage > state.totalPages) {
        state.currentPage = state.totalPages || 1;
    }
    updatePaginationControls();
    
    // Display paginated reports
    displayPaginatedReports();
}

/**
 * Update pagination controls based on current state
 */
function updatePaginationControls() {
    elements.pageIndicator.textContent = `Page ${state.currentPage} of ${state.totalPages}`;
    elements.prevPage.disabled = state.currentPage <= 1;
    elements.nextPage.disabled = state.currentPage >= state.totalPages;
}

/**
 * Change the current page
 * @param {number} delta - Page change (1 for next, -1 for previous)
 */
function changePage(delta) {
    const newPage = state.currentPage + delta;
    if (newPage >= 1 && newPage <= state.totalPages) {
        state.currentPage = newPage;
        updatePaginationControls();
        displayPaginatedReports();
    }
}

/**
 * Display paginated reports
 */
function displayPaginatedReports() {
    const startIndex = (state.currentPage - 1) * state.reportsPerPage;
    const endIndex = Math.min(startIndex + state.reportsPerPage, state.filteredReports.length);
    const paginatedReports = state.filteredReports.slice(startIndex, endIndex);
    
    // Clear current reports
    elements.reportsList.innerHTML = '';
    
    if (paginatedReports.length === 0) {
        elements.reportsList.innerHTML = '<div class="no-reports-message">No reports match your filter criteria. Try adjusting your filters.</div>';
        return;
    }
    
    // Display reports
    paginatedReports.forEach(report => {
        const reportCard = document.createElement('div');
        reportCard.className = 'report-card';
        
        reportCard.innerHTML = `
            <div class="report-header">
                <div class="report-client-badge">${report.client}</div>
                <div class="report-type-badge">${report.frequency.charAt(0).toUpperCase() + report.frequency.slice(1)}</div>
            </div>
            <h3 class="report-title">${report.title}</h3>
            <div class="report-date">${report.formatted_date} at ${report.formatted_time}</div>
            <p class="report-description">${report.description}</p>
            <div class="report-actions">
                <a href="${report.html_url}" class="report-link" target="_blank" 
                   onclick="logReportView('${report.timestamp}')">
                    <span class="icon">📄</span> View HTML
                </a>
                <a href="${report.pdf_url}" class="report-link" target="_blank"
                   onclick="logReportView('${report.timestamp}')">
                    <span class="icon">📥</span> Download PDF
                </a>
                <button class="report-analytics-btn" data-report-id="${report.timestamp}">
                    <span class="icon">📊</span> Analytics
                </button>
            </div>
        `;
        
        elements.reportsList.appendChild(reportCard);
    });
    
    // Add event listeners to analytics buttons
    document.querySelectorAll('.report-analytics-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const reportId = this.getAttribute('data-report-id');
            showReportAnalytics(reportId);
        });
    });
}

/**
 * Show analytics for a specific report
 * @param {string} reportId - Report timestamp ID
 */
async function showReportAnalytics(reportId) {
    try {
        const response = await fetch(`/api/report-details/${reportId}`);
        const data = await response.json();
        
        if (data.error) {
            alert(`Error loading report details: ${data.error}`);
            return;
        }
        
        // Format the data in a readable way
        let message = `Report Analytics for: ${data.title}\n\n`;
        message += `Client: ${data.client}\n`;
        message += `Type: ${data.frequency.charAt(0).toUpperCase() + data.frequency.slice(1)}\n`;
        message += `Created: ${data.formatted_date} at ${data.formatted_time}\n`;
        message += `File Size: ${Math.round(data.file_size / 1024)} KB\n\n`;
        
        if (data.topics && data.topics.length > 0) {
            message += `Key Topics:\n`;
            data.topics.forEach(topic => {
                message += `- ${topic}\n`;
            });
        }
        
        alert(message);
        
        // Log this view
        logReportView(reportId);
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

/**
 * Log when a report is viewed for analytics
 * @param {string} reportId - Report timestamp ID
 */
async function logReportView(reportId) {
    try {
        await fetch('/api/log-report-view', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                report_id: reportId
            })
        });
    } catch (error) {
        console.error('Error logging report view:', error);
    }
}

/**
 * Load dashboard analytics data
 */
async function loadDashboardAnalytics() {
    try {
        const response = await fetch('/api/dashboard/analytics');
        const data = await response.json();
        
        if (data.error) {
            console.error('Error loading analytics:', data.error);
            return;
        }
        
        // Store analytics in state
        state.analytics = data;
        
        // Update the analytics panel
        updateAnalyticsPanel(data);
    } catch (error) {
        console.error('Error loading analytics:', error);
    }
}

/**
 * Update the analytics panel with data
 * @param {Object} data - Analytics data
 */
function updateAnalyticsPanel(data) {
    const reportsCountElement = document.getElementById('reportsThisMonth');
    const popularClientElement = document.getElementById('popularClient');
    const popularReportElement = document.getElementById('popularReport');
    const chatInteractionsElement = document.getElementById('chatInteractions');
    
    if (reportsCountElement) {
        reportsCountElement.textContent = data.reports_generated_this_month;
    }
    
    if (popularClientElement) {
        popularClientElement.textContent = data.most_popular_client.name;
    }
    
    if (popularReportElement) {
        popularReportElement.textContent = data.most_viewed_report_type.name;
    }
    
    if (chatInteractionsElement) {
        chatInteractionsElement.textContent = data.chat_interactions;
    }
}

/**
 * Toggle the chatbot panel
 */
function toggleChatbot() {
    if (elements.chatbotPanel.style.display === 'flex') {
        elements.chatbotPanel.style.display = 'none';
        elements.chatbotToggle.style.display = 'flex';
    } else {
        elements.chatbotPanel.style.display = 'flex';
        elements.chatbotToggle.style.display = 'none';
        elements.chatbotInput.focus();
    }
}

/**
 * Send a message to the chatbot
 */
async function sendChatbotMessage() {
    const message = elements.chatbotInput.value.trim();
    if (!message) return;
    
    // Add user message to chat
    addChatMessage(message, 'user');
    
    // Clear input
    elements.chatbotInput.value = '';
    
    // Add thinking message
    const thinkingElement = document.createElement('div');
    thinkingElement.className = 'chatbot-message assistant';
    thinkingElement.id = 'chatbot-thinking';
    thinkingElement.textContent = 'Thinking...';
    elements.chatbotMessages.appendChild(thinkingElement);
    
    // Scroll to bottom
    elements.chatbotMessages.scrollTop = elements.chatbotMessages.scrollHeight;
    
    try {
        // Make API call
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                client_name: 'Global Possibilities Team',
                report_type: 'daily'
            })
        });
        
        const data = await response.json();
        
        // Remove thinking message
        document.getElementById('chatbot-thinking').remove();
        
        if (data.error) {
            addChatMessage(`Error: ${data.error}`, 'assistant');
        } else {
            addChatMessage(data.reply, 'assistant');
        }
    } catch (error) {
        // Remove thinking message
        if (document.getElementById('chatbot-thinking')) {
            document.getElementById('chatbot-thinking').remove();
        }
        
        console.error('Error:', error);
        addChatMessage('Sorry, there was an error processing your request. Please try again.', 'assistant');
    }
}

/**
 * Add a message to the chatbot conversation
 * @param {string} message - Message text
 * @param {string} sender - Message sender ('user' or 'assistant')
 */
function addChatMessage(message, sender) {
    const messageElement = document.createElement('div');
    messageElement.className = `chatbot-message ${sender}`;
    messageElement.textContent = message;
    
    elements.chatbotMessages.appendChild(messageElement);
    
    // Scroll to bottom
    elements.chatbotMessages.scrollTop = elements.chatbotMessages.scrollHeight;
}

/**
 * Toggle the preferences panel
 */
function togglePreferences() {
    if (elements.widgetPreferences.style.display === 'block') {
        elements.widgetPreferences.style.display = 'none';
    } else {
        elements.widgetPreferences.style.display = 'block';
        
        // Load existing preferences
        loadPreferences();
    }
}

/**
 * Save user preferences
 */
function saveUserPreferences() {
    // Get preferences from form
    const preferences = {
        showAnalytics: elements.showAnalytics.checked,
        showChatbot: elements.showChatbot.checked,
        gridView: elements.gridView.checked,
        receiveNotifications: elements.receiveNotifications.checked,
        darkMode: elements.darkMode.checked
    };
    
    // Save to state
    state.preferences = preferences;
    
    // Save to localStorage
    localStorage.setItem('dashboard_preferences', JSON.stringify(preferences));
    
    // Apply preferences
    applyPreferences(preferences);
    
    // Close preferences panel
    togglePreferences();
}

/**
 * Load saved preferences
 */
function loadPreferences() {
    // Load preferences from localStorage
    const savedPreferences = localStorage.getItem('dashboard_preferences');
    
    if (savedPreferences) {
        const preferences = JSON.parse(savedPreferences);
        
        // Save to state
        state.preferences = preferences;
        
        // Set checkbox states
        elements.showAnalytics.checked = preferences.showAnalytics;
        elements.showChatbot.checked = preferences.showChatbot;
        elements.gridView.checked = preferences.gridView;
        elements.receiveNotifications.checked = preferences.receiveNotifications;
        elements.darkMode.checked = preferences.darkMode;
        
        // Apply preferences
        applyPreferences(preferences);
    }
}

/**
 * Apply preferences to the UI
 * @param {Object} preferences - User preferences
 */
function applyPreferences(preferences) {
    // Apply analytics preference
    if (preferences.showAnalytics) {
        elements.analyticsPanel.style.display = 'block';
    } else {
        elements.analyticsPanel.style.display = 'none';
    }
    
    // Apply chatbot preference
    if (preferences.showChatbot) {
        elements.chatbotToggle.style.display = 'flex';
    } else {
        elements.chatbotToggle.style.display = 'none';
        elements.chatbotPanel.style.display = 'none';
    }
    
    // Apply grid view preference
    if (preferences.gridView) {
        elements.reportsList.className = 'report-list-grid';
    } else {
        elements.reportsList.className = 'report-list';
    }
    
    // Apply dark mode preference
    if (preferences.darkMode) {
        document.body.classList.add('dark-mode');
    } else {
        document.body.classList.remove('dark-mode');
    }
    
    // Apply notifications preference
    if (!preferences.receiveNotifications) {
        elements.notificationBadge.style.display = 'none';
    } else {
        updateNotificationBadge();
    }
}

/**
 * Toggle the notification center
 */
function toggleNotifications() {
    if (elements.notificationCenter.style.display === 'block') {
        elements.notificationCenter.style.display = 'none';
    } else {
        elements.notificationCenter.style.display = 'block';
        loadNotifications();
    }
}

/**
 * Load notifications from storage
 */
function loadNotifications() {
    const notificationItems = document.querySelector('.notification-items');
    const savedNotifications = JSON.parse(localStorage.getItem('notifications') || '[]');
    
    // Clear existing notifications
    notificationItems.innerHTML = '';
    
    if (savedNotifications.length === 0) {
        notificationItems.innerHTML = '<div class="no-notifications">No notifications yet</div>';
        return;
    }
    
    // Add notifications to panel
    savedNotifications.forEach(notification => {
        const notificationTime = new Date(notification.time);
        const timeAgo = getTimeAgo(notificationTime);
        
        const notificationItem = document.createElement('div');
        notificationItem.className = 'notification-item';
        notificationItem.innerHTML = `
            ${notification.read ? '' : '<div class="notification-dot"></div>'}
            <div class="notification-content">
                <div>${notification.message}</div>
                <div class="notification-time">${timeAgo}</div>
            </div>
        `;
        
        notificationItems.appendChild(notificationItem);
    });
}

/**
 * Mark all notifications as read
 */
function markAllNotificationsRead() {
    // Update DOM
    document.querySelectorAll('.notification-dot').forEach(dot => {
        dot.style.display = 'none';
    });
    
    elements.notificationBadge.style.display = 'none';
    elements.notificationBadge.textContent = '0';
    
    // Update localStorage
    const notifications = JSON.parse(localStorage.getItem('notifications') || '[]');
    notifications.forEach(notification => {
        notification.read = true;
    });
    
    localStorage.setItem('notifications', JSON.stringify(notifications));
    localStorage.setItem('notifications_read', 'true');
    
    // Reload notifications in panel
    loadNotifications();
}

/**
 * Add a new notification
 * @param {string} message - Notification message
 */
function addNotification(message) {
    const notificationItems = document.querySelector('.notification-items');
    const now = new Date();
    
    // Create notification item
    const notificationItem = document.createElement('div');
    notificationItem.className = 'notification-item';
    notificationItem.innerHTML = `
        <div class="notification-dot"></div>
        <div class="notification-content">
            <div>${message}</div>
            <div class="notification-time">Just now</div>
        </div>
    `;
    
    // Add to panel if visible
    if (elements.notificationCenter.style.display === 'block') {
        // Remove 'no notifications' message if present
        const noNotificationsMsg = notificationItems.querySelector('.no-notifications');
        if (noNotificationsMsg) {
            notificationItems.removeChild(noNotificationsMsg);
        }
        
        // Insert at the top
        notificationItems.insertBefore(notificationItem, notificationItems.firstChild);
    }
    
    // Update badge
    updateNotificationBadge();
    
    // Save notification
    const notifications = JSON.parse(localStorage.getItem('notifications') || '[]');
    notifications.unshift({
        message,
        time: now.toISOString(),
        read: false
    });
    
    localStorage.setItem('notifications', JSON.stringify(notifications));
    localStorage.setItem('notifications_read', 'false');
}

/**
 * Update the notification badge count
 */
function updateNotificationBadge() {
    const notifications = JSON.parse(localStorage.getItem('notifications') || '[]');
    const unreadCount = notifications.filter(n => !n.read).length;
    
    elements.notificationBadge.textContent = unreadCount;
    
    if (unreadCount > 0 && state.preferences.receiveNotifications) {
        elements.notificationBadge.style.display = 'flex';
    } else {
        elements.notificationBadge.style.display = 'none';
    }
}

/**
 * Format a date as a human-readable time ago string
 * @param {Date} date - Date to format
 * @returns {string} - Formatted string (e.g., "2 hours ago")
 */
function getTimeAgo(date) {
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    let interval = Math.floor(seconds / 31536000);
    if (interval >= 1) {
        return interval === 1 ? '1 year ago' : `${interval} years ago`;
    }
    
    interval = Math.floor(seconds / 2592000);
    if (interval >= 1) {
        return interval === 1 ? '1 month ago' : `${interval} months ago`;
    }
    
    interval = Math.floor(seconds / 86400);
    if (interval >= 1) {
        return interval === 1 ? '1 day ago' : `${interval} days ago`;
    }
    
    interval = Math.floor(seconds / 3600);
    if (interval >= 1) {
        return interval === 1 ? '1 hour ago' : `${interval} hours ago`;
    }
    
    interval = Math.floor(seconds / 60);
    if (interval >= 1) {
        return interval === 1 ? '1 minute ago' : `${interval} minutes ago`;
    }
    
    return seconds <= 10 ? 'just now' : `${Math.floor(seconds)} seconds ago`;
}

/**
 * Debounce function to limit how often a function can be called
 * @param {Function} func - Function to debounce
 * @param {number} delay - Delay in milliseconds
 * @returns {Function} - Debounced function
 */
function debounce(func, delay) {
    let timeoutId;
    return function(...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
            func.apply(this, args);
        }, delay);
    };
}

// Initialize dashboard when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', initDashboard); 