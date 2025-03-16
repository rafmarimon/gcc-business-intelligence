import os
import logging
import json
from datetime import datetime
from pathlib import Path
import markdown
from dotenv import load_dotenv
import shutil
import weasyprint

# Import our modules
from processors.news_analyzer import GCCBusinessNewsAnalyzer
from generators.linkedin_content import LinkedInContentGenerator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ConsolidatedReport")

class ConsolidatedReportGenerator:
    """
    Generates a consolidated report containing daily business intelligence and LinkedIn posts.
    """
    def __init__(self, reports_dir='reports', content_dir='content', data_dir='data'):
        """Initialize the consolidated report generator."""
        self.reports_dir = reports_dir
        self.content_dir = content_dir
        self.data_dir = data_dir
        
        # Create directories if they don't exist
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs(self.content_dir, exist_ok=True)
        
        # Initialize components
        self.analyzer = GCCBusinessNewsAnalyzer(
            reports_dir=self.reports_dir,
            data_dir=self.data_dir
        )
        self.linkedin_generator = LinkedInContentGenerator(
            reports_dir=self.reports_dir,
            content_dir=self.content_dir,
            data_dir=self.data_dir
        )
    
    def generate_all(self, articles=None):
        """Generate the complete report: daily analysis and LinkedIn posts."""
        logger.info("Starting consolidated report generation...")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Step 1: Generate the daily report
        logger.info("Generating daily business intelligence report...")
        report_path, report_text = self.analyzer.generate_daily_report(articles)
        
        if not report_path or not report_text:
            logger.error("Failed to generate daily report.")
            return None, None, None
        
        logger.info(f"Daily report generated at {report_path}")
        
        # Step 2: Generate LinkedIn posts based on the report
        logger.info("Generating LinkedIn posts...")
        linkedin_posts = self.linkedin_generator.generate_linkedin_posts()
        
        if not linkedin_posts:
            logger.warning("No LinkedIn posts were generated. Using fallback posts.")
            # Create fallback LinkedIn posts if none were generated
            fallback_posts = [
                {
                    "title": "US-UAE Business Partnership Developments",
                    "content": """🇺🇸🇦🇪 **Strategic Business Alliances: US and UAE**

The US-UAE business relationship continues to strengthen, with ongoing collaborations in key sectors including technology, energy, and defense.

This bilateral relationship creates significant opportunities for businesses in both countries, with the UAE serving as a strategic gateway to the broader Middle East market and the US providing access to advanced technologies and investment opportunities.

The US-UAE Business Council reports that bilateral trade has been steadily increasing, demonstrating the robust economic ties between these nations.

What opportunities do you see in this growing partnership? How might your business benefit from these strengthening ties?

#USUAERelations #InternationalTrade #BusinessDiplomacy #GlobalOpportunities #UAEBusiness #USBusiness""",
                    "category": "us_uae_relations"
                },
                {
                    "title": "UAE's Economic Diversification Strategy",
                    "content": """📊 **UAE's Economic Transformation Journey**

The UAE continues to make remarkable progress in its economic diversification strategy, reducing oil dependency while developing robust sectors in finance, tourism, technology, and renewable energy.

Recent government initiatives and investments in innovation hubs, SME development, and sustainable projects demonstrate the UAE's commitment to building a knowledge-based economy that can thrive in a post-oil world.

As the landscape evolves, businesses positioned to support this transformation are finding significant growth opportunities across multiple sectors.

How is your organization adapting to the UAE's changing economic priorities? What new market opportunities do you see emerging from this transformation?

#UAEEconomy #EconomicDiversification #InnovationStrategy #BusinessGrowth #MiddleEastBusiness #FutureEconomy""",
                    "category": "economy"
                },
                {
                    "title": "Digital Transformation in GCC Banking",
                    "content": """💳 **Banking Revolution: Digital Transformation in the GCC**

GCC financial institutions are rapidly adopting digital technologies, with online banking usage surging and fintech partnerships becoming increasingly common across the region.

This digital shift is fundamentally changing how businesses and consumers interact with financial services, offering greater convenience, efficiency, and new financial products tailored to the region's unique needs.

As traditional banking models evolve, companies that can navigate this digital ecosystem will find themselves at a competitive advantage.

Is your business prepared for the region's digital financial transformation? What opportunities do you see in this rapidly evolving landscape?

#DigitalBanking #FinTech #GCCFinance #BankingInnovation #DigitalTransformation #MiddleEastFinance""",
                    "category": "finance"
                }
            ]
            linkedin_posts = fallback_posts
            logger.info("Created 3 fallback LinkedIn posts to ensure content is available")
        else:
            logger.info(f"Generated {len(linkedin_posts)} LinkedIn posts")
        
        # Step 3: Create the consolidated report
        consolidated_path = self._create_consolidated_report(report_text, linkedin_posts, timestamp)
        
        if consolidated_path:
            logger.info(f"Consolidated report generated at {consolidated_path}")
            
            # Create HTML version for better viewing
            html_path = self._create_html_version(consolidated_path)
            if html_path:
                logger.info(f"HTML version generated at {html_path}")
                
                # Create PDF version (report only, no LinkedIn posts)
                pdf_path = self._create_pdf_version(report_text, timestamp)
                if pdf_path:
                    logger.info(f"PDF version generated at {pdf_path}")
                    return consolidated_path, html_path, pdf_path
                
                return consolidated_path, html_path, None
            
            return consolidated_path, None, None
        
        logger.error("Failed to generate consolidated report.")
        return None, None, None
    
    def _create_consolidated_report(self, report_text, linkedin_posts, timestamp):
        """Combine the daily report and LinkedIn posts into a single markdown file."""
        try:
            file_path = os.path.join(self.reports_dir, f"consolidated_report_{timestamp}.md")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                # Write the title
                current_date = datetime.now().strftime("%B %d, %Y")
                f.write(f"# Global Possibilities - Daily Business Intelligence Report: {current_date}\n\n")
                f.write(f"**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("---\n\n")
                
                # Add table of contents
                f.write("## Table of Contents\n\n")
                f.write("1. [Daily Business Intelligence Report](#daily-business-intelligence-report)\n")
                if linkedin_posts:
                    f.write("2. [LinkedIn Content](#linkedin-content)\n")
                f.write("\n---\n\n")
                
                # Add the daily report
                f.write("## Daily Business Intelligence Report\n\n")
                f.write(report_text)
                f.write("\n\n---\n\n")
                
                # Add LinkedIn posts if available
                if linkedin_posts:
                    f.write("## LinkedIn Content\n\n")
                    f.write("The following LinkedIn posts have been generated based on the business intelligence report:\n\n")
                    
                    for i, post in enumerate(linkedin_posts):
                        f.write(f"### Post {i+1}: {post.get('title', 'Business Insight')}\n\n")
                        f.write(f"```\n{post.get('content', '')}\n```\n\n")
                
                # Add footer
                f.write("\n\n---\n\n")
                f.write("*© Global Possibilities. All rights reserved.*\n")
            
            return file_path
            
        except Exception as e:
            logger.error(f"Error creating consolidated report: {e}")
            return None
    
    def _create_html_version(self, markdown_path):
        """Create an HTML version of the consolidated report for easier viewing."""
        try:
            # Read the markdown content
            with open(markdown_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            # Convert to HTML
            html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code', 'nl2br'])
            
            # Format current date for display
            current_date = datetime.now().strftime('%B %d, %Y')
            current_year = datetime.now().year
            
            # Check if the logo exists
            logo_file = os.path.join('reports', 'assets', 'images', 'logo.svg')
            logo_html = ""
            if os.path.exists(logo_file):
                with open(logo_file, 'r') as f:
                    logo_svg = f.read()
                logo_html = logo_svg
            else:
                # Fallback to Font Awesome icon
                logo_html = '<i class="fas fa-globe-americas logo-icon"></i>'
            
            # JavaScript for enhancing the report
            js_script = """
                <script>
                    /* Wait for document to fully load before executing */
                    document.addEventListener('DOMContentLoaded', function() {
                        console.log('DOM fully loaded. Initializing chatbot...');
                        
                        /* Find all LinkedIn post sections and apply custom styling */
                        const codeBlocks = document.querySelectorAll('pre');
                        codeBlocks.forEach(block => {
                            if (block.parentElement.previousElementSibling && 
                                block.parentElement.previousElementSibling.tagName.startsWith('H') &&
                                block.parentElement.previousElementSibling.textContent.includes('Post')) {
                                block.parentElement.classList.add('linkedin-post');
                            }
                        });
                        
                        /* Find any tables in the content and make them responsive */
                        const tables = document.querySelectorAll('table');
                        tables.forEach(table => {
                            const wrapper = document.createElement('div');
                            wrapper.style.overflowX = 'auto';
                            table.parentNode.insertBefore(wrapper, table);
                            wrapper.appendChild(table);
                        });
                        
                        /* Chatbot functionality */
                        const chatbotToggle = document.getElementById('chatbot-toggle');
                        const chatbot = document.getElementById('chatbot');
                        const closeChat = document.getElementById('close-chat');
                        const chatMessages = document.getElementById('chat-messages');
                        const chatForm = document.getElementById('chat-form');
                        const userInput = document.getElementById('user-input');
                        const apiKeyInput = document.getElementById('api-key-input');
                        const apiKeyForm = document.getElementById('api-key-form');
                        const chatInterface = document.getElementById('chat-interface');
                        
                        console.log('Chatbot elements:', { 
                            toggle: chatbotToggle, 
                            chatbot: chatbot, 
                            closeBtn: closeChat,
                            form: chatForm,
                            apiForm: apiKeyForm
                        });
                        
                        /* Get the report content for context */
                        const reportContent = document.querySelector('.content-wrapper').textContent;
                        const reportSummary = reportContent.substring(0, 8000); // First 8000 chars as context
                        
                        /* Check for stored API key */
                        let apiKey = localStorage.getItem('openai_api_key');
                        if (apiKey) {
                            apiKeyForm.style.display = 'none';
                            chatInterface.style.display = 'flex';
                        }
                        
                        /* Function to add a message to the chat */
                        function addMessage(sender, message) {
                            const messageEl = document.createElement('div');
                            messageEl.className = `message ${sender}-message`;
                            
                            /* Format code blocks if any */
                            message = message.replace(/```([\\s\\S]*?)```/g, '<pre><code>$1</code></pre>');
                            
                            messageEl.innerHTML = `<div class="message-content">${message}</div>`;
                            chatMessages.appendChild(messageEl);
                            
                            /* Auto scroll to bottom */
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                        }
                        
                        /* API key submission */
                        if (apiKeyForm) {
                            apiKeyForm.addEventListener('submit', function(e) {
                                e.preventDefault();
                                const key = apiKeyInput.value.trim();
                                if (!key) return;
                                
                                /* Store API key in local storage */
                                localStorage.setItem('openai_api_key', key);
                                apiKey = key;
                                
                                /* Hide API form and show chat interface */
                                apiKeyForm.style.display = 'none';
                                chatInterface.style.display = 'flex';
                                
                                /* Add welcome message */
                                setTimeout(function() {
                                    addMessage('bot', 'Hello! I\\'m your GCC Business Intelligence assistant. I can help you understand the content of this report and answer questions about business trends in the UAE/GCC region.');
                                }, 300);
                            });
                        }
                        
                        /* Toggle chatbot visibility */
                        if (chatbotToggle) {
                            console.log('Adding click event listener to chatbot toggle');
                            chatbotToggle.addEventListener('click', function() {
                                console.log('Chatbot toggle clicked');
                                chatbot.classList.toggle('open');
                                if (chatbot.classList.contains('open')) {
                                    console.log('Chatbot opened');
                                    if (apiKey) {
                                        userInput.focus();
                                    } else {
                                        apiKeyInput.focus();
                                    }
                                }
                            });
                        } else {
                            console.error('Chatbot toggle button not found!');
                        }
                        
                        /* Close chatbot */
                        if (closeChat) {
                            closeChat.addEventListener('click', function() {
                                chatbot.classList.remove('open');
                            });
                        }
                        
                        /* Handle chat submission */
                        if (chatForm) {
                            chatForm.addEventListener('submit', async function(e) {
                                e.preventDefault();
                                
                                const message = userInput.value.trim();
                                if (!message) return;
                                
                                /* Add user message to chat */
                                addMessage('user', message);
                                userInput.value = '';
                                
                                /* Add loading indicator */
                                const loadingEl = document.createElement('div');
                                loadingEl.className = 'loading-indicator';
                                loadingEl.innerHTML = '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';
                                chatMessages.appendChild(loadingEl);
                                chatMessages.scrollTop = chatMessages.scrollHeight;
                                
                                try {
                                    /* Send request to OpenAI API directly */
                                    const response = await fetch('https://api.openai.com/v1/chat/completions', {
                                        method: 'POST',
                                        headers: {
                                            'Content-Type': 'application/json',
                                            'Authorization': `Bearer ${apiKey}`
                                        },
                                        body: JSON.stringify({
                                            model: "gpt-3.5-turbo",
                                            messages: [
                                                {
                                                    role: "system", 
                                                    content: `You are a knowledgeable business intelligence assistant specializing in GCC region economics and business trends. 
                                                    Your responses should be helpful, professional, and focused on providing accurate information about UAE and GCC business topics. 
                                                    Keep responses concise (2-3 paragraphs maximum) but informative.
                                                    
                                                    Here's the content from the business intelligence report that you can refer to:
                                                    
                                                    ${reportSummary}`
                                                },
                                                { role: "user", content: message }
                                            ],
                                            max_tokens: 800,
                                            temperature: 0.7
                                        })
                                    });
                                    
                                    if (!response.ok) {
                                        const errorData = await response.json();
                                        throw new Error(errorData.error?.message || 'API request failed');
                                    }
                                    
                                    const data = await response.json();
                                    
                                    /* Remove loading indicator */
                                    loadingEl.remove();
                                    
                                    /* Add bot message to chat */
                                    const reply = data.choices[0].message.content.trim();
                                    addMessage('bot', reply);
                                } catch (error) {
                                    /* Remove loading indicator */
                                    loadingEl.remove();
                                    
                                    /* Add error message */
                                    console.error('Error:', error);
                                    
                                    if (error.message.includes('API key')) {
                                        addMessage('bot', 'There seems to be an issue with your API key. Please check that it\\'s entered correctly or try a new key.');
                                        
                                        /* Reset to API key input */
                                        localStorage.removeItem('openai_api_key');
                                        apiKey = null;
                                        apiKeyForm.style.display = 'block';
                                        chatInterface.style.display = 'none';
                                        apiKeyInput.value = '';
                                    } else {
                                        addMessage('bot', 'Sorry, there was an error connecting to the OpenAI API: ' + error.message);
                                    }
                                }
                            });
                        }
                        
                        /* Add initial welcome message */
                        if (apiKey) {
                            setTimeout(function() {
                                addMessage('bot', 'Hello! I\\'m your GCC Business Intelligence assistant. I can help you understand the content of this report and answer questions about business trends in the UAE/GCC region.');
                            }, 500);
                        }
                        
                        console.log('Chatbot initialization complete.');
                    });
                </script>
            """
            
            # Add CSS styling
            styled_html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Global Possibilities | UAE/GCC Business Intelligence Report</title>
                <!-- Google Fonts - Montserrat and Open Sans -->
                <link rel="preconnect" href="https://fonts.googleapis.com">
                <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
                <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&family=Open+Sans:wght@400;500;600&display=swap" rel="stylesheet">
                
                <!-- Font Awesome for icons -->
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
                
                <style>
                    :root {{
                        --primary-color: #0D3E6D;
                        --secondary-color: #2E2E2E;
                        --accent-color: #E1ECF9;
                        --light-bg: #F9FAFC;
                        --white: #ffffff;
                        --gray-100: #f8f9fa;
                        --gray-200: #e9ecef;
                        --gray-300: #dee2e6;
                        --gray-400: #ced4da;
                        --gray-500: #adb5bd;
                        --gray-600: #6c757d;
                        --gray-700: #495057;
                        --shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
                        --border-radius: 8px;
                    }}
                    
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    
                    body {{
                        font-family: 'Open Sans', sans-serif;
                        line-height: 1.7;
                        background-color: var(--light-bg);
                        color: var(--secondary-color);
                    }}
                    
                    .container {{
                        max-width: 1140px;
                        margin: 0 auto;
                        padding: 0 20px;
                    }}
                    
                    /* Header Styles */
                    header {{
                        background-color: var(--white);
                        box-shadow: var(--shadow);
                        position: sticky;
                        top: 0;
                        z-index: 100;
                    }}
                    
                    .header-container {{
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        padding: 15px 20px;
                    }}
                    
                    .logo {{
                        display: flex;
                        align-items: center;
                    }}
                    
                    .logo h1 {{
                        font-family: 'Montserrat', sans-serif;
                        font-size: 1.5rem;
                        font-weight: 600;
                        color: var(--primary-color);
                        margin: 0;
                        border: none;
                        padding: 0;
                    }}
                    
                    .logo-icon {{
                        color: var(--primary-color);
                        font-size: 1.8rem;
                        margin-right: 10px;
                    }}
                    
                    .logo svg {{
                        height: 32px;
                        width: auto;
                        margin-right: 10px;
                    }}
                    
                    .date-badge {{
                        background-color: var(--accent-color);
                        color: var(--primary-color);
                        padding: 5px 12px;
                        border-radius: 20px;
                        font-size: 0.85rem;
                        font-weight: 500;
                    }}
                    
                    /* Main Content Styles */
                    main {{
                        padding: 40px 0;
                    }}
                    
                    .report-title {{
                        text-align: center;
                        margin-bottom: 40px;
                    }}
                    
                    .report-title h1 {{
                        font-family: 'Montserrat', sans-serif;
                        font-size: 2.2rem;
                        font-weight: 700;
                        color: var(--primary-color);
                        margin-bottom: 10px;
                        border: none;
                        text-align: center;
                    }}
                    
                    .report-title p {{
                        color: var(--gray-600);
                        font-size: 1.1rem;
                    }}
                    
                    /* Card Styles */
                    .card {{
                        background-color: var(--white);
                        border-radius: var(--border-radius);
                        box-shadow: var(--shadow);
                        margin-bottom: 30px;
                        overflow: hidden;
                    }}
                    
                    .card-header {{
                        background-color: var(--primary-color);
                        color: var(--white);
                        padding: 15px 20px;
                        font-family: 'Montserrat', sans-serif;
                        font-weight: 600;
                    }}
                    
                    .card-body {{
                        padding: 25px;
                    }}
                    
                    /* Typography Styles */
                    h1, h2, h3, h4, h5, h6 {{
                        font-family: 'Montserrat', sans-serif;
                        color: var(--primary-color);
                        margin-top: 1.5em;
                        margin-bottom: 0.8em;
                        font-weight: 600;
                    }}
                    
                    h1 {{
                        font-size: 2rem;
                        border-bottom: 2px solid var(--accent-color);
                        padding-bottom: 10px;
                        margin-bottom: 20px;
                    }}
                    
                    h2 {{
                        font-size: 1.75rem;
                    }}
                    
                    h3 {{
                        font-size: 1.5rem;
                    }}
                    
                    h4 {{
                        font-size: 1.25rem;
                    }}
                    
                    p {{
                        margin-bottom: 1rem;
                    }}
                    
                    hr {{
                        border: 0;
                        height: 1px;
                        background: var(--gray-300);
                        margin: 30px 0;
                    }}
                    
                    /* Code and Pre Styles */
                    pre {{
                        background-color: var(--gray-100);
                        border: 1px solid var(--gray-300);
                        border-radius: var(--border-radius);
                        padding: 15px;
                        overflow-x: auto;
                        margin: 20px 0;
                    }}
                    
                    code {{
                        font-family: 'Courier New', Courier, monospace;
                        font-size: 0.9em;
                    }}
                    
                    blockquote {{
                        border-left: 4px solid var(--primary-color);
                        background-color: var(--accent-color);
                        padding: 15px;
                        margin: 20px 0;
                        border-radius: 0 var(--border-radius) var(--border-radius) 0;
                    }}
                    
                    /* Table Styles */
                    table {{
                        border-collapse: collapse;
                        width: 100%;
                        margin: 20px 0;
                        border-radius: var(--border-radius);
                        overflow: hidden;
                        box-shadow: var(--shadow);
                    }}
                    
                    table, th, td {{
                        border: 1px solid var(--gray-300);
                    }}
                    
                    th, td {{
                        padding: 12px 15px;
                        text-align: left;
                    }}
                    
                    th {{
                        background-color: var(--primary-color);
                        color: var(--white);
                        font-weight: 600;
                    }}
                    
                    tr:nth-child(even) {{
                        background-color: var(--gray-100);
                    }}
                    
                    /* Image Styles */
                    img {{
                        max-width: 100%;
                        height: auto;
                        border-radius: var(--border-radius);
                        margin: 20px 0;
                        box-shadow: var(--shadow);
                    }}
                    
                    /* Link Styles */
                    a {{
                        color: var(--primary-color);
                        text-decoration: none;
                        font-weight: 500;
                        transition: color 0.2s;
                    }}
                    
                    a:hover {{
                        color: #0A2E51;
                        text-decoration: underline;
                    }}
                    
                    /* List Styles */
                    ul, ol {{
                        margin-left: 20px;
                        margin-bottom: 20px;
                    }}
                    
                    li {{
                        margin-bottom: 8px;
                    }}
                    
                    /* LinkedIn Post Styles */
                    .linkedin-post {{
                        background-color: var(--white);
                        border: 1px solid var(--gray-300);
                        border-radius: var(--border-radius);
                        padding: 20px;
                        margin: 20px 0;
                        box-shadow: var(--shadow);
                    }}
                    
                    .linkedin-post pre {{
                        background-color: var(--light-bg);
                        border: none;
                        padding: 15px;
                        border-radius: var(--border-radius);
                        white-space: pre-wrap;
                    }}
                    
                    /* Stats Card Styles */
                    .stats-container {{
                        display: flex;
                        flex-wrap: wrap;
                        gap: 20px;
                        margin: 30px 0;
                    }}
                    
                    .stat-card {{
                        flex: 1;
                        min-width: 200px;
                        background-color: var(--white);
                        border-radius: var(--border-radius);
                        padding: 20px;
                        box-shadow: var(--shadow);
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        text-align: center;
                    }}
                    
                    .stat-value {{
                        font-size: 2rem;
                        font-weight: 700;
                        color: var(--primary-color);
                        margin: 10px 0;
                    }}
                    
                    .stat-label {{
                        color: var(--gray-600);
                        font-size: 0.9rem;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                    }}
                    
                    .stat-icon {{
                        color: var(--primary-color);
                        font-size: 1.5rem;
                        margin-bottom: 10px;
                    }}
                    
                    /* Footer Styles */
                    footer {{
                        background-color: var(--primary-color);
                        color: var(--white);
                        padding: 40px 0;
                        margin-top: 60px;
                    }}
                    
                    .footer-content {{
                        display: flex;
                        justify-content: space-between;
                        flex-wrap: wrap;
                    }}
                    
                    .footer-logo {{
                        display: flex;
                        align-items: center;
                        margin-bottom: 20px;
                    }}
                    
                    .footer-logo h2 {{
                        font-family: 'Montserrat', sans-serif;
                        font-size: 1.5rem;
                        font-weight: 600;
                        color: var(--white);
                        margin: 0;
                    }}
                    
                    .footer-links {{
                        flex: 1;
                        max-width: 300px;
                    }}
                    
                    .footer-links h3 {{
                        color: var(--white);
                        font-size: 1.2rem;
                        margin-bottom: 15px;
                    }}
                    
                    .footer-links ul {{
                        list-style: none;
                        margin: 0;
                        padding: 0;
                    }}
                    
                    .footer-links li {{
                        margin-bottom: 8px;
                    }}
                    
                    .footer-links a {{
                        color: var(--gray-300);
                        transition: color 0.2s;
                    }}
                    
                    .footer-links a:hover {{
                        color: var(--white);
                    }}
                    
                    .copyright {{
                        text-align: center;
                        padding-top: 20px;
                        margin-top: 30px;
                        border-top: 1px solid rgba(255, 255, 255, 0.1);
                        color: var(--gray-400);
                        font-size: 0.9rem;
                    }}
                    
                    /* Chatbot Styles */
                    .chatbot-toggle {{
                        position: fixed;
                        bottom: 30px;
                        right: 30px;
                        background-color: var(--primary-color);
                        color: var(--white);
                        width: 60px;
                        height: 60px;
                        border-radius: 50%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        cursor: pointer;
                        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                        z-index: 999;
                        transition: all 0.3s ease;
                    }}
                    
                    .chatbot-toggle:hover {{
                        transform: scale(1.05);
                        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
                    }}
                    
                    .chatbot-toggle i {{
                        font-size: 24px;
                    }}
                    
                    .chatbot {{
                        position: fixed;
                        bottom: 30px;
                        right: 30px;
                        width: 380px;
                        height: 500px;
                        background-color: var(--white);
                        border-radius: 16px;
                        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
                        z-index: 1000;
                        overflow: hidden;
                        display: flex;
                        flex-direction: column;
                        transform: scale(0);
                        transform-origin: bottom right;
                        transition: transform 0.3s ease-out;
                        opacity: 0;
                    }}
                    
                    .chatbot.open {{
                        transform: scale(1);
                        opacity: 1;
                    }}
                    
                    .chat-header {{
                        background-color: var(--primary-color);
                        color: var(--white);
                        padding: 15px 20px;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    }}
                    
                    .chat-header h3 {{
                        margin: 0;
                        font-size: 1.1rem;
                        color: var(--white);
                    }}
                    
                    .close-chat {{
                        background: none;
                        border: none;
                        color: var(--white);
                        font-size: 1.2rem;
                        cursor: pointer;
                    }}
                    
                    .chat-messages {{
                        flex: 1;
                        padding: 20px;
                        overflow-y: auto;
                        display: flex;
                        flex-direction: column;
                        gap: 15px;
                    }}
                    
                    .message {{
                        max-width: 80%;
                        padding: 12px 16px;
                        border-radius: 18px;
                        line-height: 1.5;
                        font-size: 0.95rem;
                        position: relative;
                    }}
                    
                    .user-message {{
                        align-self: flex-end;
                        background-color: var(--primary-color);
                        color: var(--white);
                        border-bottom-right-radius: 4px;
                    }}
                    
                    .bot-message {{
                        align-self: flex-start;
                        background-color: var(--accent-color);
                        color: var(--secondary-color);
                        border-bottom-left-radius: 4px;
                    }}
                    
                    .message-content {{
                        word-break: break-word;
                    }}
                    
                    .message pre {{
                        background-color: rgba(0, 0, 0, 0.05);
                        padding: 10px;
                        border-radius: 6px;
                        overflow-x: auto;
                        margin: 10px 0;
                        font-size: 0.85rem;
                    }}
                    
                    .chat-form {{
                        display: flex;
                        padding: 15px;
                        border-top: 1px solid var(--gray-300);
                        background-color: var(--white);
                    }}
                    
                    .chat-input {{
                        flex: 1;
                        border: 1px solid var(--gray-300);
                        border-radius: 24px;
                        padding: 10px 15px;
                        outline: none;
                        font-family: inherit;
                        font-size: 0.95rem;
                    }}
                    
                    .chat-input:focus {{
                        border-color: var(--primary-color);
                    }}
                    
                    .send-button {{
                        background-color: var(--primary-color);
                        color: var(--white);
                        border: none;
                        border-radius: 50%;
                        width: 40px;
                        height: 40px;
                        margin-left: 10px;
                        cursor: pointer;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        transition: all 0.2s;
                    }}
                    
                    .send-button:hover {{
                        background-color: #0A2E51;
                    }}
                    
                    .loading-indicator {{
                        display: flex;
                        align-self: flex-start;
                        background-color: var(--accent-color);
                        padding: 12px 16px;
                        border-radius: 18px;
                        border-bottom-left-radius: 4px;
                    }}
                    
                    .dot {{
                        width: 8px;
                        height: 8px;
                        margin: 0 3px;
                        background-color: var(--gray-600);
                        border-radius: 50%;
                        display: inline-block;
                        animation: dot-pulse 1.5s infinite ease-in-out;
                    }}
                    
                    .dot:nth-child(2) {{
                        animation-delay: 0.2s;
                    }}
                    
                    .dot:nth-child(3) {{
                        animation-delay: 0.4s;
                    }}
                    
                    @keyframes dot-pulse {{
                        0%, 100% {{ transform: scale(0.8); opacity: 0.5; }}
                        50% {{ transform: scale(1.2); opacity: 1; }}
                    }}
                    
                    /* Responsive Styles */
                    @media (max-width: 768px) {{
                        .header-container {{
                            flex-direction: column;
                            align-items: flex-start;
                        }}
                        
                        .date-badge {{
                            margin-top: 10px;
                        }}
                        
                        .stats-container {{
                            flex-direction: column;
                        }}
                        
                        .stat-card {{
                            width: 100%;
                        }}
                        
                        .footer-content {{
                            flex-direction: column;
                        }}
                        
                        .footer-links {{
                            max-width: 100%;
                            margin-bottom: 20px;
                        }}
                        
                        .chatbot {{
                            width: 100%;
                            height: 100%;
                            bottom: 0;
                            right: 0;
                            border-radius: 0;
                        }}
                    }}
                    
                    /* API Key Form */
                    .api-key-form {{
                        display: flex;
                        flex-direction: column;
                        padding: 20px;
                        height: 100%;
                    }}
                    
                    .api-key-instructions {{
                        margin-bottom: 20px;
                    }}
                    
                    .api-key-instructions p {{
                        margin-bottom: 10px;
                        font-size: 0.9rem;
                        line-height: 1.5;
                    }}
                    
                    .api-key-input-container {{
                        display: flex;
                        flex-direction: column;
                        gap: 10px;
                    }}
                    
                    #api-key-input {{
                        padding: 10px 15px;
                        border: 1px solid var(--gray-300);
                        border-radius: 4px;
                        font-family: inherit;
                        font-size: 0.9rem;
                    }}
                    
                    .api-key-submit {{
                        background-color: var(--primary-color);
                        color: var(--white);
                        border: none;
                        border-radius: 4px;
                        padding: 10px 15px;
                        font-weight: 500;
                        cursor: pointer;
                        transition: background-color 0.2s;
                    }}
                    
                    .api-key-submit:hover {{
                        background-color: #0A2E51;
                    }}
                    
                    /* Chat interface */
                    .chat-interface {{
                        flex: 1;
                        display: flex;
                        flex-direction: column;
                    }}
                </style>
            </head>
            <body>
                <!-- Header -->
                <header>
                    <div class="header-container container">
                        <div class="logo">
                            {logo_html}
                            <h1>Global Possibilities</h1>
                        </div>
                        <div class="date-badge">
                            <i class="far fa-calendar-alt"></i> {current_date}
                        </div>
                    </div>
                </header>
                
                <!-- Main Content -->
                <main class="container">
                    <div class="report-title">
                        <h1>Daily Business Intelligence Report</h1>
                        <p>Key insights and analysis for regional business leaders</p>
                    </div>
                    
                    <!-- Content Wrapper -->
                    <div class="content-wrapper">
                        {html_content}
                    </div>
                </main>
                
                <!-- Footer -->
                <footer>
                    <div class="container">
                        <div class="footer-content">
                            <div class="footer-logo">
                                {logo_html}
                                <h2>Global Possibilities</h2>
                            </div>
                            <div class="footer-links">
                                <h3>Business Intelligence</h3>
                                <ul>
                                    <li><a href="#">Daily Reports</a></li>
                                    <li><a href="#">LinkedIn Content</a></li>
                                    <li><a href="#">Market Analysis</a></li>
                                </ul>
                            </div>
                            <div class="footer-links">
                                <h3>Resources</h3>
                                <ul>
                                    <li><a href="#">News Archive</a></li>
                                    <li><a href="#">Research Papers</a></li>
                                    <li><a href="#">Data Sources</a></li>
                                </ul>
                            </div>
                        </div>
                        <div class="copyright">
                            <p>&copy; {current_year} Global Possibilities. All rights reserved.</p>
                            <p>Generated by the Global Possibilities Business Intelligence Platform</p>
                        </div>
                    </div>
                </footer>
                
                <!-- Chatbot -->
                <div class="chatbot-toggle" id="chatbot-toggle">
                    <i class="fas fa-comments"></i>
                </div>
                
                <div class="chatbot" id="chatbot">
                    <div class="chat-header">
                        <h3>GCC Business Intelligence Assistant</h3>
                        <button class="close-chat" id="close-chat">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    
                    <!-- API Key Form -->
                    <form class="api-key-form" id="api-key-form">
                        <div class="api-key-instructions">
                            <p><strong>OpenAI API Key Required</strong></p>
                            <p>To use the chatbot, please enter your OpenAI API key. Your key will be stored locally in your browser and is only used to send requests to OpenAI.</p>
                            <p><small>Your key is stored only on your device and never sent to our servers.</small></p>
                        </div>
                        <div class="api-key-input-container">
                            <input type="password" id="api-key-input" placeholder="sk-..." autocomplete="off">
                            <button type="submit" class="api-key-submit">Start Chat</button>
                        </div>
                    </form>
                    
                    <!-- Chat Interface -->
                    <div class="chat-interface" id="chat-interface" style="display: none; flex-direction: column; height: 100%;">
                        <div class="chat-messages" id="chat-messages">
                            <!-- Messages will be added here -->
                        </div>
                        <form class="chat-form" id="chat-form">
                            <input type="text" class="chat-input" id="user-input" placeholder="Ask about the report or GCC business trends..." autocomplete="off">
                            <button type="submit" class="send-button">
                                <i class="fas fa-paper-plane"></i>
                            </button>
                        </form>
                    </div>
                </div>
                
                <!-- Optional JavaScript -->
                {js_script}
            </body>
            </html>
            """
            
            # Save the HTML file
            html_path = markdown_path.replace('.md', '.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(styled_html)
            
            # Copy any images from reports directory to maintain references
            img_dir = os.path.join(os.path.dirname(html_path), 'images')
            os.makedirs(img_dir, exist_ok=True)
            
            # Check for keyword chart and copy it
            chart_path = os.path.join(self.reports_dir, 'keyword_analysis.png')
            if os.path.exists(chart_path):
                shutil.copy(chart_path, os.path.join(img_dir, 'keyword_analysis.png'))
            
            # Create readme for the chatbot
            chatbot_readme_path = os.path.join(self.reports_dir, 'CHATBOT_README.md')
            with open(chatbot_readme_path, 'w', encoding='utf-8') as f:
                f.write("""# Chatbot Feature in HTML Reports

The HTML reports now include an integrated chatbot that allows users to ask questions about the report content and get insights about GCC/UAE business trends.

## How It Works

1. Click the chat icon in the bottom right corner of the report page.
2. You'll be prompted to enter an OpenAI API key (this is required to use the chatbot feature).
3. Once you've entered your API key, you can ask questions about the report or general questions about UAE/GCC business topics.

## Privacy & Security

- Your OpenAI API key is stored only in your browser's local storage and is never sent to our servers.
- The API key is used to make direct requests from your browser to OpenAI's API.
- The report content is sent to OpenAI as context for the chatbot to provide relevant answers.

## Sample Questions

Try asking the chatbot questions like:
- "Summarize the main points of this report."
- "What are the key business trends in the UAE mentioned in this report?"
- "Explain the latest developments in US-UAE relations."
- "What investment opportunities are highlighted in this report?"
- "Tell me about recent regulatory changes in the GCC region."

## Troubleshooting

If you encounter any issues:
1. Make sure your OpenAI API key is valid and has sufficient credits.
2. Check your internet connection.
3. Try refreshing the page and entering your API key again.
""")
            
            return html_path
            
        except Exception as e:
            logger.error(f"Error creating HTML version: {e}")
            return None
    
    def _create_pdf_only_report(self, report_text, timestamp):
        """Create a PDF-specific report with only the business intelligence content (no LinkedIn posts)."""
        try:
            current_date = datetime.now().strftime("%B %d, %Y")
            
            # Format current date for display
            current_year = datetime.now().year
            
            # Check if the logo exists
            logo_file = os.path.join('reports', 'assets', 'images', 'logo.svg')
            logo_html = ""
            if os.path.exists(logo_file):
                with open(logo_file, 'r') as f:
                    logo_svg = f.read()
                logo_html = logo_svg
            else:
                # Fallback to Font Awesome icon
                logo_html = '<i class="fas fa-globe-americas logo-icon"></i>'
            
            # Convert the markdown report to HTML
            html_content = markdown.markdown(report_text, extensions=['tables', 'fenced_code', 'nl2br'])
            
            # Create the PDF-specific HTML (without LinkedIn content)
            styled_html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Global Possibilities | Daily Business Intelligence Report</title>
                <!-- Google Fonts - Montserrat and Open Sans -->
                <link rel="preconnect" href="https://fonts.googleapis.com">
                <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
                <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&family=Open+Sans:wght@400;500;600&display=swap" rel="stylesheet">
                
                <style>
                    :root {{
                        --primary-color: #0D3E6D;
                        --secondary-color: #2E2E2E;
                        --accent-color: #E1ECF9;
                        --light-bg: #F9FAFC;
                        --white: #ffffff;
                        --gray-100: #f8f9fa;
                        --gray-200: #e9ecef;
                        --gray-300: #dee2e6;
                        --gray-400: #ced4da;
                        --gray-500: #adb5bd;
                        --gray-600: #6c757d;
                        --gray-700: #495057;
                        --shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
                        --border-radius: 8px;
                    }}
                    
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    
                    body {{
                        font-family: 'Open Sans', sans-serif;
                        line-height: 1.7;
                        background-color: var(--white);
                        color: var(--secondary-color);
                    }}
                    
                    .container {{
                        width: 100%;
                        max-width: 1140px;
                        margin: 0 auto;
                        padding: 0 20px;
                    }}
                    
                    /* Header Styles */
                    header {{
                        padding: 20px 0;
                        border-bottom: 1px solid var(--gray-300);
                    }}
                    
                    .header-container {{
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    }}
                    
                    .logo {{
                        display: flex;
                        align-items: center;
                    }}
                    
                    .logo h1 {{
                        font-family: 'Montserrat', sans-serif;
                        font-size: 1.5rem;
                        font-weight: 600;
                        color: var(--primary-color);
                        margin: 0;
                        border: none;
                        padding: 0;
                    }}
                    
                    .logo svg {{
                        height: 40px;
                        width: auto;
                        margin-right: 15px;
                    }}
                    
                    .date-badge {{
                        font-size: 1rem;
                        font-weight: 500;
                        color: var(--primary-color);
                    }}
                    
                    /* Main Content Styles */
                    main {{
                        padding: 40px 0;
                    }}
                    
                    .report-title {{
                        margin-bottom: 40px;
                    }}
                    
                    .report-title h1 {{
                        font-family: 'Montserrat', sans-serif;
                        font-size: 2rem;
                        font-weight: 700;
                        color: var(--primary-color);
                        margin-bottom: 10px;
                        border: none;
                    }}
                    
                    .report-title p {{
                        color: var(--gray-600);
                        font-size: 1.1rem;
                    }}
                    
                    /* Typography Styles */
                    h1, h2, h3, h4, h5, h6 {{
                        font-family: 'Montserrat', sans-serif;
                        color: var(--primary-color);
                        margin-top: 1.5em;
                        margin-bottom: 0.8em;
                        font-weight: 600;
                    }}
                    
                    h1 {{
                        font-size: 2rem;
                        border-bottom: 2px solid var(--accent-color);
                        padding-bottom: 10px;
                        margin-bottom: 20px;
                    }}
                    
                    h2 {{
                        font-size: 1.75rem;
                    }}
                    
                    h3 {{
                        font-size: 1.5rem;
                    }}
                    
                    p {{
                        margin-bottom: 1rem;
                    }}
                    
                    ul, ol {{
                        margin-left: 20px;
                        margin-bottom: 20px;
                    }}
                    
                    li {{
                        margin-bottom: 8px;
                    }}
                    
                    /* Key Takeaway Styles */
                    strong {{
                        color: var(--primary-color);
                    }}
                    
                    /* Footer Styles */
                    footer {{
                        padding: 20px 0;
                        border-top: 1px solid var(--gray-300);
                        margin-top: 40px;
                    }}
                    
                    .copyright {{
                        text-align: center;
                        color: var(--gray-600);
                        font-size: 0.9rem;
                    }}
                </style>
            </head>
            <body>
                <!-- Header -->
                <header>
                    <div class="header-container container">
                        <div class="logo">
                            {logo_html}
                            <h1>Global Possibilities</h1>
                        </div>
                        <div class="date-badge">
                            {current_date}
                        </div>
                    </div>
                </header>
                
                <!-- Main Content -->
                <main class="container">
                    <div class="report-title">
                        <h1>Daily Business Intelligence Report</h1>
                        <p>Key insights and analysis for regional business leaders</p>
                    </div>
                    
                    <!-- Content Wrapper -->
                    <div class="content-wrapper">
                        {html_content}
                    </div>
                </main>
                
                <!-- Footer -->
                <footer>
                    <div class="container">
                        <div class="copyright">
                            <p>&copy; {current_year} Global Possibilities. All rights reserved.</p>
                        </div>
                    </div>
                </footer>
            </body>
            </html>
            """
            
            # Save the PDF-specific HTML to a temporary file
            temp_html_path = os.path.join(self.reports_dir, f"temp_pdf_report_{timestamp}.html")
            with open(temp_html_path, 'w', encoding='utf-8') as f:
                f.write(styled_html)
            
            # Generate PDF from the temporary HTML
            pdf_path = os.path.join(self.reports_dir, f"consolidated_report_{timestamp}.pdf")
            html = weasyprint.HTML(filename=temp_html_path)
            pdf = html.write_pdf()
            
            # Save the PDF
            with open(pdf_path, 'wb') as f:
                f.write(pdf)
            
            # Remove the temporary HTML file
            try:
                os.remove(temp_html_path)
            except Exception as e:
                logger.warning(f"Could not remove temporary HTML file: {e}")
            
            return pdf_path
            
        except Exception as e:
            logger.error(f"Error creating PDF-only report: {e}")
            return None
    
    def _create_pdf_version(self, report_text, timestamp):
        """Create a PDF version with only the business intelligence report (no LinkedIn posts)."""
        try:
            # Generate a PDF-only report
            pdf_path = self._create_pdf_only_report(report_text, timestamp)
            
            if pdf_path:
                logger.info(f"PDF version (report only) saved to {pdf_path}")
                return pdf_path
            else:
                logger.error("Failed to create PDF-only report")
                return None
        
        except Exception as e:
            logger.error(f"Error creating PDF version: {e}")
            return None


if __name__ == "__main__":
    # Test the consolidated report generator
    generator = ConsolidatedReportGenerator()
    md_path, html_path, pdf_path = generator.generate_all()
    
    if md_path:
        print(f"Consolidated report generated at {md_path}")
        if html_path:
            print(f"HTML version available at {html_path}")
        if pdf_path:
            print(f"PDF version available at {pdf_path}")
    else:
        print("Failed to generate consolidated report.") 