# Market Intelligence Platform

A comprehensive platform for monitoring, analyzing, and generating insights from external data sources to inform business decisions.

## Features

- **Automated Data Collection**: Crawl and extract content from various web sources.
- **Client-Specific Monitoring**: Track topics relevant to specific clients or business areas.
- **LLM-Powered Summaries**: Automatically generate concise article summaries using OpenAI's language models.
- **Intelligent Report Generation**: Create daily, weekly, and monthly reports tailored to each client's interests.
- **LinkedIn Content Creation**: Generate engaging LinkedIn posts based on the collected data.
- **Web Dashboard**: Access all features through a modern web interface.

## LLM-Powered Article Summarization

The platform leverages OpenAI's GPT models to automatically generate summaries of crawled articles. This feature enables:

- **Real-time Summarization**: Articles are summarized immediately upon crawling.
- **Batch Processing**: Run scheduled jobs to summarize backlogged articles.
- **Quality Control**: Regenerate or manually edit summaries as needed.
- **API Access**: Integrate summaries into other workflows via the API.

### How It Works

1. When an article is crawled, the platform extracts its content.
2. The content is sent to OpenAI's API with a prompt specifically designed for summarization.
3. The generated summary is stored with the article and indexed for quick retrieval.
4. Summaries are used in reports, LinkedIn posts, and displayed in the dashboard.

## Setup and Installation

### Prerequisites

- Python 3.9 or higher
- Redis for data storage
- OpenAI API key

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/market-intelligence-platform.git
   cd market-intelligence-platform
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Copy the example environment file and edit it:
   ```
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

5. Initialize the system:
   ```
   python -m src.main setup
   ```

## Usage

### Command Line Interface

The platform provides a command-line interface for various operations:

```
# Start the web server
python -m src.main web

# Crawl all sources
python -m src.main crawl --all

# Auto-summarize articles
python -m src.main summarize --limit 20

# Generate a report
python -m src.main report --client-id CLIENT_ID --type daily

# Generate LinkedIn content
python -m src.main linkedin --client-id CLIENT_ID
```

### Web Dashboard

Access the web dashboard at http://localhost:5000 after starting the web server.

## Configuration

### Auto-Summarization Settings

Configure the summarization behavior in `.env`:

```
# OpenAI API Settings
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-3.5-turbo  # or gpt-4 for higher quality

# Summarization Settings
MAX_SUMMARY_LENGTH=300
SUMMARIZE_ON_CRAWL=true
```

### Scheduling Tasks

Set up cron jobs for regular execution:

```
# Set up all cron jobs (summarization, reports, crawling)
python -m src.utils.setup_cron --task all --interval hourly
```

## API Reference

The platform provides a RESTful API for integration with other systems:

```
# Get a list of articles
GET /api/articles

# Get a specific article
GET /api/articles/{article_id}

# Generate a summary for an article
POST /api/articles/{article_id}/summarize

# Generate summaries in batch
POST /api/articles/summarize-batch
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 