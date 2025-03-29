# GCC Business Intelligence Platform - Enhancements

This document outlines the enhancements made to the GCC Business Intelligence platform to improve reliability, performance, scalability, and security.

## Table of Contents

1. [Redis Caching Layer](#redis-caching-layer)
2. [Robust API Utilities](#robust-api-utilities)
3. [Role-Based Authentication System](#role-based-authentication-system)
4. [CI/CD Pipeline](#cicd-pipeline)
5. [Data Ingestion with Airbyte ETL](#data-ingestion-with-airbyte-etl)
6. [Dockerization](#dockerization)
7. [Configuration](#configuration)
8. [Installation and Setup](#installation-and-setup)
9. [Monitoring and Maintenance](#monitoring-and-maintenance)

## Redis Caching Layer

A Redis caching layer has been implemented to improve performance and reduce load on external APIs:

- Located in `src/utils/redis_cache.py`
- Features include:
  - Configurable TTL (Time-To-Live) for cached responses
  - Fallback to in-memory cache when Redis is unavailable
  - Decorator for easily caching function results
  - Support for both simple key-value pairs and complex data structures
  - Automatic serialization and deserialization of JSON data

### How to Use

```python
from src.utils.redis_cache import get_cache

# Get cache instance
cache = get_cache()

# Cache data
cache.set('key', data, ttl=3600)  # Cache for 1 hour

# Retrieve data
data = cache.get('key')

# Use as decorator
from src.utils.redis_cache import cache_result

@cache_result(ttl=3600)
def fetch_data(param1, param2):
    # Function implementation
    return data
```

## Robust API Utilities

Enhanced API utilities have been implemented to improve reliability when communicating with external APIs:

- Located in `src/utils/api_utils.py`
- Features include:
  - Automatic retry mechanism with exponential backoff
  - Circuit breaker pattern to prevent repeated calls to failing services
  - Comprehensive error handling and logging
  - Rate limiting to prevent API quota exhaustion
  - Response validation and sanitization

### How to Use

```python
from src.utils.api_utils import ApiClient

# Create client instance
api_client = ApiClient(base_url="https://api.example.com")

# Make robust API calls
response = api_client.get("/endpoint", 
                         retry_attempts=3, 
                         timeout=10,
                         rate_limit={"calls": 100, "period": 60})

# Post data with automatic retries
response = api_client.post("/endpoint", 
                          data={"key": "value"}, 
                          retry_on_status_codes=[429, 500, 502, 503, 504])
```

## Role-Based Authentication System

A comprehensive role-based authentication system has been implemented:

- Located in `src/utils/auth.py`
- Features include:
  - JWT-based authentication
  - Role-based access control (Admin, Analyst, Viewer, Client)
  - Fine-grained permissions system
  - Protection against brute force attacks
  - Session management
  - Secure password storage with bcrypt

### Roles and Permissions

| Role | Permissions |
|------|-------------|
| Admin | Full access to all features |
| Analyst | Create and edit reports, view all data |
| Viewer | View reports and dashboards |
| Client | View specific assigned reports |

### How to Use

```python
from src.utils.auth import AuthManager, require_auth, require_permission

auth = AuthManager()

# In your Flask routes:
@app.route('/protected')
@require_auth
def protected_route():
    return "Authenticated access only"

@app.route('/admin')
@require_permission('admin:access')
def admin_route():
    return "Admin access only"
```

## CI/CD Pipeline

A GitHub Actions CI/CD pipeline has been set up for automated testing, building, and deployment:

- Located in `.github/workflows/ci-cd.yml`
- Features include:
  - Automated testing with pytest
  - Code coverage reporting
  - Static code analysis with flake8
  - Docker image building and publishing
  - Automated deployment to Digital Ocean
  - Environment-specific configurations

### Pipeline Stages

1. **Test**: Runs unit tests and code quality checks
2. **Build**: Creates and publishes Docker images
3. **Deploy**: Deploys the application to production or staging environment

## Data Ingestion with Airbyte ETL

An Airbyte integration has been implemented for streamlined data ingestion:

- Located in `src/utils/airbyte_etl.py`
- Features include:
  - Configuration for various data sources (news, government data)
  - Data transformation and normalization
  - Integration with existing collectors
  - Scheduling and monitoring of data pipelines
  - Error handling and reporting

### Setting Up Data Sources

1. Configure source in the `airbyte-config` directory
2. Use the AirbyteETL class to set up connections
3. Import the data into the existing collectors

```python
from src.utils.airbyte_etl import AirbyteETL

etl = AirbyteETL()

# Set up news data source
etl.setup_news_sources()

# Import data from Airbyte to collectors
etl.import_to_collectors('/path/to/data', 'news')
```

## Dockerization

The application has been containerized for easier deployment and scaling:

- `Dockerfile` for building the application container
- `docker-compose.yml` for orchestrating multiple services
- Environment-specific configuration via Docker environment variables

### Services Included

- Application container
- Redis cache
- (Optional) PostgreSQL database
- (Optional) Prometheus & Grafana for monitoring

## Configuration

Configuration has been centralized and made more flexible:

- Environment variable support
- Configuration override via files
- Separate configurations for development, testing, and production

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Port to run the application on | 3000 |
| `REDIS_URL` | URL for Redis connection | redis://redis:6379/0 |
| `JWT_SECRET` | Secret for JWT token signing | (Generated) |
| `LOG_LEVEL` | Logging level | INFO |
| `API_TIMEOUT` | Default timeout for API calls | 30 |
| `ENVIRONMENT` | Application environment | development |

## Installation and Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.9+
- Git

### Setup Steps

1. Clone the repository
   ```
   git clone https://github.com/your-org/gcc-business-intelligence.git
   cd gcc-business-intelligence
   ```

2. Set up environment variables (create a `.env` file)
   ```
   ENVIRONMENT=development
   REDIS_URL=redis://localhost:6379/0
   JWT_SECRET=your-secret-key
   ```

3. Start the application using Docker Compose
   ```
   docker-compose up -d
   ```

4. Access the application at http://localhost:3000

### Manual Setup (without Docker)

1. Install dependencies
   ```
   pip install -r requirements.txt
   ```

2. Set up Redis (if not using Docker)
   ```
   sudo apt update
   sudo apt install redis-server
   sudo systemctl start redis-server
   ```

3. Run the application
   ```
   python src/app.py
   ```

## Monitoring and Maintenance

The application includes tools for monitoring and maintenance:

- Prometheus metrics for performance monitoring
- Health check endpoints
- Detailed logging with different levels
- API usage statistics

### Health Check

Access the health check endpoint at `/api/health` to verify the application status.

### Logs

Logs are stored in the `logs` directory and rotated daily. The log level can be configured using the `LOG_LEVEL` environment variable.

### Backup and Restore

For backing up data:

```bash
# Backup Redis data
redis-cli SAVE
cp /var/lib/redis/dump.rdb /backup/redis-backup-$(date +%Y%m%d).rdb

# Backup application data
tar -czf /backup/app-data-$(date +%Y%m%d).tar.gz /app/data
```

---

## Contributing

Please see CONTRIBUTING.md for guidelines on contributing to this project.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 