"""Database configuration management."""

import os
from typing import Optional
from config.settings import settings


class DatabaseConfig:
    """Manages database configuration."""
    
    @staticmethod
    def get_host() -> str:
        """Get database host."""
        return os.getenv("DB_HOST", "localhost")
    
    @staticmethod
    def get_port() -> int:
        """Get database port."""
        return int(os.getenv("DB_PORT", "5432"))
    
    @staticmethod
    def get_name() -> str:
        """Get database name."""
        return os.getenv("DB_NAME", "")
    
    @staticmethod
    def get_user() -> str:
        """Get database user."""
        return os.getenv("DB_USER", "")
    
    @staticmethod
    def get_password() -> str:
        """Get database password."""
        return os.getenv("DB_PASSWORD", "")
    
    @staticmethod
    def get_connection_url() -> str:
        """Get database connection URL.
        
        Returns:
            PostgreSQL connection URL
        """
        host = DatabaseConfig.get_host()
        port = DatabaseConfig.get_port()
        name = DatabaseConfig.get_name()
        user = DatabaseConfig.get_user()
        password = DatabaseConfig.get_password()
        
        return f"postgresql://{user}:{password}@{host}:{port}/{name}"
    
    @staticmethod
    def validate() -> bool:
        """Validate database configuration.
        
        Returns:
            True if all required settings are present
        """
        if not DatabaseConfig.get_name():
            return False
        if not DatabaseConfig.get_user():
            return False
        if not DatabaseConfig.get_password():
            return False
        return True

