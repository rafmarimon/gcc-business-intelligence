# GCC Business Intelligence Hybrid Connector Guide

This guide explains how to work with our hybrid Airbyte connector strategy, combining the flexibility of Python CDK connectors with the simplicity of Low-Code connectors, augmented by shared adapter services.

## Architecture Overview

Our hybrid connector architecture consists of:

1. **Python CDK Connectors**: Used for complex sources requiring web scraping, ML processing, or custom logic
2. **Low-Code YAML Connectors**: Used for simpler API sources with standard authentication/pagination
3. **Adapter Services**: Shared microservices that extend Low-Code connector capabilities:
   - **Text Processing Service**: Provides NLP, content enrichment, and transformation
   - **Authentication Service**: Handles complex auth patterns (OAuth2, token refresh, HMAC signing)

## Development vs. Production Environment

We use separate dependency configurations to optimize both development and production:

### Development Environment

- Includes the Airbyte CDK, testing tools, and additional dependencies
- Suitable for local development and CI/CD testing
- Uses the `dev-requirements.txt` file

### Production Environment

- Minimal dependencies without development tools
- Optimized for DigitalOcean and production deployment
- Uses the `requirements.txt` file

## Getting Started

### Building the Base Images

```bash
# Build both development and production base images
docker-compose -f docker-compose.connectors.yml build connector-base-dev connector-base-prod
```

### Running the Adapter Services

```bash
# Start the adapter services and Redis cache
docker-compose -f docker-compose.connectors.yml up -d text-processing-service auth-service redis
```

## Creating New Connectors

### Low-Code Connector (For Standard API Sources)

1. Create a new directory in `connectors/low-code/`
2. Create a `source.yaml` file following the Airbyte Low-Code spec
3. Add any configuration files needed
4. Reference the adapter services to extend capabilities

Example directory structure:
```
connectors/
└── low-code/
    └── your_connector_name/
        ├── source.yaml      # Main connector definition
        └── spec.yaml        # Configuration spec
```

### Python CDK Connector (For Complex Sources)

1. Create a new directory in `connectors/python-cdk/`
2. Create a `Dockerfile` that extends our base image
3. Add source code and connector-specific requirements
4. Use the standard Airbyte CDK patterns

Example directory structure:
```
connectors/
└── python-cdk/
    └── your_connector_name/
        ├── Dockerfile
        ├── requirements.txt
        ├── source.py
        └── main.py
```

## Calling Adapter Services

### Authentication Adapter

The authentication adapter provides endpoints for:

1. **OAuth2 Token Management**: `http://auth-service:8091/get-token`
2. **API Key Validation**: `http://auth-service:8091/validate-api-key`
3. **Custom Auth Schemes**: `http://auth-service:8091/custom-auth`

Example in low-code connector:
```yaml
authenticator:
  type: "CustomAuthenticator"
  class_name: "auth_service"
  url: "http://auth-service:8091/get-token"
```

### Text Processing Adapter

The text processing adapter provides endpoints for:

1. **Content Enrichment**: `http://text-processing-service:8090/enrich`
2. **Data Transformation**: `http://text-processing-service:8090/transform`

Example in low-code connector:
```yaml
transformations:
  - type: "RemoteTransform"
    url: "http://text-processing-service:8090/enrich"
```

## Deployment

### Local Development

For local development with the full CDK and tools:

```bash
# Build with development target
docker-compose -f docker-compose.connectors.yml build --build-arg target=dev

# Run with development configuration
docker-compose -f docker-compose.connectors.yml up
```

### Production Deployment

For production deployment with minimal dependencies:

```bash
# Build with production target
docker-compose -f docker-compose.connectors.yml build --build-arg target=prod

# Run with production configuration
docker-compose -f docker-compose.connectors.yml up
```

## Troubleshooting

### Common Issues

1. **Dependency Conflicts**: If you encounter dependency conflicts, ensure you're using the correct base image (dev vs. prod)

2. **Connection Issues between Services**: Verify all services are on the same Docker network (`gcc_net`)

3. **Authentication Failures**: Check environment variables are properly set (API keys, credentials)

### Debugging

Set the environment variable `LOGLEVEL=DEBUG` to enable verbose logging in both adapter services and connectors.

## Next Steps

- Explore using adapter services for additional capabilities like data validation, schema enforcement, etc.
- Consider adding more adapter services for specific domain functionality
- Monitor service performance and scale as needed 