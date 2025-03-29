document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const reportsContainer = document.getElementById('reports-container');
    const forecastsContainer = document.getElementById('forecasts-container');
    const visualizationsContainer = document.getElementById('visualizations-container');
    const linkedinPostsContainer = document.getElementById('linkedin-posts-container');
    const generateReportBtn = document.getElementById('generate-report-btn');
    const generateForecastBtn = document.getElementById('generate-forecast-btn');
    const generateLinkedInBtn = document.getElementById('generate-linkedin-content-btn');
    const mlStatusContainer = document.getElementById('ml-status');
    const reportModal = document.getElementById('report-modal');
    const forecastModal = document.getElementById('forecast-modal');
    const linkedinModal = document.getElementById('linkedin-modal');
    const closeModalBtn = document.querySelector('.close-modal');
    const closeForecastModalBtn = document.querySelector('.close-forecast-modal');
    const closeLinkedInModalBtn = document.getElementById('close-linkedin-modal');
    const reportForm = document.getElementById('report-form');
    const forecastForm = document.getElementById('forecast-form');
    const linkedinForm = document.getElementById('linkedin-form');
    const loadingSpinner = document.getElementById('loading');
    const linkedinPostsLoading = document.getElementById('linkedin-posts-loading');
    const dashboardTabs = document.querySelectorAll('.dashboard-tab');
    const dashboardSections = document.querySelectorAll('.dashboard-section');
    const linkedinPostTypeFilter = document.getElementById('linkedin-post-type');
    const linkedinSearch = document.getElementById('linkedin-search');
    const gpt4oImageToggle = document.getElementById('gpt4o-image-toggle');
    const currentImageModel = document.getElementById('current-image-model');
    const customizeImageCheckbox = document.getElementById('linkedin-customize-image');
    const linkedinImageOptions = document.getElementById('linkedin-image-options');
    
    // LinkedIn pagination
    let linkedinCurrentPage = 1;
    let linkedinTotalPages = 1;
    const linkedinItemsPerPage = 10;
    const prevLinkedInPageBtn = document.getElementById('prevLinkedInPage');
    const nextLinkedInPageBtn = document.getElementById('nextLinkedInPage');
    const linkedinPageIndicator = document.getElementById('linkedinPageIndicator');
    
    // Load content on page load
    loadReports();
    loadForecasts();
    loadLinkedInContent();
    checkMlStatus();
    checkImageGenerationModel();
    setupVisualizationOptions();
    
    // Event Listeners
    if (generateReportBtn) {
        generateReportBtn.addEventListener('click', openReportModal);
    }
    
    if (generateForecastBtn) {
        generateForecastBtn.addEventListener('click', openForecastModal);
    }
    
    if (generateLinkedInBtn) {
        generateLinkedInBtn.addEventListener('click', openLinkedInModal);
    }
    
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeReportModal);
    }
    
    if (closeForecastModalBtn) {
        closeForecastModalBtn.addEventListener('click', closeForecastModal);
    }
    
    if (closeLinkedInModalBtn) {
        closeLinkedInModalBtn.addEventListener('click', closeLinkedInModal);
    }
    
    if (reportForm) {
        reportForm.addEventListener('submit', handleReportGeneration);
    }
    
    if (forecastForm) {
        forecastForm.addEventListener('submit', handleForecastGeneration);
    }
    
    if (linkedinForm) {
        linkedinForm.addEventListener('submit', handleLinkedInGeneration);
    }
    
    // LinkedIn filters
    if (linkedinPostTypeFilter) {
        linkedinPostTypeFilter.addEventListener('change', () => {
            linkedinCurrentPage = 1;
            loadLinkedInContent();
        });
    }
    
    if (linkedinSearch) {
        linkedinSearch.addEventListener('input', debounce(() => {
            linkedinCurrentPage = 1;
            loadLinkedInContent();
        }, 500));
    }
    
    // LinkedIn pagination
    if (prevLinkedInPageBtn) {
        prevLinkedInPageBtn.addEventListener('click', () => {
            if (linkedinCurrentPage > 1) {
                linkedinCurrentPage--;
                loadLinkedInContent();
            }
        });
    }
    
    if (nextLinkedInPageBtn) {
        nextLinkedInPageBtn.addEventListener('click', () => {
            if (linkedinCurrentPage < linkedinTotalPages) {
                linkedinCurrentPage++;
                loadLinkedInContent();
            }
        });
    }
    
    // GPT-4o image toggle
    if (gpt4oImageToggle) {
        gpt4oImageToggle.addEventListener('change', updateImageGenerationModel);
    }
    
    // Customize image options toggle
    if (customizeImageCheckbox) {
        customizeImageCheckbox.addEventListener('change', function() {
            if (this.checked) {
                linkedinImageOptions.style.display = 'block';
            } else {
                linkedinImageOptions.style.display = 'none';
            }
        });
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
        if (e.target === linkedinModal) {
            closeLinkedInModal();
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

    /**
     * Check the current image generation model setting
     */
    function checkImageGenerationModel() {
        if (!currentImageModel) return;
        
        fetch('/api/config/image-generation')
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    console.error('Error fetching image generation config:', data.error);
                    return;
                }
                
                const useGPT4o = data.use_gpt4o_images === true;
                
                // Update the toggle
                if (gpt4oImageToggle) {
                    gpt4oImageToggle.checked = useGPT4o;
                }
                
                // Update the display
                updateImageModelDisplay(useGPT4o ? 'gpt-4o' : 'dall-e');
            })
            .catch(error => {
                console.error('Error checking image generation model:', error);
                updateImageModelDisplay('dall-e'); // Default fallback
            });
    }
    
    /**
     * Update the image generation model setting
     */
    function updateImageGenerationModel() {
        const useGPT4o = gpt4oImageToggle.checked;
        
        // Show loading state
        updateImageModelDisplay('loading');
        
        // Call API to update the setting
        fetch('/api/config/image-generation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                use_gpt4o_images: useGPT4o
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Error updating image generation model:', data.error);
                showToast('Error', 'Failed to update image generation model', 'error');
                // Revert the toggle
                gpt4oImageToggle.checked = !useGPT4o;
                updateImageModelDisplay(!useGPT4o ? 'gpt-4o' : 'dall-e');
                return;
            }
            
            // Update the display
            updateImageModelDisplay(useGPT4o ? 'gpt-4o' : 'dall-e');
            showToast('Success', `Image generation model updated to ${useGPT4o ? 'GPT-4o' : 'DALL-E'}`, 'success');
        })
        .catch(error => {
            console.error('Error updating image generation model:', error);
            showToast('Error', 'Failed to update image generation model', 'error');
            // Revert the toggle
            gpt4oImageToggle.checked = !useGPT4o;
            updateImageModelDisplay(!useGPT4o ? 'gpt-4o' : 'dall-e');
        });
    }
    
    /**
     * Update the image model display
     */
    function updateImageModelDisplay(model) {
        if (!currentImageModel) return;
        
        if (model === 'loading') {
            currentImageModel.innerHTML = '<span class="spinner-border" style="width: 1rem; height: 1rem;"></span> Updating...';
            return;
        }
        
        if (model === 'gpt-4o') {
            currentImageModel.innerHTML = 'GPT-4o <span class="image-model-badge gpt4o">Primary</span>';
        } else {
            currentImageModel.innerHTML = 'DALL-E <span class="image-model-badge dalle">Primary</span>';
        }
    }
    
    /**
     * Load LinkedIn content from the API
     */
    function loadLinkedInContent() {
        if (!linkedinPostsContainer) return;
        
        // Show loading spinner
        if (linkedinPostsLoading) {
            linkedinPostsLoading.style.display = 'block';
        }
        
        // Get filter values
        const postType = linkedinPostTypeFilter ? linkedinPostTypeFilter.value : 'all';
        const searchQuery = linkedinSearch ? linkedinSearch.value : '';
        
        // Build query string
        let queryParams = new URLSearchParams();
        if (postType !== 'all') {
            queryParams.append('type', postType);
        }
        if (searchQuery) {
            queryParams.append('search', searchQuery);
        }
        queryParams.append('limit', linkedinItemsPerPage);
        queryParams.append('offset', (linkedinCurrentPage - 1) * linkedinItemsPerPage);
        
        fetch(`/api/linkedin/posts?${queryParams.toString()}`)
            .then(response => response.json())
            .then(data => {
                if (linkedinPostsLoading) {
                    linkedinPostsLoading.style.display = 'none';
                }
                
                if (linkedinPostsContainer) {
                    if (data.posts && data.posts.length > 0) {
                        displayLinkedInPosts(data.posts);
                        
                        // Update pagination
                        const totalItems = data.meta.total;
                        linkedinTotalPages = Math.ceil(totalItems / linkedinItemsPerPage);
                        
                        if (linkedinPageIndicator) {
                            linkedinPageIndicator.textContent = `Page ${linkedinCurrentPage} of ${linkedinTotalPages}`;
                        }
                        
                        if (prevLinkedInPageBtn) {
                            prevLinkedInPageBtn.disabled = linkedinCurrentPage <= 1;
                        }
                        
                        if (nextLinkedInPageBtn) {
                            nextLinkedInPageBtn.disabled = linkedinCurrentPage >= linkedinTotalPages;
                        }
                    } else {
                        linkedinPostsContainer.innerHTML = '<p class="no-reports-message">No LinkedIn posts found. Generate your first post!</p>';
                        
                        // Reset pagination
                        if (linkedinPageIndicator) {
                            linkedinPageIndicator.textContent = 'Page 1 of 1';
                        }
                        
                        if (prevLinkedInPageBtn) {
                            prevLinkedInPageBtn.disabled = true;
                        }
                        
                        if (nextLinkedInPageBtn) {
                            nextLinkedInPageBtn.disabled = true;
                        }
                    }
                }
            })
            .catch(error => {
                console.error('Error loading LinkedIn posts:', error);
                if (linkedinPostsLoading) {
                    linkedinPostsLoading.style.display = 'none';
                }
                
                if (linkedinPostsContainer) {
                    linkedinPostsContainer.innerHTML = '<p class="no-reports-message">Error loading LinkedIn posts. Please try again later.</p>';
                }
                
                showToast('Error', 'Failed to load LinkedIn posts. Please try again later.', 'error');
            });
    }
    
    /**
     * Display LinkedIn posts in the container
     */
    function displayLinkedInPosts(posts) {
        if (!linkedinPostsContainer) return;
        
        linkedinPostsContainer.innerHTML = '';
        
        posts.forEach(post => {
            const postCard = document.createElement('div');
            postCard.className = 'linkedin-post-card';
            
            // Format the hashtags
            let hashtagsHTML = '';
            if (post.hashtags && post.hashtags.length > 0) {
                hashtagsHTML = post.hashtags.slice(0, 5).map(tag => {
                    return `<span class="linkedin-hashtag">${tag}</span>`;
                }).join(' ');
                
                if (post.hashtags.length > 5) {
                    hashtagsHTML += ' <span class="linkedin-hashtag">+' + (post.hashtags.length - 5) + ' more</span>';
                }
            }
            
            postCard.innerHTML = `
                <div class="linkedin-post-header">
                    <h3 class="linkedin-post-title">${post.title}</h3>
                    <span class="linkedin-post-type ${post.type}">${post.type.replace('_', ' ')}</span>
                </div>
                <div class="linkedin-post-content">
                    ${post.image_url ? `<img src="${post.image_url}" alt="LinkedIn post image" class="linkedin-post-image">` : ''}
                    <div class="linkedin-post-text">${post.preview}</div>
                    <div class="linkedin-post-date">${post.formatted_date} at ${post.formatted_time}</div>
                    <div class="linkedin-post-hashtags">${hashtagsHTML}</div>
                </div>
                <div class="linkedin-post-actions">
                    <button class="linkedin-view-btn" data-post-id="${post.id}">
                        <i class="fas fa-eye"></i> View
                    </button>
                    <button class="linkedin-download-btn" data-post-id="${post.id}">
                        <i class="fas fa-download"></i> Download
                    </button>
                </div>
            `;
            
            // Add event listeners
            postCard.querySelector('.linkedin-view-btn').addEventListener('click', () => {
                viewLinkedInPost(post.id);
            });
            
            postCard.querySelector('.linkedin-download-btn').addEventListener('click', () => {
                downloadLinkedInPost(post.id);
            });
            
            linkedinPostsContainer.appendChild(postCard);
        });
    }
    
    /**
     * Open the LinkedIn generation modal
     */
    function openLinkedInModal() {
        if (linkedinModal) {
            linkedinModal.style.display = 'block';
        }
    }
    
    /**
     * Close the LinkedIn generation modal
     */
    function closeLinkedInModal() {
        if (linkedinModal) {
            linkedinModal.style.display = 'none';
        }
    }
    
    /**
     * Handle LinkedIn content generation form submission
     */
    function handleLinkedInGeneration(e) {
        e.preventDefault();
        
        const postType = document.getElementById('linkedin-post-type-select').value;
        const client = document.getElementById('linkedin-client').value;
        const contentText = document.getElementById('linkedin-content-text').value;
        
        // Get image customization if enabled
        const customizeImage = document.getElementById('linkedin-customize-image').checked;
        let imageOptions = null;
        
        if (customizeImage) {
            const imagePrompt = document.getElementById('linkedin-image-prompt').value;
            const imageStyle = document.querySelector('input[name="linkedin-image-style"]:checked').value;
            
            if (imagePrompt || imageStyle) {
                imageOptions = {
                    prompt: imagePrompt,
                    style: imageStyle
                };
            }
        }
        
        // Disable the form while generating
        const generateBtn = document.getElementById('linkedin-generate-btn');
        const originalBtnText = generateBtn.textContent;
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<span class="spinner-border"></span> Generating...';
        
        // Prepare data for API call
        const data = {
            post_type: postType,
            client: client
        };
        
        if (contentText) {
            data.content_text = contentText;
        }
        
        if (imageOptions) {
            data.image_options = imageOptions;
        }
        
        // Call the API to generate the content
        fetch('/api/linkedin/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            // Re-enable the form
            generateBtn.disabled = false;
            generateBtn.textContent = originalBtnText;
            
            if (data.success) {
                showToast('Success', data.message, 'success');
                closeLinkedInModal();
                
                // Don't reload immediately, as the generation is running in a background thread
                setTimeout(() => {
                    loadLinkedInContent();
                }, 10000); // Wait 10 seconds before reloading
            } else {
                showToast('Error', data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error generating LinkedIn content:', error);
            
            // Re-enable the form
            generateBtn.disabled = false;
            generateBtn.textContent = originalBtnText;
            
            showToast('Error', 'Failed to generate LinkedIn content. Please try again later.', 'error');
        });
    }
    
    /**
     * View a LinkedIn post in a modal
     */
    function viewLinkedInPost(postId) {
        fetch(`/api/linkedin/post/${postId}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showToast('Error', data.error, 'error');
                    return;
                }
                
                // Create a modal to display the post
                const viewModal = document.createElement('div');
                viewModal.className = 'modal';
                viewModal.style.display = 'block';
                
                // Format the hashtags
                let hashtagsHTML = '';
                if (data.hashtags && data.hashtags.length > 0) {
                    hashtagsHTML = data.hashtags.map(tag => {
                        return `<span class="linkedin-hashtag">${tag}</span>`;
                    }).join(' ');
                }
                
                // Format the text with line breaks
                const formattedText = data.text.replace(/\n/g, '<br>');
                
                viewModal.innerHTML = `
                    <div class="modal-content" style="max-width: 800px;">
                        <span class="close">&times;</span>
                        <h2>${data.title}</h2>
                        <div class="linkedin-post-full">
                            <div class="linkedin-post-meta">
                                <span class="linkedin-post-type ${data.type}">${data.type.replace('_', ' ')}</span>
                                <span class="linkedin-post-date">${data.formatted_date} at ${data.formatted_time}</span>
                            </div>
                            ${data.image_url ? `
                                <div class="linkedin-post-image-container">
                                    <img src="${data.image_url}" alt="LinkedIn post image" style="max-width: 100%; border-radius: 4px; margin: 1rem 0;">
                                    ${data.image_generator ? `<div class="image-generator-info">Image generated by ${data.image_generator}</div>` : ''}
                                </div>
                            ` : ''}
                            <div class="linkedin-post-full-text" style="margin: 1rem 0; line-height: 1.6;">
                                ${formattedText}
                            </div>
                            <div class="linkedin-post-hashtags" style="margin-top: 1rem;">
                                ${hashtagsHTML}
                            </div>
                        </div>
                        <div class="modal-actions" style="margin-top: 2rem; display: flex; justify-content: space-between;">
                            <button class="btn btn-sm" onclick="copyToClipboard('${postId}')">
                                <i class="fas fa-copy"></i> Copy Text
                            </button>
                            <button class="btn btn-sm" onclick="downloadLinkedInPost('${postId}')">
                                <i class="fas fa-download"></i> Download
                            </button>
                        </div>
                    </div>
                `;
                
                // Add event listener to close the modal
                viewModal.querySelector('.close').addEventListener('click', () => {
                    document.body.removeChild(viewModal);
                });
                
                // Add event listener to close on click outside
                viewModal.addEventListener('click', (e) => {
                    if (e.target === viewModal) {
                        document.body.removeChild(viewModal);
                    }
                });
                
                document.body.appendChild(viewModal);
                
                // Add the copy function to the window object
                window.copyToClipboard = function(id) {
                    const postText = data.text;
                    navigator.clipboard.writeText(postText)
                        .then(() => {
                            showToast('Success', 'Post text copied to clipboard', 'success');
                        })
                        .catch(err => {
                            showToast('Error', 'Failed to copy text', 'error');
                            console.error('Could not copy text: ', err);
                        });
                };
                
                // Add the download function to the window object
                window.downloadLinkedInPost = downloadLinkedInPost;
            })
            .catch(error => {
                console.error('Error viewing LinkedIn post:', error);
                showToast('Error', 'Failed to load post details', 'error');
            });
    }
    
    /**
     * Download a LinkedIn post as markdown
     */
    function downloadLinkedInPost(postId) {
        fetch(`/api/linkedin/post/${postId}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showToast('Error', data.error, 'error');
                    return;
                }
                
                // Format the text with Markdown line breaks
                const formattedText = data.text;
                
                // Create a markdown file
                let markdown = `# ${data.title}\n\n`;
                markdown += `**Type:** ${data.type.replace('_', ' ')}\n`;
                markdown += `**Date:** ${data.formatted_date} at ${data.formatted_time}\n\n`;
                markdown += formattedText + '\n\n';
                
                if (data.image_url) {
                    markdown += `![LinkedIn post image](${data.image_url})\n\n`;
                }
                
                if (data.hashtags && data.hashtags.length > 0) {
                    markdown += `**Hashtags:** ${data.hashtags.join(' ')}\n`;
                }
                
                // Create a blob and download it
                const blob = new Blob([markdown], { type: 'text/markdown' });
                const url = URL.createObjectURL(blob);
                
                const a = document.createElement('a');
                a.href = url;
                a.download = `linkedin_post_${postId}.md`;
                document.body.appendChild(a);
                a.click();
                
                // Clean up
                setTimeout(() => {
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                }, 0);
                
                showToast('Success', 'Post downloaded as markdown', 'success');
            })
            .catch(error => {
                console.error('Error downloading LinkedIn post:', error);
                showToast('Error', 'Failed to download post', 'error');
            });
    }
    
    /**
     * Debounce function for search input
     */
    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }
}); 