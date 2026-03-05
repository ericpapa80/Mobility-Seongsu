"""Storage abstractions for saving data to various backends."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pathlib import Path


class BaseStorage(ABC):
    """Base class for all storage backends.
    
    Storage backends handle saving normalized data to various destinations
    (files, databases, cloud storage, etc.).
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize storage backend.
        
        Args:
            config: Storage-specific configuration
        """
        self.config = config or {}
    
    @abstractmethod
    def save(self, data: Dict[str, Any], metadata: Dict[str, Any] = None) -> str:
        """Save data to storage backend.
        
        Args:
            data: Normalized data to save
            metadata: Optional metadata (source, timestamp, etc.)
            
        Returns:
            Storage location/path/identifier
        """
        pass
    
    @abstractmethod
    def exists(self, identifier: str) -> bool:
        """Check if data exists in storage.
        
        Args:
            identifier: Storage identifier/path
            
        Returns:
            True if data exists, False otherwise
        """
        pass
    
    def close(self):
        """Close storage connection (if applicable)."""
        pass

