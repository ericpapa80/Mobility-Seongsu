"""File handling utilities for saving data in JSON and CSV formats."""

import json
import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import pandas as pd
from core.logger import get_logger

logger = get_logger(__name__)


class FileHandler:
    """Handles file operations for scrapers."""
    
    @staticmethod
    def save_json(
        data: Union[Dict, List],
        filepath: Union[str, Path],
        ensure_ascii: bool = False,
        indent: int = 2
    ) -> Path:
        """Save data to JSON file.
        
        Args:
            data: Data to save (dict or list)
            filepath: Path to save file
            ensure_ascii: Whether to escape non-ASCII characters
            indent: JSON indentation level
            
        Returns:
            Path to saved file
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)
        
        logger.info(f"JSON file saved: {filepath}")
        return filepath
    
    @staticmethod
    def save_csv(
        data: Union[Dict, List],
        filepath: Union[str, Path],
        flatten_nested: bool = True
    ) -> Path:
        """Save data to CSV file.
        
        Args:
            data: Data to save (dict or list of dicts)
            filepath: Path to save file
            flatten_nested: Whether to flatten nested dictionaries
            
        Returns:
            Path to saved file
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to list if single dict
        if isinstance(data, dict):
            data = [data]
        
        if not data:
            logger.warning("No data to save to CSV")
            filepath.touch()
            return filepath
        
        # Flatten nested dictionaries if needed
        if flatten_nested:
            flattened_data = [FileHandler._flatten_dict(item) if isinstance(item, dict) else item 
                            for item in data]
        else:
            flattened_data = data
        
        # Get all unique keys
        all_keys = set()
        for item in flattened_data:
            if isinstance(item, dict):
                all_keys.update(item.keys())
        
        # Write CSV
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            if flattened_data and isinstance(flattened_data[0], dict):
                writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
                writer.writeheader()
                for row in flattened_data:
                    # Handle multi-line values by replacing newlines with space
                    cleaned_row = {}
                    for key, value in row.items():
                        if isinstance(value, str):
                            # Replace newlines and carriage returns with space
                            cleaned_row[key] = value.replace('\n', ' ').replace('\r', ' ')
                        else:
                            cleaned_row[key] = value
                    writer.writerow(cleaned_row)
            else:
                writer = csv.writer(f)
                for row in flattened_data:
                    writer.writerow(row)
        
        logger.info(f"CSV file saved: {filepath}")
        return filepath
    
    @staticmethod
    def _flatten_dict(d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
        """Flatten nested dictionary.
        
        Args:
            d: Dictionary to flatten
            parent_key: Parent key prefix
            sep: Separator for nested keys
            
        Returns:
            Flattened dictionary
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(FileHandler._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                # Convert list to string representation
                items.append((new_key, str(v)))
            else:
                items.append((new_key, v))
        return dict(items)
    
    @staticmethod
    def save_both_formats(
        data: Union[Dict, List],
        base_path: Union[str, Path],
        filename_prefix: str = "data"
    ) -> Dict[str, Path]:
        """Save data in both JSON and CSV formats.
        
        Args:
            data: Data to save
            base_path: Base directory path
            filename_prefix: Prefix for filename (without extension)
            
        Returns:
            Dictionary with 'json' and 'csv' keys containing file paths
        """
        base_path = Path(base_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        json_path = base_path / f"{filename_prefix}_{timestamp}.json"
        csv_path = base_path / f"{filename_prefix}_{timestamp}.csv"
        
        json_file = FileHandler.save_json(data, json_path)
        csv_file = FileHandler.save_csv(data, csv_path)
        
        return {
            'json': json_file,
            'csv': csv_file
        }
    
    @staticmethod
    def load_json(filepath: Union[str, Path]) -> Union[Dict, List]:
        """Load data from JSON file.
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            Loaded data (dict or list)
        """
        filepath = Path(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"JSON file loaded: {filepath}")
        return data
    
    @staticmethod
    def load_csv(filepath: Union[str, Path]) -> List[Dict]:
        """Load data from CSV file.
        
        Args:
            filepath: Path to CSV file
            
        Returns:
            List of dictionaries
        """
        filepath = Path(filepath)
        data = []
        with open(filepath, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        logger.info(f"CSV file loaded: {filepath}")
        return data

