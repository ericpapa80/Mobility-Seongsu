"""File-based storage implementation."""

import json
import csv
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

from core.storage import BaseStorage
from core.logger import get_logger

logger = get_logger(__name__)


class FileStorage(BaseStorage):
    """File-based storage using JSON and CSV formats.
    
    This is the default storage backend that saves data to local filesystem.
    """
    
    def __init__(self, base_dir: Optional[Path] = None, config: Optional[Dict[str, Any]] = None):
        """Initialize file storage.
        
        Args:
            base_dir: Base directory for storing files
            config: Storage configuration
                - save_json: Whether to save JSON files (default: True)
                - save_csv: Whether to save CSV files (default: True)
                - source_name: Source name for directory structure
        """
        super().__init__(config)
        self.base_dir = base_dir or Path("data/processed")
        self.save_json = self.config.get('save_json', True)
        self.save_csv = self.config.get('save_csv', True)
        self.source_name = self.config.get('source_name', 'default')
        
        # Create base directory
        self.storage_dir = self.base_dir / self.source_name
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, data: Dict[str, Any], metadata: Dict[str, Any] = None) -> str:
        """Save data to files.
        
        Args:
            data: Normalized data to save
            metadata: Optional metadata
            
        Returns:
            Base path where files were saved
        """
        # Generate timestamp directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamp_dir = self.storage_dir / timestamp
        timestamp_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = []
        
        # Save JSON
        if self.save_json:
            json_path = timestamp_dir / f"{self.source_name}_normalized_{timestamp}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            saved_files.append(str(json_path))
            logger.info(f"Saved JSON to {json_path}")
        
        # Save CSV (if data contains items)
        if self.save_csv and 'data' in data and 'items' in data['data']:
            csv_path = timestamp_dir / f"{self.source_name}_normalized_{timestamp}.csv"
            items = data['data']['items']
            
            if items:
                # Flatten items for CSV
                # 모든 아이템을 확인하여 필드명 수집 (None 값 처리)
                all_fieldnames = set()
                flattened_items = []
                
                for item in items:
                    flattened = self._flatten_item(item)
                    flattened_items.append(flattened)
                    all_fieldnames.update(flattened.keys())
                
                fieldnames = sorted(list(all_fieldnames))
                
                with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                    writer.writeheader()
                    
                    for flattened in flattened_items:
                        writer.writerow(flattened)
                
                saved_files.append(str(csv_path))
                logger.info(f"Saved CSV to {csv_path}")
        
        return str(timestamp_dir)
    
    def _get_csv_fieldnames(self, sample_item: Dict[str, Any]) -> list:
        """Get CSV fieldnames from sample item.
        
        Args:
            sample_item: Sample item to extract fieldnames from
            
        Returns:
            List of fieldnames
        """
        fieldnames = []
        
        for key, value in sample_item.items():
            if key == 'raw':
                # Skip raw data in CSV
                continue
            elif value is None:
                # Handle None values (e.g., coordinates when not geocoded)
                # Add the key itself for None values
                fieldnames.append(key)
            elif isinstance(value, dict):
                # Flatten nested dictionaries
                for nested_key in value.keys():
                    fieldnames.append(f"{key}_{nested_key}")
            else:
                fieldnames.append(key)
        
        return fieldnames
    
    def _flatten_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten nested item for CSV.
        
        Args:
            item: Item to flatten
            
        Returns:
            Flattened item
        """
        flattened = {}
        
        for key, value in item.items():
            if key == 'raw':
                continue
            elif value is None:
                # Handle None values (e.g., coordinates when not geocoded)
                flattened[key] = None
            elif isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    flattened[f"{key}_{nested_key}"] = nested_value
            else:
                flattened[key] = value
        
        return flattened
    
    def exists(self, identifier: str) -> bool:
        """Check if storage path exists.
        
        Args:
            identifier: Path to check
            
        Returns:
            True if path exists, False otherwise
        """
        return Path(identifier).exists()
    
    def close(self):
        """File storage doesn't need connection closing."""
        pass

