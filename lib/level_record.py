"""
Level record data class.
Ported from phi-plugin-main/lib/LevelRecord.js
"""

from dataclasses import dataclass


@dataclass
class LevelRecord:
    """Represents a single level record (score for one difficulty).
    
    Attributes:
        fc: Whether the level is fully comboed
        score: Score value (0-1000000)
        acc: Accuracy percentage (0-100)
    """
    fc: bool = False
    score: int = 0
    acc: float = 0.0
    
    @property
    def is_phi(self) -> bool:
        """Check if this is a PHI score (1000000 score and 100% accuracy)."""
        return self.score == 1000000 and self.acc == 100.0
    
    @property
    def rating(self) -> str:
        """Get the rating based on score and FC status.
        
        Returns:
            Rating string: 'phi', 'FC', 'V', 'S', 'A', 'B', 'C', or 'F'
        """
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
        """Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'fc': self.fc,
            'score': self.score,
            'acc': self.acc,
            'rating': self.rating,
            'is_phi': self.is_phi
        }
