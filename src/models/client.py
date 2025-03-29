#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Client Model Module

This module provides a model for storing and retrieving client profiles
in Redis. Client profiles include name, interests, and other metadata.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from src.utils.redis_cache import RedisCache

# Configure logging
logger = logging.getLogger(__name__)

class ClientModel:
    """
    Model for managing client profiles in Redis.
    """
    
    def __init__(self, redis_cache: Optional[RedisCache] = None):
        """
        Initialize the client model.
        
        Args:
            redis_cache: Optional Redis cache instance. If not provided, a new one will be created.
        """
        self.redis = redis_cache or RedisCache()
    
    def create_client(self, name: str, interests: List[str], 
                     metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new client profile.
        
        Args:
            name: Client name
            interests: List of interests/topics for content matching
            metadata: Optional additional metadata
            
        Returns:
            The created client profile
        """
        client_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        client = {
            "id": client_id,
            "name": name,
            "interests": interests,
            "created_at": timestamp,
            "updated_at": timestamp,
            "metadata": metadata or {}
        }
        
        # Save to Redis
        redis_key = f"client:{client_id}"
        self.redis.set(redis_key, client)
        
        # Also save in an index for easy listing
        index_key = f"clients:index:{name.lower().replace(' ', '_')}:{client_id}"
        self.redis.set(index_key, {"id": client_id, "name": name})
        
        logger.info(f"Created client: {name} (ID: {client_id})")
        return client
    
    def update_client(self, client_id: str, name: Optional[str] = None,
                     interests: Optional[List[str]] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Update an existing client profile.
        
        Args:
            client_id: The client ID
            name: Optional new name
            interests: Optional new interests
            metadata: Optional new metadata
            
        Returns:
            Updated client profile or None if not found
        """
        redis_key = f"client:{client_id}"
        client = self.redis.get(redis_key)
        
        if not client:
            logger.error(f"Client not found: {client_id}")
            return None
        
        # Update fields
        if name:
            # Delete old index
            old_index_key = f"clients:index:{client['name'].lower().replace(' ', '_')}:{client_id}"
            self.redis.delete(old_index_key)
            
            # Update name and create new index
            client['name'] = name
            new_index_key = f"clients:index:{name.lower().replace(' ', '_')}:{client_id}"
            self.redis.set(new_index_key, {"id": client_id, "name": name})
        
        if interests is not None:
            client['interests'] = interests
            
        if metadata is not None:
            client['metadata'] = metadata
            
        # Update timestamp
        client['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Save updated client
        self.redis.set(redis_key, client)
        
        logger.info(f"Updated client: {client['name']} (ID: {client_id})")
        return client
    
    def delete_client(self, client_id: str) -> bool:
        """
        Delete a client profile.
        
        Args:
            client_id: The client ID
            
        Returns:
            True if deleted, False if not found
        """
        redis_key = f"client:{client_id}"
        client = self.redis.get(redis_key)
        
        if not client:
            logger.error(f"Client not found: {client_id}")
            return False
        
        # Delete the client and index
        index_key = f"clients:index:{client['name'].lower().replace(' ', '_')}:{client_id}"
        self.redis.delete(index_key)
        self.redis.delete(redis_key)
        
        logger.info(f"Deleted client: {client['name']} (ID: {client_id})")
        return True
    
    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a client by ID.
        
        Args:
            client_id: The client ID
            
        Returns:
            Client profile or None if not found
        """
        redis_key = f"client:{client_id}"
        return self.redis.get(redis_key)
    
    def get_all_clients(self) -> List[Dict[str, Any]]:
        """
        Get all client profiles.
        
        Returns:
            List of client profiles
        """
        clients = []
        
        if self.redis.redis_enabled and self.redis.connected:
            try:
                # Using Redis scan pattern
                keys = self.redis.redis.keys("client:*")
                
                for key in keys:
                    client = self.redis.get(key)
                    if client:
                        clients.append(client)
                
            except Exception as e:
                logger.error(f"Error retrieving clients: {str(e)}")
        
        return clients
    
    def search_clients(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for clients by name.
        
        Args:
            query: Search query
            
        Returns:
            List of matching client profiles
        """
        query = query.lower()
        clients = []
        
        all_clients = self.get_all_clients()
        for client in all_clients:
            if query in client.get('name', '').lower():
                clients.append(client)
                
        return clients
    
    def get_clients_by_interest(self, interest: str) -> List[Dict[str, Any]]:
        """
        Get clients that have a specific interest.
        
        Args:
            interest: The interest to filter by
            
        Returns:
            List of client profiles with the specified interest
        """
        interest = interest.lower()
        clients = []
        
        all_clients = self.get_all_clients()
        for client in all_clients:
            client_interests = [i.lower() for i in client.get('interests', [])]
            if interest in client_interests:
                clients.append(client)
                
        return clients

# Singleton instance for easy access
client_model = ClientModel()

def get_client_model() -> ClientModel:
    """
    Get the singleton client model instance.
    
    Returns:
        The ClientModel instance
    """
    return client_model 