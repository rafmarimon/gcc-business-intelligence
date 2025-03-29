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
                     contact_email: Optional[str] = None,
                     metadata: Optional[Dict[str, Any]] = None,
                     additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new client profile.
        
        Args:
            name: Client name
            industry: Client industry
            interests: List of client interests/topics
            contact_email: Optional contact email
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
        
        # Normalize interests (lowercase and remove duplicates)
        normalized_interests = list(set([i.lower().strip() for i in interests if i.strip()]))
        
        # Create client object
        client = {
            "id": client_id,
            "name": name,
            "industry": industry,
            "interests": normalized_interests,
            "created_at": timestamp,
            "updated_at": timestamp,
            "active": True
        }
        
        # Add optional fields
        if contact_email:
            client["contact_email"] = contact_email
            
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
            active: Optional new active status
            additional_data: Optional additional client data
            
        Returns:
            The updated client profile data or None if client not found
        """
        client = self.get_client(client_id)
        if not client:
            logger.error(f"Cannot update client - not found: {client_id}")
            return None
        
        # Track old interests for indexing updates
        old_interests = client.get("interests", [])
        
        # Update fields if provided
        if name:
            client["name"] = name
        
        if industry:
            client["industry"] = industry
        
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
        Delete a client profile.
        
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
            
            # Delete the client key
            client_key = f"client:{client_id}"
            self.redis_cache.delete(client_key)
            
            logger.info(f"Deleted client: {client.get('name', client_id)} (ID: {client_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting client {client_id}: {str(e)}")
            return False
    
    def get_all_client_ids(self) -> List[str]:
        """
        Get list of all client IDs.
        
        Returns:
            List of client IDs
        """
        client_index_key = "clients:all"
        client_ids = self.redis_cache.get(client_index_key) or []
        
        # If no client IDs are found using the index, try to find them directly
        if not client_ids:
            # Search for all keys that match the pattern "client:*"
            all_keys = self.redis_cache.scan(0, "client:*", 100)[1] if hasattr(self.redis_cache, 'scan') else []
            
            # Extract client IDs from keys
            if all_keys:
                client_ids = [key.split(':')[1] for key in all_keys]
                
                # Update the index
                if client_ids:
                    self.redis_cache.set(client_index_key, client_ids)
        
        return client_ids
    
    def get_all_clients(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all client profiles.
        
        Args:
            active_only: Whether to return only active clients
            
        Returns:
            List of client profile data
        """
        client_ids = self.get_all_client_ids()
        
        clients = []
        for client_id in client_ids:
            client = self.get_client(client_id)
            if client:
                if not active_only or client.get("active", True):
                    clients.append(client)
        
        return clients
    
    def get_clients_by_interest(self, interest: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get clients that have a specific interest.
        
        Args:
            interest: The interest to filter by
            active_only: Whether to return only active clients
            
        Returns:
            List of client profile data
        """
        interest_key = f"interest:{interest.lower().strip()}"
        client_ids = self.redis_cache.get(interest_key) or []
        
        clients = []
        for client_id in client_ids:
            client = self.get_client(client_id)
            if client:
                if not active_only or client.get("active", True):
                    clients.append(client)
        
        return clients
    
    def search_clients(self, query: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Search for clients matching a query string.
        
        Args:
            query: The search query
            active_only: Whether to return only active clients
            
        Returns:
            List of matching client profile data
        """
        query = query.lower()
        all_clients = self.get_all_clients(active_only=active_only)
        
        results = []
        for client in all_clients:
            if (query in client.get("name", "").lower() or
                query in client.get("industry", "").lower() or
                any(query in interest.lower() for interest in client.get("interests", []))):
                results.append(client)
        
        return results
    
    def create_demo_clients(self) -> List[Dict[str, Any]]:
        """
        Create a set of demo clients for testing.
        
        Returns:
            List of created demo client profiles
        """
        # First, check if we already have clients
        existing_clients = self.get_all_clients()
        if existing_clients:
            logger.info(f"Skipping demo client creation - {len(existing_clients)} clients already exist")
            return existing_clients
        
        demo_clients = [
            {
                "name": "TechInnovate Corp",
                "industry": "Technology",
                "interests": ["AI", "machine learning", "cloud computing", "cybersecurity", "tech trends"],
                "contact_email": "info@techinnovate.example.com"
            },
            {
                "name": "Global Finance Partners",
                "industry": "Finance",
                "interests": ["banking", "fintech", "market analysis", "investment trends", "economic outlook"],
                "contact_email": "info@gfpartners.example.com"
            },
            {
                "name": "EcoSustain Solutions",
                "industry": "Renewable Energy",
                "interests": ["sustainability", "renewable energy", "climate tech", "green initiatives", "ESG"],
                "contact_email": "contact@ecosustain.example.com"
            },
            {
                "name": "HealthPlus Innovations",
                "industry": "Healthcare",
                "interests": ["health tech", "biotech", "pharmaceutical", "medical devices", "healthcare policy"],
                "contact_email": "info@healthplus.example.com"
            },
            {
                "name": "RetailConnect Group",
                "industry": "Retail",
                "interests": ["e-commerce", "consumer trends", "retail tech", "supply chain", "market analysis"],
                "contact_email": "hello@retailconnect.example.com"
            }
        ]
        
        created_clients = []
        for client_data in demo_clients:
            client = self.create_client(
                name=client_data["name"],
                industry=client_data["industry"],
                interests=client_data["interests"],
                contact_email=client_data["contact_email"]
            )
            created_clients.append(client)
        
        logger.info(f"Created {len(created_clients)} demo clients")
        return created_clients

def get_client_model() -> ClientModel:
    """
    Get a ClientModel instance.
    
    Returns:
        ClientModel: A client model instance
    """
    return ClientModel() 