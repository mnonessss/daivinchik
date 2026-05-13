from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, nullable=False, primary_key=True, index=True)
    telegram_id = Column(Integer, nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    last_active = Column(DateTime, nullable=False, default=datetime.now)
    referral_id = Column(Integer, index=True)


class Profiles(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True, nullable=False)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, unique=True
        )
    name = Column(String, nullable=False, unique=True)
    age = Column(Integer, index=True)
    gender = Column(String, index=True)
    city = Column(String, index=True)
    bio = Column(String)
    photos_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    preferred_age_min = Column(Integer, nullable=False, default=0)
    preferred_age_max = Column(Integer, nullable=False, default=150)
    preferred_city = Column(String)
    preferred_gender = Column(String)


class Ranking(Base):
    __tablename__ = "ranking"

    id = Column(Integer, primary_key=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    primary_score = Column(Float, nullable=False, default=0.0)
    behavioral_score = Column(Float, nullable=False, default=0.0)
    final_score = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)


class Interactions(Base):
    __tablename__ = "interactions"
    __table_args__ = (
        Index("ix_interactions_from_to_action", "from_user", "to_user", "action"),
    )

    id = Column(Integer, primary_key=True, index=True, nullable=False)
    from_user = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    to_user = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class ProfilePhotos(Base):
    __tablename__ = "profile_photos"

    id = Column(Integer, primary_key=True, index=True, nullable=False)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    telegram_file_id = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
