"""
GetInfo class for managing song metadata.
Ported from phi-plugin-main/model/getInfo.js
"""

import os
import csv
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .songs_info import SongsInfo
from .chart import Chart


# Constants
ALL_LEVEL = ['EZ', 'HD', 'IN', 'AT', 'LEGACY']
LEVEL = ['EZ', 'HD', 'IN', 'AT']
MAX_DIFFICULTY = 17.6


@dataclass
class VersionInfo:
    """Version information."""
    version_label: str = ""
    update_date: int = 0
    whatsnew: str = ""
    version_code: int = 0
    version: str = ""


class GetInfo:
    """Manages song metadata and information.
    
    This class loads and manages all song information including:
    - Song metadata (name, composer, illustrator, etc.)
    - Chart data (difficulty, notes, etc.)
    - Nicknames and aliases
    - Chapter information
    - Version history
    """
    
    def __init__(self, resources_path: str):
        """Initialize GetInfo.
        
        Args:
            resources_path: Path to resources directory
        """
        self.resources_path = Path(resources_path)
        self.info_path = self.resources_path / 'info'
        
        # Data storage
        self.ori_info: Dict[str, SongsInfo] = {}
        self.songsid: Dict[str, str] = {}  # id -> song name
        self.idssong: Dict[str, str] = {}  # song name -> id
        self.illlist: List[str] = []  # IDs with illustrations
        self.songlist: List[str] = []  # All song names
        self.id_list: List[str] = []  # All song IDs
        
        # Nickname data
        self.nicklist: Dict[str, List[str]] = {}  # id -> nicknames
        self.songnick: Dict[str, List[str]] = {}  # nickname -> ids
        
        # Chapter data
        self.chap_list: Dict[str, List[str]] = {}
        self.chap_nick: Dict[str, List[str]] = {}
        
        # Difficulty data
        self.info_by_difficulty: Dict[str, List[Chart]] = {}
        
        # Version data
        self.version_info_by_label: Dict[str, VersionInfo] = {}
        self.version_info_by_code: Dict[int, VersionInfo] = {}
        
        # Tips
        self.tips: List[str] = []
        
        # Notice
        self.notice_json: Dict[str, Any] = {'title': '', 'code': 0, 'content': []}
        
        # Initialization flag
        self._initialized = False
    
    async def init(self) -> None:
        """Initialize song information from data files.
        
        This loads all song metadata from CSV, JSON, and YAML files.
        """
        if self._initialized:
            return
        
        print("[phi-plugin] 初始化曲目信息")
        
        # Load song info from CSV
        await self._load_song_info()
        
        # Load difficulty data
        await self._load_difficulty_data()
        
        # Load nicknames
        await self._load_nicknames()
        
        # Load chapter info
        await self._load_chapter_info()
        
        # Load tips
        await self._load_tips()
        
        # Load notice
        await self._load_notice()
        
        # Build difficulty index
        self._build_difficulty_index()
        
        self._initialized = True
        print("[phi-plugin] 初始化曲目信息完成")
    
    async def _load_song_info(self) -> None:
        """Load song information from CSV and JSON files."""
        # Load info.csv
        info_csv_path = self.info_path / 'info.csv'
        if info_csv_path.exists():
            with open(info_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    song_id = row.get('id', '')
                    if not song_id:
                        continue
                    
                    # Add .0 suffix if not present
                    if not song_id.endswith('.0'):
                        song_id_with_suffix = f"{song_id}.0"
                    else:
                        song_id_with_suffix = song_id
                        song_id = song_id[:-2]
                    
                    # Store mappings
                    song_name = row.get('song', '')
                    self.songsid[song_id_with_suffix] = song_name
                    self.idssong[song_name] = song_id_with_suffix
                    
                    # Create song info
                    self.ori_info[song_id_with_suffix] = SongsInfo(
                        id=song_id_with_suffix,
                        song=song_name,
                        composer=row.get('composer', ''),
                        illustrator=row.get('illustrator', ''),
                        chapter=row.get('chapter', ''),
                        bpm=row.get('bpm', ''),
                        length=row.get('length', '')
                    )
                    
                    # Add to lists
                    self.illlist.append(song_id_with_suffix)
                    self.songlist.append(song_name)
                    self.id_list.append(song_id_with_suffix)
        
        # Load infolist.json for additional info
        infolist_path = self.info_path / 'infolist.json'
        if infolist_path.exists():
            with open(infolist_path, 'r', encoding='utf-8') as f:
                infolist = json.load(f)
                for song_id_without_suffix, data in infolist.items():
                    song_id = f"{song_id_without_suffix}.0"
                    if song_id in self.ori_info:
                        # Update existing info
                        song_info = self.ori_info[song_id]
                        if 'chapter' in data:
                            song_info.chapter = data['chapter']
                        if 'bpm' in data:
                            song_info.bpm = data['bpm']
                        if 'length' in data:
                            song_info.length = data['length']
    
    async def _load_difficulty_data(self) -> None:
        """Load difficulty data from CSV."""
        # Load difficulty.csv
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
                    
                    # Parse difficulties for each level
                    for level in LEVEL:
                        if level in row and row[level]:
                            try:
                                difficulty = float(row[level])
                                charter = row.get(f"{level}_charter", '')
                                
                                song_info.chart[level] = Chart(
                                    id=song_id,
                                    rank=level,
                                    charter=charter,
                                    difficulty=difficulty
                                )
                            except ValueError:
                                continue
        
        # Load notesInfo.json for note counts
        notes_path = self.info_path / 'notesInfo.json'
        if notes_path.exists():
            with open(notes_path, 'r', encoding='utf-8') as f:
                notes_info = json.load(f)
                for song_id_without_suffix, levels in notes_info.items():
                    song_id = f"{song_id_without_suffix}.0"
                    if song_id not in self.ori_info:
                        continue
                    
                    song_info = self.ori_info[song_id]
                    
                    for level, notes_data in levels.items():
                        if level in song_info.chart:
                            chart = song_info.chart[level]
                            # Parse note counts
                            if 't' in notes_data:
                                t = notes_data['t']
                                chart.tap = t[0] if len(t) > 0 else 0
                                chart.drag = t[1] if len(t) > 1 else 0
                                chart.hold = t[2] if len(t) > 2 else 0
                                chart.flick = t[3] if len(t) > 3 else 0
                                chart.combo = sum(t[:4])
                            
                            # Parse max time
                            if 'm' in notes_data:
                                chart.maxTime = notes_data['m']
                            
                            # Parse distribution
                            if 'd' in notes_data:
                                chart.distribution = notes_data['d']
    
    async def _load_nicknames(self) -> None:
        """Load song nicknames from YAML."""
        nicklist_path = self.info_path / 'nicklist.yaml'
        if nicklist_path.exists():
            with open(nicklist_path, 'r', encoding='utf-8') as f:
                nicklist_data = yaml.safe_load(f) or {}
                
                for song_id_without_suffix, nicks in nicklist_data.items():
                    song_id = f"{song_id_without_suffix}.0"
                    if song_id not in self.ori_info:
                        continue
                    
                    self.nicklist[song_id] = nicks
                    
                    # Build reverse mapping
                    for nick in nicks:
                        if nick not in self.songnick:
                            self.songnick[nick] = []
                        self.songnick[nick].append(song_id)
    
    async def _load_chapter_info(self) -> None:
        """Load chapter information from YAML."""
        chaplist_path = self.info_path / 'chaplist.yaml'
        if chaplist_path.exists():
            with open(chaplist_path, 'r', encoding='utf-8') as f:
                self.chap_list = yaml.safe_load(f) or {}
                
                # Build reverse mapping
                for chapter, aliases in self.chap_list.items():
                    for alias in aliases:
                        if alias not in self.chap_nick:
                            self.chap_nick[alias] = []
                        self.chap_nick[alias].append(chapter)
    
    async def _load_tips(self) -> None:
        """Load tips from YAML."""
        tips_path = self.info_path / 'tips.yaml'
        if tips_path.exists():
            with open(tips_path, 'r', encoding='utf-8') as f:
                self.tips = yaml.safe_load(f) or []
    
    async def _load_notice(self) -> None:
        """Load notice from JSON."""
        notice_path = self.info_path / 'notice.json'
        if notice_path.exists():
            with open(notice_path, 'r', encoding='utf-8') as f:
                self.notice_json = json.load(f)
    
    def _build_difficulty_index(self) -> None:
        """Build index of songs by difficulty."""
        self.info_by_difficulty = {}
        
        for song_id, song_info in self.ori_info.items():
            for level, chart in song_info.chart.items():
                difficulty_key = f"{chart.difficulty:.1f}"
                
                if difficulty_key not in self.info_by_difficulty:
                    self.info_by_difficulty[difficulty_key] = []
                
                self.info_by_difficulty[difficulty_key].append(chart)
    
    def get_info(self, song_id: str) -> Optional[SongsInfo]:
        """Get song info by ID.
        
        Args:
            song_id: Song ID (with or without .0 suffix)
            
        Returns:
            SongsInfo or None
        """
        # Add .0 suffix if not present
        if not song_id.endswith('.0'):
            song_id = f"{song_id}.0"
        
        return self.ori_info.get(song_id)
    
    def get_info_by_name(self, song_name: str) -> Optional[SongsInfo]:
        """Get song info by name.
        
        Args:
            song_name: Song name
            
        Returns:
            SongsInfo or None
        """
        song_id = self.idssong.get(song_name)
        if song_id:
            return self.ori_info.get(song_id)
        return None
    
    def get_song_id(self, song_name: str) -> Optional[str]:
        """Get song ID by name.
        
        Args:
            song_name: Song name
            
        Returns:
            Song ID or None
        """
        return self.idssong.get(song_name)
    
    def get_song_name(self, song_id: str) -> Optional[str]:
        """Get song name by ID.
        
        Args:
            song_id: Song ID
            
        Returns:
            Song name or None
        """
        # Add .0 suffix if not present
        if not song_id.endswith('.0'):
            song_id = f"{song_id}.0"
        
        return self.songsid.get(song_id)
    
    def get_nicknames(self, song_id: str) -> List[str]:
        """Get nicknames for a song.
        
        Args:
            song_id: Song ID
            
        Returns:
            List of nicknames
        """
        # Add .0 suffix if not present
        if not song_id.endswith('.0'):
            song_id = f"{song_id}.0"
        
        return self.nicklist.get(song_id, [])
    
    def fuzzy_search(self, query: str, distance_threshold: float = 0.85) -> List[str]:
        """Fuzzy search for songs by name or nickname.
        
        Args:
            query: Search query
            distance_threshold: Jaro-Winkler distance threshold
            
        Returns:
            List of matching song IDs
        """
        from difflib import SequenceMatcher
        
        results = []
        
        # Search in song names
        for song_id, song_name in self.songsid.items():
            ratio = SequenceMatcher(None, query.lower(), song_name.lower()).ratio()
            if ratio >= distance_threshold:
                results.append((song_id, ratio))
        
        # Search in nicknames
        for nick, ids in self.songnick.items():
            ratio = SequenceMatcher(None, query.lower(), nick.lower()).ratio()
            if ratio >= distance_threshold:
                for song_id in ids:
                    results.append((song_id, ratio))
        
        # Sort by similarity and remove duplicates
        results.sort(key=lambda x: x[1], reverse=True)
        seen = set()
        unique_results = []
        for song_id, ratio in results:
            if song_id not in seen:
                seen.add(song_id)
                unique_results.append(song_id)
        
        return unique_results
    
    def get_chapter_songs(self, chapter: str) -> List[str]:
        """Get songs in a chapter.
        
        Args:
            chapter: Chapter name
            
        Returns:
            List of song IDs
        """
        results = []
        for song_id, song_info in self.ori_info.items():
            if song_info.chapter == chapter:
                results.append(song_id)
        return results
    
    def get_difficulty_songs(self, difficulty: float, level: str = None) -> List[Chart]:
        """Get songs by difficulty.
        
        Args:
            difficulty: Difficulty value
            level: Optional level filter
            
        Returns:
            List of charts
        """
        difficulty_key = f"{difficulty:.1f}"
        charts = self.info_by_difficulty.get(difficulty_key, [])
        
        if level:
            charts = [c for c in charts if c.rank == level]
        
        return charts
    
    def get_random_song(self, min_difficulty: float = 0, max_difficulty: float = 20, 
                        level: str = None) -> Optional[SongsInfo]:
        """Get a random song.
        
        Args:
            min_difficulty: Minimum difficulty
            max_difficulty: Maximum difficulty
            level: Optional level filter
            
        Returns:
            Random SongsInfo or None
        """
        import random
        
        candidates = []
        for song_id, song_info in self.ori_info.items():
            for chart_level, chart in song_info.chart.items():
                if min_difficulty <= chart.difficulty <= max_difficulty:
                    if level is None or chart_level == level:
                        candidates.append(song_info)
                        break
        
        return random.choice(candidates) if candidates else None


# Global instance
_get_info_instance: Optional[GetInfo] = None


def get_info_instance(resources_path: str = None) -> GetInfo:
    """Get or create global GetInfo instance.
    
    Args:
        resources_path: Path to resources directory (required on first call)
        
    Returns:
        GetInfo instance
    """
    global _get_info_instance
    
    if _get_info_instance is None:
        if resources_path is None:
            raise ValueError("resources_path required on first call")
        _get_info_instance = GetInfo(resources_path)
    
    return _get_info_instance
