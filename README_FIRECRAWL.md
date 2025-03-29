# Firecrawl Web Scraping Test Suite

This repository contains test scripts for evaluating the [Firecrawl](https://docs.firecrawl.dev/api-reference/introduction) web scraping API and comparing it with traditional scraping methods.

## Overview

Firecrawl is a web scraping API service that handles JavaScript rendering, proxy management, and rate limiting for you. These scripts help you test its capabilities and compare it with direct scraping using BeautifulSoup.

## Setup

1. Clone this repository
2. Install the required dependencies:
   ```
   pip install requests beautifulsoup4 python-dotenv
   ```
3. Set up your Firecrawl API key in one of these ways:
   - Add it to the `.env` file with the key `FIRECRAWL_API_KEY`
   - Pass it as a command-line argument when running the scripts

## Scripts

### 1. Basic Firecrawl Test (`test_firecrawl.py`)

A simple script to test the Firecrawl API for scraping content from a news article.

**Usage:**
```bash
python test_firecrawl.py --api-key YOUR_API_KEY
```

**Features:**
- Tests the full page scraping endpoint
- Tests the data extraction endpoint with specific selectors
- Saves results as JSON files
- Provides a summary of the test results

### 2. UAE News Scraping Test (`test_firecrawl_uae_news.py`)

Specialized for scraping UAE business news sites using Firecrawl.

**Usage:**
```bash
python test_firecrawl_uae_news.py --api-key YOUR_API_KEY
```

**Features:**
- Tests scraping from multiple UAE news sites
- Extracts article links from each site
- Scrapes individual articles with site-specific selectors
- Saves results in a structured format (JSON and CSV)
- Provides a detailed report of the scraping process

### 3. Scraping Method Comparison (`compare_scraping_methods.py`)

Compares Firecrawl with direct scraping using BeautifulSoup.

**Usage:**
```bash
python compare_scraping_methods.py --api-key YOUR_API_KEY
```

**Features:**
- Compares scraping the same URLs with both methods
- Measures success rates and response times
- Compares data extraction capabilities
- Generates comprehensive comparison reports
- Creates a summary with performance metrics

## Key Capabilities Tested

1. **Full Page Scraping**: Retrieving the complete HTML and text content of a page
2. **Data Extraction**: Using CSS selectors to extract specific elements from a page
3. **JavaScript Rendering**: Testing how well each method handles JavaScript-rendered content
4. **Link Extraction**: Identifying and extracting links from pages
5. **Error Handling**: Testing how each method handles various error conditions
6. **Performance**: Comparing response times and success rates

## Example Workflow

1. First, test the basic Firecrawl functionality:
   ```
   python test_firecrawl.py --api-key YOUR_API_KEY
   ```

2. Then, test scraping from UAE news sites:
   ```
   python test_firecrawl_uae_news.py --api-key YOUR_API_KEY
   ```

3. Finally, compare with BeautifulSoup:
   ```
   python compare_scraping_methods.py --api-key YOUR_API_KEY
   ```

## Interpreting Results

For each test run, the scripts generate various output files:

- **JSON files**: Contain detailed raw data from the scraping operations
- **CSV files**: Provide structured data for analysis
- **Summary reports**: Offer overviews of performance metrics and success rates

Compare these outputs to evaluate:
- Which method is more reliable for your target sites
- Performance differences
- Quality of extracted data
- Handling of different web technologies

## Troubleshooting

- **API Key Issues**: Ensure your Firecrawl API key is valid and properly formatted
- **Connection Errors**: Check your internet connection and confirm the target sites are online
- **Selector Problems**: If data extraction fails, review and refine your CSS selectors

## Extending the Tests

You can modify these scripts to test:
- Different target websites
- Custom CSS selectors
- Additional scraping parameters
- New extraction techniques

## License

This project is open source and available under the MIT License.

## Acknowledgments

- [Firecrawl](https://docs.firecrawl.dev) for providing the web scraping API
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) for direct scraping capabilities 