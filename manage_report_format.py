#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Report Format Manager

This script manages report output format settings and branding options.
It allows users to define templates, styles, and branding for GCC reports.
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# Ensure proper imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import required modules
try:
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

log_filename = os.path.join(log_dir, f'format_manager_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ReportFormatManager:
    """Manages report formats, templates, and branding options."""
    
    def __init__(self):
        """Initialize the format manager."""
        # Initialize Redis cache
        self.redis = RedisCache()
        
        # Define storage directories
        templates_dir = os.environ.get('TEMPLATES_DIR', 'src/templates')
        self.templates_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), templates_dir))
        
        assets_dir = os.environ.get('ASSETS_DIR', 'src/static/assets')
        self.assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), assets_dir))
        
        # Create directories if they don't exist
        os.makedirs(os.path.join(self.templates_dir, 'report_templates'), exist_ok=True)
        os.makedirs(os.path.join(self.assets_dir, 'logos'), exist_ok=True)
        os.makedirs(os.path.join(self.assets_dir, 'css'), exist_ok=True)
        
        # Default format settings
        self.default_format = {
            'name': 'default',
            'template': 'standard',
            'css_theme': 'default',
            'logo': None,
            'header': 'GCC Market Intelligence Report',
            'footer': '© {{current_year}} GCC Market Intelligence',
            'accent_color': '#2c3e50',
            'secondary_color': '#3498db',
            'font_family': 'Arial, Helvetica, sans-serif',
            'include_toc': True,
            'output_formats': ['html', 'pdf'],
            'page_size': 'A4',
            'margin': '1in',
            'enable_charts': True,
            'client_customized': False
        }
        
        # Initialize default format if not exists
        if not self.redis.get('report_format:default'):
            self.redis.set('report_format:default', self.default_format)
            logger.info("Initialized default report format")
        
        logger.info("Report format manager initialized")
    
    def list_formats(self) -> List[Dict[str, Any]]:
        """List all available report formats."""
        # Get all keys with the report_format: prefix
        format_keys = self.redis.scan('report_format:*')
        
        formats = []
        for key in format_keys:
            format_data = self.redis.get(key)
            if format_data:
                # Add format_id to the data
                format_id = key.split(':', 1)[1]
                format_data['id'] = format_id
                formats.append(format_data)
        
        return formats
    
    def get_format(self, format_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific report format by ID."""
        format_data = self.redis.get(f'report_format:{format_id}')
        if not format_data:
            logger.warning(f"Format not found: {format_id}")
            return None
        
        # Add format_id to the data
        format_data['id'] = format_id
        return format_data
    
    def create_format(self, format_data: Dict[str, Any]) -> str:
        """Create a new report format."""
        # Validate required fields
        required_fields = ['name']
        for field in required_fields:
            if field not in format_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Create new format with default values
        new_format = self.default_format.copy()
        new_format.update(format_data)
        
        # Generate ID from name if not provided
        format_id = format_data.get('id', format_data['name'].lower().replace(' ', '_'))
        
        # Save to Redis
        self.redis.set(f'report_format:{format_id}', new_format)
        logger.info(f"Created report format: {format_id}")
        
        return format_id
    
    def update_format(self, format_id: str, format_data: Dict[str, Any]) -> bool:
        """Update an existing report format."""
        existing_format = self.redis.get(f'report_format:{format_id}')
        if not existing_format:
            logger.warning(f"Format not found: {format_id}")
            return False
        
        # Update existing format
        updated_format = existing_format.copy()
        updated_format.update(format_data)
        
        # Save to Redis
        self.redis.set(f'report_format:{format_id}', updated_format)
        logger.info(f"Updated report format: {format_id}")
        
        return True
    
    def delete_format(self, format_id: str) -> bool:
        """Delete a report format."""
        if format_id == 'default':
            logger.warning("Cannot delete default format")
            return False
        
        existing_format = self.redis.get(f'report_format:{format_id}')
        if not existing_format:
            logger.warning(f"Format not found: {format_id}")
            return False
        
        # Delete from Redis
        self.redis.delete(f'report_format:{format_id}')
        logger.info(f"Deleted report format: {format_id}")
        
        return True
    
    def list_templates(self) -> List[str]:
        """List all available report templates."""
        templates_path = os.path.join(self.templates_dir, 'report_templates')
        templates = []
        
        for file in os.listdir(templates_path):
            if file.endswith('.html') or file.endswith('.jinja'):
                templates.append(file.rsplit('.', 1)[0])
        
        return templates
    
    def get_template_content(self, template_name: str) -> Optional[str]:
        """Get the content of a template."""
        # Check for HTML and Jinja extensions
        for ext in ['.html', '.jinja']:
            template_path = os.path.join(self.templates_dir, 'report_templates', f"{template_name}{ext}")
            if os.path.isfile(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    return f.read()
        
        logger.warning(f"Template not found: {template_name}")
        return None
    
    def save_template(self, template_name: str, content: str, overwrite: bool = False) -> bool:
        """Save a template."""
        template_path = os.path.join(self.templates_dir, 'report_templates', f"{template_name}.html")
        
        # Check if file exists and overwrite flag
        if os.path.isfile(template_path) and not overwrite:
            logger.warning(f"Template already exists: {template_name}")
            return False
        
        # Save template
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Saved template: {template_name}")
        return True
    
    def delete_template(self, template_name: str) -> bool:
        """Delete a template."""
        # Check for HTML and Jinja extensions
        for ext in ['.html', '.jinja']:
            template_path = os.path.join(self.templates_dir, 'report_templates', f"{template_name}{ext}")
            if os.path.isfile(template_path):
                os.remove(template_path)
                logger.info(f"Deleted template: {template_name}")
                return True
        
        logger.warning(f"Template not found: {template_name}")
        return False
    
    def list_css_themes(self) -> List[str]:
        """List all available CSS themes."""
        css_path = os.path.join(self.assets_dir, 'css')
        themes = []
        
        for file in os.listdir(css_path):
            if file.endswith('.css'):
                themes.append(file.rsplit('.', 1)[0])
        
        return themes
    
    def get_css_content(self, theme_name: str) -> Optional[str]:
        """Get the content of a CSS theme."""
        css_path = os.path.join(self.assets_dir, 'css', f"{theme_name}.css")
        if not os.path.isfile(css_path):
            logger.warning(f"CSS theme not found: {theme_name}")
            return None
        
        with open(css_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def save_css_theme(self, theme_name: str, content: str, overwrite: bool = False) -> bool:
        """Save a CSS theme."""
        css_path = os.path.join(self.assets_dir, 'css', f"{theme_name}.css")
        
        # Check if file exists and overwrite flag
        if os.path.isfile(css_path) and not overwrite:
            logger.warning(f"CSS theme already exists: {theme_name}")
            return False
        
        # Save CSS theme
        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Saved CSS theme: {theme_name}")
        return True
    
    def delete_css_theme(self, theme_name: str) -> bool:
        """Delete a CSS theme."""
        css_path = os.path.join(self.assets_dir, 'css', f"{theme_name}.css")
        if not os.path.isfile(css_path):
            logger.warning(f"CSS theme not found: {theme_name}")
            return False
        
        os.remove(css_path)
        logger.info(f"Deleted CSS theme: {theme_name}")
        return True
    
    def list_logos(self) -> List[str]:
        """List all available logos."""
        logos_path = os.path.join(self.assets_dir, 'logos')
        logos = []
        
        for file in os.listdir(logos_path):
            if file.endswith(('.png', '.jpg', '.jpeg', '.svg')):
                logos.append(file)
        
        return logos
    
    def upload_logo(self, file_path: str, new_name: Optional[str] = None) -> Optional[str]:
        """Upload a logo."""
        if not os.path.isfile(file_path):
            logger.warning(f"File not found: {file_path}")
            return None
        
        # Get file extension
        _, ext = os.path.splitext(file_path)
        
        # Generate new name if not provided
        if not new_name:
            new_name = f"logo_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        elif not new_name.endswith(('.png', '.jpg', '.jpeg', '.svg')):
            new_name = f"{new_name}{ext}"
        
        # Copy logo to assets directory
        dest_path = os.path.join(self.assets_dir, 'logos', new_name)
        try:
            import shutil
            shutil.copy2(file_path, dest_path)
            logger.info(f"Uploaded logo: {new_name}")
            return new_name
        except Exception as e:
            logger.error(f"Error uploading logo: {str(e)}")
            return None
    
    def delete_logo(self, logo_name: str) -> bool:
        """Delete a logo."""
        logo_path = os.path.join(self.assets_dir, 'logos', logo_name)
        if not os.path.isfile(logo_path):
            logger.warning(f"Logo not found: {logo_name}")
            return False
        
        os.remove(logo_path)
        logger.info(f"Deleted logo: {logo_name}")
        return True
    
    def assign_format_to_client(self, client_id: str, format_id: str) -> bool:
        """Assign a format to a client."""
        # Verify format exists
        format_data = self.redis.get(f'report_format:{format_id}')
        if not format_data:
            logger.warning(f"Format not found: {format_id}")
            return False
        
        # Save client format preference
        self.redis.set(f'client:{client_id}:report_format', format_id)
        logger.info(f"Assigned format {format_id} to client {client_id}")
        
        return True
    
    def get_client_format(self, client_id: str) -> str:
        """Get the format assigned to a client."""
        format_id = self.redis.get(f'client:{client_id}:report_format')
        if not format_id:
            # Return default if not set
            return 'default'
        
        return format_id

def main():
    """Main function to parse arguments and execute commands."""
    parser = argparse.ArgumentParser(description='Report Format Manager')
    
    # Command selection
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List formats
    list_formats_parser = subparsers.add_parser('list-formats', help='List all report formats')
    
    # Get format
    get_format_parser = subparsers.add_parser('get-format', help='Get a specific report format')
    get_format_parser.add_argument('format_id', help='Format ID')
    
    # Create format
    create_format_parser = subparsers.add_parser('create-format', help='Create a new report format')
    create_format_parser.add_argument('name', help='Format name')
    create_format_parser.add_argument('--template', help='Template name')
    create_format_parser.add_argument('--css-theme', help='CSS theme name')
    create_format_parser.add_argument('--logo', help='Logo filename')
    create_format_parser.add_argument('--header', help='Report header text')
    create_format_parser.add_argument('--footer', help='Report footer text')
    create_format_parser.add_argument('--accent-color', help='Accent color (hex code)')
    create_format_parser.add_argument('--secondary-color', help='Secondary color (hex code)')
    create_format_parser.add_argument('--font-family', help='Font family')
    create_format_parser.add_argument('--include-toc', type=bool, help='Include table of contents')
    create_format_parser.add_argument('--output-formats', help='Comma-separated list of output formats')
    create_format_parser.add_argument('--page-size', help='Page size (e.g., A4, Letter)')
    create_format_parser.add_argument('--margin', help='Page margin (e.g., 1in, 2cm)')
    create_format_parser.add_argument('--enable-charts', type=bool, help='Enable charts')
    
    # Update format
    update_format_parser = subparsers.add_parser('update-format', help='Update an existing report format')
    update_format_parser.add_argument('format_id', help='Format ID')
    update_format_parser.add_argument('--name', help='Format name')
    update_format_parser.add_argument('--template', help='Template name')
    update_format_parser.add_argument('--css-theme', help='CSS theme name')
    update_format_parser.add_argument('--logo', help='Logo filename')
    update_format_parser.add_argument('--header', help='Report header text')
    update_format_parser.add_argument('--footer', help='Report footer text')
    update_format_parser.add_argument('--accent-color', help='Accent color (hex code)')
    update_format_parser.add_argument('--secondary-color', help='Secondary color (hex code)')
    update_format_parser.add_argument('--font-family', help='Font family')
    update_format_parser.add_argument('--include-toc', type=bool, help='Include table of contents')
    update_format_parser.add_argument('--output-formats', help='Comma-separated list of output formats')
    update_format_parser.add_argument('--page-size', help='Page size (e.g., A4, Letter)')
    update_format_parser.add_argument('--margin', help='Page margin (e.g., 1in, 2cm)')
    update_format_parser.add_argument('--enable-charts', type=bool, help='Enable charts')
    
    # Delete format
    delete_format_parser = subparsers.add_parser('delete-format', help='Delete a report format')
    delete_format_parser.add_argument('format_id', help='Format ID')
    
    # List templates
    list_templates_parser = subparsers.add_parser('list-templates', help='List all report templates')
    
    # Get template
    get_template_parser = subparsers.add_parser('get-template', help='Get a template content')
    get_template_parser.add_argument('template_name', help='Template name')
    
    # Save template
    save_template_parser = subparsers.add_parser('save-template', help='Save a template')
    save_template_parser.add_argument('template_name', help='Template name')
    save_template_parser.add_argument('file_path', help='Path to template file')
    save_template_parser.add_argument('--overwrite', action='store_true', help='Overwrite existing template')
    
    # Delete template
    delete_template_parser = subparsers.add_parser('delete-template', help='Delete a template')
    delete_template_parser.add_argument('template_name', help='Template name')
    
    # List CSS themes
    list_css_parser = subparsers.add_parser('list-css', help='List all CSS themes')
    
    # Get CSS theme
    get_css_parser = subparsers.add_parser('get-css', help='Get a CSS theme content')
    get_css_parser.add_argument('theme_name', help='Theme name')
    
    # Save CSS theme
    save_css_parser = subparsers.add_parser('save-css', help='Save a CSS theme')
    save_css_parser.add_argument('theme_name', help='Theme name')
    save_css_parser.add_argument('file_path', help='Path to CSS file')
    save_css_parser.add_argument('--overwrite', action='store_true', help='Overwrite existing theme')
    
    # Delete CSS theme
    delete_css_parser = subparsers.add_parser('delete-css', help='Delete a CSS theme')
    delete_css_parser.add_argument('theme_name', help='Theme name')
    
    # List logos
    list_logos_parser = subparsers.add_parser('list-logos', help='List all logos')
    
    # Upload logo
    upload_logo_parser = subparsers.add_parser('upload-logo', help='Upload a logo')
    upload_logo_parser.add_argument('file_path', help='Path to logo file')
    upload_logo_parser.add_argument('--name', help='New name for the logo')
    
    # Delete logo
    delete_logo_parser = subparsers.add_parser('delete-logo', help='Delete a logo')
    delete_logo_parser.add_argument('logo_name', help='Logo name')
    
    # Assign format to client
    assign_format_parser = subparsers.add_parser('assign-format', help='Assign a format to a client')
    assign_format_parser.add_argument('client_id', help='Client ID')
    assign_format_parser.add_argument('format_id', help='Format ID')
    
    # Get client format
    get_client_format_parser = subparsers.add_parser('get-client-format', help='Get the format assigned to a client')
    get_client_format_parser.add_argument('client_id', help='Client ID')
    
    # Output options
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    args = parser.parse_args()
    
    # Initialize format manager
    manager = ReportFormatManager()
    
    # Execute command
    result = None
    
    if args.command == 'list-formats':
        formats = manager.list_formats()
        if args.json:
            result = {'formats': formats}
        else:
            print("Available report formats:")
            for fmt in formats:
                print(f"  {fmt['id']}: {fmt['name']}")
                print(f"    Template: {fmt['template']}")
                print(f"    CSS Theme: {fmt['css_theme']}")
                print(f"    Logo: {fmt['logo'] or 'None'}")
                print()
    
    elif args.command == 'get-format':
        format_data = manager.get_format(args.format_id)
        if format_data:
            if args.json:
                result = format_data
            else:
                print(f"Format: {format_data['id']} ({format_data['name']})")
                for key, value in format_data.items():
                    if key not in ['id', 'name']:
                        print(f"  {key}: {value}")
        else:
            print(f"Format not found: {args.format_id}")
            return 1
    
    elif args.command == 'create-format':
        format_data = {'name': args.name}
        
        # Add optional parameters
        if args.template:
            format_data['template'] = args.template
        if args.css_theme:
            format_data['css_theme'] = args.css_theme
        if args.logo:
            format_data['logo'] = args.logo
        if args.header:
            format_data['header'] = args.header
        if args.footer:
            format_data['footer'] = args.footer
        if args.accent_color:
            format_data['accent_color'] = args.accent_color
        if args.secondary_color:
            format_data['secondary_color'] = args.secondary_color
        if args.font_family:
            format_data['font_family'] = args.font_family
        if args.include_toc is not None:
            format_data['include_toc'] = args.include_toc
        if args.output_formats:
            format_data['output_formats'] = args.output_formats.split(',')
        if args.page_size:
            format_data['page_size'] = args.page_size
        if args.margin:
            format_data['margin'] = args.margin
        if args.enable_charts is not None:
            format_data['enable_charts'] = args.enable_charts
        
        try:
            format_id = manager.create_format(format_data)
            if args.json:
                result = {'format_id': format_id, 'success': True}
            else:
                print(f"Created format: {format_id}")
        except ValueError as e:
            print(f"Error: {str(e)}")
            return 1
    
    elif args.command == 'update-format':
        format_data = {}
        
        # Add optional parameters
        if args.name:
            format_data['name'] = args.name
        if args.template:
            format_data['template'] = args.template
        if args.css_theme:
            format_data['css_theme'] = args.css_theme
        if args.logo:
            format_data['logo'] = args.logo
        if args.header:
            format_data['header'] = args.header
        if args.footer:
            format_data['footer'] = args.footer
        if args.accent_color:
            format_data['accent_color'] = args.accent_color
        if args.secondary_color:
            format_data['secondary_color'] = args.secondary_color
        if args.font_family:
            format_data['font_family'] = args.font_family
        if args.include_toc is not None:
            format_data['include_toc'] = args.include_toc
        if args.output_formats:
            format_data['output_formats'] = args.output_formats.split(',')
        if args.page_size:
            format_data['page_size'] = args.page_size
        if args.margin:
            format_data['margin'] = args.margin
        if args.enable_charts is not None:
            format_data['enable_charts'] = args.enable_charts
        
        if not format_data:
            print("Error: No updates specified")
            return 1
        
        success = manager.update_format(args.format_id, format_data)
        if success:
            if args.json:
                result = {'format_id': args.format_id, 'success': True}
            else:
                print(f"Updated format: {args.format_id}")
        else:
            print(f"Format not found: {args.format_id}")
            return 1
    
    elif args.command == 'delete-format':
        success = manager.delete_format(args.format_id)
        if success:
            if args.json:
                result = {'format_id': args.format_id, 'success': True}
            else:
                print(f"Deleted format: {args.format_id}")
        else:
            print(f"Error deleting format: {args.format_id}")
            return 1
    
    elif args.command == 'list-templates':
        templates = manager.list_templates()
        if args.json:
            result = {'templates': templates}
        else:
            print("Available templates:")
            for template in templates:
                print(f"  {template}")
    
    elif args.command == 'get-template':
        content = manager.get_template_content(args.template_name)
        if content:
            if args.json:
                result = {'template': args.template_name, 'content': content}
            else:
                print(f"Template: {args.template_name}")
                print(content)
        else:
            print(f"Template not found: {args.template_name}")
            return 1
    
    elif args.command == 'save-template':
        # Read template content from file
        try:
            with open(args.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file: {str(e)}")
            return 1
        
        success = manager.save_template(args.template_name, content, args.overwrite)
        if success:
            if args.json:
                result = {'template': args.template_name, 'success': True}
            else:
                print(f"Saved template: {args.template_name}")
        else:
            print(f"Error saving template: {args.template_name}")
            return 1
    
    elif args.command == 'delete-template':
        success = manager.delete_template(args.template_name)
        if success:
            if args.json:
                result = {'template': args.template_name, 'success': True}
            else:
                print(f"Deleted template: {args.template_name}")
        else:
            print(f"Template not found: {args.template_name}")
            return 1
    
    elif args.command == 'list-css':
        themes = manager.list_css_themes()
        if args.json:
            result = {'themes': themes}
        else:
            print("Available CSS themes:")
            for theme in themes:
                print(f"  {theme}")
    
    elif args.command == 'get-css':
        content = manager.get_css_content(args.theme_name)
        if content:
            if args.json:
                result = {'theme': args.theme_name, 'content': content}
            else:
                print(f"CSS Theme: {args.theme_name}")
                print(content)
        else:
            print(f"CSS theme not found: {args.theme_name}")
            return 1
    
    elif args.command == 'save-css':
        # Read CSS content from file
        try:
            with open(args.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file: {str(e)}")
            return 1
        
        success = manager.save_css_theme(args.theme_name, content, args.overwrite)
        if success:
            if args.json:
                result = {'theme': args.theme_name, 'success': True}
            else:
                print(f"Saved CSS theme: {args.theme_name}")
        else:
            print(f"Error saving CSS theme: {args.theme_name}")
            return 1
    
    elif args.command == 'delete-css':
        success = manager.delete_css_theme(args.theme_name)
        if success:
            if args.json:
                result = {'theme': args.theme_name, 'success': True}
            else:
                print(f"Deleted CSS theme: {args.theme_name}")
        else:
            print(f"CSS theme not found: {args.theme_name}")
            return 1
    
    elif args.command == 'list-logos':
        logos = manager.list_logos()
        if args.json:
            result = {'logos': logos}
        else:
            print("Available logos:")
            for logo in logos:
                print(f"  {logo}")
    
    elif args.command == 'upload-logo':
        logo_name = manager.upload_logo(args.file_path, args.name)
        if logo_name:
            if args.json:
                result = {'logo': logo_name, 'success': True}
            else:
                print(f"Uploaded logo: {logo_name}")
        else:
            print("Error uploading logo")
            return 1
    
    elif args.command == 'delete-logo':
        success = manager.delete_logo(args.logo_name)
        if success:
            if args.json:
                result = {'logo': args.logo_name, 'success': True}
            else:
                print(f"Deleted logo: {args.logo_name}")
        else:
            print(f"Logo not found: {args.logo_name}")
            return 1
    
    elif args.command == 'assign-format':
        success = manager.assign_format_to_client(args.client_id, args.format_id)
        if success:
            if args.json:
                result = {'client_id': args.client_id, 'format_id': args.format_id, 'success': True}
            else:
                print(f"Assigned format {args.format_id} to client {args.client_id}")
        else:
            print(f"Error assigning format: Format {args.format_id} not found")
            return 1
    
    elif args.command == 'get-client-format':
        format_id = manager.get_client_format(args.client_id)
        if args.json:
            result = {'client_id': args.client_id, 'format_id': format_id}
        else:
            print(f"Client {args.client_id} uses format: {format_id}")
    
    else:
        parser.print_help()
        return 1
    
    # Output JSON if requested
    if args.json and result:
        print(json.dumps(result, indent=2))
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 