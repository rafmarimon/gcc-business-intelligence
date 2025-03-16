# Global Possibilities - UAE/GCC Business Intelligence Platform

A comprehensive platform for collecting, analyzing, and generating actionable insights from business news in the UAE and GCC region.

## Overview

This platform automates the following workflow:

1. **News Collection**: Scrapes business news from major UAE/GCC news sources
2. **Analysis**: Analyzes collected news using NLP and LLMs to identify trends, opportunities, and key insights
3. **Report Generation**: Creates detailed weekly reports with visualizations and actionable intelligence
4. **LinkedIn Content**: Automatically generates professional LinkedIn posts based on the most significant insights
5. **Interactive Reports**: Provides HTML reports with the company logo and an interactive chatbot assistant

The entire process can be triggered with a single command, producing both detailed business intelligence reports and ready-to-post LinkedIn content.

## Features

- **Automated News Collection**: Scrapes business articles from multiple configurable sources
- **Intelligent Analysis**: Uses NLP and OpenAI's GPT models to identify trends, opportunities, and insights
- **Keyword Analysis**: Tracks frequency and correlation of business-relevant keywords
- **Visualization**: Generates charts and graphs to visualize data trends
- **Report Generation**: Creates comprehensive markdown and HTML reports
- **LinkedIn Content Generation**: Automatically creates professional social media posts
- **Consolidated Output**: Combines all insights and content into a single, well-formatted report
- **Interactive Chatbot**: AI-powered assistant that can answer questions about the report and GCC business trends
- **Professional Design**: Modern, responsive HTML design with Global Possibilities branding

## Project Structure

```
.
├── config/                   # Configuration files
│   ├── news_sources.json     # News source definitions and selectors
│   └── keywords.json         # Keywords for trend analysis
├── content/                  # Generated LinkedIn posts
├── data/                     # Collected news data (JSON/CSV)
├── reports/                  # Generated reports
│   └── assets/               # Report assets (images, logo)
├── logs/                     # Log files
├── src/                      # Source code
│   ├── collectors/           # Data collection modules
│   │   └── news_collector.py # News web scraping module
│   ├── processors/           # Data processing modules
│   │   └── news_analyzer.py  # News analysis and report generation
│   ├── generators/           # Content generation modules
│   │   ├── linkedin_content.py     # LinkedIn post generator
│   │   └── consolidated_report.py   # Combined report generator
│   ├── utils/                # Utility modules
│   │   └── openai_utils.py   # OpenAI API wrapper with rate limiting
│   ├── api_server.py         # API server for chatbot functionality
│   └── manual_run.py         # Script to run the complete process
├── .env                      # Environment variables (API keys, etc.)
├── requirements.txt          # Python dependencies
├── setup.py                  # Installation and setup script
└── README.md                 # This file
```

## Installation

### Prerequisites

- Python 3.8 or higher
- An OpenAI API key (for report generation and LinkedIn posts)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/gcc-business-intelligence.git
   cd gcc-business-intelligence
   ```

2. Run the setup script:
   ```bash
   python setup.py
   ```

   This will:
   - Create necessary directories
   - Set up a virtual environment
   - Install required dependencies
   - Create template configuration files

3. Edit the `.env` file to add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

4. Install additional packages for the chatbot feature:
   ```bash
   pip install flask flask-cors
   ```

## Usage

### Run the Complete Process

To run the entire workflow (collection, analysis, and content generation):

```bash
# Activate the virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the complete process
python src/manual_run.py
```

### Run Specific Steps

You can run specific parts of the process using command-line flags:

```bash
# Skip collection (use existing data)
python src/manual_run.py --skip-collection

# Skip report generation
python src/manual_run.py --skip-report

# Generate report but don't open browser automatically
python src/manual_run.py --no-browser
```

### Using the Interactive Chatbot

The HTML reports include an interactive chatbot that can answer questions about the report content and GCC business trends. To use this feature:

1. Start the API server:
   ```bash
   source venv/bin/activate
   python src/api_server.py
   ```

2. Open the HTML report in your browser.

3. Click the chat icon in the bottom-right corner to open the chatbot interface.

4. Ask questions about the report content or GCC business trends.

### View the Results

- **Reports**: Check the `reports/` directory for generated reports (both Markdown and HTML)
- **LinkedIn Content**: Find generated posts in the `content/` directory
- **Collected Data**: Raw collected news data is stored in the `data/` directory

## Customization

### Adding News Sources

Edit the `config/news_sources.json` file to add or modify news sources:

```json
{
  "source_id": {
    "name": "News Source Name",
    "url": "https://example.com/business",
    "language": "en",
    "country": "UAE",
    "selectors": {
      "article": "CSS selector for article containers",
      "headline": "CSS selector for headlines",
      "summary": "CSS selector for article summaries",
      "link": "CSS selector for article links",
      "date": "CSS selector for publication dates"
    },
    "base_url": "https://example.com"
  }
}
```

### Modifying Analysis Keywords

Edit the `config/keywords.json` file to customize keywords used for trend analysis:

```json
{
  "category_name": [
    "keyword1",
    "keyword2",
    "..."
  ]
}
```

### Customizing Report Templates

The HTML report template can be customized by modifying the `_create_html_version` method in the `src/generators/consolidated_report.py` file. This includes:

- Styling and theming
- Layout and structure
- Chatbot functionality
- Logo and branding elements

## Technologies Used

- **Web Scraping**: BeautifulSoup, Requests
- **Data Processing**: Pandas, NLTK
- **Visualization**: Matplotlib, Seaborn
- **Report Generation**: Markdown, HTML, CSS
- **AI/LLM**: OpenAI GPT-3.5/4
- **Environment Management**: python-dotenv
- **API Server**: Flask, Flask-CORS
- **Frontend**: HTML, CSS, JavaScript

## License

Copyright © Global Possibilities. All rights reserved.

## Acknowledgments

This project was developed to provide actionable business intelligence and content generation for professionals focused on the UAE and GCC markets. 