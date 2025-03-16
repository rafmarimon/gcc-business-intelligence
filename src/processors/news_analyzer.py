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
                    return json.load(f)
            
            # Find the most recent JSON file in the data directory
            json_files = glob.glob(os.path.join(self.data_dir, 'news_data_*.json'))
            if not json_files:
                logger.warning("No news data files found.")
                return []
            
            latest_file = max(json_files, key=os.path.getctime)
            logger.info(f"Loading news data from {latest_file}")
            
            with open(latest_file, 'r') as f:
                return json.load(f)
        
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
        
        # Basic statistics
        stats = {
            'total_articles': len(df),
            'sources': df['source_name'].nunique(),
            'countries': df['country'].nunique(),
            'date_range': {
                'earliest': df['collected_at'].min() if 'collected_at' in df else "Unknown",
                'latest': df['collected_at'].max() if 'collected_at' in df else "Unknown"
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
    
    def _create_keyword_chart(self, keyword_counts, max_keywords=15):
        """Create a bar chart of top keywords."""
        try:
            # Sort and slice
            sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
            top_keywords = sorted_keywords[:max_keywords]
            
            # Prepare data
            keywords = [item[0] for item in top_keywords]
            counts = [item[1] for item in top_keywords]
            
            # Create the plot
            plt.figure(figsize=(12, 6))
            sns.barplot(x=counts, y=keywords)
            plt.title('Top Keywords Mentioned in Business News')
            plt.xlabel('Weighted Frequency')
            plt.tight_layout()
            
            # Save the figure
            chart_path = os.path.join(self.reports_dir, 'keyword_analysis.png')
            plt.savefig(chart_path)
            plt.close()
            
            logger.info(f"Keyword analysis chart saved to {chart_path}")
        except Exception as e:
            logger.error(f"Error creating keyword chart: {e}")
    
    def _generate_system_prompt(self):
        """Generate the system prompt for the LLM."""
        return """
        You are a business intelligence analyst specializing in UAE and GCC markets. Your task is to create a 
        professional daily business intelligence report in the style of Global Possibilities.

        The report should follow this structure:
        1. Title: "Global Possibilities - Daily Business Intelligence Report: [CURRENT_DATE]"
        2. Three key industry updates, each formatted as follows:
           - Clear headline/title
           - Brief summary of the update (1-2 paragraphs)
           - Bullet points for key details
           - "Key Takeaway" section highlighted at the end of each update

        Maintain a formal but accessible business tone. Keep the language concise, clear, and professional.
        Include relevant business insights where applicable. Focus on the most significant developments.

        If available, include one section specifically about US-UAE business or diplomatic relations.
        
        Use markdown formatting for the report, with proper section headers, bullet points, and emphasis where appropriate.
        """

    def _generate_user_prompt(self, articles, stats):
        """Generate the user prompt for the LLM based on the articles and stats."""
        article_summaries = []
        
        for i, article in enumerate(articles[:20]):  # Limit to 20 articles to keep within token limits
            title = article.get('headline', 'No title')
            source = article.get('source_name', 'Unknown source')
            summary = article.get('summary', 'No summary available')
            url = article.get('url', '')
            published_at = article.get('published_at', 'Unknown date')
            
            article_summary = f"{i+1}. \"{title}\" ({source}, {published_at})\n{summary}\nSource: {url}\n"
            article_summaries.append(article_summary)
        
        article_text = "\n".join(article_summaries)
        
        # Get current date in readable format
        current_date = datetime.now().strftime("%B %d, %Y")
        
        return f"""
        Today's Date: {current_date}

        Based on the following news articles from UAE/GCC region, create a daily business intelligence report.
        Focus on the 3 most significant developments that business leaders should know about.

        NEWS ARTICLES:
        {article_text}

        STATISTICS:
        - Total articles: {stats.get('total_articles', 0)}
        - Top sources: {', '.join(stats.get('top_sources', [])[:3])}
        - Top topics: {', '.join(stats.get('top_keywords', [])[:5])}

        Follow the structure outlined in your instructions. Be concise yet comprehensive. 
        Focus on the business implications of each development.
        """

    def generate_report_with_llm(self, articles, stats):
        """Generate a report using OpenAI's language model."""
        if not articles or not self.api_key:
            return self._generate_fallback_report(articles, stats)
        
        system_prompt = self._generate_system_prompt()
        user_prompt = self._generate_user_prompt(articles, stats)
        
        try:
            logger.info("Generating report using OpenAI API with exponential backoff.")
            response = self.openai_client.create_chat_completion(
                model="gpt-4o",  # Using the latest GPT model for best results
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            logger.info("Report generated successfully.")
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating report with OpenAI: {e}")
            return self._generate_fallback_report(articles, stats)

    def _generate_fallback_report(self, articles, stats):
        """Generate a fallback report when OpenAI is unavailable."""
        current_date = datetime.now().strftime("%B %d, %Y")
        
        report = f"""# Global Possibilities - Daily Business Intelligence Report: {current_date}

## Executive Summary
This is an automated fallback report generated due to API limitations. 
We've collected {stats.get('total_articles', 0)} news articles from various sources in the UAE/GCC region.

"""
        
        # Add top news articles as updates
        for i, article in enumerate(articles[:3]):
            if i >= 3:  # Limit to 3 key updates
                break
                
            title = article.get('headline', 'Business Update')
            source = article.get('source_name', 'Unknown source')
            summary = article.get('summary', 'No details available')
            
            report += f"""## Update {i+1}: {title}

{summary}

### Key Details:
* Reported by {source}
* Published on {article.get('published_at', 'Unknown date')}
* Category: {article.get('category', 'General')}

**Key Takeaway:** This intelligence requires further analysis as it was generated in fallback mode.

"""
        
        # Add footer
        report += """

---

*This is an automated report by Global Possibilities. For more comprehensive analysis, please ensure
your OpenAI API key has sufficient quota.*
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
    # Test the analyzer
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