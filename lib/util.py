"""
Utility functions for bit manipulation and data processing.
Ported from phi-plugin-main/lib/Util.js and model/fCompute.js
"""


def get_bit(data: int, index: int) -> bool:
    """Get bit at specific index from integer.
    
    Args:
        data: Integer value to extract bit from
        index: Bit position (0-based)
        
    Returns:
        True if bit is set, False otherwise
    """
    return bool(data & (1 << index))


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


def calculate_rks(acc: float, difficulty: float) -> float:
    """Calculate RKS (Rating Score) based on ACC and difficulty.
    
    RKS formula from Phigros:
    - ACC == 100%: RKS = difficulty (full score uses chart difficulty directly)
    - ACC < 70%: RKS = 0 (invalid ACC)
    - Otherwise: RKS = difficulty * ((acc - 55) / 45)^2
    
    Args:
        acc: Accuracy percentage (0-100)
        difficulty: Chart difficulty rating
        
    Returns:
        Calculated RKS value
    """
    if acc == 100.0:
        return float(difficulty)
    elif acc < 70.0:
        return 0.0
    else:
        return difficulty * (((acc - 55.0) / 45.0) ** 2)


def calculate_suggest(target_rks: float, difficulty: float) -> float:
    """Calculate required ACC to achieve target RKS.
    
    Formula: acc = 45 * sqrt(rks / difficulty) + 55
    
    Args:
        target_rks: Target RKS value
        difficulty: Chart difficulty rating
        
    Returns:
        Required ACC percentage, or -1 if impossible
    """
    if difficulty <= 0:
        return -1.0
    
    acc = 45.0 * ((target_rks / difficulty) ** 0.5) + 55.0
    
    if acc >= 100.0:
        return -1.0  # Impossible
    return acc


def calculate_b30_rks(phi_rks: list, b27_rks: list) -> float:
    """Calculate overall B30 RKS.
    
    B30 RKS = average of top 3 PHI + top 27 normal scores
    
    Args:
        phi_rks: List of PHI score RKS values (top 3)
        b27_rks: List of normal score RKS values (top 27)
        
    Returns:
        Overall B30 RKS
    """
    all_rks = []
    
    # Add top 3 PHI scores
    if phi_rks:
        all_rks.extend(sorted(phi_rks, reverse=True)[:3])
    
    # Add top 27 normal scores
    if b27_rks:
        all_rks.extend(sorted(b27_rks, reverse=True)[:27])
    
    if not all_rks:
        return 0.0
    
    return sum(all_rks) / 30.0
