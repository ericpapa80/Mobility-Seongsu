# -*- coding: utf-8 -*-
"""Logging utility for scrapers."""

import logging
import sys
import io
from pathlib import Path
from datetime import datetime
from typing import Optional

# Windows에서 한글 출력을 위한 인코딩 설정
if sys.platform == 'win32':
    # stdout과 stderr의 인코딩을 UTF-8로 설정
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    else:
        # Python 3.6 이하 호환
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def setup_logger(
    name: str,
    log_dir: Optional[Path] = None,
    level: int = logging.INFO,
    console_output: bool = True
) -> logging.Logger:
    """Setup and configure a logger.
    
    Args:
        name: Logger name
        log_dir: Directory to save log files (default: logs/)
        level: Logging level (default: INFO)
        console_output: Whether to output to console (default: True)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"{name}_{timestamp}.log"
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str, log_dir: Optional[Path] = None) -> logging.Logger:
    """Get or create a logger instance.
    
    Args:
        name: Logger name
        log_dir: Directory to save log files (default: logs/)
        
    Returns:
        Logger instance
    """
    if log_dir is None:
        log_dir = Path("logs")
    
    return setup_logger(name, log_dir=log_dir)

