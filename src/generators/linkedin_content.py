import os
import json
import logging
import re
import uuid
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
    def __init__(self, output_dir='content', config_path='config/linkedin_config.json', model='gpt-4o'):
        """Initialize the LinkedIn content generator.
        
        Args:
            output_dir: Directory to store generated content
            config_path: Path to the LinkedIn config JSON file
            model: The OpenAI model to use (default: gpt-4o)
        """
        self.output_dir = output_dir
        self.config_path = config_path
        self.model = model
        
        # Create directories for content and images
        self.images_dir = os.path.join(output_dir, 'images')
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)
        
        # Load configuration
        self.config = self._load_config()
        
        # Set up OpenAI
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            logger.warning("OpenAI API key not found in environment variables. LLM features will not work.")
        else:
            # Set up our OpenAI client with exponential backoff
            self.openai_client = OpenAIClient(self.api_key)
    
    def _load_config(self):
        """Load LinkedIn post configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                logger.info(f"Loaded LinkedIn configuration from {self.config_path}")
                return config
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading LinkedIn config: {e}")
            # Return default configuration
            return {
                "post_types": ["general", "market_update", "sector_focus", "us_uae_relations", "investment_opportunities"],
                "hashtags": ["#UAE", "#GCC", "#BusinessIntelligence", "#UAEBusiness", "#GulfBusiness"],
                "post_frequency": 4,
                "hashtags_per_post": {"min": 3, "max": 5},
                "include_images": True,
                "image_style": "natural"
            }
    
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
            "engagement_question": "Question to drive comments",
            "image_prompt": "A detailed and specific prompt for generating an image that complements the post content"
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
        - Include a detailed image prompt that will be used to generate a compelling visual for this post
        - The image prompt should be specific (not generic) and related to the content of the post
        - For image prompts, focus on UAE/GCC regional imagery, business themes, and relevant visuals
        - The image prompt should be 2-4 sentences describing a professional business image
        """
        
        # Customize based on post type
        if post_type == "market_update":
            base_prompt += """
            - Focus on general market trends and conditions
            - Highlight key economic indicators
            - Discuss implications for international businesses
            - For the image prompt, suggest visualizations of market data, financial districts in UAE, or symbols of economic growth
            """
        elif post_type == "sector_focus":
            base_prompt += """
            - Focus on a specific sector mentioned in the report
            - Highlight growth opportunities or challenges
            - Include sector-specific metrics or developments
            - For the image prompt, suggest an image representing the specific sector being discussed
            """
        elif post_type == "us_uae_relations":
            base_prompt += """
            - Focus on US-UAE business relations
            - Highlight recent developments or opportunities
            - Discuss implications for businesses in both countries
            - For the image prompt, suggest visuals representing US-UAE cooperation, trade, or diplomatic relations
            """
        elif post_type == "investment_opportunities":
            base_prompt += """
            - Focus on investment opportunities in UAE/GCC
            - Highlight specific projects or sectors with potential
            - Include relevant economic indicators or growth projections
            - For the image prompt, suggest images of investment themes, development projects, or construction in the UAE
            """
        else:  # general
            base_prompt += """
            - Create a general overview of the key insights
            - Balance between different aspects covered in the report
            - Highlight the most significant findings
            - For the image prompt, suggest a balanced visual that represents UAE/GCC business landscape
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
                
                # Parse content and generate image if needed
                post_data = self._parse_post_content(content)
                
                # Generate an image for the post if enabled in config
                if self.config.get("include_images", True) and "image_prompt" in post_data:
                    image_path = self._generate_image_for_post(post_data["image_prompt"], post_type)
                    if image_path:
                        post_data["image_path"] = image_path
                
                return self._format_post(post_data)
                
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
                    
                    # Parse content and generate image if needed
                    post_data = self._parse_post_content(content)
                    
                    # Generate an image for the post if enabled in config
                    if self.config.get("include_images", True) and "image_prompt" in post_data:
                        image_path = self._generate_image_for_post(post_data["image_prompt"], post_type)
                        if image_path:
                            post_data["image_path"] = image_path
                    
                    return self._format_post(post_data)
                    
                except Exception as e2:
                    logger.error(f"Error generating LinkedIn post with GPT-3.5-Turbo: {e2}")
                    return self._generate_fallback_post(post_type, f"OpenAI API errors: {e}, {e2}")
                
        except Exception as e:
            logger.error(f"Error generating LinkedIn post: {e}")
            return self._generate_fallback_post(post_type, str(e))
    
    def _parse_post_content(self, json_content):
        """Parse the JSON response into a structured format."""
        try:
            return json.loads(json_content)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {e}")
            # Try to extract content directly with regex
            data = {}
            
            title_match = re.search(r'"title":\s*"([^"]+)"', json_content)
            body_match = re.search(r'"body":\s*"([^"]+)"', json_content)
            question_match = re.search(r'"engagement_question":\s*"([^"]+)"', json_content)
            image_prompt_match = re.search(r'"image_prompt":\s*"([^"]+)"', json_content)
            
            data["title"] = title_match.group(1) if title_match else "Business Insight: UAE/GCC Markets"
            data["body"] = body_match.group(1) if body_match else json_content.replace('\\n', '\n')
            data["engagement_question"] = question_match.group(1) if question_match else "What are your thoughts on these developments?"
            data["image_prompt"] = image_prompt_match.group(1) if image_prompt_match else None
            
            # Extract hashtags
            hashtags_match = re.search(r'"hashtags":\s*\[(.*?)\]', json_content)
            if hashtags_match:
                hashtags_str = hashtags_match.group(1)
                hashtags = re.findall(r'"([^"]+)"', hashtags_str)
                data["hashtags"] = hashtags
            else:
                data["hashtags"] = ["#UAEBusiness", "#GCCMarkets", "#BusinessIntelligence"]
            
            return data
    
    def _generate_image_for_post(self, image_prompt, post_type):
        """Generate an image for the LinkedIn post using GPT-4o or DALL-E."""
        try:
            if not image_prompt:
                logger.warning("No image prompt provided for image generation.")
                return None
                
            # Enhance the prompt for better results
            enhanced_prompt = f"Create a professional business image for a LinkedIn post about {post_type} in UAE/GCC markets. {image_prompt} The style should be professional, clean, and suitable for business content. Include UAE/GCC visual elements where appropriate."
            
            # Generate a unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"linkedin_{post_type}_{timestamp}_{unique_id}.png"
            image_path = os.path.join(self.images_dir, filename)
            
            # Generate the image
            logger.info(f"Generating image for LinkedIn post with prompt: {image_prompt[:50]}...")
            result = self.openai_client.generate_image(
                prompt=enhanced_prompt,
                size="1024x1024", 
                quality="standard",
                style=self.config.get("image_style", "natural"),
                save_path=image_path
            )
            
            # Handle the new result format from the enhanced image generation
            if isinstance(result, dict):
                # Extract the image path or URL from the result dict
                image_generator = result.get("image_generator", "dall-e")
                result_data = result.get("result", None)
                
                # Log which model was used
                logger.info(f"Image generated using {image_generator} model")
                
                # If we got back a saved path, return it
                if result_data and os.path.exists(result_data):
                    logger.info(f"Image generated successfully and saved to {result_data}")
                    return result_data
                
                # Otherwise, result_data might be a URL or base64 data
                elif result_data:
                    # If it's the image path we requested, check if it exists
                    if result_data == image_path and os.path.exists(image_path):
                        logger.info(f"Image generated successfully and saved to {image_path}")
                        return image_path
                    else:
                        logger.info(f"Image was generated but not saved locally. Using URL or data.")
                        return result_data
                else:
                    logger.warning("Image generation did not return a valid result")
                    return None
            else:
                # Handle the old format for backward compatibility
                if os.path.exists(image_path):
                    logger.info(f"Image generated successfully and saved to {image_path}")
                    return image_path
                else:
                    logger.warning("Image was generated but not saved locally.")
                    return result  # This will be the URL
                
        except Exception as e:
            logger.error(f"Error generating image for post: {str(e)}")
            return None
    
    def _format_post(self, content):
        """Format the post content into a complete LinkedIn post."""
        try:
            # Extract fields with fallbacks
            if isinstance(content, str):
                # Try to parse as JSON if it's a string
                try:
                    content = json.loads(content)
                except:
                    # Return as is if not valid JSON
                    return content
            
            title = content.get('title', 'Business Insight: UAE/GCC Markets')
            body = content.get('body', 'No content generated.')
            hashtags = content.get('hashtags', ['#UAEBusiness', '#GCCMarkets', '#BusinessIntelligence'])
            question = content.get('engagement_question', 'What are your thoughts on these developments?')
            image_path = content.get('image_path', None)
            
            # Format hashtags
            if isinstance(hashtags, list):
                hashtag_text = ' '.join(hashtags)
            else:
                hashtag_text = hashtags
            
            # Combine everything
            formatted_post = f"{title}\n\n{body}\n\n{question}\n\n{hashtag_text}"
            
            # Create a post object with text and image path
            post_object = {
                "text": formatted_post,
                "image_path": image_path,
                "metadata": {
                    "title": title,
                    "body": body,
                    "hashtags": hashtags,
                    "question": question,
                    "generated_at": datetime.now().isoformat(),
                }
            }
            
            return post_object
            
        except Exception as e:
            logger.error(f"Error formatting post: {e}")
            if isinstance(content, dict) and 'image_path' in content:
                image_path = content['image_path']
            else:
                image_path = None
                
            return {
                "text": str(content),
                "image_path": image_path,
                "metadata": {
                    "error": str(e),
                    "generated_at": datetime.now().isoformat(),
                }
            }
    
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
        
        # Create the fallback post object
        fallback_post = {
            "text": f"{title}\n\n{body}\n\n{question}\n\n{hashtags}",
            "image_path": None,
            "metadata": {
                "title": title,
                "body": body, 
                "hashtags": hashtags.split(),
                "question": question,
                "generated_at": datetime.now().isoformat(),
                "fallback_reason": error_reason
            }
        }
        
        return fallback_post
    
    def save_post(self, post_content, post_type="general"):
        """Save a LinkedIn post to a file."""
        try:
            if not post_content:
                logger.error("No post content to save.")
                return None
                
            # Create a timestamp-based filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"linkedin_{post_type}_{timestamp}.json"
            file_path = os.path.join(self.output_dir, filename)
            
            # Save the post content
            with open(file_path, 'w', encoding='utf-8') as f:
                if isinstance(post_content, dict):
                    json.dump(post_content, f, indent=2)
                else:
                    f.write(post_content)
                    
            logger.info(f"Saved LinkedIn post to {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving LinkedIn post: {e}")
            return None
    
    def generate_linkedin_posts(self, report_text=None):
        """Generate multiple LinkedIn posts of different types."""
        try:
            post_types = self.config.get("post_types", ["general", "market_update", "sector_focus"])
            posts = []
            
            # If report text is provided, use it directly
            if report_text:
                # Generate posts for each type
                for post_type in post_types:
                    logger.info(f"Generating {post_type} LinkedIn post from provided text...")
                    post = self._generate_post_from_text(report_text, post_type)
                    if post:
                        posts.append(post)
                        # Save the post
                        self.save_post(post, post_type)
            else:
                # Try to find the latest report
                report_path = self._find_latest_report()
                if not report_path:
                    logger.error("No report found for generating LinkedIn posts.")
                    return None
                    
                # Generate posts for each type
                for post_type in post_types:
                    logger.info(f"Generating {post_type} LinkedIn post from report {report_path}...")
                    post = self.generate_post(report_path, post_type)
                    if post:
                        posts.append(post)
                        # Save the post
                        self.save_post(post, post_type)
            
            # Format posts to markdown
            markdown_content = self._format_posts_to_markdown(posts)
            
            # Save markdown to file
            markdown_path = os.path.join(self.output_dir, f"linkedin_posts_{datetime.now().strftime('%Y%m%d')}.md")
            with open(markdown_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
                
            logger.info(f"Generated {len(posts)} LinkedIn posts and saved to {markdown_path}")
            
            return {
                "posts": posts,
                "markdown_path": markdown_path
            }
                
        except Exception as e:
            logger.error(f"Error generating LinkedIn posts: {e}")
            return None
    
    def _generate_post_from_text(self, report_text, post_type="general"):
        """Generate a LinkedIn post directly from report text."""
        try:
            if not report_text:
                logger.warning("Empty report text.")
                return self._generate_fallback_post(post_type, "Empty report text")
            
            if not self.api_key:
                return self._generate_fallback_post(post_type, "OpenAI API key not configured")
            
            system_prompt = self._generate_system_prompt()
            user_prompt = self._generate_user_prompt(report_text, post_type)
            
            # Try with specified model
            try:
                logger.info(f"Generating {post_type} LinkedIn post using {self.model} model.")
                response = self.openai_client.create_chat_completion(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    response_format={"type": "json_object"}
                )
                
                # Parse the JSON response
                content = response.choices[0].message.content
                logger.info(f"LinkedIn post generated successfully with {self.model}.")
                
                # Parse content and generate image if needed
                post_data = self._parse_post_content(content)
                
                # Generate an image for the post if enabled in config
                if self.config.get("include_images", True) and "image_prompt" in post_data:
                    image_path = self._generate_image_for_post(post_data["image_prompt"], post_type)
                    if image_path:
                        post_data["image_path"] = image_path
                
                return self._format_post(post_data)
                
            except Exception as e:
                logger.error(f"Error generating LinkedIn post with {self.model}: {e}")
                
                # Fallback to GPT-3.5-Turbo
                if self.model != "gpt-3.5-turbo":
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
                        
                        # Parse content and generate image if needed
                        post_data = self._parse_post_content(content)
                        
                        # Generate an image for the post if enabled in config
                        if self.config.get("include_images", True) and "image_prompt" in post_data:
                            image_path = self._generate_image_for_post(post_data["image_prompt"], post_type)
                            if image_path:
                                post_data["image_path"] = image_path
                        
                        return self._format_post(post_data)
                        
                    except Exception as e2:
                        logger.error(f"Error with fallback model: {e2}")
                        return self._generate_fallback_post(post_type, f"OpenAI API errors: {e}, {e2}")
                else:
                    return self._generate_fallback_post(post_type, f"OpenAI API error: {e}")
                
        except Exception as e:
            logger.error(f"Error generating LinkedIn post: {e}")
            return self._generate_fallback_post(post_type, str(e))
    
    def _find_latest_report(self):
        """Find the latest consolidated report to use as a basis."""
        try:
            # Look in standard report locations
            reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'reports')
            
            # Find all markdown files that look like consolidated reports
            md_files = []
            for root, _, files in os.walk(reports_dir):
                for file in files:
                    if file.startswith('consolidated_report_') and file.endswith('.md'):
                        md_path = os.path.join(root, file)
                        md_files.append((md_path, os.path.getmtime(md_path)))
            
            # Sort by modification time (newest first)
            md_files.sort(key=lambda x: x[1], reverse=True)
            
            if md_files:
                latest_report = md_files[0][0]
                logger.info(f"Found latest report: {latest_report}")
                return latest_report
            else:
                logger.warning("No consolidated reports found.")
                return None
                
        except Exception as e:
            logger.error(f"Error finding latest report: {e}")
            return None
    
    def _format_posts_to_markdown(self, posts):
        """Format a list of posts into a markdown document."""
        try:
            if not posts:
                return "# No LinkedIn Posts Generated\n\nNo posts were generated. Please check the logs for details."
                
            markdown = "# Generated LinkedIn Posts\n\n"
            markdown += f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n\n"
            
            for i, post in enumerate(posts):
                markdown += f"## Post {i+1}\n\n"
                
                if isinstance(post, dict):
                    # Extract metadata
                    metadata = post.get('metadata', {})
                    post_type = metadata.get('post_type', f"Type {i+1}")
                    title = metadata.get('title', 'Untitled')
                    
                    # Add title and content
                    markdown += f"### {title}\n\n"
                    markdown += "```\n"
                    markdown += post.get('text', 'No content available.')
                    markdown += "\n```\n\n"
                    
                    # Add image if available
                    image_path = post.get('image_path')
                    if image_path:
                        # Convert to relative path for markdown if possible
                        try:
                            rel_path = os.path.relpath(image_path, os.path.dirname(self.output_dir))
                            markdown += f"![LinkedIn Post Image]({rel_path})\n\n"
                        except:
                            markdown += f"Image available at: {image_path}\n\n"
                else:
                    # If post is just a string
                    markdown += "```\n"
                    markdown += str(post)
                    markdown += "\n```\n\n"
                    
                # Add separator
                markdown += "---\n\n"
                
            return markdown
            
        except Exception as e:
            logger.error(f"Error formatting posts to markdown: {e}")
            return f"# Error Formatting Posts\n\nAn error occurred: {str(e)}\n\nRaw posts: {str(posts)}"

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