from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    username = Column(String)
    user_name = Column(String, default="друг")
    notification_time = Column(String, default="07:00")
    temperature_sensitivity = Column(String, default="normal")
    timezone = Column(String, default="Europe/Moscow")
    timezone_initialized = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    alerts_enabled = Column(Boolean, default=True)
    current_streak = Column(Integer, default=0)
    best_streak = Column(Integer, default=0)
    last_check_date = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_notification = Column(DateTime(timezone=True))

    cities = relationship("City", back_populates="user", cascade="all, delete-orphan")
    history = relationship("WeatherHistory", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("NotificationPreference", uselist=False, back_populates="user", cascade="all, delete-orphan")
    snapshots = relationship("WeatherSnapshot", back_populates="user", cascade="all, delete-orphan")
    wardrobe = relationship("WardrobeItem", back_populates="user", cascade="all, delete-orphan")

class City(Base):
    __tablename__ = "cities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    city_name = Column(String, nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="cities")

class WeatherHistory(Base):
    __tablename__ = "weather_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    city_name = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    temp_avg = Column(Float)
    temp_min = Column(Float)
    temp_max = Column(Float)
    condition = Column(String)
    precipitation = Column(Float)
    wind_speed = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint('user_id', 'city_name', 'date', name='_user_city_date_uc'),)

    user = relationship("User", back_populates="history")

class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    daily_forecast = Column(Boolean, default=True)
    rain_alerts = Column(Boolean, default=True)
    temp_change_alerts = Column(Boolean, default=True)
    uv_alerts = Column(Boolean, default=True)
    air_quality_alerts = Column(Boolean, default=True)
    perfect_weather_alerts = Column(Boolean, default=True)
    severe_weather_alerts = Column(Boolean, default=True)
    last_rain_alert = Column(DateTime(timezone=True))
    last_temp_alert = Column(DateTime(timezone=True))
    last_uv_alert = Column(DateTime(timezone=True))
    last_air_quality_alert = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="preferences")

class WeatherSnapshot(Base):
    __tablename__ = "weather_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    city_name = Column(String)
    temp = Column(Float)
    condition = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="snapshots")

class WardrobeItem(Base):
    __tablename__ = "wardrobe"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    photo_file_id = Column(String, nullable=False)
    clothing_type = Column(String)
    material = Column(String)
    warmth_level = Column(String)
    suitable_temp_min = Column(Integer)
    suitable_temp_max = Column(Integer)
    style = Column(String)
    description = Column(Text)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="wardrobe")
