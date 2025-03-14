#!/usr/bin/env python3
"""
Global Possibilities - UAE/GCC Business Intelligence Platform
Setup Script

This script sets up the environment for the GCC Business Intelligence Platform:
1. Creates necessary directories
2. Installs required dependencies
3. Sets up environment variables
4. Initializes configuration files
"""

import os
import sys
import subprocess
import json
import shutil
from pathlib import Path

def print_header():
    """Print the setup header."""
    print("\n" + "="*80)
    print(" "*20 + "Global Possibilities - Business Intelligence Platform" + " "*20)
    print(" "*30 + "Setup Script" + " "*30)
    print("="*80 + "\n")

def create_directories():
    """Create necessary directories for the project."""
    print("Creating directories...")
    
    # List of directories to create
    directories = [
        "data",
        "reports",
        "content",
        "logs",
        "config"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"  - Created '{directory}' directory")
    
    print("Directory setup complete.\n")

def install_dependencies():
    """Install Python dependencies from requirements.txt."""
    print("Installing dependencies...")
    
    # Check if requirements.txt exists
    if not os.path.exists("requirements.txt"):
        print("  ERROR: requirements.txt not found!")
        return False
    
    # Check if venv exists, create if it doesn't
    if not os.path.exists("venv"):
        print("  Creating virtual environment...")
        try:
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            print("  - Virtual environment created successfully")
        except subprocess.CalledProcessError:
            print("  ERROR: Failed to create virtual environment!")
            return False
    
    # Install dependencies
    print("  Installing required packages...")
    
    # Determine the pip executable
    pip_cmd = os.path.join("venv", "bin", "pip") if os.name != "nt" else os.path.join("venv", "Scripts", "pip")
    
    try:
        subprocess.run([pip_cmd, "install", "-U", "pip"], check=True)
        subprocess.run([pip_cmd, "install", "-r", "requirements.txt"], check=True)
        print("  - Packages installed successfully")
    except subprocess.CalledProcessError:
        print("  ERROR: Failed to install dependencies!")
        return False
    
    print("Dependency installation complete.\n")
    return True

def setup_env_file():
    """Set up the .env file with required variables."""
    print("Setting up environment variables...")
    
    env_file = ".env"
    
    # Check if .env already exists
    if os.path.exists(env_file):
        overwrite = input("  .env file already exists. Overwrite? (y/n): ").lower()
        if overwrite != "y":
            print("  - Skipping environment setup")
            return
    
    # Create default .env content
    env_content = """# Global Possibilities - UAE/GCC Business Intelligence Platform
# Environment Variables

# OpenAI API Key (required for report generation and LinkedIn posts)
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration (if using MongoDB)
MONGODB_URI=mongodb://localhost:27017
DB_NAME=gcc_business_news

# Email Configuration (for sending reports)
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your_email@example.com
SMTP_PASSWORD=your_email_password
REPORT_RECIPIENTS=recipient1@example.com,recipient2@example.com

# Web Scraping Settings
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36
SCRAPE_TIMEOUT=30
"""
    
    # Write to .env file
    with open(env_file, "w") as f:
        f.write(env_content)
    
    print("  - Created .env file with template values")
    print("  - IMPORTANT: Edit the .env file to add your actual API keys and settings!")
    print("Environment setup complete.\n")

def setup_config_files():
    """Set up configuration files for the platform."""
    print("Setting up configuration files...")
    
    # Create news sources configuration
    sources_config = {
        "gulf_news": {
            "name": "Gulf News",
            "url": "https://gulfnews.com/business",
            "language": "en",
            "country": "UAE",
            "selectors": {
                "article": "div[class*='story']",
                "headline": "*[class*='title'] a",
                "summary": "*[class*='teaser']",
                "link": "*[class*='title'] a",
                "date": "time"
            },
            "base_url": "https://gulfnews.com"
        },
        "khaleej_times": {
            "name": "Khaleej Times",
            "url": "https://www.khaleejtimes.com/business",
            "language": "en",
            "country": "UAE",
            "selectors": {
                "article": "article",
                "headline": "h4 a",
                "summary": "div.desc",
                "link": "h4 a",
                "date": ".time-elapsed"
            },
            "base_url": "https://www.khaleejtimes.com"
        },
        "arabian_business": {
            "name": "Arabian Business",
            "url": "https://www.arabianbusiness.com/news",
            "language": "en",
            "country": "UAE",
            "selectors": {
                "article": ".list-item",
                "headline": "h3 a",
                "summary": ".teaser",
                "link": "h3 a",
                "date": ".date-display-single"
            },
            "base_url": "https://www.arabianbusiness.com"
        },
        "the_national": {
            "name": "The National",
            "url": "https://www.thenationalnews.com/business",
            "language": "en",
            "country": "UAE",
            "selectors": {
                "article": "article",
                "headline": ".headline a",
                "summary": ".standfirst",
                "link": ".headline a",
                "date": "time"
            },
            "base_url": "https://www.thenationalnews.com"
        },
        "zawya": {
            "name": "Zawya",
            "url": "https://www.zawya.com/en/business",
            "language": "en",
            "country": "MENA",
            "selectors": {
                "article": ".article-card",
                "headline": ".article-title a",
                "summary": ".article-description",
                "link": ".article-title a",
                "date": ".article-time"
            },
            "base_url": "https://www.zawya.com"
        }
    }
    
    # Create analysis keywords configuration
    keywords_config = {
        "economic": [
            "GDP", "inflation", "investment", "economic growth", "recession", 
            "fiscal policy", "monetary policy", "trade", "export", "import",
            "currency", "dirham", "riyal", "budget", "deficit", "surplus"
        ],
        "sectors": [
            "oil", "gas", "energy", "renewable", "solar", "sustainability", 
            "technology", "fintech", "healthcare", "retail", "real estate", 
            "tourism", "hospitality", "aviation", "banking", "construction"
        ],
        "policy": [
            "regulation", "law", "legislation", "policy", "government", "initiative",
            "ministry", "authority", "compliance", "legal", "framework", "strategy"
        ],
        "corporate": [
            "merger", "acquisition", "IPO", "startup", "funding", "investment round",
            "expansion", "partnership", "joint venture", "collaboration", "CEO", 
            "executive", "board", "corporate", "company", "business"
        ],
        "events": [
            "expo", "exhibition", "conference", "summit", "forum", "event",
            "launch", "announcement", "unveiling", "meeting", "ceremony"
        ],
        "regional": [
            "UAE", "Dubai", "Abu Dhabi", "Saudi Arabia", "KSA", "Qatar", "Bahrain",
            "Kuwait", "Oman", "GCC", "Middle East", "MENA", "Riyadh", "Doha", "Vision 2030"
        ],
        "global": [
            "global", "international", "worldwide", "foreign", "overseas", 
            "China", "US", "USA", "Europe", "Asia", "Africa", "Western", "Eastern"
        ]
    }
    
    # Write configuration files
    os.makedirs("config", exist_ok=True)
    
    with open("config/news_sources.json", "w") as f:
        json.dump(sources_config, f, indent=2)
    
    with open("config/keywords.json", "w") as f:
        json.dump(keywords_config, f, indent=2)
    
    print("  - Created news sources configuration")
    print("  - Created keywords configuration")
    print("Configuration setup complete.\n")

def verify_installation():
    """Verify that the installation is working."""
    print("Verifying installation...")
    
    # Check if venv exists
    if not os.path.exists("venv"):
        print("  ERROR: Virtual environment not found!")
        return False
    
    # Determine the python executable
    python_cmd = os.path.join("venv", "bin", "python") if os.name != "nt" else os.path.join("venv", "Scripts", "python")
    
    # Try to import the required packages
    try:
        result = subprocess.run([python_cmd, "-c", "import requests, beautifulsoup4, pandas, openai, dotenv, markdown"], 
                               stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        if result.returncode != 0:
            print(f"  ERROR: Package verification failed!")
            return False
    except subprocess.CalledProcessError:
        print("  ERROR: Failed to verify packages!")
        return False
    
    print("  - Package verification successful")
    
    # Check if main files exist
    required_files = [
        "src/manual_run.py",
        "src/collectors/news_collector.py",
        "src/processors/news_analyzer.py",
        "src/generators/linkedin_content.py",
        "src/generators/consolidated_report.py"
    ]
    
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print("  WARNING: The following required files are missing:")
        for f in missing_files:
            print(f"    - {f}")
        return False
    
    print("  - All required files are present")
    print("Installation verification complete.\n")
    return True

def display_next_steps():
    """Display next steps for the user."""
    print("\n" + "="*80)
    print(" "*30 + "NEXT STEPS" + " "*30)
    print("="*80)
    
    print("""
1. Edit the .env file to add your OpenAI API key and other settings.

2. Start using the platform with the following commands:
   
   # Activate the virtual environment
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   
   # Run the full process (collection + analysis + LinkedIn posts)
   python src/manual_run.py
   
   # Skip collection and use existing data
   python src/manual_run.py --skip-collection
   
   # Skip report generation
   python src/manual_run.py --skip-report

3. Check the generated reports in the 'reports' directory.

4. View LinkedIn posts in the 'content' directory.

5. Customize the news sources in 'config/news_sources.json' if needed.

Thank you for installing the Global Possibilities Business Intelligence Platform!
""")

def main():
    """Main setup function."""
    print_header()
    
    # Create directories
    create_directories()
    
    # Install dependencies
    if not install_dependencies():
        print("\nERROR: Setup failed during dependency installation.")
        sys.exit(1)
    
    # Set up environment file
    setup_env_file()
    
    # Set up configuration files
    setup_config_files()
    
    # Verify installation
    if verify_installation():
        print("\nSetup completed successfully!")
    else:
        print("\nWARNING: Setup completed with some issues.")
    
    # Display next steps
    display_next_steps()

if __name__ == "__main__":
    main() 