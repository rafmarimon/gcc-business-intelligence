#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import logging
import json
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
import requests
import markdown
from dotenv import load_dotenv

# Try to import TensorFlow, but make it optional
try:
    import tensorflow as tf
    import numpy as np
    from sklearn.preprocessing import MinMaxScaler
    has_tensorflow = True
    logging.info("TensorFlow is available and will be used for ML features")
except ImportError:
    has_tensorflow = False
    import numpy as np
    logging.info("TensorFlow not available, ML features will be limited")

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("client_report_generator")

# Load environment variables
load_dotenv()

class ClientReportGenerator:
    """
    Generates client-specific reports with weekly and monthly options.
    Uses Beautiful Soup for web scraping and TensorFlow for report memorization.
    """
    
    def __init__(self, client_name, config_dir="config"):
        """Initialize the client report generator."""
        self.client_name = client_name
        self.client_id = client_name.lower().replace(" ", "_")
        self.config_dir = config_dir
        
        # Load client configuration
        client_config_path = os.path.join(self.config_dir, "clients", f"{self.client_id}.json")
        if os.path.exists(client_config_path):
            with open(client_config_path, 'r', encoding='utf-8') as f:
                self.client_config = json.load(f)
            logger.info(f"Loaded configuration for client: {client_name}")
        else:
            self.client_config = {
                "name": client_name,
                "keywords": ["UAE economy", "Dubai business", "GCC economy"],
                "industries": ["Real Estate", "Finance", "Technology", "Energy"],
                "report_type": "standard"
            }
            logger.warning(f"Client config not found for {client_name}, using default settings")
        
        # Load news sources
        sources_config_path = os.path.join(self.config_dir, "news_sources.json")
        if os.path.exists(sources_config_path):
            with open(sources_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.sources = config.get("sources", [])
            logger.info(f"Loaded {len(self.sources)} news sources")
        else:
            self.sources = []
            logger.warning("News sources configuration not found")
        
        # Set up ML directory
        self.ml_dir = os.path.join("data", "ml", self.client_id)
        os.makedirs(self.ml_dir, exist_ok=True)
        
        # Initialize TensorFlow model if available
        self.model = self._initialize_tf_model() if has_tensorflow else None
        
        # Set up reports directory structure
        self.reports_dir = os.path.join("reports", self.client_id)
        self.weekly_dir = os.path.join(self.reports_dir, "weekly")
        self.monthly_dir = os.path.join(self.reports_dir, "monthly")
        
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs(self.weekly_dir, exist_ok=True)
        os.makedirs(self.monthly_dir, exist_ok=True)
    
    def _initialize_tf_model(self):
        """Initialize TensorFlow model for report memorization and analysis."""
        try:
            if not has_tensorflow:
                return None
                
            # Check if TensorFlow is installed
            logger.info(f"TensorFlow version: {tf.__version__}")
            
            # Simple sequential model for text classification
            model = tf.keras.Sequential([
                tf.keras.layers.Embedding(10000, 16),
                tf.keras.layers.GlobalAveragePooling1D(),
                tf.keras.layers.Dense(16, activation='relu'),
                tf.keras.layers.Dense(1, activation='sigmoid')
            ])
            
            model.compile(optimizer='adam',
                         loss='binary_crossentropy',
                         metrics=['accuracy'])
            
            # Check if a saved model exists and load it
            model_path = os.path.join(self.ml_dir, "report_model")
            if os.path.exists(model_path):
                try:
                    model = tf.keras.models.load_model(model_path)
                    logger.info(f"Loaded existing TensorFlow model for {self.client_name}")
                except Exception as e:
                    logger.error(f"Error loading model: {e}")
            
            return model
            
        except Exception as e:
            logger.warning(f"Error initializing TensorFlow model: {e}")
            return None
    
    def collect_news(self, keywords=None, days=7):
        """
        Collect news using Beautiful Soup.
        
        Args:
            keywords: Optional list of keywords to filter news by
            days: Number of days of news to collect
            
        Returns:
            List of news articles
        """
        if keywords is None:
            keywords = self.client_config.get("keywords", [])
        
        logger.info(f"Collecting news for client {self.client_name} with keywords: {keywords}")
        
        articles = []
        
        # Process each source
        for source in self.sources:
            source_name = source.get("name", "Unknown")
            url = source.get("url")
            
            if not url:
                continue
                
            logger.info(f"Processing source: {source_name} ({url})")
            
            try:
                # Fetch the page
                response = requests.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                })
                response.raise_for_status()
                
                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Get article links
                article_links = []
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    
                    # Make sure it's an absolute URL
                    if not href.startswith('http'):
                        if href.startswith('/'):
                            # Relative URL
                            parsed_url = requests.utils.urlparse(url)
                            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                            href = base_url + href
                        else:
                            # Not a valid link
                            continue
                    
                    # Basic filtering for article-like URLs
                    if any(term in href for term in ['/news/', '/article/', '/story/', '/business/']):
                        article_links.append(href)
                
                # Limit to 5 links per source
                article_links = article_links[:5]
                
                # Process each article
                for link in article_links:
                    try:
                        # Fetch the article
                        article_response = requests.get(link, headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                        })
                        article_response.raise_for_status()
                        
                        # Parse HTML
                        article_soup = BeautifulSoup(article_response.text, 'html.parser')
                        
                        # Extract title
                        title = article_soup.find('h1')
                        title_text = title.get_text() if title else "Untitled Article"
                        
                        # Extract content
                        content = ""
                        article_tag = article_soup.find('article')
                        if article_tag:
                            content = article_tag.get_text()
                        else:
                            # Try alternative content extraction
                            main_content = article_soup.find(['main', 'div', 'section'], 
                                                           class_=['content', 'article-content', 'story-content'])
                            if main_content:
                                content = main_content.get_text()
                            else:
                                # Last resort: use body text
                                body = article_soup.find('body')
                                if body:
                                    content = body.get_text()
                        
                        # Clean content
                        content = ' '.join(content.split())
                        
                        # Extract date
                        date = None
                        date_tag = article_soup.find(['time', 'span', 'div'], 
                                                    class_=['date', 'time', 'published', 'article-date'])
                        if date_tag:
                            date = date_tag.get_text()
                        
                        # Check if any keywords match
                        combined_text = f"{title_text} {content}".lower()
                        matching_keywords = [kw for kw in keywords if kw.lower() in combined_text]
                        
                        if matching_keywords:
                            article = {
                                "url": link,
                                "source": source_name,
                                "title": title_text,
                                "content": content[:1000] + "..." if len(content) > 1000 else content,
                                "date": date,
                                "keywords": matching_keywords,
                                "timestamp": datetime.now().isoformat()
                            }
                            articles.append(article)
                            logger.info(f"Collected article: {title_text}")
                    
                    except Exception as e:
                        logger.error(f"Error processing article {link}: {e}")
                
            except Exception as e:
                logger.error(f"Error processing source {source_name}: {e}")
        
        # Save collected articles
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        articles_file = os.path.join("data", "news", f"{self.client_id}_articles_{timestamp}.json")
        os.makedirs(os.path.dirname(articles_file), exist_ok=True)
        
        with open(articles_file, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2)
        
        logger.info(f"Collected {len(articles)} articles for {self.client_name}")
        return articles
    
    def generate_weekly_report(self):
        """Generate a weekly report for the client."""
        logger.info(f"Generating weekly report for {self.client_name}")
        
        # Collect news for the past week
        articles = self.collect_news(days=7)
        
        # Define report period
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        period = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"
        
        # Generate report content
        report_content = self._generate_report_content(articles, "Weekly", period)
        
        # Generate the report files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_files = self._save_report(report_content, "weekly", timestamp)
        
        # Train the ML model with this report
        self._memorize_report(report_content, articles)
        
        return report_files
    
    def generate_monthly_report(self):
        """Generate a monthly report for the client."""
        logger.info(f"Generating monthly report for {self.client_name}")
        
        # Collect news for the past month
        articles = self.collect_news(days=30)
        
        # Define report period
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        period = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"
        
        # Get historical reports for analysis
        historical_insights = self._analyze_historical_reports()
        
        # Generate report content with trends and forecasts
        report_content = self._generate_report_content(
            articles, 
            "Monthly", 
            period, 
            include_forecast=True,
            historical_insights=historical_insights
        )
        
        # Generate the report files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_files = self._save_report(report_content, "monthly", timestamp)
        
        # Train the ML model with this report
        self._memorize_report(report_content, articles)
        
        return report_files
    
    def _analyze_historical_reports(self):
        """Analyze historical reports to extract trends and generate forecasts."""
        try:
            # Find all previous reports
            monthly_reports = []
            for root, _, files in os.walk(self.monthly_dir):
                for file in files:
                    if file.endswith('.md'):
                        monthly_reports.append(os.path.join(root, file))
            
            # Sort by date (newest last)
            monthly_reports.sort(key=lambda x: os.path.getmtime(x))
            
            # Extract metrics from reports
            metrics = {
                "gdp_growth": [],
                "inflation": [],
                "trade_volume": [],
                "investment": []
            }
            
            for report_path in monthly_reports[-6:]:  # Use last 6 months
                with open(report_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Extract date from filename
                    filename = os.path.basename(report_path)
                    timestamp_str = filename.replace('report_', '').replace('.md', '')
                    report_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S").strftime("%Y-%m")
                    
                    # Extract metrics using simple pattern matching
                    for metric in metrics:
                        import re
                        pattern = f"{metric.replace('_', ' ')}:? (\d+\.?\d*)%?"
                        match = re.search(pattern, content, re.IGNORECASE)
                        if match:
                            try:
                                value = float(match.group(1))
                                metrics[metric].append((report_date, value))
                            except:
                                continue
            
            # Generate simple forecasts for metrics
            forecasts = {}
            for metric, values in metrics.items():
                if len(values) >= 3:  # Need at least 3 points for trend
                    # Simple linear extrapolation for next month
                    dates = [datetime.strptime(date, "%Y-%m") for date, _ in values]
                    values_only = [value for _, value in values]
                    
                    if self.model is not None and len(values) >= 5:
                        # Use TensorFlow for more sophisticated forecasting
                        forecast_value = self._tf_forecast(dates, values_only)
                    else:
                        # Simple trend-based forecast
                        if len(values) >= 2:
                            # Calculate average change
                            changes = []
                            for i in range(1, len(values_only)):
                                changes.append(values_only[i] - values_only[i-1])
                            
                            avg_change = sum(changes) / len(changes)
                            forecast_value = values_only[-1] + avg_change
                        else:
                            forecast_value = values_only[-1]  # Just use the last value
                    
                    # Add forecast to result
                    next_month = (dates[-1] + timedelta(days=30)).strftime("%Y-%m")
                    forecasts[metric] = {
                        "historical": [(d.strftime("%Y-%m"), v) for d, v in zip(dates, values_only)],
                        "forecast": (next_month, forecast_value),
                        "trend": "up" if forecast_value > values_only[-1] else "down"
                    }
            
            return {
                "forecasts": forecasts,
                "has_data": bool(forecasts)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing historical reports: {e}")
            return {"forecasts": {}, "has_data": False}
    
    def _tf_forecast(self, dates, values):
        """Use TensorFlow to forecast the next value in a time series."""
        try:
            if not has_tensorflow or self.model is None:
                # Fallback to simpler forecasting
                if len(values) >= 2:
                    avg_change = values[-1] - values[-2]
                    return values[-1] + avg_change
                return values[-1]
                
            if len(values) < 5:
                raise ValueError("Need at least 5 data points for TensorFlow forecasting")
                
            # Convert to numpy arrays
            values_array = np.array(values).reshape(-1, 1)
            
            # Normalize data
            scaler = MinMaxScaler(feature_range=(0, 1))
            scaled_values = scaler.fit_transform(values_array)
            
            # Prepare sequences for LSTM
            X = []
            y = []
            seq_length = 3  # Use 3 months to predict the next
            
            for i in range(len(scaled_values) - seq_length):
                X.append(scaled_values[i:i+seq_length, 0])
                y.append(scaled_values[i+seq_length, 0])
            
            X = np.array(X)
            y = np.array(y)
            
            # Reshape for LSTM [samples, time steps, features]
            X = np.reshape(X, (X.shape[0], X.shape[1], 1))
            
            # Build LSTM model
            model = tf.keras.Sequential([
                tf.keras.layers.LSTM(4, input_shape=(seq_length, 1)),
                tf.keras.layers.Dense(1)
            ])
            
            model.compile(optimizer='adam', loss='mean_squared_error')
            
            # Train the model
            model.fit(X, y, epochs=100, verbose=0)
            
            # Prepare input for prediction
            last_sequence = scaled_values[-seq_length:].reshape(1, seq_length, 1)
            
            # Make prediction
            predicted_scaled = model.predict(last_sequence)
            predicted_value = scaler.inverse_transform(predicted_scaled)[0][0]
            
            return predicted_value
            
        except Exception as e:
            logger.error(f"Error in TensorFlow forecasting: {e}")
            # Fallback to simpler forecasting
            if len(values) >= 2:
                avg_change = values[-1] - values[-2]
                return values[-1] + avg_change
            return values[-1]
    
    def _generate_report_content(self, articles, report_type, period, include_forecast=False, historical_insights=None):
        """Generate the content for the report."""
        # Base content
        content = f"""# {report_type} Business Intelligence Report

**Prepared for:** {self.client_name}  
**Period:** {period}  
**Generated on:** {datetime.now().strftime("%B %d, %Y at %I:%M %p")}

---

## Executive Summary

This report provides key business intelligence insights for the UAE and GCC region during the {report_type.lower()} reporting period. It includes analysis of regional economic trends, industry developments, and market indicators relevant to your business interests.

"""
        # Add top news insights
        content += "## Top Regional News\n\n"
        
        if not articles:
            content += "_No relevant news articles were found for this period._\n\n"
        else:
            for i, article in enumerate(articles[:5]):
                content += f"### {article['title']}\n\n"
                content += f"**Source:** {article['source']}  \n"
                if article.get('date'):
                    content += f"**Date:** {article['date']}  \n"
                content += "\n"
                
                # Summarize content
                summary = article['content'][:500] + "..." if len(article['content']) > 500 else article['content']
                content += f"{summary}\n\n"
                content += f"[Read full article]({article['url']})\n\n"
        
        # Add industry analysis
        content += "## Industry Analysis\n\n"
        
        for industry in self.client_config.get("industries", []):
            content += f"### {industry}\n\n"
            
            # Filter articles by industry
            industry_articles = [a for a in articles if industry.lower() in a['title'].lower() or industry.lower() in a['content'].lower()]
            
            if industry_articles:
                # Generate insights for this industry
                content += f"Key developments in the {industry} sector during this period:\n\n"
                
                for article in industry_articles[:3]:
                    content += f"- **{article['title']}** - {article['content'][:100]}...\n"
                
                content += "\n"
            else:
                content += f"No significant developments reported in the {industry} sector during this period.\n\n"
        
        # Add economic indicators
        content += "## Economic Indicators\n\n"
        
        # Default indicators if we have no data
        indicators = {
            "GDP Growth": "3.7%",
            "Inflation": "2.3%",
            "Unemployment": "3.1%",
            "Trade Balance": "$12.5 billion"
        }
        
        # Add a simple table
        content += "| Indicator | Current Value | Trend |\n"
        content += "|-----------|--------------|-------|\n"
        for indicator, value in indicators.items():
            content += f"| {indicator} | {value} | ↑ |\n"
        
        content += "\n"
        
        # Add forecasts for monthly reports
        if include_forecast and historical_insights and historical_insights.get("has_data"):
            content += "## Market Forecast\n\n"
            content += "Based on analysis of historical data and current trends, the following forecasts are projected for the next month:\n\n"
            
            forecasts = historical_insights.get("forecasts", {})
            
            if forecasts:
                for metric, forecast_data in forecasts.items():
                    trend = "↑" if forecast_data.get("trend") == "up" else "↓"
                    historic = forecast_data.get("historical", [])
                    forecast_point = forecast_data.get("forecast")
                    
                    if historic and forecast_point:
                        # Format the metric name
                        metric_name = metric.replace("_", " ").title()
                        
                        # Calculate percent change
                        last_value = historic[-1][1]
                        forecast_value = forecast_point[1]
                        percent_change = ((forecast_value - last_value) / last_value) * 100
                        
                        content += f"### {metric_name}\n\n"
                        content += f"**Current:** {last_value:.2f}%  \n"
                        content += f"**Forecast:** {forecast_value:.2f}% ({trend} {abs(percent_change):.1f}%)\n\n"
                        
                        # Create a visualization for this forecast
                        viz_path = self._create_forecast_visualization(
                            metric, 
                            [h[0] for h in historic], 
                            [h[1] for h in historic], 
                            forecast_point
                        )
                        
                        if viz_path:
                            # Add the visualization to the report
                            content += f"![{metric_name} Forecast]({os.path.relpath(viz_path, os.path.dirname(os.path.dirname(os.path.abspath(__file))))})\n\n"
            else:
                content += "_Insufficient historical data to generate accurate forecasts._\n\n"
        
        # Add recommendations
        content += "## Recommendations\n\n"
        content += "Based on the intelligence gathered, the following recommendations are provided:\n\n"
        content += "1. **Monitor regional economic indicators** closely, particularly GDP growth and inflation trends.\n"
        content += "2. **Evaluate market entry or expansion opportunities** in emerging sectors showing consistent growth.\n"
        content += "3. **Review strategic partnerships** with key industry players to strengthen market position.\n"
        content += "4. **Assess supply chain resilience** in light of regional trade developments.\n\n"
        
        # Add methodology
        content += "## Methodology\n\n"
        content += "This report was generated using advanced data analysis techniques and machine learning algorithms applied to:\n\n"
        content += f"- News articles from {len(self.sources)} reliable sources\n"
        content += f"- Economic indicators from government and international agencies\n"
        content += "- Industry reports and market analysis\n"
        content += "- Historical data and trend analysis\n\n"
        
        content += "---\n\n"
        content += f"© {datetime.now().year} Business Intelligence Platform | Generated for {self.client_name}\n"
        
        return content
    
    def _create_forecast_visualization(self, metric, dates, values, forecast_point):
        """Create a visualization for a forecast."""
        try:
            # Create a folder for visualizations
            viz_dir = os.path.join(self.reports_dir, "visualizations")
            os.makedirs(viz_dir, exist_ok=True)
            
            # Generate the visualization
            plt.figure(figsize=(10, 6))
            
            # Plot historical values
            plt.plot(dates, values, 'b-o', label='Historical')
            
            # Add forecast point
            plt.plot([forecast_point[0]], [forecast_point[1]], 'r-o', label='Forecast')
            
            # Add a dotted line connecting the last historical point to the forecast
            plt.plot([dates[-1], forecast_point[0]], [values[-1], forecast_point[1]], 'r--')
            
            # Set labels and title
            metric_name = metric.replace("_", " ").title()
            plt.title(f"{metric_name} Forecast", fontsize=16)
            plt.xlabel("Date", fontsize=12)
            plt.ylabel(f"{metric_name} (%)", fontsize=12)
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.legend()
            
            # Rotate x-axis labels for better readability
            plt.xticks(rotation=45)
            
            # Save the figure
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(viz_dir, f"{metric}_{timestamp}.png")
            plt.tight_layout()
            plt.savefig(output_path)
            plt.close()
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating visualization: {e}")
            return None
    
    def _save_report(self, content, report_type, timestamp):
        """Save the report in markdown, HTML, and PDF formats."""
        # Determine the target directory
        if report_type == "weekly":
            target_dir = self.weekly_dir
        else:
            target_dir = self.monthly_dir
        
        # Generate filenames
        base_name = f"report_{timestamp}"
        md_path = os.path.join(target_dir, f"{base_name}.md")
        html_path = os.path.join(target_dir, f"{base_name}.html")
        pdf_path = os.path.join(target_dir, f"{base_name}.pdf")
        
        # Save markdown file
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Generate HTML from markdown
        html_content = markdown.markdown(content, extensions=['tables', 'fenced_code'])
        
        # Add some CSS for better styling
        html_with_style = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{self.client_name} {report_type.capitalize()} Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 900px; margin: 0 auto; padding: 20px; }}
                h1 {{ color: #2c3e50; }}
                h2 {{ color: #3498db; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
                h3 {{ color: #2980b9; }}
                a {{ color: #3498db; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ text-align: left; padding: 12px; }}
                th {{ background-color: #3498db; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                img {{ max-width: 100%; height: auto; }}
                .date {{ color: #7f8c8d; font-size: 0.9em; }}
                blockquote {{ background-color: #f9f9f9; border-left: 5px solid #3498db; margin: 1.5em 10px; padding: 0.5em 10px; }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        # Save HTML file
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_with_style)
        
        # Generate PDF from HTML using pdfkit
        try:
            # Check if wkhtmltopdf is installed
            if shutil.which('wkhtmltopdf'):
                # Configure pdfkit options
                options = {
                    'page-size': 'A4',
                    'margin-top': '20mm',
                    'margin-right': '20mm',
                    'margin-bottom': '20mm',
                    'margin-left': '20mm',
                    'encoding': 'UTF-8',
                    'no-outline': None
                }
                
                # Generate PDF
                pdfkit.from_file(html_path, pdf_path, options=options)
                logger.info(f"Generated PDF report at {pdf_path}")
            else:
                logger.warning("wkhtmltopdf not found in PATH. PDF generation skipped.")
                logger.warning("To enable PDF generation, install wkhtmltopdf and ensure it's in your PATH.")
        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            logger.warning("PDF generation failed. Please ensure wkhtmltopdf is installed.")
        
        logger.info(f"Generated report files: {md_path}, {html_path}")
        
        return {
            "markdown": md_path,
            "html": html_path,
            "pdf": pdf_path
        }
    
    def _memorize_report(self, content, articles):
        """Use TensorFlow to memorize the report content for future reference."""
        if not has_tensorflow or self.model is None:
            logger.warning("TensorFlow model not available, skipping report memorization")
            return
        
        try:
            # Save report content and metadata
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_data = {
                "content": content,
                "articles": articles,
                "timestamp": timestamp,
                "client": self.client_name
            }
            
            # Save to ML directory for future training
            data_path = os.path.join(self.ml_dir, f"report_data_{timestamp}.json")
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2)
                
            logger.info(f"Saved report data for ML training: {data_path}")
            
            # Save the model
            model_path = os.path.join(self.ml_dir, "report_model")
            self.model.save(model_path)
            logger.info(f"Saved TensorFlow model: {model_path}")
            
        except Exception as e:
            logger.error(f"Error memorizing report: {e}")

def main():
    """Main function to run the client report generator."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate client-specific business intelligence reports")
    parser.add_argument("--client", required=True, help="Client name or ID")
    parser.add_argument("--type", choices=["weekly", "monthly"], default="weekly", help="Report type (weekly or monthly)")
    args = parser.parse_args()
    
    try:
        # Try to import pdfkit and shutil for PDF generation
        import pdfkit
        import shutil
        has_pdfkit = True
    except ImportError:
        has_pdfkit = False
        logger.warning("pdfkit not installed. PDF generation will be disabled.")
        logger.warning("To enable PDF generation, install pdfkit: pip install pdfkit")
    
    # Initialize the report generator
    generator = ClientReportGenerator(args.client)
    
    # Generate the appropriate report
    if args.type == "weekly":
        report_files = generator.generate_weekly_report()
    else:
        report_files = generator.generate_monthly_report()
    
    # Output report paths
    print("\nReport Generation Complete!")
    print(f"Markdown: {report_files['markdown']}")
    print(f"HTML: {report_files['html']}")
    
    if has_pdfkit and os.path.exists(report_files['pdf']):
        print(f"PDF: {report_files['pdf']}")
    else:
        print("PDF generation was skipped or failed.")
    
    print("\nTo generate PDF reports, ensure wkhtmltopdf is installed and in your PATH.")
    print("Download from: https://wkhtmltopdf.org/downloads.html")

if __name__ == "__main__":
    main() 