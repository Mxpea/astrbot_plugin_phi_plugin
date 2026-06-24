"""
Byte reader for parsing binary data.
Ported from phi-plugin-main/lib/ByteReader.js
"""

import struct
from typing import Optional


class ByteReader:
    """Binary data reader for parsing Phigros save data."""
    
    def __init__(self, data: bytes, position: int = 0):
        """Initialize ByteReader.
        
        Args:
            data: Binary data to read from
            position: Starting position in data
        """
        if isinstance(data, str):
            # Assume hex string
            self.data = bytes.fromhex(data)
        else:
            self.data = data
        self.position = position
    
    def remaining(self) -> int:
        """Get number of remaining bytes.
        
        Returns:
            Number of bytes remaining
        """
        return len(self.data) - self.position
    
    def get_byte(self) -> int:
        """Read a single byte.
        
        Returns:
            Byte value (0-255)
        """
        if self.position >= len(self.data):
            raise IndexError("No more bytes to read")
        value = self.data[self.position]
        self.position += 1
        return value
    
    def put_byte(self, num: int) -> None:
        """Write a single byte.
        
        Args:
            num: Byte value to write (0-255)
        """
        self.data[self.position] = num & 0xFF
        self.position += 1
    
    def get_all_bytes(self) -> bytes:
        """Get all remaining bytes.
        
        Returns:
            Remaining bytes as bytes object
        """
        return self.data[self.position:]
    
    def get_short(self) -> int:
        """Read a 16-bit short integer (little-endian).
        
        Returns:
            Short integer value
        """
        if self.position + 2 > len(self.data):
            raise IndexError("Not enough bytes for short")
        value = struct.unpack_from('<H', self.data, self.position)[0]
        self.position += 2
        return value
    
    def put_short(self, num: int) -> None:
        """Write a 16-bit short integer (little-endian).
        
        Args:
            num: Short integer value to write
        """
        struct.pack_into('<H', self.data, self.position, num & 0xFFFF)
        self.position += 2
    
    def get_int(self) -> int:
        """Read a 32-bit integer (little-endian).
        
        Returns:
            Integer value
        """
        if self.position + 4 > len(self.data):
            raise IndexError("Not enough bytes for int")
        value = struct.unpack_from('<i', self.data, self.position)[0]
        self.position += 4
        return value
    
    def put_int(self, num: int) -> None:
        """Write a 32-bit integer (little-endian).
        
        Args:
            num: Integer value to write
        """
        struct.pack_into('<i', self.data, self.position, num)
        self.position += 4
    
    def get_float(self) -> float:
        """Read a 32-bit float (little-endian).
        
        Returns:
            Float value
        """
        if self.position + 4 > len(self.data):
            raise IndexError("Not enough bytes for float")
        value = struct.unpack_from('<f', self.data, self.position)[0]
        self.position += 4
        return value
    
    def put_float(self, num: float) -> None:
        """Write a 32-bit float (little-endian).
        
        Args:
            num: Float value to write
        """
        struct.pack_into('<f', self.data, self.position, num)
        self.position += 4
    
    def get_varint(self) -> int:
        """Read a variable-length integer.
        
        Variable-length integer encoding:
        - If first byte < 128: single byte value
        - If first byte >= 128: two bytes, lower 7 bits of first + 7 bits of second
        
        Returns:
            Integer value
        """
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
        """Skip variable-length integer(s).
        
        Args:
            num: Number of varints to skip. If None, skip one.
        """
        if num is not None:
            for _ in range(num):
                self.skip_varint()
        else:
            if self.position < len(self.data):
                if self.data[self.position] > 127:
                    self.position += 2
                else:
                    self.position += 1
    
    def get_bytes(self) -> bytes:
        """Read a length-prefixed byte array.
        
        Returns:
            Byte array
        """
        length = self.get_byte()
        if self.position + length > len(self.data):
            raise IndexError("Not enough bytes for byte array")
        result = self.data[self.position:self.position + length]
        self.position += length
        return result
    
    def get_string(self) -> str:
        """Read a length-prefixed UTF-8 string.
        
        Returns:
            String value
        """
        length = self.get_varint()
        if self.position + length > len(self.data):
            raise IndexError("Not enough bytes for string")
        result = self.data[self.position:self.position + length].decode('utf-8')
        self.position += length
        return result
    
    def put_string(self, s: str) -> None:
        """Write a length-prefixed UTF-8 string.
        
        Args:
            s: String to write
        """
        encoded = s.encode('utf-8')
        self.put_byte(len(encoded))
        self.data[self.position:self.position + len(encoded)] = encoded
        self.position += len(encoded)
    
    def skip_string(self) -> None:
        """Skip a length-prefixed string."""
        length = self.get_byte()
        self.position += length
