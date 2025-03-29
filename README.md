# Market Intelligence Platform

A comprehensive platform for gathering market intelligence, generating client-specific reports, and creating LinkedIn content.

## Features

- **Web Dashboard**: Intuitive web interface for managing clients, reports, and content
- **Automated Crawling**: Collect articles from various sources based on client interests
- **AI-Generated Reports**: Generate personalized market intelligence reports using GPT-4
- **Document Processing**: Upload and analyze PDF, DOCX, TXT, CSV, and XLSX files
- **LinkedIn Content Generation**: Create professional LinkedIn posts from reports and articles
- **AI Chatbot**: Ask questions about clients, reports, and market data

## Project Structure

```
src/
├── crawler.py                  # Article crawling functionality
├── dashboard.py                # Flask web dashboard
├── document_processor.py       # External file processing
├── report_generator.py         # AI report generation
├── linkedin_generator.py       # LinkedIn content creation
├── chatbot_ai.py               # AI chatbot functionality
├── models/
│   └── client_model.py         # Client data management
├── utils/
│   └── redis_cache.py          # Redis cache utilities
├── templates/                  # HTML templates
├── static/                     # Static assets
└── uploads/                    # Uploaded files storage
```

## Setup

### Prerequisites

- Python 3.8+
- Redis server
- OpenAI API key

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/market-intelligence-platform.git
   cd market-intelligence-platform
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file with the following variables:
   ```
   OPENAI_API_KEY=your_openai_api_key
   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_PASSWORD=your_redis_password_if_any
   FLASK_SECRET_KEY=your_random_secret_key
   ```

4. Start the Redis server:
   ```
   redis-server
   ```

5. Run the application:
   ```
   python src/dashboard.py
   ```

6. Open your browser and navigate to:
   ```
   http://localhost:3000
   ```

## Usage

### Managing Clients

1. Create a new client with their industry and interests
2. Add sources to crawl for articles
3. Update client details as needed

### Generating Reports

1. Trigger a crawl to collect latest articles
2. Generate a report based on collected articles
3. View report history and export as needed

### Working with External Data

1. Upload external files (PDF, DOCX, TXT, CSV, XLSX)
2. View file content and metadata
3. Generate reports based on uploaded files

### Creating LinkedIn Content

1. Generate LinkedIn posts from reports or articles
2. Customize the tone (professional, casual, engaging)
3. Include AI-generated images if desired

### Using the AI Chatbot

1. Ask questions about client data, reports, and market trends
2. Get AI-generated responses with source citations
3. Use suggested follow-up questions for deeper insights

## License

[MIT License](LICENSE)

## Contact

Your Name - your.email@example.com 