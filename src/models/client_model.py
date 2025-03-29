#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Client Model Module for Market Intelligence Platform.

This module provides functionality for managing client profiles in Redis,
including storage, retrieval, and updating of client information.
"""

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from src.utils.redis_cache import get_redis_cache

# Configure logging
logger = logging.getLogger(__name__)

class ClientModel:
    """
    Client Model for managing client profiles in Redis.
    
    Attributes:
        redis_cache: Redis cache instance for storing client data
    """
    
    def __init__(self):
        """Initialize the ClientModel."""
        self.redis_cache = get_redis_cache()
        logger.info("ClientModel initialized")
    
    def create_client(self, name: str, industry: Optional[str] = None, interests: Optional[List[str]] = None, 
                     contact_email: Optional[str] = None, website: Optional[str] = None,
                     sources: Optional[List[str]] = None, description: Optional[str] = None,
                     metadata: Optional[Dict[str, Any]] = None,
                     additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new client profile.
        
        Args:
            name: Client name
            industry: Client industry
            interests: List of client interests/topics
            contact_email: Optional contact email
            website: Optional client website
            sources: Optional list of news sources to crawl
            description: Optional client description
            metadata: Optional metadata dictionary
            additional_data: Optional additional client data
            
        Returns:
            The created client profile data
        """
        # Generate a unique ID for this client
        client_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Set default values if not provided
        interests = interests or []
        industry = industry or ""
        sources = sources or []
        
        # Normalize interests (lowercase and remove duplicates)
        normalized_interests = list(set([i.lower().strip() for i in interests if i.strip()]))
        
        # Clean up sources list
        normalized_sources = list(set([s.strip() for s in sources if s.strip()]))
        
        # Create client object
        client = {
            "id": client_id,
            "name": name,
            "industry": industry,
            "interests": normalized_interests,
            "sources": normalized_sources,
            "created_at": timestamp,
            "updated_at": timestamp,
            "active": True
        }
        
        # Add optional fields
        if contact_email:
            client["contact_email"] = contact_email
            
        if website:
            client["website"] = website
            
        if description:
            client["description"] = description
            
        # Add metadata if provided
        if metadata:
            for key, value in metadata.items():
                if key not in client:  # Don't overwrite existing fields
                    client[key] = value
        
        # Add any additional data
        if additional_data:
            for key, value in additional_data.items():
                if key not in client:  # Don't overwrite existing fields
                    client[key] = value
        
        # Store in Redis
        client_key = f"client:{client_id}"
        self.redis_cache.set(client_key, client)
        
        # Add to client index
        client_index_key = "clients:all"
        client_index = self.redis_cache.get(client_index_key) or []
        client_index.append(client_id)
        self.redis_cache.set(client_index_key, client_index)
        
        # Index by interests
        for interest in normalized_interests:
            interest_key = f"interest:{interest}"
            interest_clients = self.redis_cache.get(interest_key) or []
            if client_id not in interest_clients:
                interest_clients.append(client_id)
                self.redis_cache.set(interest_key, interest_clients)
        
        # Index by industry
        if industry:
            industry_key = f"industry:{industry.lower()}"
            industry_clients = self.redis_cache.get(industry_key) or []
            if client_id not in industry_clients:
                industry_clients.append(client_id)
                self.redis_cache.set(industry_key, industry_clients)
        
        logger.info(f"Created new client: {name} (ID: {client_id})")
        return client
    
    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a client by ID.
        
        Args:
            client_id: The client ID
            
        Returns:
            The client profile data or None if not found
        """
        client_key = f"client:{client_id}"
        client = self.redis_cache.get(client_key)
        
        if not client:
            logger.warning(f"Client not found: {client_id}")
            return None
        
        return client
    
    def update_client(self, client_id: str, 
                     name: Optional[str] = None,
                     industry: Optional[str] = None,
                     interests: Optional[List[str]] = None,
                     contact_email: Optional[str] = None,
                     website: Optional[str] = None,
                     sources: Optional[List[str]] = None,
                     description: Optional[str] = None,
                     active: Optional[bool] = None,
                     additional_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Update an existing client profile.
        
        Args:
            client_id: The client ID
            name: Optional new name
            industry: Optional new industry
            interests: Optional new interests
            contact_email: Optional new contact email
            website: Optional new website
            sources: Optional new news sources
            description: Optional new description
            active: Optional new active status
            additional_data: Optional additional client data
            
        Returns:
            The updated client profile data or None if client not found
        """
        client = self.get_client(client_id)
        if not client:
            logger.error(f"Cannot update client - not found: {client_id}")
            return None
        
        # Track old interests and industry for indexing updates
        old_interests = client.get("interests", [])
        old_industry = client.get("industry", "").lower()
        
        # Update fields if provided
        if name:
            client["name"] = name
        
        if industry is not None:
            client["industry"] = industry
            
            # Update industry index
            if old_industry != industry.lower():
                # Remove from old industry index
                if old_industry:
                    industry_key = f"industry:{old_industry}"
                    industry_clients = self.redis_cache.get(industry_key) or []
                    if client_id in industry_clients:
                        industry_clients.remove(client_id)
                        self.redis_cache.set(industry_key, industry_clients)
                
                # Add to new industry index
                if industry:
                    industry_key = f"industry:{industry.lower()}"
                    industry_clients = self.redis_cache.get(industry_key) or []
                    if client_id not in industry_clients:
                        industry_clients.append(client_id)
                        self.redis_cache.set(industry_key, industry_clients)
        
        if interests is not None:
            # Normalize interests (lowercase and remove duplicates)
            normalized_interests = list(set([i.lower().strip() for i in interests if i.strip()]))
            client["interests"] = normalized_interests
            
            # Update interest indexes
            # Remove from old interests
            for interest in old_interests:
                if interest not in normalized_interests:
                    interest_key = f"interest:{interest}"
                    interest_clients = self.redis_cache.get(interest_key) or []
                    if client_id in interest_clients:
                        interest_clients.remove(client_id)
                        self.redis_cache.set(interest_key, interest_clients)
            
            # Add to new interests
            for interest in normalized_interests:
                if interest not in old_interests:
                    interest_key = f"interest:{interest}"
                    interest_clients = self.redis_cache.get(interest_key) or []
                    if client_id not in interest_clients:
                        interest_clients.append(client_id)
                        self.redis_cache.set(interest_key, interest_clients)
        
        if contact_email is not None:
            client["contact_email"] = contact_email
            
        if website is not None:
            client["website"] = website
            
        if sources is not None:
            # Normalize sources
            normalized_sources = list(set([s.strip() for s in sources if s.strip()]))
            client["sources"] = normalized_sources
            
        if description is not None:
            client["description"] = description
        
        if active is not None:
            client["active"] = active
        
        # Add any additional data
        if additional_data:
            for key, value in additional_data.items():
                client[key] = value
        
        # Update timestamp
        client["updated_at"] = datetime.now().isoformat()
        
        # Store in Redis
        client_key = f"client:{client_id}"
        self.redis_cache.set(client_key, client)
        
        logger.info(f"Updated client: {client.get('name', client_id)} (ID: {client_id})")
        return client
    
    def delete_client(self, client_id: str) -> bool:
        """
        Delete a client profile and all associated data.
        
        Args:
            client_id: The client ID
            
        Returns:
            True if successful, False otherwise
        """
        client = self.get_client(client_id)
        if not client:
            logger.error(f"Cannot delete client - not found: {client_id}")
            return False
        
        try:
            # Remove from client index
            client_index_key = "clients:all"
            client_index = self.redis_cache.get(client_index_key) or []
            if client_id in client_index:
                client_index.remove(client_id)
                self.redis_cache.set(client_index_key, client_index)
            
            # Remove from interest indexes
            interests = client.get("interests", [])
            for interest in interests:
                interest_key = f"interest:{interest}"
                interest_clients = self.redis_cache.get(interest_key) or []
                if client_id in interest_clients:
                    interest_clients.remove(client_id)
                    self.redis_cache.set(interest_key, interest_clients)
            
            # Remove from industry index
            industry = client.get("industry", "").lower()
            if industry:
                industry_key = f"industry:{industry}"
                industry_clients = self.redis_cache.get(industry_key) or []
                if client_id in industry_clients:
                    industry_clients.remove(client_id)
                    self.redis_cache.set(industry_key, industry_clients)
            
            # Delete client data
            # 1. Articles
            article_key = f"client:{client_id}:articles"
            self.redis_cache.delete(article_key)
            
            # 2. Reports
            report_history_key = f"client:{client_id}:report_history"
            report_history = self.redis_cache.get(report_history_key) or []
            for report_id in report_history:
                report_key = f"report:{report_id}"
                self.redis_cache.delete(report_key)
            self.redis_cache.delete(report_history_key)
            
            # 3. Latest report reference
            latest_report_key = f"client:{client_id}:latest_report"
            self.redis_cache.delete(latest_report_key)
            
            # 4. External data
            external_data_list_key = f"client:{client_id}:external_data_list"
            external_data_list = self.redis_cache.get(external_data_list_key) or []
            for data_id in external_data_list:
                data_key = f"client:{client_id}:external_data:{data_id}"
                self.redis_cache.delete(data_key)
            self.redis_cache.delete(external_data_list_key)
            
            # 5. Any other client-specific keys
            # Find all keys with pattern client:{client_id}:*
            all_client_keys = self.redis_cache.keys(f"client:{client_id}:*")
            for key in all_client_keys:
                self.redis_cache.delete(key)
            
            # Delete the client key
            client_key = f"client:{client_id}"
            self.redis_cache.delete(client_key)
            
            logger.info(f"Deleted client: {client.get('name', client_id)} (ID: {client_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting client {client_id}: {str(e)}")
            return False
    
    def get_all_clients(self) -> List[Dict[str, Any]]:
        """
        Retrieve all clients.
        
        Returns:
            List of all client profiles
        """
        client_index_key = "clients:all"
        client_ids = self.redis_cache.get(client_index_key) or []
        
        clients = []
        for client_id in client_ids:
            client = self.get_client(client_id)
            if client and client.get("active", True):  # Only return active clients
                clients.append(client)
        
        # Sort by name
        clients.sort(key=lambda x: x.get("name", "").lower())
        
        return clients
    
    def get_clients_by_interest(self, interest: str) -> List[Dict[str, Any]]:
        """
        Retrieve clients by interest.
        
        Args:
            interest: The interest to search for
            
        Returns:
            List of client profiles with the specified interest
        """
        interest_key = f"interest:{interest.lower()}"
        client_ids = self.redis_cache.get(interest_key) or []
        
        clients = []
        for client_id in client_ids:
            client = self.get_client(client_id)
            if client and client.get("active", True):  # Only return active clients
                clients.append(client)
        
        # Sort by name
        clients.sort(key=lambda x: x.get("name", "").lower())
        
        return clients
    
    def get_clients_by_industry(self, industry: str) -> List[Dict[str, Any]]:
        """
        Retrieve clients by industry.
        
        Args:
            industry: The industry to search for
            
        Returns:
            List of client profiles in the specified industry
        """
        industry_key = f"industry:{industry.lower()}"
        client_ids = self.redis_cache.get(industry_key) or []
        
        clients = []
        for client_id in client_ids:
            client = self.get_client(client_id)
            if client and client.get("active", True):  # Only return active clients
                clients.append(client)
        
        # Sort by name
        clients.sort(key=lambda x: x.get("name", "").lower())
        
        return clients
    
    def add_client_tag(self, client_id: str, tag: str) -> bool:
        """
        Add a tag to a client.
        
        Args:
            client_id: The client ID
            tag: The tag to add
            
        Returns:
            True if successful, False otherwise
        """
        client = self.get_client(client_id)
        if not client:
            logger.error(f"Cannot add tag - client not found: {client_id}")
            return False
        
        # Normalize tag
        tag = tag.lower().strip()
        if not tag:
            return False
        
        # Add tag to client
        tags = client.get("tags", [])
        if tag not in tags:
            tags.append(tag)
            client["tags"] = tags
            
            # Update client
            client_key = f"client:{client_id}"
            self.redis_cache.set(client_key, client)
            
            # Update tag index
            tag_key = f"tag:{tag}"
            tag_clients = self.redis_cache.get(tag_key) or []
            if client_id not in tag_clients:
                tag_clients.append(client_id)
                self.redis_cache.set(tag_key, tag_clients)
            
            logger.info(f"Added tag '{tag}' to client {client.get('name', client_id)} (ID: {client_id})")
            return True
        
        return False  # Tag already exists
    
    def remove_client_tag(self, client_id: str, tag: str) -> bool:
        """
        Remove a tag from a client.
        
        Args:
            client_id: The client ID
            tag: The tag to remove
            
        Returns:
            True if successful, False otherwise
        """
        client = self.get_client(client_id)
        if not client:
            logger.error(f"Cannot remove tag - client not found: {client_id}")
            return False
        
        # Normalize tag
        tag = tag.lower().strip()
        if not tag:
            return False
        
        # Remove tag from client
        tags = client.get("tags", [])
        if tag in tags:
            tags.remove(tag)
            client["tags"] = tags
            
            # Update client
            client_key = f"client:{client_id}"
            self.redis_cache.set(client_key, client)
            
            # Update tag index
            tag_key = f"tag:{tag}"
            tag_clients = self.redis_cache.get(tag_key) or []
            if client_id in tag_clients:
                tag_clients.remove(client_id)
                self.redis_cache.set(tag_key, tag_clients)
            
            logger.info(f"Removed tag '{tag}' from client {client.get('name', client_id)} (ID: {client_id})")
            return True
        
        return False  # Tag doesn't exist
    
    def get_clients_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """
        Retrieve clients by tag.
        
        Args:
            tag: The tag to search for
            
        Returns:
            List of client profiles with the specified tag
        """
        tag_key = f"tag:{tag.lower()}"
        client_ids = self.redis_cache.get(tag_key) or []
        
        clients = []
        for client_id in client_ids:
            client = self.get_client(client_id)
            if client and client.get("active", True):  # Only return active clients
                clients.append(client)
        
        # Sort by name
        clients.sort(key=lambda x: x.get("name", "").lower())
        
        return clients

# Create a singleton instance
_client_model = None

def get_client_model() -> ClientModel:
    """
    Get the singleton client model instance.
    
    Returns:
        The ClientModel instance
    """
    global _client_model
    if _client_model is None:
        _client_model = ClientModel()
    return _client_model 