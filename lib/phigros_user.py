"""
Phigros user data class.
Ported from phi-plugin-main/lib/PhigrosUser.js
"""

import zipfile
import io
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any

from .save_manager import SaveManager, SaveInfo
from .byte_reader import ByteReader
from .game_record import GameRecord
from .game_progress import GameProgress
from .level_record import LevelRecord


@dataclass
class GameUser:
    """Game user information."""
    avatar: str = ""
    self_intro: str = ""
    background: str = ""
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'GameUser':
        """Parse from binary data.
        
        Args:
            data: Binary data to parse
            
        Returns:
            GameUser instance
        """
        reader = ByteReader(data)
        
        # Read avatar
        avatar = reader.get_string()
        
        # Read self introduction
        self_intro = reader.get_string()
        
        # Read background
        background = reader.get_string()
        
        return cls(
            avatar=avatar,
            self_intro=self_intro,
            background=background
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'avatar': self.avatar,
            'self_intro': self.self_intro,
            'background': self.background
        }


@dataclass
class GameSettings:
    """Game settings."""
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'GameSettings':
        """Parse from binary data.
        
        Args:
            data: Binary data to parse
            
        Returns:
            GameSettings instance
        """
        # For now, just return empty settings
        # Can be extended if needed
        return cls()
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {}


@dataclass
class PhigrosUser:
    """Phigros user data.
    
    Attributes:
        session: Session token
        is_global: Whether this is a global (international) account
        save_info: Save information
        game_record: Game records
        game_progress: Game progress
        game_user: Game user info
        game_settings: Game settings
    """
    session: str = ""
    is_global: bool = False
    save_info: Optional[SaveInfo] = None
    game_record: Optional[GameRecord] = None
    game_progress: Optional[GameProgress] = None
    game_user: Optional[GameUser] = None
    game_settings: Optional[GameSettings] = None
    
    def __post_init__(self):
        """Validate session token."""
        if self.session and not self._validate_session(self.session):
            raise ValueError("SessionToken格式错误")
    
    @staticmethod
    def _validate_session(session: str) -> bool:
        """Validate session token format.
        
        Args:
            session: Session token to validate
            
        Returns:
            True if valid, False otherwise
        """
        import re
        return bool(re.match(r'^[a-z0-9A-Z]{25}$', session))
    
    async def get_save_info(self) -> SaveInfo:
        """Get save information from cloud.
        
        Returns:
            SaveInfo object
            
        Raises:
            Exception: If no save found
        """
        save_manager = SaveManagerGB() if self.is_global else SaveManager()
        saves = await save_manager.save_check(self.session)
        
        if not saves:
            raise Exception("未找到存档QAQ！")
        
        # Use the first save
        self.save_info = saves[0]
        return self.save_info
    
    async def build_record(self) -> None:
        """Build game record from cloud save.
        
        Downloads and parses the save file.
        
        Raises:
            Exception: If save info not available or parsing fails
        """
        if not self.save_info:
            await self.get_save_info()
        
        if not self.save_info.game_file or not self.save_info.game_file.url:
            raise Exception("获取存档链接失败！")
        
        # Download save file
        save_data = await SaveManager.download_save(self.save_info.game_file.url)
        
        try:
            # Open as ZIP
            with zipfile.ZipFile(io.BytesIO(save_data)) as zf:
                # Parse gameProgress
                if 'gameProgress' in zf.namelist():
                    progress_data = zf.read('gameProgress')
                    # Skip first byte (encryption flag)
                    decrypted = await SaveManager.decrypt_save(progress_data[1:])
                    self.game_progress = GameProgress.from_bytes(decrypted)
                
                # Parse user
                if 'user' in zf.namelist():
                    user_data = zf.read('user')
                    decrypted = await SaveManager.decrypt_save(user_data[1:])
                    self.game_user = GameUser.from_bytes(decrypted)
                
                # Parse settings
                if 'settings' in zf.namelist():
                    settings_data = zf.read('settings')
                    decrypted = await SaveManager.decrypt_save(settings_data[1:])
                    self.game_settings = GameSettings.from_bytes(decrypted)
                
                # Parse gameRecord
                if 'gameRecord' in zf.namelist():
                    record_data = zf.read('gameRecord')
                    reader = ByteReader(record_data)
                    version = reader.get_byte()
                    
                    if version != GameRecord.version:
                        raise Exception("版本号已更新，请更新PhigrosLibrary。")
                    
                    decrypted = await SaveManager.decrypt_save(reader.get_all_bytes())
                    self.game_record = GameRecord.from_bytes(decrypted)
        
        except zipfile.BadZipFile:
            raise Exception("解压zip文件失败！")
    
    def get_player_id(self) -> str:
        """Get player ID.
        
        Returns:
            Player ID string
        """
        if self.save_info:
            return self.save_info.player_id
        return ""
    
    def get_rks(self) -> float:
        """Get ranking score.
        
        Returns:
            Ranking score
        """
        if self.save_info and self.save_info.summary:
            return self.save_info.summary.ranking_score
        return 0.0
    
    def get_challenge_mode(self) -> tuple:
        """Get challenge mode info.
        
        Returns:
            Tuple of (color, rank)
        """
        if self.save_info and self.save_info.summary:
            rank = self.save_info.summary.challenge_mode_rank
            return (rank // 100, rank % 100)
        return (0, 0)
    
    def get_money(self) -> List[int]:
        """Get money values.
        
        Returns:
            List of money values [KiB, MiB, GiB, TiB, PiB]
        """
        if self.game_progress:
            return self.game_progress.money
        return [0, 0, 0, 0, 0]
    
    def format_money(self) -> str:
        """Format money as string.
        
        Returns:
            Formatted money string
        """
        money = self.get_money()
        parts = []
        units = ['KiB', 'MiB', 'GiB', 'TiB', 'PiB']
        
        for i, (amount, unit) in enumerate(zip(money, units)):
            if amount > 0:
                parts.append(f"{amount}{unit}")
        
        return ' '.join(parts) if parts else '0KiB'
    
    def to_dict(self) -> dict:
        """Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        result = {
            'player_id': self.get_player_id(),
            'rks': self.get_rks(),
            'challenge_mode': self.get_challenge_mode(),
            'money': self.format_money()
        }
        
        if self.game_user:
            result['user'] = self.game_user.to_dict()
        
        if self.game_progress:
            result['progress'] = self.game_progress.to_dict()
        
        return result


# Alias for global version
SaveManagerGB = SaveManager
