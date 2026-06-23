"""
SongsInfo data class.
Ported from phi-plugin-main/model/class/SongsInfo.js
"""

from dataclasses import dataclass, field
from typing import Dict, Optional

from .chart import Chart


@dataclass
class SongsInfo:
    """Represents information about a song.
    
    Attributes:
        id: Song ID (with .0 suffix)
        song: Song name
        illustration: Path to illustration
        can_t_be_letter: Whether song cannot be used in letter guessing game
        can_t_be_guessill: Whether song cannot be used in illustration guessing game
        chapter: Chapter name
        bpm: BPM value
        composer: Composer name
        length: Song length
        illustrator: Illustrator name
        spinfo: Special info
        isOriginal: Whether this is an original song
        chart: Dictionary of chart data by difficulty
        sp_vis: Whether this is a special visible song
    """
    id: str = ""
    song: str = ""
    illustration: str = ""
    can_t_be_letter: bool = False
    can_t_be_guessill: bool = False
    chapter: str = ""
    bpm: str = ""
    composer: str = ""
    length: str = ""
    illustrator: str = ""
    spinfo: str = ""
    isOriginal: bool = False
    chart: Dict[str, Chart] = field(default_factory=dict)
    sp_vis: bool = False
    
    @classmethod
    def from_dict(cls, data: dict, get_illustration=None) -> 'SongsInfo':
        """Parse from dictionary.
        
        Args:
            data: Dictionary with song info data
            get_illustration: Optional function to get illustration path
            
        Returns:
            SongsInfo instance
        """
        song_info = cls(
            id=data.get('id', ''),
            song=data.get('song', ''),
            can_t_be_letter=data.get('can_t_be_letter', False),
            can_t_be_guessill=data.get('can_t_be_guessill', False),
            chapter=data.get('chapter', ''),
            bpm=data.get('bpm', ''),
            composer=data.get('composer', ''),
            length=data.get('length', ''),
            illustrator=data.get('illustrator', ''),
            spinfo=data.get('spinfo', ''),
            isOriginal=data.get('isOriginal', False),
            sp_vis=data.get('sp_vis', False)
        )
        
        # Get illustration
        if get_illustration and data.get('id'):
            song_info.illustration = get_illustration(data['id'])
        else:
            song_info.illustration = data.get('illustration', '')
        
        # Parse charts
        if 'chart' in data and isinstance(data['chart'], dict):
            for level, chart_data in data['chart'].items():
                if chart_data:
                    song_info.chart[level] = Chart.from_dict(chart_data)
        
        return song_info
    
    def get_difficulty(self, level: int) -> Optional[float]:
        """Get difficulty for a specific level.
        
        Args:
            level: Level index (0=EZ, 1=HD, 2=IN, 3=AT, 4=LEGACY)
            
        Returns:
            Difficulty value or None
        """
        level_names = ['EZ', 'HD', 'IN', 'AT', 'LEGACY']
        if level < 0 or level >= len(level_names):
            return None
        
        level_name = level_names[level]
        if level_name in self.chart:
            return self.chart[level_name].difficulty
        return None
    
    def get_chart(self, level: str) -> Optional[Chart]:
        """Get chart for a specific level.
        
        Args:
            level: Level name (EZ, HD, IN, AT, LEGACY)
            
        Returns:
            Chart or None
        """
        return self.chart.get(level)
    
    def has_level(self, level: str) -> bool:
        """Check if song has a specific level.
        
        Args:
            level: Level name
            
        Returns:
            True if level exists
        """
        return level in self.chart
    
    @property
    def max_difficulty(self) -> float:
        """Get maximum difficulty across all levels."""
        if not self.chart:
            return 0.0
        return max(chart.difficulty for chart in self.chart.values())
    
    @property
    def available_levels(self) -> list:
        """Get list of available levels."""
        return list(self.chart.keys())
    
    def to_dict(self) -> dict:
        """Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        result = {
            'id': self.id,
            'song': self.song,
            'illustration': self.illustration,
            'chapter': self.chapter,
            'bpm': self.bpm,
            'composer': self.composer,
            'length': self.length,
            'illustrator': self.illustrator,
            'spinfo': self.spinfo,
            'isOriginal': self.isOriginal,
            'sp_vis': self.sp_vis,
            'available_levels': self.available_levels,
            'max_difficulty': self.max_difficulty
        }
        
        if self.chart:
            result['chart'] = {level: chart.to_dict() for level, chart in self.chart.items()}
        
        return result
