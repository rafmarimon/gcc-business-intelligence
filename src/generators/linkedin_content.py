import os
import json
import logging
import re
from datetime import datetime
from dotenv import load_dotenv
from src.utils.openai_utils import OpenAIClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LinkedInContentGenerator")

class LinkedInContentGenerator:
    """
    Generates professional LinkedIn content based on business intelligence reports.
    """
    def __init__(self, output_dir='content'):
        """Initialize the LinkedIn content generator."""
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Set up OpenAI
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            logger.warning("OpenAI API key not found in environment variables. LLM features will not work.")
        else:
            # Set up our OpenAI client with exponential backoff
            self.openai_client = OpenAIClient(self.api_key)
    
    def _generate_system_prompt(self):
        """Generate system prompt for LinkedIn content generation."""
        return """
        You are an expert business content creator specializing in UAE and GCC markets.
        You create engaging, professional LinkedIn posts that highlight key business insights
        and trends from intelligence reports.
        
        Your LinkedIn posts should:
        1. Be clear, concise, and professional
        2. Include a compelling hook in the first line
        3. Highlight 2-3 key insights or trends
        4. Include relevant hashtags (5-7 max)
        5. End with a thought-provoking question to drive engagement
        6. Be between 200-300 words total
        7. Format text to be easily scannable (use line breaks)
        8. Maintain an authoritative but conversational tone
        
        Respond in JSON format with the following structure:
        {
            "title": "Post title/hook",
            "body": "Main content with insights",
            "hashtags": ["hashtag1", "hashtag2", ...],
            "engagement_question": "Question to drive comments"
        }
        """
    
    def _generate_user_prompt(self, report_content, post_type="general"):
        """Generate user prompt for the OpenAI API based on post type."""
        
        base_prompt = f"""
        Generate a professional LinkedIn post based on the following business intelligence report about UAE/GCC markets.
        
        POST TYPE: {post_type.upper()}
        
        REPORT CONTENT:
        {report_content[:2000]}  # Limit to first 2000 chars for context
        
        ADDITIONAL INSTRUCTIONS:
        """
        
        # Customize based on post type
        if post_type == "market_update":
            base_prompt += """
            - Focus on general market trends and conditions
            - Highlight key economic indicators
            - Discuss implications for international businesses
            """
        elif post_type == "sector_focus":
            base_prompt += """
            - Focus on a specific sector mentioned in the report
            - Highlight growth opportunities or challenges
            - Include sector-specific metrics or developments
            """
        elif post_type == "us_uae_relations":
            base_prompt += """
            - Focus on US-UAE business relations
            - Highlight recent developments or opportunities
            - Discuss implications for businesses in both countries
            """
        elif post_type == "investment_opportunities":
            base_prompt += """
            - Focus on investment opportunities in UAE/GCC
            - Highlight specific projects or sectors with potential
            - Include relevant economic indicators or growth projections
            """
        else:  # general
            base_prompt += """
            - Create a general overview of the key insights
            - Balance between different aspects covered in the report
            - Highlight the most significant findings
            """
        
        return base_prompt
    
    def generate_post(self, report_path, post_type="general"):
        """Generate a LinkedIn post based on a business intelligence report."""
        try:
            # Load report content
            if not os.path.exists(report_path):
                logger.error(f"Report file not found: {report_path}")
                return None
            
            with open(report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()
            
            if not report_content:
                logger.warning("Empty report content.")
                return self._generate_fallback_post(post_type, "Empty report content")
            
            if not self.api_key:
                return self._generate_fallback_post(post_type, "OpenAI API key not configured")
            
            system_prompt = self._generate_system_prompt()
            user_prompt = self._generate_user_prompt(report_content, post_type)
            
            # Try with GPT-4o first
            try:
                logger.info(f"Generating {post_type} LinkedIn post using GPT-4o model.")
                response = self.openai_client.create_chat_completion(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    response_format={"type": "json_object"}
                )
                
                # Parse the JSON response
                content = response.choices[0].message.content
                logger.info("LinkedIn post generated successfully with GPT-4o.")
                return self._format_post(content)
                
            except Exception as e:
                logger.error(f"Error generating LinkedIn post with GPT-4o: {e}")
                
                # Fallback to GPT-3.5-Turbo
                try:
                    logger.info("Falling back to GPT-3.5-Turbo model.")
                    response = self.openai_client.create_chat_completion(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.7,
                        response_format={"type": "json_object"}
                    )
                    
                    # Parse the JSON response
                    content = response.choices[0].message.content
                    logger.info("LinkedIn post generated successfully with GPT-3.5-Turbo.")
                    return self._format_post(content)
                    
                except Exception as e2:
                    logger.error(f"Error generating LinkedIn post with GPT-3.5-Turbo: {e2}")
                    return self._generate_fallback_post(post_type, f"OpenAI API errors: {e}, {e2}")
                
        except Exception as e:
            logger.error(f"Error generating LinkedIn post: {e}")
            return self._generate_fallback_post(post_type, str(e))
    
    def _format_post(self, json_content):
        """Format the JSON response into a complete LinkedIn post."""
        try:
            # Parse JSON
            content = json.loads(json_content)
            
            # Extract fields with fallbacks
            title = content.get('title', 'Business Insight: UAE/GCC Markets')
            body = content.get('body', 'No content generated.')
            hashtags = content.get('hashtags', ['#UAEBusiness', '#GCCMarkets', '#BusinessIntelligence'])
            question = content.get('engagement_question', 'What are your thoughts on these developments?')
            
            # Format hashtags
            hashtag_text = ' '.join(hashtags)
            
            # Combine everything
            formatted_post = f"{title}\n\n{body}\n\n{question}\n\n{hashtag_text}"
            
            return formatted_post
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {e}")
            # If we can't parse JSON, try to extract content directly
            try:
                # Look for title, body, hashtags sections
                title_match = re.search(r'"title":\s*"([^"]+)"', json_content)
                body_match = re.search(r'"body":\s*"([^"]+)"', json_content)
                question_match = re.search(r'"engagement_question":\s*"([^"]+)"', json_content)
                
                title = title_match.group(1) if title_match else "Business Insight: UAE/GCC Markets"
                body = body_match.group(1) if body_match else json_content.replace('\\n', '\n')
                question = question_match.group(1) if question_match else "What are your thoughts on these developments?"
                
                # Add default hashtags
                hashtag_text = "#UAEBusiness #GCCMarkets #BusinessIntelligence"
                
                return f"{title}\n\n{body}\n\n{question}\n\n{hashtag_text}"
                
            except Exception as e2:
                logger.error(f"Error extracting content from non-JSON response: {e2}")
                return f"Error formatting LinkedIn post. Raw content:\n\n{json_content}"
    
    def _generate_fallback_post(self, post_type="general", error_reason="API limitations"):
        """Generate a fallback LinkedIn post when OpenAI is unavailable."""
        current_date = datetime.now().strftime("%B %d, %Y")
        
        # Base template
        title = f"UAE/GCC Business Update: {current_date}"
        body = "Due to technical limitations, we're sharing a simplified update on UAE/GCC markets today."
        question = "What business trends are you monitoring in the UAE/GCC region?"
        
        # Customize based on post type
        if post_type == "market_update":
            body += "\n\nThe UAE and GCC markets continue to show resilience amid global economic challenges. Key sectors including technology, finance, and renewable energy have been particularly active this month. UAE's diversification strategy remains on track with new initiatives to boost non-oil economic growth."
            hashtags = "#UAEMarkets #GCCEconomy #MarketUpdate #BusinessIntelligence #GlobalTrade #EmergingMarkets"
            question = "Which economic indicators do you track to gauge UAE market performance?"
            
        elif post_type == "sector_focus":
            body += "\n\nThe technology sector in the UAE/GCC region continues to attract significant investment. Government initiatives supporting digital transformation are creating new opportunities for businesses and entrepreneurs. Fintech, AI, and renewable tech appear to be the fastest-growing segments in the regional ecosystem."
            hashtags = "#UAETech #GCCInnovation #DigitalTransformation #TechInvestment #FinTech #AIinnovation"
            question = "Which tech sector in the UAE offers the most promising growth potential?"
            
        elif post_type == "us_uae_relations":
            body += "\n\nUS-UAE business relations remain strong with continued growth in bilateral trade. Recent diplomatic engagements have highlighted opportunities in key sectors including defense, energy, and technology. American businesses are finding new pathways for market entry and expansion throughout the Emirates."
            hashtags = "#USUAERelations #InternationalTrade #BusinessDiplomacy #GlobalOpportunities #TradePartners"
            question = "How has your business navigated the US-UAE business landscape?"
            
        elif post_type == "investment_opportunities":
            body += "\n\nThe UAE continues to enhance its position as a global investment hub. Recent regulatory changes have further improved market access for foreign investors. Key sectors showing promising ROI include real estate, technology, healthcare, and financial services. Government-backed projects present additional stable investment options."
            hashtags = "#UAEInvestment #GCCOpportunities #ForeignInvestment #EmergingMarkets #CapitalGrowth"
            question = "What investment criteria do you prioritize when considering UAE/GCC opportunities?"
            
        else:  # general
            body += "\n\nThe UAE and broader GCC region continue to demonstrate economic resilience and innovation. Strategic initiatives focused on diversification, sustainability, and digital transformation are creating new opportunities for businesses across multiple sectors. Regional collaboration is strengthening the overall business ecosystem."
            hashtags = "#UAEBusiness #GCCEconomy #BusinessIntelligence #MarketInsights #GlobalTrade"
            question = "What aspects of the UAE/GCC business landscape are you most interested in?"
        
        # Add footer explaining the fallback
        body += f"\n\n(Note: This is an automated post generated due to {error_reason}. Full AI-powered insights will resume in our next update.)"
        
        return f"{title}\n\n{body}\n\n{question}\n\n{hashtags}"
    
    def save_post(self, post_content, post_type="general"):
        """Save the generated LinkedIn post to a file."""
        try:
            if not post_content:
                logger.warning("No content to save.")
                return None
                
            # Create a timestamp for the filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"linkedin_{post_type}_{timestamp}.txt"
            file_path = os.path.join(self.output_dir, filename)
            
            # Save the post to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(post_content)
            
            logger.info(f"LinkedIn post saved to {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving LinkedIn post: {e}")
            return None

# Example usage
if __name__ == "__main__":
    generator = LinkedInContentGenerator()
    # Example with a sample report path - update with actual path
    sample_report_path = "reports/latest_report.md"
    
    # Check if the file exists or use a sample string for testing
    if os.path.exists(sample_report_path):
        post = generator.generate_post(sample_report_path, post_type="market_update")
    else:
        # Sample report content for testing
        sample_content = """
        # UAE/GCC Business Intelligence Report
        
        ## Executive Summary
        The UAE economy continues to show strong growth in non-oil sectors,
        particularly in technology, finance, and tourism. Recent government
        initiatives are supporting digital transformation across industries.
        
        ## Key Trends
        - Fintech investments increased by 30% in Q1
        - UAE-US trade volume reached $25 billion
        - New sustainability initiatives announced across GCC
        """
        
        # Generate post directly from sample content
        post = generator._generate_fallback_post("market_update", "testing")
    
    if post:
        file_path = generator.save_post(post, "market_update")
        print(f"Post saved to: {file_path}")
        print("\nPreview:")
        print(post[:300] + "...")
    else:
        print("Failed to generate LinkedIn post.") 