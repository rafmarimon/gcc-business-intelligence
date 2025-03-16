import os
import requests
from bs4 import BeautifulSoup
import re
import shutil
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LogoDownloader")

def download_logo(url="https://globalpossibilities.co/", output_dir="reports/assets/images"):
    """Download the logo from the Global Possibilities website."""
    try:
        logger.info(f"Attempting to download logo from {url}")
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Send a GET request to the website
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the logo image
        # Common patterns for logo elements:
        logo_candidates = []
        
        # Look for elements with "logo" in class or id
        logo_elements = soup.find_all(class_=re.compile(r'logo', re.I))
        logo_elements.extend(soup.find_all(id=re.compile(r'logo', re.I)))
        
        # Look for header/navbar images
        header_elements = soup.find_all(['header', 'nav'])
        for header in header_elements:
            logo_elements.extend(header.find_all('img'))
        
        # Extract image sources from the found elements
        for element in logo_elements:
            if element.name == 'img' and element.get('src'):
                logo_candidates.append(element.get('src'))
            else:
                imgs = element.find_all('img')
                for img in imgs:
                    if img.get('src'):
                        logo_candidates.append(img.get('src'))
        
        # Also check for SVG logos
        svg_elements = soup.find_all('svg')
        for svg in svg_elements:
            if 'logo' in str(svg).lower():
                # Save the SVG directly
                svg_path = os.path.join(output_dir, 'logo.svg')
                with open(svg_path, 'w') as f:
                    f.write(str(svg))
                logger.info(f"SVG logo saved to {svg_path}")
                return svg_path
        
        if not logo_candidates:
            logger.warning("No logo candidates found.")
            return None
        
        # Filter out duplicates and non-image URLs
        logo_candidates = list(set(logo_candidates))
        filtered_candidates = [
            url for url in logo_candidates 
            if any(ext in url.lower() for ext in ['.png', '.jpg', '.jpeg', '.svg', '.gif', '.webp'])
        ]
        
        if not filtered_candidates:
            # Handle relative URLs
            filtered_candidates = logo_candidates
        
        logger.info(f"Found {len(filtered_candidates)} potential logo images")
        
        # Download each potential logo
        for i, img_url in enumerate(filtered_candidates):
            try:
                # Handle relative URLs
                if not img_url.startswith(('http://', 'https://')):
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif img_url.startswith('/'):
                        img_url = url.rstrip('/') + img_url
                    else:
                        img_url = url.rstrip('/') + '/' + img_url
                
                # Get the filename from the URL
                filename = os.path.basename(img_url.split('?')[0])
                if not filename.endswith(('.png', '.jpg', '.jpeg', '.svg', '.gif', '.webp')):
                    # Add a default extension if none is present
                    filename = f"logo_{i}.png"
                
                # Download the image
                img_response = requests.get(img_url, headers=headers, stream=True)
                img_response.raise_for_status()
                
                img_path = os.path.join(output_dir, filename)
                with open(img_path, 'wb') as f:
                    img_response.raw.decode_content = True
                    shutil.copyfileobj(img_response.raw, f)
                
                logger.info(f"Downloaded logo: {img_path}")
                
                # Return the path of the first successfully downloaded logo
                return img_path
            
            except Exception as e:
                logger.error(f"Error downloading logo {img_url}: {e}")
        
        return None
    
    except Exception as e:
        logger.error(f"Error downloading logo: {e}")
        return None

if __name__ == "__main__":
    logo_path = download_logo()
    if logo_path:
        print(f"Logo downloaded successfully: {logo_path}")
    else:
        print("Failed to download logo.") 