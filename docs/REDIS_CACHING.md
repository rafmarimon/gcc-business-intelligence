# Redis Caching for GCC Business Intelligence Platform

This document explains how Redis caching is integrated with the GCC Business Intelligence Platform and provides setup instructions.

## Overview

Redis is used in this application for:
1. Caching OpenAI API responses to reduce API costs
2. Storing generated LinkedIn posts and images 
3. Implementing rate limiting for API endpoints
4. Tracking usage metrics

## Configuration

### Environment Variables

Set the following environment variables to configure Redis:

```
REDIS_HOST=redis-16428.c100.us-east-1-4.ec2.redns.redis-cloud.com
REDIS_PORT=16428
REDIS_USERNAME=default
REDIS_PASSWORD=your_redis_password_here
```

### Redis Cloud Setup

The application is configured to work with Redis Cloud. To set up Redis Cloud:

1. Create an account at [Redis Cloud](https://redis.com/redis-enterprise-cloud/overview/)
2. Create a subscription (the free tier provides 30MB which is sufficient for testing)
3. Create a database within your subscription
4. Note the endpoint, port, and default user credentials
5. Update the environment variables with these details

### Digital Ocean Deployment

When deploying to Digital Ocean:

1. Add the Redis environment variables to your app configuration
2. Ensure the application can access the Redis Cloud endpoint (whitelist your Digital Ocean IP if needed)
3. For larger deployments, consider upgrading the Redis Cloud plan or self-hosting Redis

## Fallback Mechanism

The application includes a fallback to in-memory caching if:
- Redis connection fails
- Redis credentials are not provided
- The Redis Python package is not installed

This ensures the application will function even without Redis, though with reduced performance.

## Key Features

### Rate Limiting

API endpoints use Redis-based rate limiting with configurable limits:
- LinkedIn post generation: 5 requests per 5 minutes
- LinkedIn post listing: 20 requests per minute
- Other API endpoints: Customizable limits

### Content Caching

The system caches:
- Generated LinkedIn posts (7 days)
- Generated images (30 days)
- API responses (5 minutes)
- OpenAI completions (1 day)

### Security Considerations

- Redis credentials are stored in environment variables, not in code
- The Redis connection uses TLS encryption
- Access is restricted to authenticated users only

## Monitoring Redis Usage

To monitor Redis usage:
1. Log into your Redis Cloud account
2. Navigate to the "Metrics" section of your database
3. View memory usage, commands processed, and connections

## Troubleshooting

If you encounter Redis connection issues:

1. Check that the Redis host is accessible from your deployment
2. Verify credentials are correctly set in environment variables
3. Check Redis Cloud dashboard for any service issues
4. Review application logs for Redis connection errors

## Dependencies

The Redis caching system requires:
- `redis==5.0.1` or later
- `python-dotenv==1.0.0` or later

These are included in the project's `requirements.txt` file. 