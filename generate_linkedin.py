#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LinkedIn Post Generator with AI-Generated Visuals

This script generates professional LinkedIn posts with AI-created images
from various sources like reports, articles, or custom inputs.
"""

import os
import sys
import json
import argparse
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import base64
from pathlib import Path
import re

# Ensure proper imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import required modules
try:
    from src.utils.openai_utils import OpenAIUtil
    from src.models.client_model import ClientModel
    from src.utils.redis_cache import RedisCache
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Error importing required modules: {str(e)}")
    print("Make sure you're running from the project root.")
    sys.exit(1)

# Load environment variables
load_dotenv()

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

log_filename = os.path.join(log_dir, f'linkedin_generator_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LinkedInPostGenerator:
    """LinkedIn post generator with AI-generated visuals."""
    
    def __init__(self):
        """Initialize the LinkedIn post generator."""
        # Initialize Redis cache
        self.redis = RedisCache()
        
        # Initialize OpenAI utility
        self.openai = OpenAIUtil()
        
        # Initialize client model
        self.client_model = ClientModel()
        
        # Set up output directory
        self.output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'linkedin_content')
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Load styles
        self.styles = {
            'corporate': 'professional, corporate style with clean layout',
            'casual': 'friendly, approachable style with warm colors',
            'informative': 'data-focused, analytical style with charts or diagrams',
            'modern': 'sleek, minimalist design with contemporary aesthetics',
            'bold': 'attention-grabbing, high-contrast design with strong elements'
        }
        
        logger.info("LinkedIn post generator initialized")
    
    def _extract_content_from_file(self, file_path: str) -> str:
        """Extract content from a markdown or text file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return ""
    
    def _extract_key_points(self, content: str, max_points: int = 5) -> List[str]:
        """Extract key points from content using OpenAI."""
        prompt = f"""
        Extract the {max_points} most important points from the following content. 
        Focus on business insights, market trends, and actionable information.
        Format each point as a concise bullet point.
        
        CONTENT:
        {content[:4000]}  # Limit content to avoid token limits
        """
        
        system_prompt = "You are an expert business analyst who extracts key insights from market intelligence reports and articles."
        
        try:
            response = self.openai.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3
            )
            
            # Extract bullet points
            points = []
            for line in response.split('\n'):
                line = line.strip()
                if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                    points.append(line.lstrip('•-* '))
            
            return points[:max_points]  # Ensure we don't exceed max_points
        
        except Exception as e:
            logger.error(f"Error extracting key points: {str(e)}")
            return []
    
    def _generate_linkedin_caption(self, 
                                   client_name: str, 
                                   content: str,
                                   key_points: List[str],
                                   style: str = 'corporate') -> str:
        """Generate a LinkedIn post caption using OpenAI."""
        style_description = self.styles.get(style, self.styles['corporate'])
        
        # Build a prompt for generating the caption
        prompt = f"""
        Create a compelling LinkedIn post for {client_name} based on the following information.
        The post should focus on GCC (Gulf Cooperation Council) market intelligence.
        
        KEY INSIGHTS:
        {' '.join([f"- {point}" for point in key_points])}
        
        STYLE: {style_description}
        
        The post should:
        1. Start with an attention-grabbing headline/question
        2. Include 2-3 key insights about the GCC market relevant to {client_name}
        3. Include relevant hashtags (max 5)
        4. Be between 1000-1200 characters total
        5. End with a call to action
        
        ADDITIONAL CONTEXT:
        {content[:500]}
        """
        
        system_prompt = """
        You are a professional LinkedIn content creator specializing in business and market intelligence posts.
        Your posts are engaging, informative, and designed to generate discussion and shares.
        """
        
        try:
            caption = self.openai.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7
            )
            
            return caption
        
        except Exception as e:
            logger.error(f"Error generating LinkedIn caption: {str(e)}")
            return "Error generating LinkedIn caption. Please try again."
    
    def _generate_image_prompt(self, 
                               client_name: str, 
                               key_points: List[str],
                               style: str = 'corporate') -> str:
        """Generate a prompt for the image generation based on content."""
        style_description = self.styles.get(style, self.styles['corporate'])
        
        prompt = f"""
        Create a detailed image prompt for a LinkedIn post about {client_name}'s market insights in the Gulf Cooperation Council (GCC) region.
        
        KEY POINTS IN THE CONTENT:
        {' '.join([f"- {point}" for point in key_points])}
        
        STYLE: {style_description}
        
        The image should:
        1. Be professional and business-appropriate
        2. Visualize the key market insights
        3. Include subtle references to the GCC region (like skylines, symbols, or colors)
        4. Work well as a LinkedIn header image
        5. Not contain any text (text will be added separately)
        
        Create a detailed prompt that will generate an effective business image representing these ideas.
        """
        
        system_prompt = """
        You are an expert image prompt engineer who creates detailed prompts for generating 
        business and market intelligence visuals. Your prompts create professional, 
        clear images that effectively communicate business concepts.
        """
        
        try:
            image_prompt = self.openai.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7
            )
            
            # Add specific instructions for image generation
            enhanced_prompt = f"""
            Professional LinkedIn header image: {image_prompt}
            
            Style: {style_description}
            Industry: {client_name}'s sector
            Region: Gulf Cooperation Council (GCC)
            Format: 16:9 ratio, business-appropriate
            """
            
            return enhanced_prompt
        
        except Exception as e:
            logger.error(f"Error generating image prompt: {str(e)}")
            return f"Professional business image for {client_name} in the GCC region, {style_description}"
    
    def _generate_image(self, 
                        prompt: str, 
                        client_name: str,
                        style: str = 'corporate') -> Optional[Dict[str, Any]]:
        """Generate an image using OpenAI's image generation capabilities."""
        try:
            # Clean the client name for filename
            clean_name = re.sub(r'[^\w\s-]', '', client_name).strip().replace(' ', '_').lower()
            
            # Create timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Define save path
            save_path = os.path.join(
                self.output_dir, 
                f"{clean_name}_{style}_{timestamp}.png"
            )
            
            # Generate the image
            logger.info(f"Generating image with prompt: {prompt[:100]}...")
            result = self.openai.generate_image(
                prompt=prompt,
                save_path=save_path,
                style="natural",
                size="1024x1024"
            )
            
            if result:
                logger.info(f"Image generated successfully using {result.get('image_generator', 'unknown')} model")
                
                return {
                    'path': save_path,
                    'generator': result.get('image_generator', 'unknown'),
                    'prompt': prompt
                }
            else:
                logger.error("Image generation failed")
                return None
                
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            return None
    
    def _save_linkedin_post(self, 
                            client_name: str, 
                            caption: str, 
                            image_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Save the LinkedIn post content to file."""
        try:
            # Clean the client name for filename
            clean_name = re.sub(r'[^\w\s-]', '', client_name).strip().replace(' ', '_').lower()
            
            # Create timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Define save path for caption
            caption_path = os.path.join(
                self.output_dir, 
                f"{clean_name}_linkedin_{timestamp}.txt"
            )
            
            # Save caption
            with open(caption_path, 'w', encoding='utf-8') as f:
                f.write(caption)
            
            # Create metadata
            metadata = {
                'client': client_name,
                'timestamp': timestamp,
                'caption_path': caption_path,
                'generated_at': datetime.now().isoformat()
            }
            
            # Add image info if available
            if image_info:
                metadata['image_path'] = image_info['path']
                metadata['image_generator'] = image_info['generator']
            
            # Save metadata
            metadata_path = os.path.join(
                self.output_dir, 
                f"{clean_name}_linkedin_{timestamp}_metadata.json"
            )
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"LinkedIn post saved: {caption_path}")
            if image_info:
                logger.info(f"LinkedIn image saved: {image_info['path']}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error saving LinkedIn post: {str(e)}")
            return {}
    
    def generate_from_report(self, 
                           report_path: str, 
                           client_name: Optional[str] = None,
                           style: str = 'corporate',
                           with_image: bool = True) -> Dict[str, Any]:
        """Generate a LinkedIn post from a report file."""
        try:
            # Extract content from report
            content = self._extract_content_from_file(report_path)
            if not content:
                logger.error(f"No content found in report: {report_path}")
                return {}
            
            # If client name not provided, try to extract from content
            if not client_name:
                # Simple heuristic - look for first name followed by "Report"
                match = re.search(r'([\w\s]+)\s+Report', content[:500])
                if match:
                    client_name = match.group(1).strip()
                else:
                    # Use filename as fallback
                    client_name = os.path.basename(report_path).split('_')[0].capitalize()
            
            # Extract key points
            key_points = self._extract_key_points(content)
            if not key_points:
                logger.warning(f"No key points extracted from report: {report_path}")
                # Create some generic points to continue
                key_points = [
                    "Market insights from the GCC region",
                    "Latest trends affecting businesses",
                    "Strategic opportunities in the Gulf market"
                ]
            
            # Generate LinkedIn caption
            caption = self._generate_linkedin_caption(client_name, content, key_points, style)
            
            # Generate image if requested
            image_info = None
            if with_image:
                image_prompt = self._generate_image_prompt(client_name, key_points, style)
                image_info = self._generate_image(image_prompt, client_name, style)
            
            # Save the post
            metadata = self._save_linkedin_post(client_name, caption, image_info)
            
            result = {
                'client_name': client_name,
                'caption': caption,
                'key_points': key_points,
                'metadata': metadata
            }
            
            if image_info:
                result['image_path'] = image_info['path']
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating LinkedIn post from report: {str(e)}")
            return {}
    
    def generate_from_custom_input(self,
                                client_name: str,
                                input_text: str,
                                style: str = 'corporate',
                                with_image: bool = True) -> Dict[str, Any]:
        """Generate a LinkedIn post from custom input text."""
        try:
            # Extract key points
            key_points = self._extract_key_points(input_text)
            if not key_points:
                logger.warning(f"No key points extracted from custom input")
                # Create some generic points to continue
                key_points = [
                    "Market insights from the GCC region",
                    "Latest trends affecting businesses",
                    "Strategic opportunities in the Gulf market"
                ]
            
            # Generate LinkedIn caption
            caption = self._generate_linkedin_caption(client_name, input_text, key_points, style)
            
            # Generate image if requested
            image_info = None
            if with_image:
                image_prompt = self._generate_image_prompt(client_name, key_points, style)
                image_info = self._generate_image(image_prompt, client_name, style)
            
            # Save the post
            metadata = self._save_linkedin_post(client_name, caption, image_info)
            
            result = {
                'client_name': client_name,
                'caption': caption,
                'key_points': key_points,
                'metadata': metadata
            }
            
            if image_info:
                result['image_path'] = image_info['path']
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating LinkedIn post from custom input: {str(e)}")
            return {}

def main():
    """Main function to parse arguments and execute commands."""
    parser = argparse.ArgumentParser(description='LinkedIn Post Generator with AI-Generated Visuals')
    
    # Input sources
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--from-report', type=str, help='Path to a report file')
    input_group.add_argument('--from-text', type=str, help='Custom text input for post generation')
    
    # Client information
    parser.add_argument('--client', type=str, help='Client name')
    
    # Style options
    parser.add_argument('--style', type=str, choices=['corporate', 'casual', 'informative', 'modern', 'bold'],
                        default='corporate', help='Style for the post and image')
    
    # Image generation
    parser.add_argument('--with-image', action='store_true', help='Generate an AI image for the post')
    parser.add_argument('--no-image', dest='with_image', action='store_false', help='Skip image generation')
    parser.set_defaults(with_image=True)
    
    args = parser.parse_args()
    
    # Initialize generator
    generator = LinkedInPostGenerator()
    
    # Generate the post based on input source
    result = {}
    if args.from_report:
        if not os.path.exists(args.from_report):
            print(f"Error: Report file not found: {args.from_report}")
            return 1
        
        result = generator.generate_from_report(
            report_path=args.from_report,
            client_name=args.client,
            style=args.style,
            with_image=args.with_image
        )
    
    elif args.from_text:
        if not args.client:
            print("Error: Client name is required when using custom text input.")
            return 1
        
        result = generator.generate_from_custom_input(
            client_name=args.client,
            input_text=args.from_text,
            style=args.style,
            with_image=args.with_image
        )
    
    # Display result
    if result:
        print("\n=== LinkedIn Post Generated ===")
        print(f"Client: {result.get('client_name', 'Unknown')}")
        
        print("\nCaption:")
        print("-" * 40)
        print(result.get('caption', 'No caption generated'))
        print("-" * 40)
        
        if 'image_path' in result:
            print(f"\nImage saved to: {result['image_path']}")
        
        if 'metadata' in result and 'caption_path' in result['metadata']:
            print(f"\nPost saved to: {result['metadata']['caption_path']}")
        
        return 0
    else:
        print("Error: Failed to generate LinkedIn post.")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 