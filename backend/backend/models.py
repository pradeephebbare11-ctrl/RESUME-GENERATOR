from sqlalchemy import Column, String, Integer
from .database import Base
import hashlib
import hmac

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    hashed_password = Column(String)
    
    def verify_password(self, password: str) -> bool:
        """Verify a password against the hashed password using PBKDF2"""
        # Hash the provided password
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), b'salt', 100000).hex()
        return hmac.compare_digest(password_hash, self.hashed_password)
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using PBKDF2 (no 72 byte limit)"""
        # Use PBKDF2 for hashing (no byte limit like bcrypt)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), b'salt', 100000).hex()
        return password_hash
