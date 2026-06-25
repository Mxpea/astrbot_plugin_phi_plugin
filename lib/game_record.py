"""
Game record data class.
Ported from phi-plugin-main/lib/GameRecord.js
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .byte_reader import ByteReader
from .level_record import LevelRecord
from .util import get_bit, calculate_rks


@dataclass
class GameRecord:
    """Represents all game records (scores for all songs).
    
    Attributes:
        songsnum: Number of songs
        records: Dictionary mapping song ID to list of LevelRecords
    """
    songsnum: int = 0
    records: Dict[str, List[Optional[LevelRecord]]] = field(default_factory=dict)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'GameRecord':
        """Parse GameRecord from binary data.
        
        Args:
            data: Binary data to parse
            
        Returns:
            GameRecord instance
            
        Raises:
            ValueError: If version mismatch
        """
        reader = ByteReader(data)
        
        # Read version byte
        version = reader.get_byte()
        if version != 1:
            raise ValueError(f"Unsupported game record version: {version}")
        
        # Read number of songs
        songsnum = reader.get_varint()
        
        records = {}
        
        # Parse each song record
        while reader.remaining() > 0:
            # Read song ID
            song_id = reader.get_string()
            
            # Skip varint (unknown purpose)
            reader.skip_varint()
            
            # Read flags
            length_flags = reader.get_byte()
            fc_flags = reader.get_byte()
            
            # Parse level records
            song_records = []
            for level in range(5):
                if Util.get_bit(length_flags, level):
                    # This level exists
                    score = reader.get_int()
                    acc = reader.get_float()
                    
                    # FC is true if score is 1000000 and acc is 100, or if FC flag is set
                    fc = (score == 1000000 and acc == 100.0) or Util.get_bit(fc_flags, level)
                    
                    record = LevelRecord(fc=fc, score=score, acc=acc)
                    song_records.append(record)
                else:
                    song_records.append(None)
            
            records[song_id] = song_records
        
        return cls(songsnum=songsnum, records=records)
    
    def get_record(self, song_id: str, level: int) -> Optional[LevelRecord]:
        """Get record for a specific song and level.
        
        Args:
            song_id: Song ID
            level: Level index (0=EZ, 1=HD, 2=IN, 3=AT, 4=LEGACY)
            
        Returns:
            LevelRecord or None if not played
        """
        if song_id not in self.records:
            return None
        if level < 0 or level >= len(self.records[song_id]):
            return None
        return self.records[song_id][level]
    
    def get_best_records(self, level: int) -> List[tuple]:
        """Get best records for a specific level, sorted by score.
        
        Args:
            level: Level index
            
        Returns:
            List of (song_id, record) tuples sorted by score descending
        """
        best = []
        for song_id, records in self.records.items():
            if level < len(records) and records[level] is not None:
                best.append((song_id, records[level]))
        
        # Sort by score descending, then by acc descending
        best.sort(key=lambda x: (x[1].score, x[1].acc), reverse=True)
        return best
    
    def get_rks_records(self, info_getter) -> List[dict]:
        """Get records with RKS calculation.
        
        RKS formula from Phigros:
        - ACC == 100%: RKS = difficulty
        - ACC < 70%: RKS = 0
        - Otherwise: RKS = difficulty * ((acc - 55) / 45)^2
        
        Args:
            info_getter: Function to get song info (difficulty, etc.)
            
        Returns:
            List of record dictionaries with RKS values
        """
        rks_records = []
        
        for song_id, records in self.records.items():
            song_info = info_getter(song_id)
            if not song_info:
                continue
            
            for level, record in enumerate(records):
                if record is None:
                    continue
                
                # Get difficulty for this level
                difficulty = song_info.get_difficulty(level)
                if difficulty is None:
                    continue
                
                # Calculate RKS using correct formula
                rks = calculate_rks(record.acc, difficulty)
                
                # Skip invalid records (ACC < 70%)
                if rks <= 0:
                    continue
                
                rks_records.append({
                    'song_id': song_id,
                    'level': level,
                    'record': record,
                    'difficulty': difficulty,
                    'rks': rks
                })
        
        # Sort by RKS descending
        rks_records.sort(key=lambda x: x['rks'], reverse=True)
        return rks_records
    
    def to_dict(self) -> dict:
        """Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        result = {}
        for song_id, records in self.records.items():
            result[song_id] = []
            for record in records:
                if record is None:
                    result[song_id].append(None)
                else:
                    result[song_id].append(record.to_dict())
        return result
