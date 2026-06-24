"""
AES encryption/decryption for Phigros save data.
Ported from phi-plugin-main/lib/AES.js
"""

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64


class AESCipher:
    """AES cipher for Phigros save encryption/decryption."""
    
    # Default key and IV from Phigros
    DEFAULT_KEY = base64.b64decode("6Jaa0qVAJZuXkZCLiOa/Ax5tIZVu+taKUN1V1nqwkks=")
    DEFAULT_IV = base64.b64decode("Kk/wisgNYwcAV8WVGMgyUw==")
    
    @staticmethod
    def encrypt(plaintext: str, key: bytes = None, iv: bytes = None) -> str:
        """Encrypt plaintext using AES-CBC.
        
        Args:
            plaintext: Text to encrypt
            key: Encryption key (default: Phigros key)
            iv: Initialization vector (default: Phigros IV)
            
        Returns:
            Base64-encoded encrypted text
        """
        if key is None:
            key = AESCipher.DEFAULT_KEY
        if iv is None:
            iv = AESCipher.DEFAULT_IV
        
        # Ensure key and iv are bytes
        if isinstance(key, str):
            key = key.encode('utf-8')
        if isinstance(iv, str):
            iv = iv.encode('utf-8')
        
        # Create cipher
        cipher = AES.new(key, AES.MODE_CBC, iv)
        
        # Pad and encrypt
        plaintext_bytes = plaintext.encode('utf-8')
        padded_data = pad(plaintext_bytes, AES.block_size)
        encrypted = cipher.encrypt(padded_data)
        
        # Return base64 encoded
        return base64.b64encode(encrypted).decode('utf-8')
    
    @staticmethod
    def decrypt(ciphertext: str, key: bytes = None, iv: bytes = None) -> bytes:
        """Decrypt ciphertext using AES-CBC.
        
        Args:
            ciphertext: Base64-encoded encrypted text
            key: Decryption key (default: Phigros key)
            iv: Initialization vector (default: Phigros IV)
            
        Returns:
            Decrypted bytes
        """
        if key is None:
            key = AESCipher.DEFAULT_KEY
        if iv is None:
            iv = AESCipher.DEFAULT_IV
        
        # Ensure key and iv are bytes
        if isinstance(key, str):
            key = key.encode('utf-8')
        if isinstance(iv, str):
            iv = iv.encode('utf-8')
        
        # Decode base64
        encrypted_data = base64.b64decode(ciphertext)
        
        # Create cipher and decrypt
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(encrypted_data)
        
        # Remove padding
        try:
            unpadded = unpad(decrypted, AES.block_size)
        except ValueError:
            # If padding is invalid, return raw decrypted data
            unpadded = decrypted
        
        return unpadded
    
    @staticmethod
    def decrypt_to_string(ciphertext: str, key: bytes = None, iv: bytes = None) -> str:
        """Decrypt ciphertext to string.
        
        Args:
            ciphertext: Base64-encoded encrypted text
            key: Decryption key (default: Phigros key)
            iv: Initialization vector (default: Phigros IV)
            
        Returns:
            Decrypted string
        """
        decrypted = AESCipher.decrypt(ciphertext, key, iv)
        return decrypted.decode('utf-8')
    
    @staticmethod
    def decrypt_to_hex(ciphertext: str, key: bytes = None, iv: bytes = None) -> str:
        """Decrypt ciphertext to hex string.
        
        Args:
            ciphertext: Base64-encoded encrypted text
            key: Decryption key (default: Phigros key)
            iv: Initialization vector (default: Phigros IV)
            
        Returns:
            Decrypted data as hex string
        """
        decrypted = AESCipher.decrypt(ciphertext, key, iv)
        return decrypted.hex()


# Convenience functions matching original JS API
async def encrypt(text: str, key: bytes = None, iv: bytes = None) -> str:
    """Encrypt text (async wrapper).
    
    Args:
        text: Text to encrypt
        key: Encryption key
        iv: Initialization vector
        
    Returns:
        Encrypted text
    """
    return AESCipher.encrypt(text, key, iv)


async def decrypt(word: str) -> str:
    """Decrypt text (async wrapper).
    
    Args:
        word: Encrypted text
        
    Returns:
        Decrypted hex string
    """
    return AESCipher.decrypt_to_hex(word)
