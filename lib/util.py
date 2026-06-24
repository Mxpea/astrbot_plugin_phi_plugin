"""
Utility functions for bit manipulation and data processing.
Ported from phi-plugin-main/lib/Util.js
"""

class Util:
    """Utility class for bit operations and data processing."""
    
    @staticmethod
    def get_bit(data: int, index: int) -> bool:
        """Get bit at specific index from integer.
        
        Args:
            data: Integer value to extract bit from
            index: Bit position (0-based)
            
        Returns:
            True if bit is set, False otherwise
        """
        return bool(data & (1 << index))
    
    @staticmethod
    def modify_bit(data: int, index: int, b: bool) -> int:
        """Modify bit at specific index in integer.
        
        Args:
            data: Original integer value
            index: Bit position (0-based)
            b: New bit value (True = 1, False = 0)
            
        Returns:
            Modified integer value
        """
        result = 1 << index
        if b:
            data |= result
        else:
            data &= ~result
        return data
    
    @staticmethod
    def get_bit_field(data: int, start: int, length: int) -> int:
        """Extract a bit field from integer.
        
        Args:
            data: Integer value to extract from
            start: Starting bit position
            length: Number of bits to extract
            
        Returns:
            Extracted bit field value
        """
        mask = (1 << length) - 1
        return (data >> start) & mask
