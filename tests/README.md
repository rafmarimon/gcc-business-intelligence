# Crawl4AI Test Suite

This directory contains tests for the various components of the Crawl4AI integration in the GCC Business Intelligence project.

## Test Files

- `test_crawl4ai_cli.py` - Tests for the Crawl4AI CLI interface, including configuration loading, parameter parsing, and basic crawling functionality.

## Running Tests

### Prerequisites

Before running the tests, make sure you have installed all the required dependencies:

```bash
pip install -r dev-requirements.txt
```

### Running the CLI Tests

To run the CLI tests specifically:

```bash
pytest test_crawl4ai_cli.py -v
```

To run a specific test class:

```bash
pytest test_crawl4ai_cli.py::TestCLIBasics -v
```

To run a specific test method:

```bash
pytest test_crawl4ai_cli.py::TestCLIBasics::test_help -v
```

### Test Coverage

The CLI tests cover:

1. **Basic CLI functionality**
   - Help command
   - Examples command
   - Required arguments validation

2. **Configuration Handling**
   - Loading YAML and JSON config files
   - Parsing key-value parameters
   - Error handling for missing config files

3. **LLM Integration**
   - Creating and verifying LLM configurations

4. **Crawling Features**
   - Basic web crawling (mocked)
   - Content extraction with schemas
   - Error handling for crawling failures

5. **Output Formats**
   - Generating and validating JSON output

## Adding New Tests

When adding new tests, follow these guidelines:

1. Group related tests in test classes
2. Use descriptive test method names that indicate what is being tested
3. Use fixtures for common setup
4. Mock external dependencies like web requests or file systems

## Troubleshooting

If you encounter issues running the tests:

1. Ensure you're using the correct Python version (Python 3.9+)
2. Check that all dependencies are installed correctly
3. Verify that the Crawl4AI package is installed and accessible
4. Ensure that any required environment variables are set 