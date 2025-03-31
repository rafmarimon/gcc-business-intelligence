#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Client Management Utility

This script provides functionality to manage client profiles, including:
- Adding/removing clients
- Managing client tags and interests
- Viewing client information
"""

import os
import sys
import json
import argparse
import logging
from typing import List, Dict, Any, Optional

# Ensure proper imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import required modules
try:
    from src.models.client_model import ClientModel
    from src.utils.redis_cache import RedisCache
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Error importing required modules: {str(e)}")
    print("Make sure you're running from the project root and dependencies are installed.")
    sys.exit(1)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def list_clients():
    """List all available clients."""
    client_model = ClientModel()
    clients = client_model.get_all_clients()
    
    if not clients:
        print("No clients found.")
        return
    
    print("\n=== Available Clients ===")
    for client in clients:
        print(f"ID: {client.get('id', 'N/A')}")
        print(f"Name: {client.get('name', 'N/A')}")
        print(f"Industry: {client.get('industry', 'N/A')}")
        print(f"Interests: {', '.join(client.get('interests_list', []))}")
        print("-" * 30)

def get_client(client_name_or_id):
    """Get a specific client by name or ID."""
    client_model = ClientModel()
    
    # Try to find by ID first
    client = client_model.get_client_by_id(client_name_or_id)
    
    # If not found, try by name
    if not client:
        clients = client_model.get_all_clients()
        for c in clients:
            if c.get('name', '').lower() == client_name_or_id.lower():
                client = c
                break
    
    if not client:
        print(f"Client not found: {client_name_or_id}")
        return None
    
    return client

def display_client(client):
    """Display client information in a formatted way."""
    if not client:
        return
    
    print("\n=== Client Information ===")
    print(f"ID: {client.get('id', 'N/A')}")
    print(f"Name: {client.get('name', 'N/A')}")
    print(f"Industry: {client.get('industry', 'N/A')}")
    
    # Display interests/tags by category if available
    interests = client.get('interests_list', [])
    if interests:
        print("\nInterests/Tags:")
        print(f"  All tags: {', '.join(interests)}")
    
    # Display categorized tags if available
    categories = client.get('tag_categories', {})
    if categories:
        print("\nCategorized Tags:")
        for category, tags in categories.items():
            print(f"  {category}: {', '.join(tags)}")
    
    print("-" * 30)

def add_tag(client_name_or_id, tag, category=None):
    """Add a tag to a client."""
    client_model = ClientModel()
    client = get_client(client_name_or_id)
    
    if not client:
        return False
    
    client_id = client.get('id')
    
    # Get current interests
    interests = client.get('interests_list', [])
    
    # Add the tag if it doesn't already exist
    if tag not in interests:
        interests.append(tag)
        
        # Update client interests
        client_model.update_client(client_id, {'interests_list': interests})
        
        # Also update categorized tags if a category is provided
        if category:
            categories = client.get('tag_categories', {})
            if category not in categories:
                categories[category] = []
            
            if tag not in categories[category]:
                categories[category].append(tag)
                client_model.update_client(client_id, {'tag_categories': categories})
        
        print(f"Added tag '{tag}' to client '{client.get('name')}'")
        if category:
            print(f"Tag added to category '{category}'")
        return True
    else:
        print(f"Tag '{tag}' already exists for client '{client.get('name')}'")
        return False

def remove_tag(client_name_or_id, tag, category=None):
    """Remove a tag from a client."""
    client_model = ClientModel()
    client = get_client(client_name_or_id)
    
    if not client:
        return False
    
    client_id = client.get('id')
    
    # Get current interests
    interests = client.get('interests_list', [])
    
    # Remove the tag if it exists
    if tag in interests:
        interests.remove(tag)
        
        # Update client interests
        client_model.update_client(client_id, {'interests_list': interests})
        
        # Also update categorized tags if needed
        if category:
            categories = client.get('tag_categories', {})
            if category in categories and tag in categories[category]:
                categories[category].remove(tag)
                client_model.update_client(client_id, {'tag_categories': categories})
        
        print(f"Removed tag '{tag}' from client '{client.get('name')}'")
        return True
    else:
        print(f"Tag '{tag}' does not exist for client '{client.get('name')}'")
        return False

def list_tags(client_name_or_id):
    """List all tags for a client."""
    client = get_client(client_name_or_id)
    
    if not client:
        return
    
    interests = client.get('interests_list', [])
    print(f"\nTags for client '{client.get('name')}':")
    
    if not interests:
        print("  No tags found.")
        return
    
    for interest in interests:
        print(f"  - {interest}")
    
    # List categorized tags if available
    categories = client.get('tag_categories', {})
    if categories:
        print("\nTags by category:")
        for category, tags in categories.items():
            print(f"  {category}: {', '.join(tags)}")

def create_client(name, industry, interests=None):
    """Create a new client."""
    client_model = ClientModel()
    
    # Check if client already exists
    clients = client_model.get_all_clients()
    for client in clients:
        if client.get('name', '').lower() == name.lower():
            print(f"Client '{name}' already exists.")
            return None
    
    # Prepare client data
    client_data = {
        'name': name,
        'industry': industry,
        'interests_list': interests or []
    }
    
    # Create the client
    client_id = client_model.create_client(client_data)
    if client_id:
        print(f"Created client '{name}' with ID {client_id}")
        return client_id
    else:
        print(f"Failed to create client '{name}'")
        return None

def update_client(client_name_or_id, field, value):
    """Update a client field."""
    client_model = ClientModel()
    client = get_client(client_name_or_id)
    
    if not client:
        return False
    
    client_id = client.get('id')
    
    # Handle special case for interests_list
    if field == 'interests' or field == 'tags':
        field = 'interests_list'
        value = value.split(',')
        value = [tag.strip() for tag in value]
    
    # Update the client
    result = client_model.update_client(client_id, {field: value})
    if result:
        print(f"Updated {field} for client '{client.get('name')}'")
        return True
    else:
        print(f"Failed to update {field} for client '{client.get('name')}'")
        return False

def categorize_tags(client_name_or_id):
    """Automatically categorize existing tags into industries, regions, topics."""
    client = get_client(client_name_or_id)
    client_model = ClientModel()
    
    if not client:
        return False
    
    client_id = client.get('id')
    interests = client.get('interests_list', [])
    
    # Define category keywords
    categories = {
        'industries': [
            'technology', 'tech', 'cloud', 'software', 'hardware', 'banking', 
            'finance', 'financial', 'insurance', 'healthcare', 'retail', 'food', 
            'beverage', 'consumer goods', 'manufacturing', 'automotive', 
            'telecom', 'media', 'entertainment', 'energy', 'oil', 'gas',
            'advertising', 'marketing', 'digital'
        ],
        'regions': [
            'uae', 'dubai', 'abu dhabi', 'saudi', 'ksa', 'qatar', 'kuwait', 
            'bahrain', 'oman', 'gcc', 'middle east', 'mena', 'gulf',
            'sharjah', 'riyadh', 'jeddah', 'doha', 'muscat', 'manama'
        ],
        'topics': [
            'regulation', 'policy', 'law', 'compliance', 'market', 'trend', 
            'competition', 'competitor', 'investment', 'startup', 'innovation',
            'sustainability', 'esg', 'climate', 'green', 'digital transformation',
            'ai', 'artificial intelligence', 'machine learning', 'big data',
            'iot', 'internet of things', 'blockchain', 'crypto', 'cybersecurity'
        ]
    }
    
    # Initialize categorized tags
    categorized = {category: [] for category in categories}
    
    # Categorize each interest
    for interest in interests:
        interest_lower = interest.lower()
        
        # Check each category
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in interest_lower:
                    if interest not in categorized[category]:
                        categorized[category].append(interest)
                    break
    
    # Add an "other" category for uncategorized tags
    categorized['other'] = [
        interest for interest in interests 
        if not any(interest in category_tags for category_tags in categorized.values())
    ]
    
    # Update client with categorized tags
    result = client_model.update_client(client_id, {'tag_categories': categorized})
    if result:
        print(f"Tags categorized for client '{client.get('name')}'")
        
        # Show the categorization
        for category, tags in categorized.items():
            if tags:
                print(f"  {category}: {', '.join(tags)}")
        
        return True
    else:
        print(f"Failed to categorize tags for client '{client.get('name')}'")
        return False

def main():
    """Main function to parse arguments and execute commands."""
    parser = argparse.ArgumentParser(description='Client management utility')
    
    # Client selection
    parser.add_argument('--client', type=str, help='Client name or ID')
    parser.add_argument('--list-clients', action='store_true', help='List all clients')
    
    # Client creation/update
    parser.add_argument('--create', action='store_true', help='Create a new client')
    parser.add_argument('--name', type=str, help='Client name (for creation)')
    parser.add_argument('--industry', type=str, help='Client industry (for creation)')
    parser.add_argument('--update-field', type=str, help='Field to update')
    parser.add_argument('--value', type=str, help='New value for field')
    
    # Tag management
    parser.add_argument('--add-tag', type=str, help='Add a tag to client')
    parser.add_argument('--remove-tag', type=str, help='Remove a tag from client')
    parser.add_argument('--list-tags', action='store_true', help='List all tags for client')
    parser.add_argument('--category', type=str, help='Tag category')
    parser.add_argument('--categorize-tags', action='store_true', help='Automatically categorize tags')
    
    args = parser.parse_args()
    
    # List all clients
    if args.list_clients:
        list_clients()
        return 0
    
    # Create a new client
    if args.create:
        if not args.name or not args.industry:
            print("Error: Name and industry are required for client creation.")
            return 1
        
        # Get initial interests if provided
        interests = []
        if args.add_tag:
            interests = [tag.strip() for tag in args.add_tag.split(',')]
        
        create_client(args.name, args.industry, interests)
        return 0
    
    # Client-specific actions
    if args.client:
        client = get_client(args.client)
        
        if not client:
            return 1
        
        # Display client info
        if not any([args.add_tag, args.remove_tag, args.list_tags, 
                   args.update_field, args.categorize_tags]):
            display_client(client)
            return 0
        
        # Add tag
        if args.add_tag:
            for tag in args.add_tag.split(','):
                add_tag(args.client, tag.strip(), args.category)
            return 0
        
        # Remove tag
        if args.remove_tag:
            for tag in args.remove_tag.split(','):
                remove_tag(args.client, tag.strip(), args.category)
            return 0
        
        # List tags
        if args.list_tags:
            list_tags(args.client)
            return 0
        
        # Update field
        if args.update_field and args.value:
            update_client(args.client, args.update_field, args.value)
            return 0
        
        # Categorize tags
        if args.categorize_tags:
            categorize_tags(args.client)
            return 0
    
    # No valid action specified
    parser.print_help()
    return 1

if __name__ == '__main__':
    sys.exit(main()) 