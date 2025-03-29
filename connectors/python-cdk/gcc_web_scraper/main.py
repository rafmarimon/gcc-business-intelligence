"""
Main script for the GCC Web Scraper connector.
"""

import sys

from source import GCCWebScraperSource

if __name__ == "__main__":
    source = GCCWebScraperSource()
    source.run(sys.argv[1:]) 