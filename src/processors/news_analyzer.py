import os
import json
import logging
import pandas as pd
from datetime import datetime
import glob
from dotenv import load_dotenv
from openai import OpenAI
from src.utils.openai_utils import OpenAIClient
from collections import Counter
import re
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("NewsAnalyzer")

class GCCBusinessNewsAnalyzer:
    """
    Analyzes collected news from UAE/GCC sources and generates reports using OpenAI.
    """
    def __init__(self, data_dir='data', reports_dir='reports', config_path='config/news_sources.json'):
        """Initialize the news analyzer."""
        self.data_dir = data_dir
        self.reports_dir = reports_dir
        self.config_path = config_path
        
        # Create reports directory if it doesn't exist
        os.makedirs(self.reports_dir, exist_ok=True)
        
        # Set up OpenAI
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            logger.warning("OpenAI API key not found in environment variables. LLM features will not work.")
        else:
            # Set up our OpenAI client with exponential backoff
            self.openai_client = OpenAIClient(self.api_key)
        
        # Load keywords from config
        self.keywords = self._load_keywords()
    
    def _load_keywords(self):
        """Load relevant keywords from the configuration file."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                return config.get('keywords', [])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading keywords from config: {e}")
            return []
    
    def load_news_data(self, specific_file=None):
        """Load the most recent news data or a specific file."""
        try:
            if specific_file and os.path.exists(specific_file):
                with open(specific_file, 'r') as f:
                    articles = json.load(f)
            else:
                # Find the most recent JSON file in the data directory
                json_files = glob.glob(os.path.join(self.data_dir, 'news_data_*.json'))
                if not json_files:
                    logger.warning("No news data files found.")
                    return []
                
                # Sort files by creation time (newest first)
                latest_file = max(json_files, key=os.path.getctime)
                logger.info(f"Loading news data from {latest_file}")
                
                with open(latest_file, 'r') as f:
                    articles = json.load(f)
            
            # Sort articles by published_at date (newest first)
            try:
                articles = sorted(
                    articles,
                    key=lambda x: x.get('published_at', x.get('collected_at', '')),
                    reverse=True
                )
                
                # Filter out articles without a headline or link
                articles = [a for a in articles if a.get('headline') and a.get('link')]
                
                # Log the date range in the data
                if articles:
                    newest = articles[0].get('published_at', articles[0].get('collected_at', 'Unknown'))
                    oldest = articles[-1].get('published_at', articles[-1].get('collected_at', 'Unknown'))
                    logger.info(f"Loaded {len(articles)} articles from {oldest} to {newest}")
                
                return articles
            except Exception as e:
                logger.error(f"Error sorting articles: {e}")
                return articles
        
        except Exception as e:
            logger.error(f"Error loading news data: {e}")
            return []
    
    def analyze_news(self, articles):
        """Analyze news articles to extract insights."""
        if not articles:
            logger.warning("No articles to analyze.")
            return {}
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(articles)
        
        # Add proper datetime fields for analysis if they don't exist
        if 'published_at' in df.columns:
            # Use published_at for date analysis
            date_field = 'published_at'
        else:
            # Fall back to collected_at if published_at doesn't exist
            date_field = 'collected_at'
        
        # Basic statistics
        stats = {
            'total_articles': len(df),
            'sources': df['source_name'].nunique(),
            'countries': df['country'].nunique(),
            'date_range': {
                'earliest': df[date_field].min() if date_field in df else "Unknown",
                'latest': df[date_field].max() if date_field in df else "Unknown"
            },
            'source_distribution': df['source_name'].value_counts().to_dict(),
            'country_distribution': df['country'].value_counts().to_dict()
        }
        
        # Extract key phrases and trending topics
        headlines = " ".join(df['headline'].tolist())
        summaries = " ".join([s for s in df['summary'].tolist() if s])
        
        # Count keyword mentions
        keyword_counts = {}
        for keyword in self.keywords:
            # Count in headlines (weighted more heavily)
            headline_count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', headlines, re.IGNORECASE)) * 2
            
            # Count in summaries
            summary_count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', summaries, re.IGNORECASE))
            
            # Total weighted count
            keyword_counts[keyword] = headline_count + summary_count
        
        # Filter out zero counts
        keyword_counts = {k: v for k, v in keyword_counts.items() if v > 0}
        
        # Add to results
        stats['keyword_analysis'] = keyword_counts
        
        # Create a simple visualization of top keywords
        if keyword_counts:
            self._create_keyword_chart(keyword_counts)
            stats['keyword_chart_path'] = os.path.join(self.reports_dir, 'keyword_analysis.png')
        
        return stats
    
    def _create_keyword_chart(self, keyword_counts):
        """Create a visualization of top keywords."""
        try:
            # Sort by count and take top 15
            top_keywords = dict(sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:15])
            
            plt.figure(figsize=(10, 6))
            plt.bar(top_keywords.keys(), top_keywords.values(), color='skyblue')
            plt.xticks(rotation=45, ha='right')
            plt.title('Top Keywords in UAE/GCC Business News')
            plt.xlabel('Keyword')
            plt.ylabel('Weighted Mentions')
            plt.tight_layout()
            
            # Save the figure
            output_path = os.path.join(self.reports_dir, 'keyword_analysis.png')
            plt.savefig(output_path)
            plt.close()
            
            logger.info(f"Keyword chart saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Error creating keyword chart: {e}")
    
    def _generate_system_prompt(self):
        """Generate system prompt for report generation."""
        return """
        You are an expert business intelligence analyst specializing in UAE and GCC markets with a focus
        on US-UAE relations. You create comprehensive and insightful reports for business professionals.
        
        Your report should:
        1. Be well-structured with clear sections and subsections
        2. Focus on business trends, opportunities, and strategic insights
        3. Highlight implications for US-UAE business relations
        4. Include actionable intelligence for decision-makers
        5. Be professional but engaging in tone
        6. Include a mix of high-level overview and specific details
        
        Structure your report with these sections:
        - Executive Summary (brief overview of key findings)
        - Market Analysis (key trends and developments)
        - US-UAE Relations (recent developments and opportunities)
        - Sector Highlights (key sectors showing activity)
        - Strategic Opportunities (potential business opportunities)
        - Action Points (recommended next steps for businesses)
        """
    
    def _generate_user_prompt(self, articles, stats):
        """Generate user prompt for the OpenAI API."""
        prompt = f"""
        Generate a comprehensive business intelligence report based on the following news data collected on {datetime.now().strftime('%B %d, %Y')}.
        
        DATA OVERVIEW:
        - Total articles analyzed: {stats.get('total_articles', 0)}
        - Sources: {stats.get('sources', 0)} different news outlets
        - Countries covered: {stats.get('countries', 0)}
        - Date range: {stats.get('date_range', {}).get('earliest', 'Unknown')} to {stats.get('date_range', {}).get('latest', 'Unknown')}
        
        TOP KEYWORDS (with mention count):
        """
        
        # Add top keywords
        if 'keyword_analysis' in stats and stats['keyword_analysis']:
            sorted_keywords = sorted(stats['keyword_analysis'].items(), key=lambda x: x[1], reverse=True)
            for keyword, count in sorted_keywords[:10]:  # Top 10 keywords
                prompt += f"- {keyword}: {count}\n"
        else:
            prompt += "No significant keywords detected.\n"
        
        # Add top news articles
        prompt += "\nKEY ARTICLES:\n"
        for i, article in enumerate(articles[:15]):  # Top 15 articles
            if i >= 15:
                break
                
            headline = article.get('headline', '')
            source = article.get('source_name', '')
            summary = article.get('summary', '')
            date = article.get('published_at', article.get('collected_at', ''))
            
            prompt += f"""
            Article {i+1}:
            - Headline: {headline}
            - Source: {source}
            - Date: {date}
            - Summary: {summary}
            """
        
        prompt += """
        REPORT REQUIREMENTS:
        - The report should be in professional Markdown format
        - Include a detailed executive summary
        - Focus on the most significant business trends and opportunities
        - Highlight implications for US-UAE business relations
        - Organize insights by sector where possible
        - Provide actionable intelligence for business leaders
        - Generate appropriate section headings and structure
        """
        
        return prompt
    
    def generate_report_with_llm(self, articles, stats):
        """Generate a report using OpenAI's language model."""
        if not articles:
            return self._generate_fallback_report(articles, stats, "No articles available")
            
        if not self.api_key:
            return self._generate_fallback_report(articles, stats, "OpenAI API key not configured")
        
        system_prompt = self._generate_system_prompt()
        user_prompt = self._generate_user_prompt(articles, stats)
        
        # Try with GPT-4o first
        try:
            logger.info("Generating report using GPT-4o model with exponential backoff.")
            response = self.openai_client.create_chat_completion(
                model="gpt-4o",  # Using the latest GPT model for best results
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            logger.info("Report generated successfully with GPT-4o.")
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating report with GPT-4o: {e}")
            
            # Fallback to GPT-3.5-Turbo if GPT-4 fails
            try:
                logger.info("Falling back to GPT-3.5-Turbo model.")
                response = self.openai_client.create_chat_completion(
                    model="gpt-3.5-turbo",  # Fallback to GPT-3.5-Turbo
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3
                )
                
                logger.info("Report generated successfully with GPT-3.5-Turbo.")
                return response.choices[0].message.content
            except Exception as e2:
                logger.error(f"Error generating report with GPT-3.5-Turbo: {e2}")
                return self._generate_fallback_report(articles, stats, f"OpenAI API errors: {e}, {e2}")

    def _generate_fallback_report(self, articles, stats, error_reason="API limitations"):
        """Generate a more comprehensive fallback report when OpenAI is unavailable."""
        current_date = datetime.now().strftime("%B %d, %Y")
        
        report = f"""# Global Possibilities - Daily Business Intelligence Report: {current_date}

## Executive Summary
This is an automated report generated due to {error_reason}. 
We've collected {stats.get('total_articles', 0)} news articles from various sources in the UAE/GCC region.

### Data Overview
- **Total Articles**: {stats.get('total_articles', 0)}
- **Sources**: {stats.get('sources', 0)} different news outlets
- **Countries covered**: {stats.get('countries', 0)}
- **Date range**: From {stats.get('date_range', {}).get('earliest', 'Unknown')} to {stats.get('date_range', {}).get('latest', 'Unknown')}

"""
        
        # Add source distribution if available
        if 'source_distribution' in stats and stats['source_distribution']:
            report += "### Source Distribution\n"
            for source, count in stats['source_distribution'].items():
                report += f"- **{source}**: {count} articles\n"
            report += "\n"
        
        # Add keyword mentions if available
        if 'keyword_analysis' in stats and stats['keyword_analysis']:
            report += "### Top Keywords\n"
            sorted_keywords = sorted(stats['keyword_analysis'].items(), key=lambda x: x[1], reverse=True)
            for keyword, count in sorted_keywords[:10]:  # Top 10 keywords
                report += f"- **{keyword}**: {count} mentions\n"
            report += "\n"
            
        report += "## Key Updates\n"
        
        # Add top news articles as updates
        if articles:
            for i, article in enumerate(articles[:5]):  # Increased from 3 to 5 articles
                if i >= 5:
                    break
                    
                title = article.get('headline', 'Business Update')
                source = article.get('source_name', 'Unknown source')
                summary = article.get('summary', 'No details available')
                link = article.get('link', '#')
                
                report += f"""### Update {i+1}: {title}

{summary}

**Key Details:**
* Reported by {source}
* Published on {article.get('published_at', article.get('collected_at', 'Unknown date'))}
* Category: {article.get('category', 'General')}
* [Read full article]({link})

"""
        else:
            report += "No articles available for updates.\n"
            
        # Add US-UAE relations section
        report += """
## US-UAE Relations Overview
The United States and United Arab Emirates continue to maintain strong diplomatic and economic ties. 
Key areas of collaboration include trade, investment, security, and cultural exchange.

## Recent Economic Indicators
- UAE non-oil sector remains resilient
- Technology investments continue to grow
- Regional trade relationships are expanding

## Next Steps
For a more detailed analysis, please ensure the OpenAI API key is functioning correctly and run the report generation again.

"""
        
        # Add footer
        report += """

---

*This is an automated report by Global Possibilities. This fallback report contains basic information extracted directly from the source data without AI-enhanced analysis.*
"""
        
        return report
    
    def generate_daily_report(self, articles=None):
        """Generate a comprehensive daily report on UAE/GCC business news."""
        try:
            # Load articles if not provided
            if articles is None:
                articles = self.load_news_data()
            
            if not articles:
                logger.warning("No articles available for report generation.")
                return None, "No articles available for report generation."
            
            # Analyze the news
            stats = self.analyze_news(articles)
            
            # Generate the report using OpenAI
            report_text = self.generate_report_with_llm(articles, stats)
            
            # Create a timestamp for the report file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_filename = f"gcc_business_report_{timestamp}.md"
            report_path = os.path.join(self.reports_dir, report_filename)
            
            # Save the report to file
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            
            logger.info(f"Daily report saved to {report_path}")
            
            return report_path, report_text
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            return None, f"Error generating report: {str(e)}"

if __name__ == "__main__":
    # Simple test when run directly
    analyzer = GCCBusinessNewsAnalyzer()
    articles = analyzer.load_news_data()
    if articles:
        report_path, report_text = analyzer.generate_daily_report(articles)
        if report_path:
            print(f"Report generated and saved to {report_path}")
            print("\nPreview:")
            print(report_text[:500] + "...")
        else:
            print("Failed to generate report.")
    else:
        print("No articles available for analysis.") 