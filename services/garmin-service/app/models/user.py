from sqlalchemy import Column, String, Boolean, DateTime, LargeBinary, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base
import uuid

class UserCredential(Base):
    __tablename__ = "user_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    service = Column(String(50), nullable=False)  # 'garmin', 'hevy', etc.
    credential_type = Column(String(50), nullable=False)  # 'username_password', 'api_key', 'oauth_token'
    encrypted_data = Column(LargeBinary, nullable=False)  # Main encrypted credential
    salt = Column(LargeBinary, nullable=False)  # Salt for encryption
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    metadata_ = Column("metadata", JSON, default={})  # Additional encrypted data