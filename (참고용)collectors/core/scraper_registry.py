"""Scraper registry for managing and discovering scrapers."""

import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Type
from core.base_scraper import BaseScraper
from core.logger import get_logger

logger = get_logger(__name__)


class ScraperRegistry:
    """Registry for managing scrapers as plugins."""
    
    def __init__(self, plugins_dir: Optional[Path] = None):
        """Initialize scraper registry.
        
        Args:
            plugins_dir: Directory containing scraper plugins (default: plugins/)
        """
        if plugins_dir is None:
            plugins_dir = Path(__file__).parent.parent / "plugins"
        self.plugins_dir = Path(plugins_dir)
        self._scrapers: Dict[str, Type[BaseScraper]] = {}
        self._scraper_info: Dict[str, dict] = {}
    
    def discover_scrapers(self) -> List[str]:
        """Discover all available scrapers in plugins directory.
        
        Returns:
            List of scraper names
        """
        discovered = []
        
        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory not found: {self.plugins_dir}")
            return discovered
        
        # Iterate through plugin directories
        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue
            
            # Skip __pycache__ and hidden directories
            if plugin_dir.name.startswith('_') or plugin_dir.name == '__pycache__':
                continue
            
            # Check for scraper module
            scraper_file = plugin_dir / "scraper.py"
            if not scraper_file.exists():
                logger.debug(f"No scraper.py found in {plugin_dir.name}")
                continue
            
            discovered.append(plugin_dir.name)
            logger.info(f"Discovered scraper: {plugin_dir.name}")
        
        return discovered
    
    def register_scraper(
        self,
        name: str,
        scraper_class: Type[BaseScraper],
        info: Optional[dict] = None
    ) -> None:
        """Register a scraper class.
        
        Args:
            name: Scraper name
            scraper_class: Scraper class (must inherit from BaseScraper)
            info: Optional metadata about the scraper
        """
        if not issubclass(scraper_class, BaseScraper):
            raise ValueError(f"Scraper class must inherit from BaseScraper")
        
        self._scrapers[name] = scraper_class
        self._scraper_info[name] = info or {}
        logger.info(f"Registered scraper: {name}")
    
    def load_scraper(self, name: str) -> Optional[Type[BaseScraper]]:
        """Load a scraper by name.
        
        Args:
            name: Scraper name
            
        Returns:
            Scraper class or None if not found
        """
        # Check if already registered
        if name in self._scrapers:
            return self._scrapers[name]
        
        # Try to load from plugins directory
        plugin_dir = self.plugins_dir / name
        if not plugin_dir.exists():
            logger.error(f"Scraper plugin not found: {name}")
            return None
        
        scraper_file = plugin_dir / "scraper.py"
        if not scraper_file.exists():
            logger.error(f"scraper.py not found in {plugin_dir}")
            return None
        
        try:
            # Import the scraper module
            module_name = f"plugins.{name}.scraper"
            module = importlib.import_module(module_name)
            
            # Find BaseScraper subclass
            for obj_name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseScraper) and 
                    obj is not BaseScraper):
                    self.register_scraper(name, obj)
                    return obj
            
            logger.error(f"No scraper class found in {module_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error loading scraper {name}: {e}")
            return None
    
    def get_scraper(self, name: str) -> Optional[Type[BaseScraper]]:
        """Get scraper class by name.
        
        Args:
            name: Scraper name
            
        Returns:
            Scraper class or None if not found
        """
        if name not in self._scrapers:
            self.load_scraper(name)
        return self._scrapers.get(name)
    
    def list_scrapers(self) -> List[str]:
        """List all registered and available scrapers.
        
        Returns:
            List of scraper names
        """
        # Discover scrapers first
        discovered = self.discover_scrapers()
        
        # Load all discovered scrapers
        for name in discovered:
            if name not in self._scrapers:
                self.load_scraper(name)
        
        return list(self._scrapers.keys())
    
    def get_scraper_info(self, name: str) -> dict:
        """Get metadata about a scraper.
        
        Args:
            name: Scraper name
            
        Returns:
            Dictionary containing scraper metadata
        """
        return self._scraper_info.get(name, {})
    
    def create_scraper_instance(
        self,
        name: str,
        **kwargs
    ) -> Optional[BaseScraper]:
        """Create an instance of a scraper.
        
        Args:
            name: Scraper name
            **kwargs: Arguments to pass to scraper constructor
            
        Returns:
            Scraper instance or None if not found
        """
        scraper_class = self.get_scraper(name)
        if scraper_class is None:
            return None
        
        try:
            return scraper_class(**kwargs)
        except Exception as e:
            logger.error(f"Error creating scraper instance {name}: {e}")
            return None


# Global registry instance
registry = ScraperRegistry()

