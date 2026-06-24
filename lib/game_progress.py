"""
Game progress data class.
Ported from phi-plugin-main/lib/GameProgress.js
"""

from dataclasses import dataclass, field
from typing import List

from .byte_reader import ByteReader
from .util import Util


@dataclass
class GameProgress:
    """Represents game progress data.
    
    Attributes:
        is_first_run: Whether this is the first run
        legacy_chapter_finished: Whether legacy chapter is finished
        already_show_collection_tip: Whether collection tip has been shown
        already_show_auto_unlock_in_tip: Whether auto unlock IN tip has been shown
        completed: Completed songs string
        song_update_info: Song update info value
        challenge_mode_rank: Challenge mode rank
        money: List of money values [KiB, MiB, GiB, TiB, PiB]
        unlock_flag_of_spasmodic: Unlock flag for Spasmodic
        unlock_flag_of_igallta: Unlock flag for Igallta
        unlock_flag_of_rrharil: Unlock flag for Rrhar'il
        flag_of_song_record_key: Flag for song record key
        random_version_unlocked: Random version unlocked flag
        chapter8_unlock_begin: Whether chapter 8 unlock has begun
        chapter8_unlock_second_phase: Whether chapter 8 unlock second phase
        chapter8_passed: Whether chapter 8 is passed
        chapter8_song_unlocked: Chapter 8 song unlocked flag
    """
    is_first_run: bool = False
    legacy_chapter_finished: bool = False
    already_show_collection_tip: bool = False
    already_show_auto_unlock_in_tip: bool = False
    completed: str = ""
    song_update_info: int = 0
    challenge_mode_rank: int = 0
    money: List[int] = field(default_factory=lambda: [0, 0, 0, 0, 0])
    unlock_flag_of_spasmodic: int = 0
    unlock_flag_of_igallta: int = 0
    unlock_flag_of_rrharil: int = 0
    flag_of_song_record_key: int = 0
    random_version_unlocked: int = 0
    chapter8_unlock_begin: bool = False
    chapter8_unlock_second_phase: bool = False
    chapter8_passed: bool = False
    chapter8_song_unlocked: int = 0
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'GameProgress':
        """Parse GameProgress from binary data.
        
        Args:
            data: Binary data to parse
            
        Returns:
            GameProgress instance
        """
        reader = ByteReader(data)
        
        # Read flags byte
        flags = reader.get_byte()
        
        # Parse flags
        is_first_run = Util.get_bit(flags, 0)
        legacy_chapter_finished = Util.get_bit(flags, 1)
        already_show_collection_tip = Util.get_bit(flags, 2)
        already_show_auto_unlock_in_tip = Util.get_bit(flags, 3)
        
        # Read other fields
        completed = reader.get_string()
        song_update_info = reader.get_varint()
        challenge_mode_rank = reader.get_short()
        
        # Read money values
        money = [reader.get_varint() for _ in range(5)]
        
        # Read unlock flags
        unlock_flag_of_spasmodic = reader.get_byte()
        unlock_flag_of_igallta = reader.get_byte()
        unlock_flag_of_rrharil = reader.get_byte()
        flag_of_song_record_key = reader.get_byte()
        random_version_unlocked = reader.get_byte()
        
        # Read chapter 8 flags
        chapter8_flags = reader.get_byte()
        chapter8_unlock_begin = Util.get_bit(chapter8_flags, 0)
        chapter8_unlock_second_phase = Util.get_bit(chapter8_flags, 1)
        chapter8_passed = Util.get_bit(chapter8_flags, 2)
        chapter8_song_unlocked = reader.get_byte()
        
        return cls(
            is_first_run=is_first_run,
            legacy_chapter_finished=legacy_chapter_finished,
            already_show_collection_tip=already_show_collection_tip,
            already_show_auto_unlock_in_tip=already_show_auto_unlock_in_tip,
            completed=completed,
            song_update_info=song_update_info,
            challenge_mode_rank=challenge_mode_rank,
            money=money,
            unlock_flag_of_spasmodic=unlock_flag_of_spasmodic,
            unlock_flag_of_igallta=unlock_flag_of_igallta,
            unlock_flag_of_rrharil=unlock_flag_of_rrharil,
            flag_of_song_record_key=flag_of_song_record_key,
            random_version_unlocked=random_version_unlocked,
            chapter8_unlock_begin=chapter8_unlock_begin,
            chapter8_unlock_second_phase=chapter8_unlock_second_phase,
            chapter8_passed=chapter8_passed,
            chapter8_song_unlocked=chapter8_song_unlocked
        )
    
    @property
    def challenge_mode(self) -> int:
        """Get challenge mode color (0-5: white, green, blue, red, gold, rainbow)."""
        return self.challenge_mode_rank // 100
    
    @property
    def challenge_mode_rank_value(self) -> int:
        """Get challenge mode rank value."""
        return self.challenge_mode_rank % 100
    
    def to_dict(self) -> dict:
        """Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'is_first_run': self.is_first_run,
            'legacy_chapter_finished': self.legacy_chapter_finished,
            'completed': self.completed,
            'challenge_mode_rank': self.challenge_mode_rank,
            'challenge_mode': self.challenge_mode,
            'challenge_mode_rank_value': self.challenge_mode_rank_value,
            'money': self.money,
            'chapter8_unlock_begin': self.chapter8_unlock_begin,
            'chapter8_unlock_second_phase': self.chapter8_unlock_second_phase,
            'chapter8_passed': self.chapter8_passed
        }
