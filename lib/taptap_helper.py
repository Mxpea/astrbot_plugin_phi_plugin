"""
TapTap QR Code Login Helper
Ported from phi-plugin-main/lib/TapTap/
"""

import aiohttp
import hashlib
import hmac
import base64
import time
import json
import secrets
from typing import Optional, Dict, Any


class TapTapHelper:
    """TapTap login helper for QR code authentication."""
    
    def __init__(self, use_global: bool = False):
        self.use_global = use_global
        self.tap_sdk_version = '2.1'
        
        # Endpoints
        self.web_host = 'https://accounts.tapapis.com'
        self.china_web_host = 'https://accounts.tapapis.cn'
        self.api_host = 'https://open.tapapis.com'
        self.china_api_host = 'https://open.tapapis.cn'
        
        # URLs
        if use_global:
            self.code_url = f"{self.web_host}/oauth2/v1/device/code"
            self.token_url = f"{self.web_host}/oauth2/v1/token"
        else:
            self.code_url = f"{self.china_web_host}/oauth2/v1/device/code"
            self.token_url = f"{self.china_web_host}/oauth2/v1/token"
        
        # Client ID (from Phigros)
        self.client_id = "rAK3FfdieFob2Nn8Am"
    
    async def request_login_qrcode(self, permissions: list = None) -> Dict[str, Any]:
        """Request a login QR code from TapTap.
        
        Args:
            permissions: List of permissions to request
            
        Returns:
            Dictionary with QR code data
        """
        if permissions is None:
            permissions = ['public_profile']
        
        device_id = secrets.token_hex(16)
        
        data = aiohttp.FormData()
        data.add_field('client_id', self.client_id)
        data.add_field('response_type', 'device_code')
        data.add_field('scope', ','.join(permissions))
        data.add_field('version', self.tap_sdk_version)
        data.add_field('platform', 'unity')
        data.add_field('info', json.dumps({'device_id': device_id}))
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.code_url, data=data) as response:
                    result = await response.json()
                    result['deviceId'] = device_id
                    return result
        except Exception as e:
            return {'error': str(e)}
    
    async def check_qrcode_result(self, qr_code_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if the QR code has been scanned and confirmed.
        
        Args:
            qr_code_data: QR code data from request_login_qrcode
            
        Returns:
            Dictionary with check result
        """
        # Get device code from the data object
        data_obj = qr_code_data.get('data', {})
        device_code = data_obj.get('device_code', '')
        device_id = qr_code_data.get('deviceId', '')
        
        data = aiohttp.FormData()
        data.add_field('grant_type', 'device_token')
        data.add_field('client_id', self.client_id)
        data.add_field('secret_type', 'hmac-sha-1')
        data.add_field('code', device_code)
        data.add_field('version', '1.0')
        data.add_field('platform', 'unity')
        data.add_field('info', json.dumps({'device_id': device_id}))
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.token_url, data=data) as response:
                    return await response.json()
        except Exception as e:
            return {'error': str(e)}
    
    async def get_profile(self, token: Dict[str, Any]) -> Dict[str, Any]:
        """Get user profile from TapTap.
        
        Args:
            token: Token data from check_qrcode_result
            
        Returns:
            Dictionary with profile data
        """
        if 'scope' not in token or 'public_profile' not in token.get('scope', ''):
            raise ValueError('Public profile permission is required.')
        
        if self.use_global:
            url = f"{self.api_host}/account/profile/v1?client_id={self.client_id}"
        else:
            url = f"{self.china_api_host}/account/profile/v1?client_id={self.client_id}"
        
        kid = token.get('kid', '')
        mac_key = token.get('mac_key', '')
        
        authorization = self._get_authorization(url, 'GET', kid, mac_key)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={'Authorization': authorization}) as response:
                return await response.json()
    
    def _get_authorization(self, request_url: str, method: str, key_id: str, mac_key: str) -> str:
        """Generate MAC authorization header.
        
        Args:
            request_url: Request URL
            method: HTTP method
            key_id: Key ID
            mac_key: MAC key
            
        Returns:
            Authorization header string
        """
        from urllib.parse import urlparse
        
        url = urlparse(request_url)
        timestamp = str(int(time.time())).zfill(10)
        random_str = self._get_random_string(16)
        host = url.hostname
        uri = url.path + url.query
        port = url.port or ('443' if url.scheme == 'https' else '80')
        other = ''
        
        sign = self._sign_data(self._merge_data(timestamp, random_str, method, uri, host, port, other), mac_key)
        
        return f'MAC id="{key_id}", ts="{timestamp}", nonce="{random_str}", mac="{sign}"'
    
    def _get_random_string(self, length: int) -> str:
        """Generate random string.
        
        Args:
            length: Length of random string
            
        Returns:
            Random string
        """
        return base64.b64encode(secrets.token_bytes(length)).decode('utf-8')
    
    def _merge_data(self, time_str: str, random_code: str, http_type: str, 
                    uri: str, domain: str, port: str, other: str) -> str:
        """Merge data for signing.
        
        Args:
            time_str: Timestamp
            random_code: Random code
            http_type: HTTP method
            uri: Request URI
            domain: Domain
            port: Port
            other: Other data
            
        Returns:
            Merged data string
        """
        prefix = f"{time_str}\n{random_code}\n{http_type}\n{uri}\n{domain}\n{port}\n"
        
        if not other:
            prefix += "\n"
        else:
            prefix += f"{other}\n"
        
        return prefix
    
    def _sign_data(self, signature_base_string: str, key: str) -> str:
        """Sign data with HMAC-SHA1.
        
        Args:
            signature_base_string: Data to sign
            key: MAC key
            
        Returns:
            Signed data
        """
        hmac_obj = hmac.new(key.encode('utf-8'), signature_base_string.encode('utf-8'), hashlib.sha1)
        return base64.b64encode(hmac_obj.digest()).decode('utf-8')


class LCHelper:
    """LeanCloud helper for Phigros login."""
    
    def __init__(self, use_global: bool = False):
        self.use_global = use_global
        
        # App keys
        self.app_key = 'Qr9AEqtuoSVS3zeD6iVbM4ZC0AtkJcQ89tywVyi0'
        self.client_id = 'rAK3FfdieFob2Nn8Am'
        self.app_key_gb = 'tG9CTm0LDD736k9HMM9lBZrbeBGRmUkjSfNLDNib'
        self.client_id_gb = 'kviehleldgxsagpozb'
        
        # URLs
        if use_global:
            self.url_lc_base = 'https://kviehlel.cloud.ap-sg.tapapis.com/1.1'
        else:
            self.url_lc_base = 'https://rak3ffdi.cloud.tds1.tapapis.cn/1.1'
    
    async def login_with_auth_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Login with auth data.
        
        Args:
            data: Auth data from TapTap
            
        Returns:
            Login response
        """
        auth_data = {'taptap': data}
        return await self._request('post', auth_data)
    
    async def login_and_get_token(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Login and get session token.
        
        Args:
            data: Auth data from TapTap
            
        Returns:
            Login response with session token
        """
        return await self.login_with_auth_data(data)
    
    async def _request(self, method: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make request to LeanCloud.
        
        Args:
            method: HTTP method
            data: Request data
            
        Returns:
            Response data
        """
        url = f"{self.url_lc_base}/users"
        headers = {
            'X-LC-Id': self.client_id,
            'Content-Type': 'application/json'
        }
        
        self._fill_headers(headers)
        
        async with aiohttp.ClientSession() as session:
            if method.lower() == 'post':
                async with session.post(url, headers=headers, json=data) as response:
                    return await response.json()
            else:
                async with session.get(url, headers=headers) as response:
                    return await response.json()
    
    def _fill_headers(self, headers: Dict[str, str]) -> None:
        """Fill headers with signature.
        
        Args:
            headers: Headers to fill
        """
        timestamp = int(time.time())
        data = f"{timestamp}{self.app_key}"
        hash_obj = hashlib.md5(data.encode('utf-8'))
        sign = f"{hash_obj.hexdigest()},{timestamp}"
        headers['X-LC-Sign'] = sign


async def get_session_token_from_qrcode(qrcode_url: str, timeout: int = 120) -> Optional[str]:
    """Get session token from QR code URL.
    
    Args:
        qrcode_url: QR code URL
        timeout: Timeout in seconds
        
    Returns:
        Session token or None if failed
    """
    taptap = TapTapHelper()
    lchelper = LCHelper()
    
    # Wait for QR code scan
    start_time = time.time()
    while time.time() - start_time < timeout:
        result = await taptap.check_qrcode_result({'device_code': qrcode_url})
        
        if result.get('success'):
            # Get profile
            profile = await taptap.get_profile(result.get('data', {}))
            
            # Get session token
            login_data = {**profile.get('data', {}), **result.get('data', {})}
            login_result = await lchelper.login_and_get_token(login_data)
            
            return login_result.get('sessionToken')
        
        # Wait before checking again
        await asyncio.sleep(2)
    
    return None
