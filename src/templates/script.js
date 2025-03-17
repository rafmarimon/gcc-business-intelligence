document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const reportsContainer = document.getElementById('reports-container');
    const generateReportBtn = document.getElementById('generate-report-btn');
    const reportModal = document.getElementById('report-modal');
    const closeModalBtn = document.querySelector('.close-modal');
    const reportForm = document.getElementById('report-form');
    const loadingSpinner = document.getElementById('loading');
    
    // Load reports on page load
    loadReports();
    
    // Event Listeners
    if (generateReportBtn) {
        generateReportBtn.addEventListener('click', openReportModal);
    }
    
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeReportModal);
    }
    
    if (reportForm) {
        reportForm.addEventListener('submit', handleReportGeneration);
    }
    
    // Window click to close modal
    window.addEventListener('click', function(e) {
        if (e.target === reportModal) {
            closeReportModal();
        }
    });

    /**
     * Load reports from the API
     */
    function loadReports() {
        // Show loading spinner
        if (reportsContainer) {
            reportsContainer.innerHTML = '<div class="spinner"></div><p>Loading reports...</p>';
        }
        
        fetch('/api/reports')
            .then(response => response.json())
            .then(data => {
                if (reportsContainer) {
                    if (data.reports && data.reports.length > 0) {
                        displayReports(data.reports);
                    } else {
                        reportsContainer.innerHTML = '<p class="text-center">No reports found. Generate your first report!</p>';
                    }
                }
            })
            .catch(error => {
                console.error('Error loading reports:', error);
                if (reportsContainer) {
                    reportsContainer.innerHTML = '<p class="text-center">Error loading reports. Please try again later.</p>';
                }
                showToast('Error', 'Failed to load reports. Please try again later.', 'error');
            });
    }
    
    /**
     * Display reports in the container
     * @param {Array} reports - The reports to display
     */
    function displayReports(reports) {
        if (!reportsContainer) return;
        
        reportsContainer.innerHTML = '';
        
        reports.forEach(report => {
            const reportDate = new Date(report.date);
            const formattedDate = reportDate instanceof Date && !isNaN(reportDate) 
                ? reportDate.toLocaleDateString('en-US', { 
                    year: 'numeric', 
                    month: 'long', 
                    day: 'numeric' 
                  }) 
                : 'Unknown Date';
            
            const reportCard = document.createElement('div');
            reportCard.className = 'report-card';
            reportCard.innerHTML = `
                <div class="report-content">
                    <span class="report-date">${formattedDate}</span>
                    <h3 class="report-title">${report.title}</h3>
                    <p class="report-description">${report.description}</p>
                    <div class="report-links">
                        <a href="${report.html_url}" target="_blank" class="report-link link-html">HTML</a>
                        <a href="${report.pdf_url}" target="_blank" class="report-link link-pdf">PDF</a>
                        <a href="${report.md_url}" target="_blank" class="report-link link-md">MD</a>
                    </div>
                </div>
            `;
            
            reportsContainer.appendChild(reportCard);
        });
    }
    
    /**
     * Open the report generation modal
     */
    function openReportModal() {
        if (reportModal) {
            reportModal.style.display = 'block';
        }
    }
    
    /**
     * Close the report generation modal
     */
    function closeReportModal() {
        if (reportModal) {
            reportModal.style.display = 'none';
        }
    }
    
    /**
     * Handle report generation form submission
     * @param {Event} e - The submit event
     */
    function handleReportGeneration(e) {
        e.preventDefault();
        
        const reportType = document.getElementById('report-type').value;
        const collectNews = document.getElementById('collect-news').checked;
        
        // Close the modal
        closeReportModal();
        
        // Show loading spinner
        if (loadingSpinner) {
            loadingSpinner.style.display = 'block';
        }
        
        // Show toast notification
        showToast('Report Generation Started', 'This process may take a few minutes. The page will update when complete.', 'success');
        
        // Call the API to generate the report
        fetch('/api/generate-report', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                report_type: reportType,
                collect_news: collectNews
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Setup polling to check for new reports
                startPollingForNewReports();
            } else {
                // Hide loading spinner
                if (loadingSpinner) {
                    loadingSpinner.style.display = 'none';
                }
                showToast('Error', data.message || 'Failed to generate report', 'error');
            }
        })
        .catch(error => {
            console.error('Error generating report:', error);
            // Hide loading spinner
            if (loadingSpinner) {
                loadingSpinner.style.display = 'none';
            }
            showToast('Error', 'Failed to generate report. Please try again later.', 'error');
        });
    }
    
    /**
     * Poll for new reports after generation is started
     */
    function startPollingForNewReports() {
        let attemptCount = 0;
        const maxAttempts = 60; // 5 minutes (5 * 60 seconds / 5 second interval)
        const pollInterval = 5000; // 5 seconds
        
        const pollTimer = setInterval(() => {
            attemptCount++;
            
            // Check for new reports
            fetch('/api/reports')
                .then(response => response.json())
                .then(data => {
                    // If we have reports or reached max attempts
                    if ((data.reports && data.reports.length > 0) || attemptCount >= maxAttempts) {
                        // Clear interval
                        clearInterval(pollTimer);
                        
                        // Hide loading spinner
                        if (loadingSpinner) {
                            loadingSpinner.style.display = 'none';
                        }
                        
                        // Update reports display
                        if (data.reports && data.reports.length > 0) {
                            displayReports(data.reports);
                            showToast('Success', 'Report generation completed!', 'success');
                        } else if (attemptCount >= maxAttempts) {
                            showToast('Timeout', 'Report generation is taking longer than expected. It will appear when complete.', 'error');
                        }
                    }
                })
                .catch(error => {
                    console.error('Error polling for reports:', error);
                    attemptCount = maxAttempts; // Stop polling on error
                    
                    // Hide loading spinner
                    if (loadingSpinner) {
                        loadingSpinner.style.display = 'none';
                    }
                    
                    showToast('Error', 'Failed to check for new reports. The report may still be generating.', 'error');
                });
            
            // Stop after max attempts
            if (attemptCount >= maxAttempts) {
                clearInterval(pollTimer);
                
                // Hide loading spinner
                if (loadingSpinner) {
                    loadingSpinner.style.display = 'none';
                }
            }
        }, pollInterval);
    }
    
    /**
     * Show a toast notification
     * @param {string} title - The notification title
     * @param {string} message - The notification message
     * @param {string} type - The notification type ('success' or 'error')
     */
    function showToast(title, message, type = 'success') {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-icon">
                ${type === 'success' ? '✓' : '✕'}
            </div>
            <div class="toast-content">
                <div class="toast-title">${title}</div>
                <div class="toast-message">${message}</div>
            </div>
            <div class="toast-close">&times;</div>
        `;
        
        // Add to document
        document.body.appendChild(toast);
        
        // Show the toast
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);
        
        // Set up close button
        const closeBtn = toast.querySelector('.toast-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                toast.classList.remove('show');
                setTimeout(() => {
                    document.body.removeChild(toast);
                }, 300);
            });
        }
        
        // Auto hide after 5 seconds
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                if (document.body.contains(toast)) {
                    document.body.removeChild(toast);
                }
            }, 300);
        }, 5000);
    }
}); 