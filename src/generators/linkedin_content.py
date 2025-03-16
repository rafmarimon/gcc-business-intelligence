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
            logger.warning("No report content provided for insight extraction.")
            return self._generate_fallback_insights(report_content)
        
        # Create a system prompt to extract insights
        system_prompt = """
        You are a professional content analyst. Extract the top 6 most significant business insights or developments 
        from the given business intelligence report. These should be the most newsworthy, impactful, 
        or strategically important pieces of information that would be valuable for LinkedIn audience.
        
        IMPORTANT: At least one of the insights MUST focus on US-UAE business relations, trade, investment, 
        or diplomatic ties that affect business. If any US-UAE relations content exists in the report, prioritize it.
        
        For each insight, provide:
        1. A brief title (5-8 words)
        2. The key fact or development (1-2 sentences)
        3. Why it matters to businesses (1 sentence)
        4. A "category" field with value "us_uae_relations" for any US-UAE related insight, or another appropriate category (e.g., "finance", "energy", "tech", etc.) for other insights
        
        Format your response as a JSON object with a key 'insights' containing an array, where each element is an object with keys: "title", "fact", "why_it_matters", "category".
        """
        
        user_prompt = f"""
        Extract the top 6 business insights from this UAE/GCC business intelligence report, ensuring at least one 
        focuses on US-UAE business or diplomatic relations:
        
        {report_content[:10000]}  # Limit to avoid token limits
        
        Please respond with only the JSON object. No preamble or explanation needed.
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
            logger.info(f"Received response from OpenAI for insight extraction. Response length: {len(content)}")
            
            # Extract JSON content and handle different possible response formats
            try:
                # First attempt direct JSON parsing
                insights_data = json.loads(content)
                
                # Check if insights exists and is a list
                if 'insights' in insights_data and isinstance(insights_data['insights'], list):
                    insights = insights_data['insights']
                    logger.info(f"Successfully extracted {len(insights)} insights from JSON response.")
                    return insights
                # If insights key doesn't exist but we have an array directly
                elif isinstance(insights_data, list):
                    logger.info(f"Successfully extracted {len(insights_data)} insights from JSON array response.")
                    return insights_data
                # If it's not a recognized format but still valid JSON, log and return fallback
                else:
                    logger.warning(f"JSON response does not contain expected 'insights' array: {insights_data.keys() if isinstance(insights_data, dict) else 'not a dict'}")
                    return self._generate_fallback_insights(report_content)
                    
            except json.JSONDecodeError as e:
                # If direct parsing fails, try to extract JSON using regex
                logger.warning(f"Failed to parse JSON directly: {str(e)}")
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    json_content = json_match.group(0)
                    try:
                        insights_data = json.loads(json_content)
                        
                        # Check for insights key
                        if 'insights' in insights_data and isinstance(insights_data['insights'], list):
                            insights = insights_data['insights']
                            logger.info(f"Successfully extracted {len(insights)} insights from regex-matched JSON.")
                            return insights
                        # If there's no insights key but we have a list of objects
                        elif isinstance(insights_data, list):
                            logger.info(f"Successfully extracted {len(insights_data)} insights from regex-matched JSON array.")
                            return insights_data
                        else:
                            logger.warning("JSON structure from regex match doesn't contain expected insights array")
                            return self._generate_fallback_insights(report_content)
                    except json.JSONDecodeError as json_err:
                        logger.error(f"Failed to parse regex-matched JSON content: {str(json_err)}")
                        return self._generate_fallback_insights(report_content)
                else:
                    # If no JSON pattern found, log and fall back
                    logger.error("No JSON pattern found in API response")
                    return self._generate_fallback_insights(report_content)
            
            except Exception as e:
                logger.error(f"Error parsing JSON response: {str(e)}")
                logger.error(f"Raw content (first 200 chars): {content[:200]}...")
                return self._generate_fallback_insights(report_content)
            
        except Exception as e:
            logger.error(f"Error extracting insights with OpenAI: {str(e)}")
            return self._generate_fallback_insights(report_content)
    
    def _generate_fallback_insights(self, report_content):
        """Generate fallback insights when OpenAI API is unavailable."""
        logger.info("Generating fallback insights without OpenAI...")
        
        # Create some sample insights based on common business topics in GCC
        fallback_insights = [
            {
                "title": "UAE-US Trade Agreement Progress",
                "fact": "Recent developments show progress in trade negotiations between the UAE and United States, with a focus on technology and renewable energy sectors.",
                "why_it_matters": "A strengthened trade partnership could open new market opportunities for businesses in both countries.",
                "category": "us_uae_relations"
            },
            {
                "title": "UAE Digital Economy Growth",
                "fact": "The UAE's digital economy is experiencing rapid growth, with increased investment in tech startups and digital infrastructure.",
                "why_it_matters": "This presents opportunities for businesses in technology, fintech, and digital transformation services.",
                "category": "technology"
            },
            {
                "title": "Saudi Vision 2030 Progress",
                "fact": "Saudi Arabia continues to advance its Vision 2030 goals with new megaprojects and economic diversification initiatives.",
                "why_it_matters": "Companies aligned with Vision 2030 priorities may find significant growth opportunities in the kingdom.",
                "category": "saudi_arabia"
            },
            {
                "title": "Sustainable Energy Investments",
                "fact": "GCC countries are increasing investments in renewable energy projects, particularly solar and green hydrogen.",
                "why_it_matters": "The shift presents both challenges for traditional energy businesses and opportunities in the green economy.",
                "category": "energy"
            },
            {
                "title": "Regional E-commerce Expansion",
                "fact": "E-commerce platforms are seeing rapid adoption across the GCC, with local players competing against global giants.",
                "why_it_matters": "Businesses should prioritize their digital retail strategy to capture the growing online consumer base.",
                "category": "retail"
            },
            {
                "title": "Financial Sector Transformation",
                "fact": "Banking and financial services in the GCC are undergoing digital transformation, with increased focus on fintech integration.",
                "why_it_matters": "This evolution is changing how businesses access financial services and manage transactions in the region.",
                "category": "finance"
            }
        ]
        
        return fallback_insights
    
    def generate_linkedin_post(self, insight, articles=None):
        """Generate a LinkedIn post for a particular insight."""
        if not insight:
            return None
        
        # Create context from articles if available
        articles_context = ""
        
        # Filter articles by category if possible
        category = insight.get('category', '')
        relevant_articles = []
        
        if articles and category:
            # For US-UAE relations, look for relevant content
            if category == "us_uae_relations":
                us_uae_keywords = [
                    'us-uae', 'uae-us', 'united states uae', 'us embassy', 'uae embassy',
                    'us-uae business council', 'us-uae relations', 'america uae', 'uae america',
                    'washington uae', 'abu dhabi us', 'dubai us', 'uae washington',
                    'us investment uae', 'uae investment us', 'us-uae trade', 'uae-us trade'
                ]
                
                for article in articles:
                    content = (
                        (article.get('headline', '') or '') + ' ' + 
                        (article.get('summary', '') or '')
                    ).lower()
                    
                    if any(keyword.lower() in content for keyword in us_uae_keywords):
                        relevant_articles.append(article)
            
            # For other categories, use simple keyword matching
            else:
                category_keywords = {
                    "technology": ["tech", "digital", "innovation", "startup", "ai", "artificial intelligence"],
                    "energy": ["energy", "renewable", "solar", "oil", "gas", "petroleum", "hydrogen"],
                    "finance": ["finance", "banking", "investment", "fintech", "market", "stock"],
                    "retail": ["retail", "e-commerce", "consumer", "shopping", "mall", "online store"],
                    "real_estate": ["real estate", "property", "construction", "housing", "building"]
                }
                
                keywords = category_keywords.get(category, [category])
                
                for article in articles:
                    content = (
                        (article.get('headline', '') or '') + ' ' + 
                        (article.get('summary', '') or '')
                    ).lower()
                    
                    if any(keyword.lower() in content for keyword in keywords):
                        relevant_articles.append(article)
            
            # If we found relevant articles, use them, otherwise use the original ones
            if not relevant_articles:
                relevant_articles = articles[:5]  # Use up to 5 articles for context
            else:
                relevant_articles = relevant_articles[:5]  # Limit to 5 most relevant
            
            articles_text = []
            for article in relevant_articles:
                headline = article.get('headline', '')
                source = article.get('source_name', '')
                articles_text.append(f"- {headline} ({source})")
            
            if articles_text:
                articles_context = "Recent articles:\n" + "\n".join(articles_text)
        
        # Create tailored system prompts based on the category
        base_system_prompt = """
        You are a skilled LinkedIn content creator specializing in business content for professionals. 
        Create a compelling LinkedIn post based on the business insight provided.
        
        The post should:
        1. Start with an attention-grabbing headline or question
        2. Present the key information concisely and clearly
        3. Explain the business implications and why this matters
        4. Include a call to action or thought-provoking conclusion
        5. End with 4-6 relevant hashtags
        
        Keep the post between 150-250 words. Use a professional but engaging tone.
        Do not include the title of the insight in the post itself.
        """
        
        # Add category-specific instructions
        category_specific_instructions = ""
        
        if category == "us_uae_relations":
            category_specific_instructions = """
            For this US-UAE relations post:
            - Highlight the bilateral business relationship between the United States and United Arab Emirates
            - Mention specific benefits for businesses in both countries
            - Reference any recent diplomatic developments that affect business
            - Consider mentioning the US-UAE Business Council or other relevant organizations if appropriate
            - Use hashtags like #USUAERelations #USUAEBusiness #GlobalTrade
            """
        elif category == "technology":
            category_specific_instructions = """
            For this technology post:
            - Highlight innovation and digital transformation in the GCC region
            - Connect the development to global tech trends
            - Use hashtags like #TechInnovation #UAETech #DigitalTransformation
            """
        elif category == "energy":
            category_specific_instructions = """
            For this energy sector post:
            - Discuss both traditional energy strengths and renewable transitions in the GCC
            - Connect to global energy market trends
            - Use hashtags like #EnergyTransition #RenewableEnergy #GCCEnergy
            """
        
        # Combine the prompts
        system_prompt = base_system_prompt
        if category_specific_instructions:
            system_prompt += "\n" + category_specific_instructions
        
        # Create the user prompt
        user_prompt = f"""
        Business Insight:
        Title: {insight.get('title', '')}
        Fact: {insight.get('fact', '')}
        Why it matters: {insight.get('why_it_matters', '')}
        Category: {category}
        
        {articles_context}
        
        Create a compelling LinkedIn post based on this insight.
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
                temperature=0.7
            )
            
            post_content = response.choices[0].message.content.strip()
            
            return {
                "title": insight.get('title', ''),
                "content": post_content,
                "category": category
            }
            
        except Exception as e:
            logger.error(f"Error generating LinkedIn post with OpenAI: {e}")
            return self._generate_fallback_post(insight)
    
    def _generate_fallback_post(self, insight):
        """Generate a fallback LinkedIn post when OpenAI is unavailable."""
        logger.info("Generating fallback LinkedIn post without OpenAI...")
        
        title = insight.get('title', '')
        fact = insight.get('fact', '')
        why_it_matters = insight.get('why_it_matters', '')
        category = insight.get('category', '')
        
        # Generate different post templates based on category
        if category == "us_uae_relations":
            post_content = f"""🇺🇸🇦🇪 **US-UAE Partnership Update**

{fact} 

This development is significant because {why_it_matters.lower()} As the bilateral relationship continues to strengthen, businesses on both sides can explore new opportunities for collaboration and growth.

The US-UAE Business Council notes that bilateral trade has been growing steadily, making the UAE one of America's most important trading partners in the Middle East.

What opportunities do you see in the evolving US-UAE business landscape?

#USUAERelations #InternationalTrade #BusinessDiplomacy #GlobalOpportunities #UAEBusiness #USBusiness"""
        
        elif category == "technology":
            post_content = f"""💡 **Tech Innovation Spotlight: UAE**

{fact} 

Why this matters: {why_it_matters}

The UAE continues to position itself as a technology hub in the Middle East, with significant investments in digital infrastructure and smart city initiatives.

Are you participating in the UAE's tech transformation? What opportunities do you see?

#UAETech #DigitalTransformation #Innovation #GCCTech #MiddleEastTech #FutureTech"""
        
        elif category == "energy":
            post_content = f"""⚡ **Energy Sector Update**

{fact} 

This development matters because {why_it_matters.lower()}

The energy landscape in the GCC continues to evolve, balancing traditional oil and gas strengths with ambitious renewable energy goals.

How is your business adapting to the changing energy dynamics in the region?

#EnergyTransition #RenewableEnergy #GCCEnergy #Sustainability #CleanTech #EnergyInnovation"""
        
        else:
            # Generic template for other categories
            post_content = f"""📊 **GCC Business Intelligence Update**

{fact} 

Why this matters: {why_it_matters}

The business landscape in the UAE and broader GCC region continues to evolve, presenting both challenges and opportunities for companies operating in this dynamic market.

What's your take on this development? How might it affect your business strategy in the region?

#UAEBusiness #GCCBusiness #BusinessIntelligence #GlobalBusiness #MiddleEastBusiness"""
        
        return {
            "title": title,
            "content": post_content,
            "category": category
        }
    
    def generate_linkedin_posts(self):
        """Generate a set of LinkedIn posts based on the latest report."""
        # Get the latest report content
        report_content = self.get_latest_report()
        if not report_content:
            logger.warning("No report content available for LinkedIn post generation.")
            # Use fallback insights to generate posts anyway
            insights = self._generate_fallback_insights("")
        else:
            # Extract insights from the report
            insights = self.extract_top_insights(report_content)
        
        # If still no insights, use fallbacks to ensure we have posts
        if not insights or len(insights) == 0:
            logger.warning("No insights extracted from report. Using fallback insights.")
            insights = self._generate_fallback_insights(report_content or "")
        
        # Get supplementary news data
        latest_articles = self.get_latest_news_data()
        
        # Generate posts for each insight
        posts = []
        for insight in insights:
            post = self.generate_linkedin_post(insight, latest_articles)
            if post:
                posts.append(post)
        
        # If still no posts, create some generic ones
        if not posts:
            logger.warning("No LinkedIn posts generated from insights. Creating generic posts.")
            generic_insights = self._generate_fallback_insights("")
            for insight in generic_insights:
                post = self._generate_fallback_post(insight)
                if post:
                    posts.append(post)
        
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