/**
 * Article Summaries Component
 * 
 * This component displays a list of recent articles with their summaries
 * and provides controls for filtering and managing summaries.
 */

const SummariesComponent = {
    init: function() {
        this.summariesContainer = document.getElementById('summaries-container');
        this.loadMoreBtn = document.getElementById('load-more-summaries');
        this.filterByClientSelect = document.getElementById('filter-by-client');
        this.generateSummariesBtn = document.getElementById('generate-summaries');
        
        this.currentPage = 1;
        this.pageSize = 10;
        this.selectedClientId = '';
        
        this.bindEvents();
        this.loadSummaries();
        this.loadClientOptions();
    },
    
    bindEvents: function() {
        if (this.loadMoreBtn) {
            this.loadMoreBtn.addEventListener('click', () => {
                this.currentPage++;
                this.loadSummaries(true);
            });
        }
        
        if (this.filterByClientSelect) {
            this.filterByClientSelect.addEventListener('change', () => {
                this.selectedClientId = this.filterByClientSelect.value;
                this.currentPage = 1;
                this.loadSummaries();
            });
        }
        
        if (this.generateSummariesBtn) {
            this.generateSummariesBtn.addEventListener('click', () => {
                this.generateSummaries();
            });
        }
    },
    
    loadClientOptions: function() {
        if (!this.filterByClientSelect) return;
        
        fetch('/api/clients')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Clear existing options
                    this.filterByClientSelect.innerHTML = '<option value="">All Clients</option>';
                    
                    // Add client options
                    data.clients.forEach(client => {
                        const option = document.createElement('option');
                        option.value = client.id;
                        option.textContent = client.name;
                        this.filterByClientSelect.appendChild(option);
                    });
                } else {
                    console.error('Failed to load clients:', data.message);
                }
            })
            .catch(error => {
                console.error('Error loading clients:', error);
            });
    },
    
    loadSummaries: function(append = false) {
        if (!this.summariesContainer) return;
        
        // Show loading indicator
        const loadingIndicator = document.createElement('div');
        loadingIndicator.className = 'loading-indicator';
        loadingIndicator.textContent = 'Loading summaries...';
        
        if (!append) {
            this.summariesContainer.innerHTML = '';
            this.summariesContainer.appendChild(loadingIndicator);
        } else {
            this.summariesContainer.appendChild(loadingIndicator);
        }
        
        // Build URL with parameters
        let url = `/api/articles?page=${this.currentPage}&limit=${this.pageSize}`;
        if (this.selectedClientId) {
            url += `&client_id=${this.selectedClientId}`;
        }
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                // Remove loading indicator
                this.summariesContainer.removeChild(loadingIndicator);
                
                if (data.success) {
                    // Clear container if not appending
                    if (!append) {
                        this.summariesContainer.innerHTML = '';
                    }
                    
                    // Add articles to container
                    data.articles.forEach(article => {
                        this.summariesContainer.appendChild(this.createArticleSummaryCard(article));
                    });
                    
                    // Show/hide load more button
                    if (data.has_more) {
                        this.loadMoreBtn.style.display = 'block';
                    } else {
                        this.loadMoreBtn.style.display = 'none';
                    }
                    
                    // Show message if no articles
                    if (data.articles.length === 0 && !append) {
                        const noResults = document.createElement('div');
                        noResults.className = 'no-results';
                        noResults.textContent = 'No articles found.';
                        this.summariesContainer.appendChild(noResults);
                    }
                } else {
                    console.error('Failed to load articles:', data.message);
                    const errorMsg = document.createElement('div');
                    errorMsg.className = 'error-message';
                    errorMsg.textContent = `Error: ${data.message}`;
                    this.summariesContainer.appendChild(errorMsg);
                }
            })
            .catch(error => {
                console.error('Error loading articles:', error);
                // Remove loading indicator
                this.summariesContainer.removeChild(loadingIndicator);
                
                const errorMsg = document.createElement('div');
                errorMsg.className = 'error-message';
                errorMsg.textContent = `Error: ${error.message}`;
                this.summariesContainer.appendChild(errorMsg);
            });
    },
    
    createArticleSummaryCard: function(article) {
        const card = document.createElement('div');
        card.className = 'article-card';
        card.dataset.articleId = article.id;
        
        // Format date
        const date = article.pub_date ? new Date(article.pub_date) : new Date(article.extracted_at);
        const formattedDate = date.toLocaleDateString();
        
        // Create summary content
        const summary = article.summary || 'No summary available';
        const hasSummary = Boolean(article.summary);
        
        card.innerHTML = `
            <div class="article-header">
                <h3 class="article-title">
                    <a href="${article.url}" target="_blank" rel="noopener noreferrer">${article.title}</a>
                </h3>
                <div class="article-meta">
                    <span class="article-date">${formattedDate}</span>
                    <span class="article-source">${article.domain || 'Unknown source'}</span>
                </div>
            </div>
            <div class="article-content">
                <div class="article-description">${article.description || ''}</div>
                <div class="article-summary ${hasSummary ? 'has-summary' : 'no-summary'}">
                    <h4>Summary</h4>
                    <p>${summary}</p>
                </div>
            </div>
            <div class="article-footer">
                <div class="article-tags">
                    ${(article.keywords || []).map(tag => `<span class="tag">${tag}</span>`).join('')}
                </div>
                <div class="article-actions">
                    ${!hasSummary ? 
                        `<button class="btn btn-sm btn-primary generate-summary-btn" data-article-id="${article.id}">
                            Generate Summary
                        </button>` : 
                        `<button class="btn btn-sm btn-outline-primary regenerate-summary-btn" data-article-id="${article.id}">
                            Regenerate
                        </button>`
                    }
                    <button class="btn btn-sm btn-outline-secondary view-full-btn" data-article-id="${article.id}">
                        View Full Article
                    </button>
                </div>
            </div>
        `;
        
        // Add event listeners
        const generateBtn = card.querySelector('.generate-summary-btn, .regenerate-summary-btn');
        if (generateBtn) {
            generateBtn.addEventListener('click', () => {
                this.generateSummaryForArticle(article.id);
            });
        }
        
        const viewFullBtn = card.querySelector('.view-full-btn');
        if (viewFullBtn) {
            viewFullBtn.addEventListener('click', () => {
                this.showFullArticleModal(article);
            });
        }
        
        return card;
    },
    
    generateSummaryForArticle: function(articleId) {
        // Find the card and update its state
        const card = this.summariesContainer.querySelector(`[data-article-id="${articleId}"]`);
        if (!card) return;
        
        const summaryContainer = card.querySelector('.article-summary');
        const actionBtn = card.querySelector('.generate-summary-btn, .regenerate-summary-btn');
        
        // Show loading state
        summaryContainer.innerHTML = '<p>Generating summary...</p>';
        actionBtn.disabled = true;
        actionBtn.textContent = 'Processing...';
        
        fetch(`/api/articles/${articleId}/summarize`, {
            method: 'POST'
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update the summary in the UI
                    summaryContainer.innerHTML = `<h4>Summary</h4><p>${data.summary}</p>`;
                    summaryContainer.classList.remove('no-summary');
                    summaryContainer.classList.add('has-summary');
                    
                    // Update the button
                    actionBtn.classList.remove('btn-primary');
                    actionBtn.classList.remove('generate-summary-btn');
                    actionBtn.classList.add('btn-outline-primary');
                    actionBtn.classList.add('regenerate-summary-btn');
                    actionBtn.textContent = 'Regenerate';
                    actionBtn.disabled = false;
                } else {
                    // Show error message
                    summaryContainer.innerHTML = `<h4>Summary</h4><p>Error: ${data.message}</p>`;
                    actionBtn.textContent = 'Try Again';
                    actionBtn.disabled = false;
                }
            })
            .catch(error => {
                console.error('Error generating summary:', error);
                summaryContainer.innerHTML = `<h4>Summary</h4><p>Error: ${error.message}</p>`;
                actionBtn.textContent = 'Try Again';
                actionBtn.disabled = false;
            });
    },
    
    generateSummaries: function() {
        // Update button state
        this.generateSummariesBtn.disabled = true;
        this.generateSummariesBtn.textContent = 'Processing...';
        
        // Call the API to generate summaries for all articles without summaries
        fetch('/api/articles/summarize-batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                client_id: this.selectedClientId || null,
                limit: 20
            })
        })
            .then(response => response.json())
            .then(data => {
                // Reset button state
                this.generateSummariesBtn.disabled = false;
                this.generateSummariesBtn.textContent = 'Generate Missing Summaries';
                
                if (data.success) {
                    // Show success message
                    const message = `Successfully summarized ${data.count} articles.`;
                    this.showNotification(message, 'success');
                    
                    // Reload summaries
                    this.currentPage = 1;
                    this.loadSummaries();
                } else {
                    // Show error message
                    this.showNotification(`Error: ${data.message}`, 'error');
                }
            })
            .catch(error => {
                console.error('Error generating summaries:', error);
                this.generateSummariesBtn.disabled = false;
                this.generateSummariesBtn.textContent = 'Generate Missing Summaries';
                this.showNotification(`Error: ${error.message}`, 'error');
            });
    },
    
    showFullArticleModal: function(article) {
        // Create modal
        const modal = document.createElement('div');
        modal.className = 'modal article-modal';
        modal.innerHTML = `
            <div class="modal-backdrop"></div>
            <div class="modal-content">
                <div class="modal-header">
                    <h2>${article.title}</h2>
                    <button class="close-modal">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="article-meta">
                        <span class="article-date">${new Date(article.pub_date || article.extracted_at).toLocaleDateString()}</span>
                        <span class="article-source">${article.domain || 'Unknown source'}</span>
                        <a href="${article.url}" target="_blank" rel="noopener noreferrer" class="article-link">View Original</a>
                    </div>
                    <div class="tabs">
                        <button class="tab-btn active" data-tab="summary">Summary</button>
                        <button class="tab-btn" data-tab="content">Full Content</button>
                        <button class="tab-btn" data-tab="meta">Metadata</button>
                    </div>
                    <div class="tab-content active" data-tab="summary">
                        <h3>Summary</h3>
                        <p>${article.summary || 'No summary available'}</p>
                        ${!article.summary ? 
                            `<button class="btn btn-sm btn-primary generate-summary-btn" data-article-id="${article.id}">
                                Generate Summary
                            </button>` : 
                            ''
                        }
                    </div>
                    <div class="tab-content" data-tab="content">
                        <h3>Full Content</h3>
                        <div class="full-content">${article.content || 'No content available'}</div>
                    </div>
                    <div class="tab-content" data-tab="meta">
                        <h3>Metadata</h3>
                        <div class="metadata">
                            <p><strong>Source:</strong> ${article.domain || 'Unknown'}</p>
                            <p><strong>Published:</strong> ${article.pub_date || 'Unknown'}</p>
                            <p><strong>Extracted:</strong> ${article.extracted_at || 'Unknown'}</p>
                            <p><strong>Keywords:</strong> ${(article.keywords || []).join(', ') || 'None'}</p>
                            <p><strong>URL:</strong> <a href="${article.url}" target="_blank" rel="noopener noreferrer">${article.url}</a></p>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-primary generate-linkedin-btn" data-article-id="${article.id}">
                        Generate LinkedIn Post
                    </button>
                    <button class="btn btn-secondary close-modal-btn">Close</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Prevent body scrolling
        document.body.classList.add('modal-open');
        
        // Handle tab switching
        const tabBtns = modal.querySelectorAll('.tab-btn');
        const tabContents = modal.querySelectorAll('.tab-content');
        
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const tab = btn.dataset.tab;
                
                // Update active tab button
                tabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // Update active tab content
                tabContents.forEach(content => {
                    if (content.dataset.tab === tab) {
                        content.classList.add('active');
                    } else {
                        content.classList.remove('active');
                    }
                });
            });
        });
        
        // Handle generate summary button
        const generateSummaryBtn = modal.querySelector('.generate-summary-btn');
        if (generateSummaryBtn) {
            generateSummaryBtn.addEventListener('click', () => {
                const summaryTab = modal.querySelector('.tab-content[data-tab="summary"]');
                summaryTab.innerHTML = '<p>Generating summary...</p>';
                
                fetch(`/api/articles/${article.id}/summarize`, {
                    method: 'POST'
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            summaryTab.innerHTML = `<h3>Summary</h3><p>${data.summary}</p>`;
                        } else {
                            summaryTab.innerHTML = `<h3>Summary</h3><p>Error: ${data.message}</p><button class="btn btn-sm btn-primary generate-summary-btn" data-article-id="${article.id}">Try Again</button>`;
                        }
                    })
                    .catch(error => {
                        console.error('Error generating summary:', error);
                        summaryTab.innerHTML = `<h3>Summary</h3><p>Error: ${error.message}</p><button class="btn btn-sm btn-primary generate-summary-btn" data-article-id="${article.id}">Try Again</button>`;
                    });
            });
        }
        
        // Handle generate LinkedIn post button
        const generateLinkedInBtn = modal.querySelector('.generate-linkedin-btn');
        if (generateLinkedInBtn) {
            generateLinkedInBtn.addEventListener('click', () => {
                generateLinkedInBtn.disabled = true;
                generateLinkedInBtn.textContent = 'Generating...';
                
                fetch(`/api/linkedin/generate`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        article_id: article.id
                    })
                })
                    .then(response => response.json())
                    .then(data => {
                        generateLinkedInBtn.disabled = false;
                        generateLinkedInBtn.textContent = 'Generate LinkedIn Post';
                        
                        if (data.success) {
                            this.showNotification('LinkedIn post generated successfully!', 'success');
                        } else {
                            this.showNotification(`Error: ${data.message}`, 'error');
                        }
                    })
                    .catch(error => {
                        console.error('Error generating LinkedIn post:', error);
                        generateLinkedInBtn.disabled = false;
                        generateLinkedInBtn.textContent = 'Generate LinkedIn Post';
                        this.showNotification(`Error: ${error.message}`, 'error');
                    });
            });
        }
        
        // Handle close modal
        const closeButtons = modal.querySelectorAll('.close-modal, .close-modal-btn, .modal-backdrop');
        closeButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                document.body.removeChild(modal);
                document.body.classList.remove('modal-open');
            });
        });
    },
    
    showNotification: function(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        // Add close button
        const closeBtn = document.createElement('button');
        closeBtn.className = 'notification-close';
        closeBtn.innerHTML = '&times;';
        closeBtn.addEventListener('click', () => {
            document.body.removeChild(notification);
        });
        
        notification.appendChild(closeBtn);
        document.body.appendChild(notification);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 5000);
    }
};

// Initialize the component when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    SummariesComponent.init();
});

export default SummariesComponent; 