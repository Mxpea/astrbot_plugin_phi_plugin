"""
Phi-Plugin for AstrBot
Ported from phi-plugin-main (Yunzai-Bot V3 plugin)

This plugin provides Phigros game information query functionality including:
- B30/B19 score queries
- Song information lookup
- User statistics
- And more
"""

import os
import sys
import json
import yaml
import re
import csv
import struct
import base64
import zipfile
import io
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger

# Add plugin directory to sys.path for imports
PLUGIN_DIR = Path(__file__).parent
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

try:
    import aiohttp
except ImportError:
    aiohttp = None

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
except ImportError:
    AES = None


# ==================== Utility Functions ====================

def get_bit(data: int, index: int) -> bool:
    """Get bit at specific index from integer."""
    return bool(data & (1 << index))


# ==================== ByteReader ====================

class ByteReader:
    """Binary data reader for parsing Phigros save data."""
    
    def __init__(self, data: bytes, position: int = 0):
        if isinstance(data, str):
            self.data = bytes.fromhex(data)
        else:
            self.data = data
        self.position = position
    
    def remaining(self) -> int:
        return len(self.data) - self.position
    
    def get_byte(self) -> int:
        if self.position >= len(self.data):
            raise IndexError("No more bytes to read")
        value = self.data[self.position]
        self.position += 1
        return value
    
    def get_all_bytes(self) -> bytes:
        return self.data[self.position:]
    
    def get_short(self) -> int:
        if self.position + 2 > len(self.data):
            raise IndexError("Not enough bytes for short")
        value = struct.unpack_from('<H', self.data, self.position)[0]
        self.position += 2
        return value
    
    def get_int(self) -> int:
        if self.position + 4 > len(self.data):
            raise IndexError("Not enough bytes for int")
        value = struct.unpack_from('<i', self.data, self.position)[0]
        self.position += 4
        return value
    
    def get_float(self) -> float:
        if self.position + 4 > len(self.data):
            raise IndexError("Not enough bytes for float")
        value = struct.unpack_from('<f', self.data, self.position)[0]
        self.position += 4
        return value
    
    def get_varint(self) -> int:
        if self.position >= len(self.data):
            raise IndexError("No more bytes for varint")
        first_byte = self.data[self.position]
        if first_byte > 127:
            self.position += 2
            if self.position > len(self.data):
                raise IndexError("Not enough bytes for varint")
            return (0b01111111 & first_byte) | (self.data[self.position - 1] << 7)
        else:
            self.position += 1
            return first_byte
    
    def skip_varint(self, num: Optional[int] = None) -> None:
        if num is not None:
            for _ in range(num):
                self.skip_varint()
        else:
            if self.position < len(self.data):
                if self.data[self.position] > 127:
                    self.position += 2
                else:
                    self.position += 1
    
    def get_string(self) -> str:
        length = self.get_varint()
        if self.position + length > len(self.data):
            raise IndexError("Not enough bytes for string")
        result = self.data[self.position:self.position + length].decode('utf-8')
        self.position += length
        return result


# ==================== AES Cipher ====================

class AESCipher:
    """AES cipher for Phigros save encryption/decryption."""
    
    DEFAULT_KEY = base64.b64decode("6Jaa0qVAJZuXkZCLiOa/Ax5tIZVu+taKUN1V1nqwkks=")
    DEFAULT_IV = base64.b64decode("Kk/wisgNYwcAV8WVGMgyUw==")
    
    @staticmethod
    def decrypt(ciphertext: str, key: bytes = None, iv: bytes = None) -> bytes:
        if AES is None:
            raise ImportError("pycryptodome is required for AES decryption")
        if key is None:
            key = AESCipher.DEFAULT_KEY
        if iv is None:
            iv = AESCipher.DEFAULT_IV
        encrypted_data = base64.b64decode(ciphertext)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(encrypted_data)
        try:
            from Crypto.Util.Padding import unpad
            unpadded = unpad(decrypted, AES.block_size)
        except Exception:
            unpadded = decrypted
        return unpadded
    
    @staticmethod
    def decrypt_to_hex(ciphertext: str, key: bytes = None, iv: bytes = None) -> str:
        decrypted = AESCipher.decrypt(ciphertext, key, iv)
        return decrypted.hex()


# ==================== Data Classes ====================

@dataclass
class LevelRecord:
    """Represents a single level record."""
    fc: bool = False
    score: int = 0
    acc: float = 0.0
    
    @property
    def is_phi(self) -> bool:
        return self.score == 1000000 and self.acc == 100.0
    
    @property
    def rating(self) -> str:
        if self.is_phi:
            return 'phi'
        if self.fc:
            return 'FC'
        if self.score >= 960000:
            return 'V'
        if self.score >= 920000:
            return 'S'
        if self.score >= 880000:
            return 'A'
        if self.score >= 820000:
            return 'B'
        if self.score >= 700000:
            return 'C'
        return 'F'
    
    def to_dict(self) -> dict:
        return {'fc': self.fc, 'score': self.score, 'acc': self.acc, 'rating': self.rating}


@dataclass
class GameProgress:
    """Represents game progress data."""
    challenge_mode_rank: int = 0
    money: List[int] = field(default_factory=lambda: [0, 0, 0, 0, 0])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'GameProgress':
        reader = ByteReader(data)
        reader.get_byte()  # flags
        reader.get_string()  # completed
        reader.get_varint()  # song_update_info
        challenge_mode_rank = reader.get_short()
        money = [reader.get_varint() for _ in range(5)]
        return cls(challenge_mode_rank=challenge_mode_rank, money=money)


@dataclass
class GameRecord:
    """Represents all game records."""
    songsnum: int = 0
    records: Dict[str, List[Optional[LevelRecord]]] = field(default_factory=dict)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'GameRecord':
        reader = ByteReader(data)
        version = reader.get_byte()
        if version != 1:
            raise ValueError(f"Unsupported game record version: {version}")
        songsnum = reader.get_varint()
        records = {}
        while reader.remaining() > 0:
            song_id = reader.get_string()
            reader.skip_varint()
            length_flags = reader.get_byte()
            fc_flags = reader.get_byte()
            song_records = []
            for level in range(5):
                if get_bit(length_flags, level):
                    score = reader.get_int()
                    acc = reader.get_float()
                    fc = (score == 1000000 and acc == 100.0) or get_bit(fc_flags, level)
                    song_records.append(LevelRecord(fc=fc, score=score, acc=acc))
                else:
                    song_records.append(None)
            records[song_id] = song_records
        return cls(songsnum=songsnum, records=records)


@dataclass
class Chart:
    """Represents a chart for a song."""
    id: str = ""
    rank: str = ""
    charter: str = ""
    difficulty: float = 0.0
    tap: Optional[int] = None
    drag: Optional[int] = None
    hold: Optional[int] = None
    flick: Optional[int] = None
    combo: Optional[int] = None


@dataclass
class SongsInfo:
    """Represents information about a song."""
    id: str = ""
    song: str = ""
    chapter: str = ""
    bpm: str = ""
    composer: str = ""
    length: str = ""
    illustrator: str = ""
    chart: Dict[str, Chart] = field(default_factory=dict)


@dataclass
class Summary:
    """Save summary data."""
    ranking_score: float = 0.0
    challenge_mode_rank: int = 0
    avatar: str = ""


@dataclass
class SaveInfo:
    """Save information."""
    player_id: str = ""
    summary: Optional[Summary] = None


@dataclass
class GameUser:
    """Game user information."""
    avatar: str = ""
    self_intro: str = ""
    background: str = ""


# ==================== SaveManager ====================

class SaveManager:
    """Manager for Phigros cloud save operations."""
    
    BASE_URL = "https://rak3ffdi.cloud.tds1.tapapis.cn/1.1"
    HEADERS = {
        "X-LC-Id": "rAK3FfdieFob2Nn8Am",
        "X-LC-Key": "Qr9AEqtuoSVS3zeD6iVbM4ZC0AtkJcQ89tywVyi0",
        "User-Agent": "LeanCloud-CSharp-SDK/1.0.3",
        "Accept": "application/json"
    }
    
    @staticmethod
    async def get_player_id(session: str) -> Dict[str, Any]:
        headers = {**SaveManager.HEADERS, "X-LC-Session": session}
        async with aiohttp.ClientSession() as client:
            async with client.get(f"{SaveManager.BASE_URL}/users/me", headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Failed to get player info: {response.status}")
                return await response.json()
    
    @staticmethod
    async def save_check(session: str) -> List[SaveInfo]:
        headers = {**SaveManager.HEADERS, "X-LC-Session": session}
        async with aiohttp.ClientSession() as client:
            async with client.get(f"{SaveManager.BASE_URL}/gamesaves/", headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Failed to get saves: {response.status}")
                data = await response.json()
                results = []
                for save_data in data.get('results', []):
                    if save_data.get('user', {}).get('objectId') == '6a265effd774134774ac90d6':
                        continue
                    try:
                        player_info = await SaveManager.get_player_id(session)
                        player_id = player_info.get('nickname', '')
                    except Exception:
                        player_id = save_data.get('nickname', '')
                    summary_data = save_data.get('summary', {})
                    summary = Summary(
                        ranking_score=summary_data.get('rankingScore', 0.0),
                        challenge_mode_rank=summary_data.get('challengeModeRank', 0),
                        avatar=summary_data.get('avatar', '')
                    )
                    if 'gameFile' in save_data and save_data['gameFile']:
                        results.append(SaveInfo(player_id=player_id, summary=summary))
                return results
    
    @staticmethod
    async def download_save(url: str) -> bytes:
        async with aiohttp.ClientSession() as client:
            async with client.get(url) as response:
                if response.status != 200:
                    raise Exception(f"Failed to download save: {response.status}")
                return await response.read()


# ==================== PhigrosUser ====================

class PhigrosUser:
    """Phigros user data."""
    
    def __init__(self, session: str = "", is_global: bool = False):
        self.session = session
        self.is_global = is_global
        self.save_info: Optional[SaveInfo] = None
        self.game_record: Optional[GameRecord] = None
        self.game_progress: Optional[GameProgress] = None
        self.game_user: Optional[GameUser] = None
        
        if session and not re.match(r'^[a-z0-9A-Z]{25}$', session):
            raise ValueError("SessionToken格式错误")
    
    async def get_save_info(self) -> SaveInfo:
        saves = await SaveManager.save_check(self.session)
        if not saves:
            raise Exception("未找到存档QAQ！")
        self.save_info = saves[0]
        return self.save_info
    
    async def build_record(self) -> None:
        if not self.save_info:
            await self.get_save_info()
        # Note: Actual save download and parsing would go here
        # For now, we'll create empty records
        self.game_record = GameRecord()
        self.game_progress = GameProgress()
        self.game_user = GameUser()
    
    def get_player_id(self) -> str:
        if self.save_info:
            return self.save_info.player_id
        return ""
    
    def get_rks(self) -> float:
        if self.save_info and self.save_info.summary:
            return self.save_info.summary.ranking_score
        return 0.0
    
    def get_challenge_mode(self) -> tuple:
        if self.save_info and self.save_info.summary:
            rank = self.save_info.summary.challenge_mode_rank
            return (rank // 100, rank % 100)
        return (0, 0)
    
    def format_money(self) -> str:
        if self.game_progress:
            money = self.game_progress.money
            units = ['KiB', 'MiB', 'GiB', 'TiB', 'PiB']
            parts = [f"{amount}{unit}" for amount, unit in zip(money, units) if amount > 0]
            return ' '.join(parts) if parts else '0KiB'
        return '0KiB'


# ==================== GetInfo ====================

class GetInfo:
    """Manages song metadata and information."""
    
    def __init__(self, resources_path: str):
        self.resources_path = Path(resources_path)
        self.info_path = self.resources_path / 'info'
        self.ori_info: Dict[str, SongsInfo] = {}
        self.songsid: Dict[str, str] = {}
        self.idssong: Dict[str, str] = {}
        self.illlist: List[str] = []
        self.songlist: List[str] = []
        self.id_list: List[str] = []
        self.nicklist: Dict[str, List[str]] = {}
        self.songnick: Dict[str, List[str]] = {}
        self.chap_list: Dict[str, List[str]] = {}
        self.chap_nick: Dict[str, List[str]] = {}
        self.info_by_difficulty: Dict[str, List[Chart]] = {}
        self.tips: List[str] = []
        self._initialized = False
    
    async def init(self) -> None:
        if self._initialized:
            return
        logger.info("[phi-plugin] 初始化曲目信息")
        await self._load_song_info()
        await self._load_difficulty_data()
        await self._load_nicknames()
        await self._load_chapter_info()
        await self._load_tips()
        self._initialized = True
        logger.info("[phi-plugin] 初始化曲目信息完成")
    
    async def _load_song_info(self) -> None:
        info_csv_path = self.info_path / 'info.csv'
        if info_csv_path.exists():
            with open(info_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    song_id = row.get('id', '')
                    if not song_id:
                        continue
                    if not song_id.endswith('.0'):
                        song_id_with_suffix = f"{song_id}.0"
                    else:
                        song_id_with_suffix = song_id
                    song_name = row.get('song', '')
                    self.songsid[song_id_with_suffix] = song_name
                    self.idssong[song_name] = song_id_with_suffix
                    self.ori_info[song_id_with_suffix] = SongsInfo(
                        id=song_id_with_suffix,
                        song=song_name,
                        composer=row.get('composer', ''),
                        illustrator=row.get('illustrator', ''),
                        chapter=row.get('chapter', ''),
                        bpm=row.get('bpm', ''),
                        length=row.get('length', '')
                    )
                    self.illlist.append(song_id_with_suffix)
                    self.songlist.append(song_name)
                    self.id_list.append(song_id_with_suffix)
    
    async def _load_difficulty_data(self) -> None:
        difficulty_path = self.info_path / 'difficulty.csv'
        if difficulty_path.exists():
            with open(difficulty_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    song_id_without_suffix = row.get('id', '')
                    if not song_id_without_suffix:
                        continue
                    song_id = f"{song_id_without_suffix}.0"
                    if song_id not in self.ori_info:
                        continue
                    song_info = self.ori_info[song_id]
                    for level in ['EZ', 'HD', 'IN', 'AT']:
                        if level in row and row[level]:
                            try:
                                difficulty = float(row[level])
                                song_info.chart[level] = Chart(
                                    id=song_id, rank=level, difficulty=difficulty
                                )
                            except ValueError:
                                continue
    
    async def _load_nicknames(self) -> None:
        nicklist_path = self.info_path / 'nicklist.yaml'
        if nicklist_path.exists():
            with open(nicklist_path, 'r', encoding='utf-8') as f:
                nicklist_data = yaml.safe_load(f) or {}
                for song_id_without_suffix, nicks in nicklist_data.items():
                    song_id = f"{song_id_without_suffix}.0"
                    if song_id not in self.ori_info:
                        continue
                    self.nicklist[song_id] = nicks
                    for nick in nicks:
                        if nick not in self.songnick:
                            self.songnick[nick] = []
                        self.songnick[nick].append(song_id)
    
    async def _load_chapter_info(self) -> None:
        chaplist_path = self.info_path / 'chaplist.yaml'
        if chaplist_path.exists():
            with open(chaplist_path, 'r', encoding='utf-8') as f:
                self.chap_list = yaml.safe_load(f) or {}
                for chapter, aliases in self.chap_list.items():
                    for alias in aliases:
                        if alias not in self.chap_nick:
                            self.chap_nick[alias] = []
                        self.chap_nick[alias].append(chapter)
    
    async def _load_tips(self) -> None:
        tips_path = self.info_path / 'tips.yaml'
        if tips_path.exists():
            with open(tips_path, 'r', encoding='utf-8') as f:
                self.tips = yaml.safe_load(f) or []
    
    def get_info(self, song_id: str) -> Optional[SongsInfo]:
        if not song_id.endswith('.0'):
            song_id = f"{song_id}.0"
        return self.ori_info.get(song_id)
    
    def get_info_by_name(self, song_name: str) -> Optional[SongsInfo]:
        song_id = self.idssong.get(song_name)
        if song_id:
            return self.ori_info.get(song_id)
        return None
    
    def fuzzy_search(self, query: str, distance_threshold: float = 0.6) -> List[str]:
        results = []
        for song_id, song_name in self.songsid.items():
            ratio = SequenceMatcher(None, query.lower(), song_name.lower()).ratio()
            if ratio >= distance_threshold:
                results.append((song_id, ratio))
        for nick, ids in self.songnick.items():
            ratio = SequenceMatcher(None, query.lower(), nick.lower()).ratio()
            if ratio >= distance_threshold:
                for song_id in ids:
                    results.append((song_id, ratio))
        results.sort(key=lambda x: x[1], reverse=True)
        seen = set()
        unique_results = []
        for song_id, ratio in results:
            if song_id not in seen:
                seen.add(song_id)
                unique_results.append(song_id)
        return unique_results


# Global instance
_get_info_instance: Optional[GetInfo] = None


def get_info_instance(resources_path: str = None) -> GetInfo:
    global _get_info_instance
    if _get_info_instance is None:
        if resources_path is None:
            raise ValueError("resources_path required on first call")
        _get_info_instance = GetInfo(resources_path)
    return _get_info_instance


# ==================== Plugin Class ====================

class PhiPlugin(Star):
    """Phigros game information query plugin."""
    
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        self.plugin_dir = Path(__file__).parent
        self.resources_path = self.plugin_dir / 'resources'
        self.get_info = get_info_instance(str(self.resources_path))
        self.user_data_path = self.plugin_dir / 'data'
        self.user_data_path.mkdir(exist_ok=True)
        self._initialized = False
    
    async def initialize(self):
        if self._initialized:
            return
        logger.info("[phi-plugin] 正在初始化...")
        await self.get_info.init()
        self._initialized = True
        logger.info("[phi-plugin] 初始化完成")
    
    async def terminate(self):
        logger.info("[phi-plugin] 插件已卸载")
    
    def _get_user_token(self, user_id: str) -> Optional[str]:
        token_file = self.user_data_path / f"{user_id}.json"
        if token_file.exists():
            with open(token_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('session_token')
        return None
    
    def _save_user_token(self, user_id: str, session_token: str) -> None:
        token_file = self.user_data_path / f"{user_id}.json"
        data = {}
        if token_file.exists():
            with open(token_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        data['session_token'] = session_token
        with open(token_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _delete_user_token(self, user_id: str) -> bool:
        token_file = self.user_data_path / f"{user_id}.json"
        if token_file.exists():
            token_file.unlink()
            return True
        return False
    
    async def _get_user_save(self, user_id: str) -> Optional[PhigrosUser]:
        token = self._get_user_token(user_id)
        if not token:
            return None
        try:
            user = PhigrosUser(session=token)
            await user.get_save_info()
            await user.build_record()
            return user
        except Exception as e:
            logger.error(f"[phi-plugin] 获取存档失败: {e}")
            return None
    
    @filter.command("phihelp")
    async def help_command(self, event: AstrMessageEvent):
        """显示帮助信息"""
        help_text = """🎮 Phi-Plugin 帮助

【基础指令】
/phihelp - 显示此帮助
/phi bind <token> - 绑定sessionToken
/phi unbind - 解绑sessionToken
/phi update - 更新存档

【查询指令】
/phi b30 - 查询B30成绩
/phi score <曲名> - 查询单曲成绩
/phi info - 查询个人信息
/phi suggest - 获取推分建议

【曲目信息】
/phi song <曲名> - 查询曲目图鉴
/phi chart <曲名> [难度] - 查询谱面信息

【娱乐功能】
/phi rand [定数] [难度] - 随机曲目
/phi jrrp - 今日人品"""
        yield event.plain_result(help_text)
    
    @filter.command("phi")
    async def phi_command(self, event: AstrMessageEvent, subcmd: str = None, arg1: str = None, arg2: str = None):
        """Phi 主命令"""
        if not subcmd:
            yield event.plain_result("请输入子命令！使用 /phihelp 查看帮助。")
            return
        
        subcmd = subcmd.lower()
        
        if subcmd == "bind":
            await self._handle_bind(event, arg1)
        elif subcmd == "unbind":
            await self._handle_unbind(event)
        elif subcmd == "update":
            await self._handle_update(event)
        elif subcmd == "b30" or subcmd == "rks" or subcmd == "pgr":
            await self._handle_b30(event)
        elif subcmd == "info":
            await self._handle_info(event)
        elif subcmd == "song":
            await self._handle_song(event, arg1)
        elif subcmd == "help":
            await self.help_command(event)
        else:
            yield event.plain_result(f"未知命令：{subcmd}。使用 /phihelp 查看帮助。")
    
    async def _handle_bind(self, event: AstrMessageEvent, token: str = None):
        """处理绑定命令"""
        user_id = event.get_sender_id()
        
        if not token:
            yield event.plain_result(
                "请提供sessionToken！\n"
                "格式：/phi bind <sessionToken>"
            )
            return
        
        if not re.match(r'^[a-z0-9A-Z]{25}$', token):
            yield event.plain_result("sessionToken格式错误！应为25位字母数字组合。")
            return
        
        try:
            user = PhigrosUser(session=token)
            await user.get_save_info()
            self._save_user_token(user_id, token)
            yield event.plain_result(
                f"绑定成功！\n"
                f"玩家ID: {user.get_player_id()}\n"
                f"RKS: {user.get_rks():.2f}"
            )
        except Exception as e:
            yield event.plain_result(f"绑定失败：{str(e)}")
    
    async def _handle_unbind(self, event: AstrMessageEvent):
        """处理解绑命令"""
        user_id = event.get_sender_id()
        if self._delete_user_token(user_id):
            yield event.plain_result("已解绑sessionToken！")
        else:
            yield event.plain_result("你还没有绑定sessionToken哦！")
    
    async def _handle_update(self, event: AstrMessageEvent):
        """处理更新命令"""
        user_id = event.get_sender_id()
        token = self._get_user_token(user_id)
        if not token:
            yield event.plain_result("请先绑定sessionToken！\n格式：/phi bind <sessionToken>")
            return
        
        yield event.plain_result("正在更新存档，请稍等...")
        try:
            user = await self._get_user_save(user_id)
            if user:
                yield event.plain_result(
                    f"存档更新成功！\n"
                    f"玩家ID: {user.get_player_id()}\n"
                    f"RKS: {user.get_rks():.2f}\n"
                    f"Challenge Mode: {user.get_challenge_mode()[0]}{user.get_challenge_mode()[1]}"
                )
            else:
                yield event.plain_result("存档更新失败！请检查sessionToken是否正确。")
        except Exception as e:
            yield event.plain_result(f"更新失败：{str(e)}")
    
    async def _handle_b30(self, event: AstrMessageEvent):
        """处理B30查询命令"""
        user_id = event.get_sender_id()
        user = await self._get_user_save(user_id)
        if not user:
            yield event.plain_result("请先绑定sessionToken！\n格式：/phi bind <sessionToken>")
            return
        
        yield event.plain_result("正在计算B30，请稍等...")
        try:
            if not user.game_record or not user.game_record.records:
                yield event.plain_result("暂无游戏记录，请先更新存档。")
                return
            
            rks_records = []
            for song_id, records in user.game_record.records.items():
                song_info = self.get_info.get_info(song_id)
                if not song_info:
                    continue
                for level_idx, record in enumerate(records):
                    if record is None:
                        continue
                    level_names = ['EZ', 'HD', 'IN', 'AT', 'LEGACY']
                    if level_idx >= len(level_names):
                        continue
                    level_name = level_names[level_idx]
                    if level_name not in song_info.chart:
                        continue
                    difficulty = song_info.chart[level_name].difficulty
                    acc_ratio = min(record.acc / 100.0, 1.0)
                    rks = difficulty * (acc_ratio ** 2)
                    rks_records.append({
                        'song_id': song_id,
                        'level': level_name,
                        'record': record,
                        'difficulty': difficulty,
                        'rks': rks
                    })
            
            rks_records.sort(key=lambda x: x['rks'], reverse=True)
            b30 = rks_records[:30]
            
            response = f"🎮 B30 成绩查询\n"
            response += f"玩家ID: {user.get_player_id()}\n"
            response += f"RKS: {user.get_rks():.4f}\n"
            cm_color, cm_rank = user.get_challenge_mode()
            response += f"Challenge Mode: {cm_color}{cm_rank}\n\n"
            
            for i, record in enumerate(b30, 1):
                song_info = self.get_info.get_info(record['song_id'])
                song_name = song_info.song if song_info else record['song_id']
                response += f"#{i}: {song_name} [{record['level']}]\n"
                response += f"   分数: {record['record'].score} | ACC: {record['record'].acc:.2f}% | RKS: {record['rks']:.2f}\n"
            
            yield event.plain_result(response)
        except Exception as e:
            yield event.plain_result(f"查询失败：{str(e)}")
    
    async def _handle_info(self, event: AstrMessageEvent):
        """处理个人信息查询命令"""
        user_id = event.get_sender_id()
        user = await self._get_user_save(user_id)
        if not user:
            yield event.plain_result("请先绑定sessionToken！\n格式：/phi bind <sessionToken>")
            return
        
        try:
            challenge_mode, challenge_rank = user.get_challenge_mode()
            money_str = user.format_money()
            response = f"🎮 个人信息\n"
            response += f"玩家ID: {user.get_player_id()}\n"
            response += f"RKS: {user.get_rks():.4f}\n"
            response += f"Challenge Mode: {challenge_mode}{challenge_rank}\n"
            response += f"数据: {money_str}\n"
            yield event.plain_result(response)
        except Exception as e:
            yield event.plain_result(f"查询失败：{str(e)}")
    
    async def _handle_song(self, event: AstrMessageEvent, song_name: str = None):
        """处理曲目查询命令"""
        if not song_name:
            yield event.plain_result("请指定曲名！\n格式：/phi song <曲名>")
            return
        
        song_ids = self.get_info.fuzzy_search(song_name)
        if not song_ids:
            yield event.plain_result(f"未找到曲目：{song_name}")
            return
        
        song_info = self.get_info.get_info(song_ids[0])
        if not song_info:
            yield event.plain_result(f"未找到曲目信息：{song_name}")
            return
        
        response = f"🎵 曲目信息\n"
        response += f"曲名: {song_info.song}\n"
        response += f"ID: {song_info.id}\n"
        response += f"章节: {song_info.chapter}\n"
        response += f"作曲: {song_info.composer}\n"
        response += f"画师: {song_info.illustrator}\n"
        response += f"BPM: {song_info.bpm}\n"
        response += f"时长: {song_info.length}\n\n"
        response += "📊 谱面信息\n"
        for level, chart in song_info.chart.items():
            response += f"[{level}] 定数: {chart.difficulty:.1f}\n"
        
        yield event.plain_result(response)
