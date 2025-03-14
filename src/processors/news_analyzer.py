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
    
    def generate_report_with_llm(self, articles, stats):
        """Generate a comprehensive report using OpenAI's LLM."""
        if not self.api_key:
            logger.error("Cannot generate report: OpenAI API key not found.")
            return self._generate_fallback_report(articles, stats)
        
        try:
            # Prepare headline data for the LLM (limit to recent top headlines to avoid token limits)
            sorted_articles = sorted(articles, key=lambda x: x.get('collected_at', ''), reverse=True)
            top_headlines = [
                {
                    'headline': a['headline'],
                    'source': a['source_name'],
                    'summary': a['summary'][:150] + '...' if len(a['summary']) > 150 else a['summary'],
                    'link': a['link'],
                    'date': a['date']
                }
                for a in sorted_articles[:20]  # Limit to top 20 most recent articles
            ]
            
            # Prepare a summary of the stats for the LLM
            stats_summary = {
                'total_articles': stats['total_articles'],
                'source_distribution': stats['source_distribution'],
                'countries': list(stats['country_distribution'].keys()),
                'top_keywords': dict(sorted(stats['keyword_analysis'].items(), key=lambda x: x[1], reverse=True)[:10])
            }
            
            # Create a system prompt with instructions
            system_prompt = """
            You are an expert business analyst focused on the UAE and GCC region. 
            Your task is to generate a professional weekly business intelligence report based on the news articles provided.
            
            The report should:
            1. Begin with an executive summary of the most significant business developments in the UAE/GCC region
            2. Highlight key trends, investments, policy changes, and market movements
            3. Analyze the implications of these developments for businesses operating in or looking to enter the region
            4. Be organized by industry sectors (e.g., Finance, Real Estate, Energy, Technology, etc.)
            5. Include a "Opportunities & Outlook" section with actionable insights
            6. Use a professional, concise and clear tone appropriate for business executives
            7. Include bullet points for easy scanning where appropriate
            8. Be around 1000-1500 words in length
            
            Format the report nicely with appropriate Markdown formatting, including headers, sub-headers, bullet points, and emphasis where needed.
            """
            
            # Create a user prompt with the data
            user_prompt = f"""
            Here is the data for your weekly UAE/GCC business intelligence report:
            
            HEADLINES:
            {json.dumps(top_headlines, indent=2)}
            
            STATISTICS:
            {json.dumps(stats_summary, indent=2)}
            
            Please generate a complete weekly business intelligence report based on this data.
            """
            
            # Call the OpenAI API with our client that has exponential backoff
            logger.info("Generating report using OpenAI API with exponential backoff...")
            
            response = self.openai_client.create_chat_completion(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=4000,
                temperature=0.5
            )
            
            # Extract the report text
            report_text = response.choices[0].message.content.strip()
            logger.info("Report generated successfully.")
            
            return report_text
            
        except Exception as e:
            logger.error(f"Error generating report with LLM: {e}")
            # Use fallback report when OpenAI fails
            return self._generate_fallback_report(articles, stats)
    
    def _generate_fallback_report(self, articles, stats):
        """Generate a fallback report when OpenAI is unavailable."""
        logger.info("Generating fallback report without OpenAI...")
        
        # Create a basic report template
        report = f"""# UAE/GCC Business Intelligence Weekly Report
        
## Executive Summary

This is a sample report generated as a fallback due to OpenAI API limitations.
The system collected {stats.get('total_articles', 0)} articles from {stats.get('sources', 0)} different sources.

## Top Headlines

"""
        
        # Add top headlines
        sorted_articles = sorted(articles, key=lambda x: x.get('collected_at', ''), reverse=True)
        for i, article in enumerate(sorted_articles[:10]):
            report += f"* **{article.get('headline', 'No headline')}** ({article.get('source_name', 'Unknown source')})\n"
            report += f"  * {article.get('summary', 'No summary available')[:150]}...\n\n"
        
        # Add statistics section
        report += """
## Market Statistics

"""
        
        # Add keyword analysis if available
        if 'keyword_analysis' in stats:
            report += "### Key Topics\n\n"
            top_keywords = sorted(stats['keyword_analysis'].items(), key=lambda x: x[1], reverse=True)[:15]
            
            for keyword, count in top_keywords:
                report += f"* **{keyword}**: {count} mentions\n"
        
        # Add country distribution if available
        if 'country_distribution' in stats:
            report += "\n### Geographic Focus\n\n"
            for country, count in stats['country_distribution'].items():
                report += f"* **{country}**: {count} articles\n"
        
        # Add closing section
        report += """

## Opportunities & Outlook

This report has been generated as a fallback due to OpenAI API limitations. In a production environment,
this section would contain AI-generated insights about market opportunities and future outlook.

---

*This is an automated report by Global Possibilities. For more comprehensive analysis, please ensure
your OpenAI API key has sufficient quota.*
"""
        
        return report
    
    def generate_weekly_report(self, articles=None):
        """Generate a comprehensive weekly report on UAE/GCC business news."""
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
            
            logger.info(f"Weekly report saved to {report_path}")
            
            return report_path, report_text
            
        except Exception as e:
            logger.error(f"Error generating weekly report: {e}")
            return None, f"Error generating report: {str(e)}"


if __name__ == "__main__":
    # Test the analyzer
    analyzer = GCCBusinessNewsAnalyzer()
    articles = analyzer.load_news_data()
    if articles:
        report_path, report_text = analyzer.generate_weekly_report(articles)
        if report_path:
            print(f"Report generated and saved to {report_path}")
            print("\nPreview:")
            print(report_text[:500] + "...")
        else:
            print("Failed to generate report.")
    else:
        print("No articles available for analysis.") 