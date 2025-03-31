# GCC Market Intelligence Report Generator

This module provides functionality to generate comprehensive market intelligence reports focused on the Gulf Cooperation Council (GCC) region for clients in the Market Intelligence Platform.

## Overview

The GCC Report Generator creates detailed market reports by:

1. Collecting and analyzing news articles, government announcements, and other sources of market intelligence
2. Focusing specifically on the Gulf region (UAE, Saudi Arabia, Qatar, Kuwait, Bahrain, and Oman)
3. Prioritizing GCC-specific content in the reports
4. Generating professional PDF and Markdown outputs with custom branding

## Features

- **GCC-focused web crawling**: Prioritizes sources from the Gulf region
- **Region tagging**: Automatically identifies and prioritizes content mentioning GCC countries
- **Customized reports**: Tailored to each client's specific interests in the region
- **Multiple output formats**: Supports both Markdown and professionally styled PDF outputs
- **AI-powered analysis**: Leverages GPT models to extract insights and generate recommendations
- **Interactive dashboard**: Web interface for managing clients, reports, and content
- **Automated scheduling**: Support for cron jobs and scheduled report generation

## Client Tagging & Interest Mapping

The system uses sophisticated client tagging to personalize intelligence gathering:

- **Interest Categorization**: Each client has stored interests organized by:
  - Industry sectors (e.g., Technology, Consumer Goods, Finance)
  - Geographic regions (e.g., UAE, Saudi Arabia, Qatar)
  - Topic categories (e.g., Regulations, Market Trends, Competitors)
  - Custom keyword groups (e.g., "Sustainability", "Digital Transformation")

- **Tag Implementation**:
  - Dashboard: Add/edit tags through the client management interface
  - CLI: Manage tags via command line:
    ```bash
    python manage_client.py --client nestle --add-tag "GCC food regulations"
    python manage_client.py --client google --list-tags
    ```

- **Automated Intelligence Filtering**:
  - Article selection prioritizes content matching client tags
  - Report sections are weighted based on tag relevance
  - AI recommendations target areas of highest interest density

Example tag structure for Google:
```json
{
  "industries": ["Technology", "Cloud Services", "Digital Advertising"],
  "regions": ["UAE", "Saudi Arabia", "Qatar"],
  "topics": ["Regulatory Changes", "Market Expansion", "Competitors"],
  "custom_keywords": ["AI initiatives", "Data centers", "Smart city"]
}
```

## Dashboard-Integrated AI Chatbot

The AI chatbot is **fully operational** and provides an interactive interface for querying market intelligence data:

- **Knowledge Base**:
  - Utilizes Redis-stored content (articles, report summaries, client profiles)
  - Indexes all generated reports and source materials
  - Updates automatically with each report generation cycle

- **Capabilities**:
  - Question answering with source citation
  - Trend analysis with temporal context
  - Client-specific insights based on historical data
  - Comparative analysis across regions or companies

- **Example Prompts**:
  ```
  "What were the top 3 infrastructure projects in UAE this quarter?"
  "Summarize Nestlé's market positioning in the GCC food sector."
  "Compare Google's cloud presence in Saudi Arabia vs. UAE."
  "What regulatory changes in Qatar might affect the tech industry?"
  "Generate key points for a presentation on GCC sustainability trends."
  ```

- **Access Methods**:
  - Web dashboard: `/clients/<client_id>/chat`
  - API endpoint: `/api/chat` (for integration with other systems)

## LinkedIn Post Generator with AI-Generated Visuals

The platform includes an advanced LinkedIn content creation system with automated image generation:

- **Content Flow**:
  1. Select source material (report, article, or insight)
  2. AI generates optimized LinkedIn caption
  3. AI creates a relevant visual to accompany the post
  4. Preview, edit, and finalize before export

- **AI Image Generation**:
  - **No uploads required** - images are generated on-demand
  - Image types include:
    - Data visualizations (charts, graphs)
    - Professional stock-style imagery
    - Branded infographic elements
    - GCC-themed visual elements

- **Dashboard Controls**:
  - Live preview of caption and generated image
  - Regeneration options for alternative visuals
  - Style controls (corporate, casual, informative)
  - One-click copy to clipboard
  - Image download options (.png, .jpg)

- **Usage**:
  ```bash
  # CLI option for headless generation
  python generate_linkedin.py --from-report reports/google/latest.md --with-image
  ```

- **Technical Implementation**:
  - Leverages OpenAI's image generation models
  - Customized prompting for business and regional relevance
  - Image caching for efficient regeneration

## External File Upload + Parsing

The system supports ingestion and analysis of external documents:

- **Supported Formats**:
  - Structured data: CSV, JSON, Excel (.xlsx)
  - Documents: PDF, DOCX, TXT
  - Media: Transcripts from audio/video files
  - Presentations: PowerPoint (.pptx)

- **Processing Pipeline**:
  1. **Upload**: Via dashboard or CLI
  2. **Parsing**: Document content extraction with format-specific handlers
  3. **Categorization**: Automatic tagging using content analysis
  4. **Storage**: Indexed and cached in Redis with client association
  5. **Integration**: Automatically incorporated into relevant reports

- **CLI Integration**:
  ```bash
  # Add external data files via command line
  python ingest_file.py --client google --file ~/documents/google_gcc_strategy.docx
  
  # Batch processing
  python ingest_directory.py --client nestle --dir ~/research/food_market/ --recursive
  ```

- **Access Control**:
  - Client-specific file association
  - Configurable retention policies
  - Role-based access permissions

## Report Output Format + Branding

Reports are professionally formatted and branded:

- **Style Customization**:
  - Client logo integration (header and footer)
  - Custom color schemes matching client branding
  - Font selection for corporate identity alignment
  - Customizable cover page templates

- **Document Structure**:
  - **Cover Page**: Client logo, report title, date range, and generation timestamp
  - **Executive Summary**: Concise overview with key highlights
  - **Regional Focus Sections**: Country-specific insights
  - **Industry Analysis**: Sector-specific trends relevant to client
  - **Article Breakdown**: Curated content with source attribution
  - **Strategic Recommendations**: Actionable insights with priority ranking
  - **Source Index**: Complete list of sources with URLs and credibility rating

- **Configuration**:
  - Stored in `config/branding/` directory
  - Example client configuration:
    ```json
    {
      "client_name": "Google",
      "primary_color": "#4285F4",
      "secondary_colors": ["#EA4335", "#FBBC05", "#34A853"],
      "logo_path": "assets/clients/google_logo.png",
      "font_heading": "Product Sans",
      "font_body": "Roboto"
    }
    ```

- **Preview Mode**:
  Generate report previews without crawling:
  ```bash
  python preview_report.py --client google --template standard
  ```

## Automated + Manual Report Scheduling

The system offers flexible scheduling options:

- **Cron Job Support**:
  ```
  # Daily summary reports (light crawling)
  0 7 * * * cd /path/to/project && python generate_all_gcc_reports.py --summary-only >> logs/daily_summary.log 2>&1
  
  # Weekly comprehensive reports (Sundays)
  0 5 * * 0 cd /path/to/project && python generate_all_gcc_reports.py --comprehensive >> logs/weekly_reports.log 2>&1
  
  # Monthly trend analysis (1st of month)
  0 6 1 * * cd /path/to/project && python generate_all_gcc_reports.py --with-trends --lookback 30 >> logs/monthly_trends.log 2>&1
  ```

- **Manual Generation Options**:
  - Dashboard triggers for on-demand reports
  - Client-specific or all-client generation
  - Configurable depth and scope:
    ```bash
    # Quick report using cached data
    python generate_client_reports.py --client google --skip-crawling --pdf-only
    
    # Comprehensive report with fresh data
    python generate_client_reports.py --client nestle --deep-crawl --both-formats
    
    # Generate reports for a specific time period
    python generate_client_reports.py --all-clients --date-range "2023-05-01,2023-05-31"
    ```

- **Notification System**:
  - Email alerts when reports are complete
  - Dashboard notifications
  - Configurable webhook integration

## TensorFlow + Future AI Readiness

The architecture is designed for advanced AI integration:

- **Current Framework Hooks**:
  - Preprocessing pipeline for structured data extraction
  - Feature extraction interfaces for model integration
  - Scoring mechanisms for content relevance
  - Model serving infrastructure

- **Planned AI Capabilities**:
  - **Predictive Market Modeling**: Forecast trends based on historical patterns
  - **Sentiment Analysis**: Regional sentiment tracking for brands and products
  - **Opportunity Scoring**: Automated identification of market opportunities
  - **Competitive Intelligence**: Comparative position tracking over time
  - **Anomaly Detection**: Early warning system for market disruptions

- **Model Integration Points**:
  The codebase includes placeholders in:
  - `src/ai/models.py`: Interface definitions for TensorFlow models
  - `src/ai/pipelines.py`: Data preparation frameworks
  - `src/ai/serving.py`: Model serving infrastructure

- **Example Custom Model Integration**:
  ```python
  # Example integration for custom sentiment analysis
  from src.ai.models import register_model
  
  @register_model('gcc_sentiment')
  class GCCSentimentAnalyzer:
      def __init__(self, model_path):
          self.model = tf.keras.models.load_model(model_path)
          
      def analyze(self, text):
          # Model-specific processing
          return {'score': 0.75, 'confidence': 0.92}
  ```

## Historical Report Access + Downloads

The system maintains a complete archive of all generated reports:

- **Storage Structure**:
  ```
  /reports/
    ├── google/
    │   ├── 2023-06-01/
    │   │   ├── google_gcc_report.md
    │   │   ├── google_gcc_report.pdf
    │   │   └── metadata.json
    │   ├── 2023-05-25/
    │   ├── 2023-05-18/
    │   └── ...
    ├── nestle/
    │   ├── 2023-06-02/
    │   └── ...
    └── ...
  ```

- **Dashboard Access**:
  - Historical report browser with filtering options
  - Comparison view for tracking changes over time
  - Batch download functionality

- **CLI Tools**:
  ```bash
  # List available reports
  python list_reports.py --client google
  
  # Fetch specific reports
  python fetch_reports.py --client nestle --last 3 --format pdf
  
  # Export report archive
  python export_reports.py --client google --since "2023-01-01" --output ~/exports/google_reports/
  
  # Generate comparison between reports
  python compare_reports.py --client google --reports "2023-05-01,2023-06-01" --output diff.html
  ```

- **Metadata Storage**:
  Each report includes a `metadata.json` file with:
  - Generation parameters
  - Source count and types
  - Processing statistics
  - Version information

## Content Filtering & Search

The platform includes powerful content discovery tools:

- **Global Search**:
  - Full-text search across all reports and articles
  - Semantic search using embedding models
  - Filter-based refinement

- **Advanced Filtering Options**:
  - **Regional**: Country-specific content (UAE, KSA, Qatar, etc.)
  - **Temporal**: Date ranges, relative time periods
  - **Topical**: Industry, sector, or subject categories
  - **Client-specific**: Tailored to individual client interests
  - **Source quality**: Filter by source credibility rating

- **Dashboard Implementation**:
  - Faceted search interface
  - Saved search configurations
  - Search result export

- **CLI Access**:
  ```bash
  # Search across all content
  python search_content.py --query "renewable energy initiatives UAE" --filter "date:last-30-days"
  
  # Client-specific search
  python search_content.py --client google --query "cloud infrastructure regulations" --output results.json
  ```

- **Search API**:
  - RESTful endpoint for programmatic access
  - Query parameters for all filtering options
  - JSON response format with pagination

## Error Logs + System Health

Comprehensive system monitoring and diagnostics:

- **Log Structure**:
  ```
  /logs/
    ├── crawler/
    │   ├── crawler_20230601.log
    │   ├── error_20230601.log
    │   └── ...
    ├── reports/
    │   ├── generation_20230601.log
    │   ├── error_20230601.log
    │   └── ...
    ├── api/
    │   ├── api_20230601.log
    │   ├── error_20230601.log
    │   └── ...
    ├── cron.log
    └── system_health.log
  ```

- **Logging Levels**:
  - DEBUG: Detailed debugging information
  - INFO: Confirmation of expected functionality
  - WARNING: Indication of potential issues
  - ERROR: Runtime errors that don't halt execution
  - CRITICAL: Critical errors requiring immediate attention

- **System Health**:
  - Connection validation for all external services
  - Resource utilization monitoring
  - Automatic retry mechanisms for transient failures
  - Alert thresholds for performance degradation

- **Diagnostics Tools**:
  ```bash
  # Validate system connections
  python validate_connections.py
  
  # Check system health
  python system_health.py --comprehensive
  
  # Test crawling for a specific source
  python test_crawler.py --source "gulfnews.com" --verbose
  
  # Analyze log patterns
  python analyze_logs.py --error-summary --last-days 7
  ```

- **Health Dashboard**:
  - Visual status indicators for all system components
  - Error rate monitoring
  - Performance metrics
  - Resource utilization graphs

## Usage

### Through the Web Dashboard

1. Navigate to the client detail page
2. Click the "GCC Report" button
3. Configure report options (format, crawling settings)
4. Click "Generate GCC Report"
5. Download the resulting PDF and/or Markdown files

### Using the Command Line

Generate a report for a specific client:

```bash
# Make sure the script is executable
chmod +x run_gcc_reports.sh

# Run for a specific client
./run_gcc_reports.sh --google
./run_gcc_reports.sh --nestle

# Output format options
./run_gcc_reports.sh --pdf-only
./run_gcc_reports.sh --md-only

# Skip crawling (use cached data)
./run_gcc_reports.sh --simulate
```

Generate reports for all clients:

```bash
# Generate reports for all clients
python generate_all_gcc_reports.py

# Specify output directory
python generate_all_gcc_reports.py --output-dir ./reports/custom_directory

# Skip crawling
python generate_all_gcc_reports.py --skip-crawling
```

### Automating with Cron

To set up automated weekly report generation, add the following to your crontab:

```
# Run GCC report generation every Monday at 7:00 AM
0 7 * * 1 cd /path/to/project && python generate_all_gcc_reports.py >> logs/cron.log 2>&1
```

## Report Structure

Each generated report includes:

1. **Executive Summary**: High-level overview focused on GCC impact
2. **Key Market Trends**: Bullet points specific to the Gulf region
3. **Industry Insights**: Analysis of developments in the client's industry within the GCC
4. **Article Headlines by GCC Country/Region**: Summary of key news stories
5. **Strategic Recommendations**: Actionable insights for operations in the GCC region

## Integration

The GCC Report Generator is fully integrated with:

- The web dashboard for easy report generation
- The Redis caching system for efficient data storage and retrieval
- The LinkedIn post generator for easy sharing of insights
- The document upload system for including additional data sources

## Troubleshooting

If you encounter issues:

1. Check Redis connectivity using `python validate_connections.py`
2. Ensure proper credentials in the `.env` file
3. Check log files in the `logs` directory
4. Try running with `--skip-crawling` to isolate crawling issues 