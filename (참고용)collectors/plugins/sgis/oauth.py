"""SGIS OAuth authentication helper."""

import time
import hashlib
import hmac
import base64
from urllib.parse import quote, urlencode
from typing import Dict
from config.scrapers.sgis import SGISConfig
from core.logger import get_logger

logger = get_logger(__name__)


class SGISOAuth:
    """SGIS OAuth 1.0 authentication helper."""
    
    @staticmethod
    def generate_signature(
        method: str,
        url: str,
        params: Dict[str, str],
        consumer_secret: str
    ) -> str:
        """Generate OAuth signature.
        
        Args:
            method: HTTP method (GET, POST)
            url: Request URL
            params: Request parameters
            consumer_secret: Consumer secret
            
        Returns:
            OAuth signature
        """
        # Sort parameters
        sorted_params = sorted(params.items())
        
        # Create parameter string
        param_string = '&'.join([f"{quote(str(k))}={quote(str(v))}" for k, v in sorted_params])
        
        # Create signature base string
        signature_base = f"{method.upper()}&{quote(url, safe='')}&{quote(param_string, safe='')}"
        
        # Generate signature
        signature = hmac.new(
            f"{consumer_secret}&".encode('utf-8'),
            signature_base.encode('utf-8'),
            hashlib.sha1
        ).digest()
        
        return base64.b64encode(signature).decode('utf-8')
    
    @staticmethod
    def get_oauth_params(additional_params: Dict[str, str] = None) -> Dict[str, str]:
        """Get OAuth parameters.
        
        Args:
            additional_params: Additional parameters to include
            
        Returns:
            Dictionary of OAuth parameters
        """
        consumer_key = SGISConfig.get_consumer_key()
        consumer_secret = SGISConfig.get_consumer_secret()
        
        if not consumer_key or not consumer_secret:
            logger.warning("SGIS consumer key or secret not found")
            return {}
        
        # OAuth parameters
        oauth_params = {
            'oauth_consumer_key': consumer_key,
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_timestamp': str(int(time.time())),
            'oauth_nonce': str(int(time.time() * 1000)),
            'oauth_version': '1.0'
        }
        
        # Add additional parameters
        if additional_params:
            oauth_params.update(additional_params)
        
        # Generate signature
        base_url = SGISConfig.get_base_url()
        # Note: Actual signature generation may need the full endpoint URL
        # This is a simplified version - adjust based on actual API requirements
        
        return oauth_params

