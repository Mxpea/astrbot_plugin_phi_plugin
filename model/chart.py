"""
Chart data class.
Ported from phi-plugin-main/model/class/Chart.js
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple


@dataclass
class Chart:
    """Represents a chart (difficulty level) for a song.
    
    Attributes:
        id: Song ID
        rank: Difficulty level (EZ, HD, IN, AT, LEGACY)
        charter: Chart designer
        difficulty: Difficulty rating
        tap: Number of tap notes
        drag: Number of drag notes
        hold: Number of hold notes
        flick: Number of flick notes
        combo: Total combo count
        maxTime: Maximum time in seconds
        distribution: Note distribution [tap, drag, hold, flick, total]
    """
    id: str = ""
    rank: str = ""
    charter: str = ""
    difficulty: float = 0.0
    tap: Optional[int] = None
    drag: Optional[int] = None
    hold: Optional[int] = None
    flick: Optional[int] = None
    combo: Optional[int] = None
    maxTime: Optional[float] = None
    distribution: Optional[List[Tuple[int, int, int, int, int]]] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Chart':
        """Parse from dictionary.
        
        Args:
            data: Dictionary with chart data
            
        Returns:
            Chart instance
        """
        chart = cls(
            id=data.get('id', ''),
            rank=data.get('rank', ''),
            charter=data.get('charter', ''),
            difficulty=float(data.get('difficulty', 0))
        )
        
        # Parse note counts if available
        if 'tap' in data:
            chart.tap = int(data.get('tap', 0))
            chart.drag = int(data.get('drag', 0))
            chart.hold = int(data.get('hold', 0))
            chart.flick = int(data.get('flick', 0))
            chart.combo = int(data.get('combo', 0))
            chart.maxTime = float(data.get('maxTime', 0))
            chart.distribution = data.get('distribution')
        
        return chart
    
    @property
    def has_notes(self) -> bool:
        """Check if note counts are available."""
        return self.tap is not None
    
    @property
    def total_notes(self) -> int:
        """Get total note count."""
        if self.combo is not None:
            return self.combo
        if self.tap is not None:
            return (self.tap or 0) + (self.drag or 0) + (self.hold or 0) + (self.flick or 0)
        return 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        result = {
            'id': self.id,
            'rank': self.rank,
            'charter': self.charter,
            'difficulty': self.difficulty
        }
        
        if self.has_notes:
            result.update({
                'tap': self.tap,
                'drag': self.drag,
                'hold': self.hold,
                'flick': self.flick,
                'combo': self.combo,
                'maxTime': self.maxTime,
                'distribution': self.distribution
            })
        
        return result
