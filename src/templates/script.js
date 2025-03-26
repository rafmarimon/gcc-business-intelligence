document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const reportsContainer = document.getElementById('reports-container');
    const forecastsContainer = document.getElementById('forecasts-container');
    const visualizationsContainer = document.getElementById('visualizations-container');
    const generateReportBtn = document.getElementById('generate-report-btn');
    const generateForecastBtn = document.getElementById('generate-forecast-btn');
    const mlStatusContainer = document.getElementById('ml-status');
    const reportModal = document.getElementById('report-modal');
    const forecastModal = document.getElementById('forecast-modal');
    const closeModalBtn = document.querySelector('.close-modal');
    const closeForecastModalBtn = document.querySelector('.close-forecast-modal');
    const reportForm = document.getElementById('report-form');
    const forecastForm = document.getElementById('forecast-form');
    const loadingSpinner = document.getElementById('loading');
    const dashboardTabs = document.querySelectorAll('.dashboard-tab');
    const dashboardSections = document.querySelectorAll('.dashboard-section');
    
    // Load content on page load
    loadReports();
    loadForecasts();
    checkMlStatus();
    setupVisualizationOptions();
    
    // Event Listeners
    if (generateReportBtn) {
        generateReportBtn.addEventListener('click', openReportModal);
    }
    
    if (generateForecastBtn) {
        generateForecastBtn.addEventListener('click', openForecastModal);
    }
    
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeReportModal);
    }
    
    if (closeForecastModalBtn) {
        closeForecastModalBtn.addEventListener('click', closeForecastModal);
    }
    
    if (reportForm) {
        reportForm.addEventListener('submit', handleReportGeneration);
    }
    
    if (forecastForm) {
        forecastForm.addEventListener('submit', handleForecastGeneration);
    }
    
    // Tab navigation
    if (dashboardTabs.length > 0) {
        dashboardTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const targetSection = tab.getAttribute('data-section');
                
                // Update active tab
                dashboardTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                
                // Show corresponding section
                dashboardSections.forEach(section => {
                    if (section.id === targetSection) {
                        section.classList.add('active');
                    } else {
                        section.classList.remove('active');
                    }
                });
            });
        });
    }
    
    // Window click to close modals
    window.addEventListener('click', function(e) {
        if (e.target === reportModal) {
            closeReportModal();
        }
        if (e.target === forecastModal) {
            closeForecastModal();
        }
    });

    /**
     * Check ML system availability
     */
    function checkMlStatus() {
        if (!mlStatusContainer) return;
        
        mlStatusContainer.innerHTML = '<div class="spinner"></div><p>Checking ML system...</p>';
        
        fetch('/api/ml-status')
            .then(response => response.json())
            .then(data => {
                if (data.available) {
                    mlStatusContainer.innerHTML = `
                        <div class="status-card success">
                            <i class="fas fa-check-circle"></i>
                            <div class="status-details">
                                <h3>ML System Ready</h3>
                                <p>TensorFlow ${data.tensorflow_version || 'Unknown'}</p>
                                <p>${data.models_available?.length || 0} models available</p>
                                <p>Training data: ${data.data_available ? 'Available' : 'Not available'}</p>
                            </div>
                        </div>
                    `;
                    
                    // Enable forecast button if it exists
                    if (generateForecastBtn) {
                        generateForecastBtn.disabled = false;
                    }
                } else {
                    mlStatusContainer.innerHTML = `
                        <div class="status-card warning">
                            <i class="fas fa-exclamation-triangle"></i>
                            <div class="status-details">
                                <h3>ML System Unavailable</h3>
                                <p>The TensorFlow ML system is not available.</p>
                                <p>You can still generate regular reports.</p>
                            </div>
                        </div>
                    `;
                    
                    // Disable forecast button if it exists
                    if (generateForecastBtn) {
                        generateForecastBtn.disabled = true;
                    }
                }
            })
            .catch(error => {
                console.error('Error checking ML status:', error);
                mlStatusContainer.innerHTML = `
                    <div class="status-card error">
                        <i class="fas fa-times-circle"></i>
                        <div class="status-details">
                            <h3>Error Checking ML Status</h3>
                            <p>Could not connect to the ML system.</p>
                        </div>
                    </div>
                `;
            });
    }

    /**
     * Set up visualization options based on available data
     */
    function setupVisualizationOptions() {
        const vizTypeSelect = document.getElementById('visualization-type');
        const metricSelect = document.getElementById('visualization-metric');
        const timeframeSelect = document.getElementById('visualization-timeframe');
        const generateVizBtn = document.getElementById('generate-visualization-btn');
        
        if (!vizTypeSelect || !metricSelect || !timeframeSelect || !generateVizBtn) return;
        
        // Fetch available metrics and visualization types
        fetch('/api/ml-data-overview')
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    console.error('Error fetching ML data overview:', data.error);
                    return;
                }
                
                // Populate metric options
                if (data.metrics && Array.isArray(data.metrics)) {
                    metricSelect.innerHTML = '';
                    data.metrics.forEach(metric => {
                        const option = document.createElement('option');
                        option.value = metric.id;
                        option.textContent = metric.name;
                        metricSelect.appendChild(option);
                    });
                }
                
                // Enable the generate button
                generateVizBtn.disabled = false;
            })
            .catch(error => {
                console.error('Error setting up visualization options:', error);
            });
        
        // Add event listener for visualization generation
        generateVizBtn.addEventListener('click', () => {
            const vizType = vizTypeSelect.value;
            const metric = metricSelect.value;
            const timeframe = timeframeSelect.value;
            
            generateVisualization(vizType, metric, timeframe);
        });
    }
    
    /**
     * Generate and display a visualization
     */
    function generateVisualization(vizType, metric, timeframe) {
        if (!visualizationsContainer) return;
        
        // Show loading state
        visualizationsContainer.innerHTML = '<div class="spinner"></div><p>Generating visualization...</p>';
        
        // Call the API to generate the visualization
        fetch(`/api/visualization/${vizType}?metric=${metric}&period=${timeframe}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    visualizationsContainer.innerHTML = `<p class="error-message">${data.error}</p>`;
                    return;
                }
                
                // Display the visualization
                visualizationsContainer.innerHTML = `
                    <div class="visualization-card">
                        <h3>${data.title}</h3>
                        <div class="visualization-image">
                            <img src="${data.visualization_url}" alt="${data.title}">
                        </div>
                    </div>
                `;
            })
            .catch(error => {
                console.error('Error generating visualization:', error);
                visualizationsContainer.innerHTML = `<p class="error-message">Error generating visualization: ${error.message}</p>`;
            });
    }

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
     * Load forecasts from the API
     */
    function loadForecasts() {
        if (!forecastsContainer) return;
        
        forecastsContainer.innerHTML = '<div class="spinner"></div><p>Loading forecasts...</p>';
        
        fetch('/api/forecasts')
            .then(response => response.json())
            .then(data => {
                if (data.forecasts && data.forecasts.length > 0) {
                    displayForecasts(data.forecasts);
                } else {
                    forecastsContainer.innerHTML = `
                        <div class="empty-state">
                            <i class="fas fa-chart-line"></i>
                            <p>No forecasts available yet. Generate your first ML forecast!</p>
                        </div>
                    `;
                }
            })
            .catch(error => {
                console.error('Error loading forecasts:', error);
                forecastsContainer.innerHTML = '<p class="text-center">Error loading forecasts. Please try again later.</p>';
                showToast('Error', 'Failed to load forecasts. Please try again later.', 'error');
            });
    }
    
    /**
     * Display forecasts in the container
     * @param {Array} forecasts - The forecasts to display
     */
    function displayForecasts(forecasts) {
        if (!forecastsContainer) return;
        
        forecastsContainer.innerHTML = '';
        
        // Group forecasts by type
        const groupedForecasts = {
            monthly: forecasts.filter(f => f.type === 'monthly'),
            quarterly: forecasts.filter(f => f.type === 'quarterly')
        };
        
        // Create section for each type
        Object.keys(groupedForecasts).forEach(type => {
            if (groupedForecasts[type].length === 0) return;
            
            const typeSection = document.createElement('div');
            typeSection.className = 'forecast-section';
            typeSection.innerHTML = `<h3 class="section-title">${type.charAt(0).toUpperCase() + type.slice(1)} Forecasts</h3>`;
            
            const typeContainer = document.createElement('div');
            typeContainer.className = 'forecast-cards';
            
            groupedForecasts[type].forEach(forecast => {
                const forecastCard = document.createElement('div');
                forecastCard.className = 'forecast-card';
                forecastCard.innerHTML = `
                    <div class="forecast-content">
                        <div class="forecast-badge ${type}">${type}</div>
                        <div class="forecast-datetime">
                            <span class="forecast-date">${forecast.formatted_date}</span>
                            <span class="forecast-time">${forecast.formatted_time}</span>
                        </div>
                        <h3 class="forecast-title">${forecast.title}</h3>
                        <p class="forecast-description">${forecast.description}</p>
                        <div class="forecast-links">
                            ${forecast.html_url ? `<a href="${forecast.html_url}" target="_blank" class="forecast-link link-html">HTML</a>` : ''}
                            ${forecast.pdf_url ? `<a href="${forecast.pdf_url}" target="_blank" class="forecast-link link-pdf">PDF</a>` : ''}
                            ${forecast.md_url ? `<a href="${forecast.md_url}" target="_blank" class="forecast-link link-md">MD</a>` : ''}
                        </div>
                    </div>
                `;
                
                typeContainer.appendChild(forecastCard);
            });
            
            typeSection.appendChild(typeContainer);
            forecastsContainer.appendChild(typeSection);
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
            const formattedDate = report.formatted_date || 'Unknown Date';
            const formattedTime = report.formatted_time || '';
            
            const reportCard = document.createElement('div');
            reportCard.className = 'report-card';
            reportCard.innerHTML = `
                <div class="report-content">
                    <div class="report-datetime">
                        <span class="report-date">${formattedDate}</span>
                        <span class="report-time">${formattedTime}</span>
                    </div>
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
     * Open the forecast generation modal
     */
    function openForecastModal() {
        if (forecastModal) {
            forecastModal.style.display = 'flex';
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
     * Close the forecast generation modal
     */
    function closeForecastModal() {
        if (forecastModal) {
            forecastModal.style.display = 'none';
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
     * Handle forecast generation form submission
     */
    function handleForecastGeneration(e) {
        e.preventDefault();
        
        // Get form data
        const formData = new FormData(forecastForm);
        const reportType = formData.get('forecast-type');
        
        // Show loading
        forecastModal.style.display = 'none';
        loadingSpinner.style.display = 'flex';
        
        // Call the API to generate the forecast
        fetch('/api/generate-forecast', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                report_type: reportType
            })
        })
        .then(response => response.json())
        .then(data => {
            loadingSpinner.style.display = 'none';
            
            if (data.error) {
                showToast('Error', `Failed to generate forecast: ${data.error}`, 'error');
                return;
            }
            
            showToast('Success', `${reportType.charAt(0).toUpperCase() + reportType.slice(1)} forecast generation started. This may take a few minutes.`, 'success');
            startPollingForNewForecasts();
        })
        .catch(error => {
            loadingSpinner.style.display = 'none';
            console.error('Error generating forecast:', error);
            showToast('Error', 'Failed to generate forecast. Please try again later.', 'error');
        });
    }
    
    /**
     * Start polling for new reports
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
     * Start polling for new forecasts
     */
    function startPollingForNewForecasts() {
        let pollCount = 0;
        const maxPolls = 30; // Poll for about 5 minutes
        
        function pollForNewForecasts() {
            pollCount++;
            
            if (pollCount > maxPolls) {
                showToast('Info', 'Forecast is taking longer than expected. It will appear once complete.', 'info');
                return;
            }
            
            fetch('/api/forecasts')
                .then(response => response.json())
                .then(data => {
                    // Reload forecasts if we have some
                    if (data.forecasts && data.forecasts.length > 0) {
                        loadForecasts();
                    }
                    
                    // Continue polling
                    setTimeout(pollForNewForecasts, 10000); // Poll every 10 seconds
                })
                .catch(error => {
                    console.error('Error polling for forecasts:', error);
                    setTimeout(pollForNewForecasts, 10000); // Try again
                });
        }
        
        // Start polling
        setTimeout(pollForNewForecasts, 10000);
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