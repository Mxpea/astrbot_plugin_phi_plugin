"""
Save manager for Phigros cloud saves.
Ported from phi-plugin-main/lib/SaveManager.js
"""

import aiohttp
import base64
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from .aes import AESCipher


@dataclass
class Summary:
    """Save summary data."""
    game_version: int = 0
    ranking_score: float = 0.0
    challenge_mode_rank: int = 0
    avatar: str = ""
    updated_at: str = ""
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Summary':
        """Parse from dictionary.
        
        Args:
            data: Dictionary with summary data
            
        Returns:
            Summary instance
        """
        return cls(
            game_version=data.get('gameVersion', 0),
            ranking_score=data.get('rankingScore', 0.0),
            challenge_mode_rank=data.get('challengeModeRank', 0),
            avatar=data.get('avatar', ''),
            updated_at=data.get('updatedAt', '')
        )


@dataclass
class GameFile:
    """Game file reference."""
    url: str = ""
    object_id: str = ""
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GameFile':
        """Parse from dictionary.
        
        Args:
            data: Dictionary with game file data
            
        Returns:
            GameFile instance
        """
        return cls(
            url=data.get('url', ''),
            object_id=data.get('objectId', '')
        )


@dataclass
class SaveInfo:
    """Save information."""
    object_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    game_file: Optional[GameFile] = None
    summary: Optional[Summary] = None
    player_id: str = ""
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SaveInfo':
        """Parse from dictionary.
        
        Args:
            data: Dictionary with save info data
            
        Returns:
            SaveInfo instance
        """
        game_file = None
        if 'gameFile' in data:
            game_file = GameFile.from_dict(data['gameFile'])
        
        summary = None
        if 'summary' in data:
            summary = Summary.from_dict(data['summary'])
        
        return cls(
            object_id=data.get('objectId', ''),
            created_at=data.get('createdAt', ''),
            updated_at=data.get('updatedAt', ''),
            game_file=game_file,
            summary=summary,
            player_id=data.get('PlayerId', data.get('nickname', ''))
        )


class SaveManager:
    """Manager for Phigros cloud save operations."""
    
    BASE_URL = "https://rak3ffdi.cloud.tds1.tapapis.cn/1.1"
    FILE_TOKENS = f"{BASE_URL}/fileTokens"
    FILE_CALLBACK = f"{BASE_URL}/fileCallback"
    SAVE = f"{BASE_URL}/gamesaves/"
    USER_INFO = f"{BASE_URL}/users/me"
    FILES = f"{BASE_URL}/files/"
    
    HEADERS = {
        "X-LC-Id": "rAK3FfdieFob2Nn8Am",
        "X-LC-Key": "Qr9AEqtuoSVS3zeD6iVbM4ZC0AtkJcQ89tywVyi0",
        "User-Agent": "LeanCloud-CSharp-SDK/1.0.3",
        "Accept": "application/json"
    }
    
    @staticmethod
    async def get_player_id(session: str) -> Dict[str, Any]:
        """Get player ID from session.
        
        Args:
            session: Session token
            
        Returns:
            Player info dictionary
        """
        headers = {**SaveManager.HEADERS, "X-LC-Session": session}
        
        async with aiohttp.ClientSession() as client:
            async with client.get(SaveManager.USER_INFO, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Failed to get player info: {response.status}")
                return await response.json()
    
    @staticmethod
    async def save_array(session: str) -> List[Dict[str, Any]]:
        """Get list of saves.
        
        Args:
            session: Session token
            
        Returns:
            List of save dictionaries
        """
        headers = {**SaveManager.HEADERS, "X-LC-Session": session}
        
        async with aiohttp.ClientSession() as client:
            async with client.get(SaveManager.SAVE, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Failed to get saves: {response.status}")
                data = await response.json()
                return data.get('results', [])
    
    @staticmethod
    async def save_check(session: str) -> List[SaveInfo]:
        """Check and get save info.
        
        Args:
            session: Session token
            
        Returns:
            List of SaveInfo objects
            
        Raises:
            Exception: If no saves found
        """
        array = await SaveManager.save_array(session)
        
        if not array:
            raise Exception("TK 对应存档列表为空，请检查是否同步存档QAQ！")
        
        results = []
        for save_data in array:
            # Skip specific user ID
            if save_data.get('user', {}).get('objectId') == '6a265effd774134774ac90d6':
                continue
            
            # Get player ID
            try:
                player_info = await SaveManager.get_player_id(session)
                save_data['PlayerId'] = player_info.get('nickname', '')
            except Exception:
                save_data['PlayerId'] = save_data.get('nickname', '')
            
            # Parse summary
            if 'summary' in save_data:
                save_data['summary'] = Summary.from_dict(save_data['summary'])
            
            # Only include saves with game files
            if 'gameFile' in save_data and save_data['gameFile']:
                results.append(SaveInfo.from_dict(save_data))
        
        return results
    
    @staticmethod
    async def download_save(url: str) -> bytes:
        """Download save file from URL.
        
        Args:
            url: URL to download from
            
        Returns:
            Save file bytes
        """
        async with aiohttp.ClientSession() as client:
            async with client.get(url) as response:
                if response.status != 200:
                    raise Exception(f"Failed to download save: {response.status}")
                return await response.read()
    
    @staticmethod
    async def decrypt_save(data: bytes) -> bytes:
        """Decrypt save data.
        
        Args:
            data: Encrypted save data
            
        Returns:
            Decrypted save data
        """
        # Convert to base64 string for decryption
        b64_string = base64.b64encode(data).decode('utf-8')
        decrypted = AESCipher.decrypt(b64_string)
        return decrypted


class SaveManagerGB(SaveManager):
    """Save manager for global (international) version."""
    
    # Global version uses the same API but may have different endpoints
    # For now, use the same base URL
    pass
