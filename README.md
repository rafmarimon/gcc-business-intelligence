# GP Business Intelligence Platform

A comprehensive business intelligence platform focused on GCC markets, automating the collection, analysis, and reporting of business news and trends.

## Features

- **Automated News Collection**: Collect news from multiple sources across the GCC region
- **Intelligent Analysis**: Process news articles using ML to identify key trends, topics, and sentiment
- **Client-Specific Reports**: Generate customized reports for different clients (Google, Nestle, etc.)
- **Multiple Report Frequencies**: Support for daily, weekly, monthly, and quarterly report generation
- **Interactive Reports**: HTML reports with interactive elements and embedded chatbot functionality
- **LinkedIn Content Generation**: Automatically create LinkedIn posts based on report insights
- **Web Interface**: Easy-to-use interface for generating and viewing reports

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Required Python packages (listed in requirements.txt)
- Environment variables for API keys (optional)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/gp-business-intelligence.git
   cd gp-business-intelligence
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Set up configuration files:
   - News sources configuration in `config/news_sources.json`
   - LinkedIn configuration in `config/linkedin_config.json`
   - Client configurations in `config/clients/`

4. Set up environment variables (optional):
   ```
   NEWS_API_KEY=your_news_api_key
   OPENAI_API_KEY=your_openai_api_key
   ```

### Running the Platform

#### Using the Web Interface

1. Start the API server:
   ```
   python src/api_server.py
   ```

2. Open your browser and navigate to `http://localhost:5000`

#### Using the Command Line

Generate a report using the command line:

```
python src/manual_run.py --client general --frequency daily
```

Command line options:
- `--client`: Client to generate a report for (general, google, nestle)
- `--frequency`: Report frequency (daily, weekly, monthly, quarterly)
- `--skip-collection`: Skip news collection and use existing data
- `--no-browser`: Don't open the report in a browser automatically
- `--open-latest`: Open the latest report without generating a new one

## Client-Specific Reports

The platform supports generating custom reports for different clients with specific focus areas:

### General (Global Possibilities Team)

Internal reports with full analysis and LinkedIn content generation.

```
python src/manual_run.py --client general --frequency daily
```

### Google

Reports focused on tech and digital transformation in the GCC region.

```
python src/manual_run.py --client google --frequency weekly
```

### Nestle

Reports focused on consumer goods and sustainability in the GCC region.

```
python src/manual_run.py --client nestle --frequency monthly
```

## Adding New Clients

To add a new client:

1. Create a new configuration file in `config/clients/` with the client name (e.g., `clientname.json`)
2. Define the client parameters including name, description, keywords, and report types
3. Run reports for the new client using the `--client clientname` parameter

## Report Structure

The generated reports include:

- Executive summary
- Key trends and insights
- Major news highlights
- Sentiment analysis
- Keyword analysis
- Sector-specific information
- Visualizations and charts
- Client-specific focus areas
- LinkedIn content suggestions (for internal reports)

## Directory Structure

```
gp-business-intelligence/
├── config/                  # Configuration files
│   ├── clients/             # Client-specific configurations
│   ├── linkedin_config.json # LinkedIn content generation settings
│   └── news_sources.json    # News sources configuration
├── data/                    # Collected data storage
├── reports/                 # Generated reports
│   ├── general/             # Reports for internal team
│   ├── google/              # Reports for Google
│   └── nestle/              # Reports for Nestle
├── src/                     # Source code
│   ├── api_server.py        # API server for web interface
│   ├── collectors/          # News collection modules
│   ├── generators/          # Report generation modules
│   ├── manual_run.py        # Command-line interface
│   ├── processors/          # News processing and analysis
│   ├── static/              # Static web files
│   └── templates/           # HTML templates
└── README.md                # This file
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built by the Global Possibilities Team
- Uses OpenAI for advanced text generation
- Integrated with various news APIs and sources 