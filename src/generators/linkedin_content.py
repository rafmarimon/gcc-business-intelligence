import os
import json
import logging
import glob
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from src.utils.openai_utils import OpenAIClient
import re
from pathlib import Path

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LinkedInGenerator")

class LinkedInContentGenerator:
    """
    Generates LinkedIn content based on the latest business intelligence reports.
    """
    def __init__(self, reports_dir='reports', content_dir='content', data_dir='data'):
        """Initialize the LinkedIn content generator."""
        self.reports_dir = reports_dir
        self.content_dir = content_dir
        self.data_dir = data_dir
        
        # Create content directory if it doesn't exist
        os.makedirs(self.content_dir, exist_ok=True)
        
        # Set up OpenAI
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            logger.warning("OpenAI API key not found in environment variables. LLM features will not work.")
        else:
            # Set up our OpenAI client with exponential backoff
            self.openai_client = OpenAIClient(self.api_key)
    
    def get_latest_report(self):
        """Get the most recent business intelligence report."""
        try:
            report_files = glob.glob(os.path.join(self.reports_dir, 'gcc_business_report_*.md'))
            if not report_files:
                logger.warning("No report files found.")
                return None
            
            latest_report = max(report_files, key=os.path.getctime)
            logger.info(f"Found latest report: {latest_report}")
            
            with open(latest_report, 'r', encoding='utf-8') as f:
                report_content = f.read()
            
            return report_content
        
        except Exception as e:
            logger.error(f"Error getting latest report: {e}")
            return None
    
    def get_latest_news_data(self):
        """Get the most recent news data to supplement the report."""
        try:
            json_files = glob.glob(os.path.join(self.data_dir, 'news_data_*.json'))
            if not json_files:
                logger.warning("No news data files found.")
                return []
            
            latest_file = max(json_files, key=os.path.getctime)
            
            with open(latest_file, 'r') as f:
                articles = json.load(f)
            
            # Get the most recent 10 articles
            sorted_articles = sorted(articles, key=lambda x: x.get('collected_at', ''), reverse=True)
            return sorted_articles[:10]
        
        except Exception as e:
            logger.error(f"Error getting latest news data: {e}")
            return []
    
    def extract_top_insights(self, report_content):
        """Extract the top insights from the report for LinkedIn content."""
        if not report_content:
            return []
        
        # Create a system prompt to extract insights
        system_prompt = """
        You are a professional content analyst. Extract the top 5 most significant business insights or developments 
        from the given business intelligence report. These should be the most newsworthy, impactful, 
        or strategically important pieces of information that would be valuable for LinkedIn audience.
        
        For each insight, provide:
        1. A brief title (5-8 words)
        2. The key fact or development (1-2 sentences)
        3. Why it matters to businesses (1 sentence)
        
        Format your response as a JSON array where each element is an object with keys: "title", "fact", "why_it_matters".
        """
        
        user_prompt = f"""
        Extract the top 5 business insights from this UAE/GCC business intelligence report:
        
        {report_content[:10000]}  # Limit to avoid token limits
        
        Please respond with only the JSON array. No preamble or explanation needed.
        """
        
        try:
            if not self.api_key:
                logger.error("Cannot extract insights: OpenAI API key not found.")
                return self._generate_fallback_insights(report_content)
                
            logger.info("Extracting top insights using OpenAI API with exponential backoff...")
            response = self.openai_client.create_chat_completion(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.4,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content.strip()
            
            # Extract JSON content
            try:
                # Use regex to find JSON pattern if needed
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    json_content = json_match.group(0)
                    insights = json.loads(json_content)
                    return insights.get('insights', []) if isinstance(insights, dict) else insights
                else:
                    insights = json.loads(content)
                    return insights.get('insights', []) if isinstance(insights, dict) else insights
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing insights JSON: {e}")
                logger.error(f"Raw content: {content[:200]}...")
                return self._generate_fallback_insights(report_content)
            
        except Exception as e:
            logger.error(f"Error extracting insights with OpenAI: {e}")
            return self._generate_fallback_insights(report_content)
    
    def _generate_fallback_insights(self, report_content):
        """Generate fallback insights when OpenAI API is unavailable."""
        logger.info("Generating fallback insights without OpenAI...")
        
        # Create some sample insights based on common business topics in GCC
        fallback_insights = [
            {
                "title": "UAE Digital Economy Growth",
                "fact": "The UAE's digital economy is experiencing rapid growth, with increased investment in tech startups and digital infrastructure.",
                "why_it_matters": "This presents opportunities for businesses in technology, fintech, and digital transformation services."
            },
            {
                "title": "Saudi Vision 2030 Progress",
                "fact": "Saudi Arabia continues to advance its Vision 2030 goals with new megaprojects and economic diversification initiatives.",
                "why_it_matters": "Companies aligned with Vision 2030 priorities may find significant growth opportunities in the kingdom."
            },
            {
                "title": "Sustainable Energy Investments",
                "fact": "GCC countries are increasing investments in renewable energy projects, particularly solar and green hydrogen.",
                "why_it_matters": "The shift presents both challenges for traditional energy businesses and opportunities in the green economy."
            },
            {
                "title": "Regional E-commerce Expansion",
                "fact": "E-commerce platforms are seeing rapid adoption across the GCC, with local players competing against global giants.",
                "why_it_matters": "Businesses should prioritize their digital retail strategy to capture the growing online consumer base."
            },
            {
                "title": "Financial Sector Transformation",
                "fact": "Banking and financial services in the GCC are undergoing digital transformation, with increased focus on fintech integration.",
                "why_it_matters": "This evolution is changing how businesses access financial services and manage transactions in the region."
            }
        ]
        
        return fallback_insights
    
    def generate_linkedin_post(self, insight, articles=None):
        """Generate a LinkedIn post for a particular insight."""
        if not insight:
            return None
        
        # Create context from articles if available
        articles_context = ""
        if articles:
            articles_sample = articles[:5]  # Use up to 5 articles for context
            articles_text = []
            for article in articles_sample:
                headline = article.get('headline', '')
                source = article.get('source_name', '')
                articles_text.append(f"- {headline} ({source})")
            
            if articles_text:
                articles_context = "Recent articles:\n" + "\n".join(articles_text)
        
        # Create a system prompt for LinkedIn post generation
        system_prompt = """
        You are a professional business content writer for LinkedIn. Your task is to create an engaging, 
        informative, and professional LinkedIn post based on a business insight from the UAE/GCC region.
        
        The post should:
        1. Start with a compelling hook or question to grab attention
        2. Present the key information clearly and concisely
        3. Explain why this development matters to businesses
        4. Include a call to action or thought-provoking conclusion
        5. End with 4-6 relevant hashtags (including some regional ones like #UAE #GCC #Dubai)
        6. Be around 150-250 words (1300-1800 characters)
        7. Use professional language suitable for business executives
        8. Include appropriate emoji for visual engagement (2-4 total)
        
        The tone should be: informative, insightful, and professionally conversational.
        """
        
        user_prompt = f"""
        Create a LinkedIn post based on this business insight from the UAE/GCC region:
        
        TITLE: {insight.get('title', '')}
        
        KEY FACT: {insight.get('fact', '')}
        
        WHY IT MATTERS: {insight.get('why_it_matters', '')}
        
        {articles_context}
        
        Please create an engaging and professional LinkedIn post that will resonate with business leaders.
        """
        
        try:
            if not self.api_key:
                logger.error("Cannot generate LinkedIn post: OpenAI API key not found.")
                return self._generate_fallback_post(insight)
                
            logger.info(f"Generating LinkedIn post for insight: {insight.get('title', '')}")
            response = self.openai_client.create_chat_completion(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            post_content = response.choices[0].message.content.strip()
            
            return {
                'title': insight.get('title', ''),
                'content': post_content,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating LinkedIn post with OpenAI: {e}")
            return self._generate_fallback_post(insight)
    
    def _generate_fallback_post(self, insight):
        """Generate a fallback LinkedIn post when OpenAI API is unavailable."""
        logger.info(f"Generating fallback LinkedIn post for: {insight.get('title', '')}")
        
        title = insight.get('title', 'Business Insight')
        fact = insight.get('fact', '')
        why_it_matters = insight.get('why_it_matters', '')
        
        # Create a template-based post
        post_content = f"""📊 **{title}** 📊

Did you know? {fact}

Why this matters: {why_it_matters}

At Global Possibilities, we help businesses navigate the dynamic GCC market landscape and capitalize on emerging opportunities.

What's your take on this development? Share your thoughts in the comments below!

#Business #GCCEconomy #UAE #SaudiArabia #BusinessIntelligence #GlobalPossibilities"""
        
        return {
            'title': title,
            'content': post_content,
            'generated_at': datetime.now().isoformat()
        }
    
    def generate_linkedin_posts(self):
        """Generate a set of LinkedIn posts based on the latest report."""
        # Get the latest report content
        report_content = self.get_latest_report()
        if not report_content:
            logger.warning("No report content available for LinkedIn post generation.")
            return []
        
        # Get supplementary news data
        latest_articles = self.get_latest_news_data()
        
        # Extract insights from the report
        insights = self.extract_top_insights(report_content)
        if not insights:
            logger.warning("No insights extracted from report.")
            return []
        
        # Generate posts for each insight
        posts = []
        for insight in insights:
            post = self.generate_linkedin_post(insight, latest_articles)
            if post:
                posts.append(post)
        
        if not posts:
            logger.warning("No LinkedIn posts were generated.")
            return []
        
        # Save posts to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(self.content_dir, f'linkedin_posts_{timestamp}.json')
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(posts, f, indent=2)
            
            logger.info(f"Generated {len(posts)} LinkedIn posts and saved to {output_path}")
        except Exception as e:
            logger.error(f"Error saving LinkedIn posts: {e}")
        
        return posts


if __name__ == "__main__":
    # Test the generator
    generator = LinkedInContentGenerator()
    posts = generator.generate_linkedin_posts()
    
    if posts:
        print(f"Generated {len(posts)} LinkedIn posts.")
        print("\nSample post:")
        print(posts[0]['content'])
    else:
        print("No LinkedIn posts were generated.") 