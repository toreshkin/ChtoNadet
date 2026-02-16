import logging
from sqlalchemy import select, update, delete, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from .models import User, City, WeatherHistory, NotificationPreference, WeatherSnapshot, WardrobeItem
import datetime

logger = logging.getLogger(__name__)

async def init_db(session: AsyncSession):
    # This will be handled by Alembic in a real setup, 
    # but for initial migrate we can use create_all if needed.
    # However, we have an existing DB, so we should be careful.
    pass

async def upsert_user(session: AsyncSession, user_id: int, username: str, user_name: str = "друг", timezone: str = 'Europe/Moscow'):
    result = await session.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    
    if user:
        user.username = username
        user.timezone = timezone
    else:
        user = User(
            user_id=user_id, 
            username=username, 
            user_name=user_name, 
            timezone=timezone,
            is_active=True,
            alerts_enabled=True
        )
        session.add(user)
        # Also create notification preferences
        prefs = NotificationPreference(user_id=user_id)
        session.add(prefs)
        
    await session.commit()
    return user

async def get_user(session: AsyncSession, user_id: int):
    result = await session.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()

async def get_all_active_users(session: AsyncSession):
    result = await session.execute(select(User).where(User.is_active == True))
    return result.scalars().all()

async def update_user_field(session: AsyncSession, user_id: int, field: str, value):
    await session.execute(update(User).where(User.user_id == user_id).values({field: value}))
    await session.commit()

async def add_city(session: AsyncSession, user_id: int, city_name: str, lat: float, lon: float, is_primary: bool = False):
    if is_primary:
        await session.execute(update(City).where(City.user_id == user_id).values(is_primary=False))
    
    # Check if first city
    count_result = await session.execute(select(func.count(City.id)).where(City.user_id == user_id))
    count = count_result.scalar()
    if count == 0:
        is_primary = True

    new_city = City(user_id=user_id, city_name=city_name, latitude=lat, longitude=lon, is_primary=is_primary)
    session.add(new_city)
    await session.commit()
    return new_city

async def get_user_cities(session: AsyncSession, user_id: int):
    result = await session.execute(
        select(City)
        .where(City.user_id == user_id)
        .order_by(desc(City.is_primary), City.id)
    )
    return result.scalars().all()

async def remove_city(session: AsyncSession, user_id: int, city_id: int):
    await session.execute(delete(City).where(City.id == city_id, City.user_id == user_id))
    await session.commit()
    
    # Ensure there's still a primary city
    cities = await get_user_cities(session, user_id)
    if cities and not any(c.is_primary for c in cities):
        cities[0].is_primary = True
        await session.commit()

async def set_primary_city(session: AsyncSession, user_id: int, city_id: int):
    await session.execute(update(City).where(City.user_id == user_id).values(is_primary=False))
    await session.execute(update(City).where(City.id == city_id, City.user_id == user_id).values(is_primary=True))
    await session.commit()

async def save_weather_history(session: AsyncSession, user_id: int, city_name: str, date: str, data: dict):
    # or_replace equivalent in SQLAlchemy is a bit more involved, 
    # but since it's a small app, we can check and insert/update.
    # Actually, using a proper upsert is better but backend dependent.
    # For now, simple check:
    date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    result = await session.execute(
        select(WeatherHistory)
        .where(WeatherHistory.user_id == user_id, WeatherHistory.city_name == city_name, WeatherHistory.date == date_obj)
    )
    hist = result.scalar_one_or_none()
    
    if hist:
        hist.temp_avg = data['temp_avg']
        hist.temp_min = data['temp_min']
        hist.temp_max = data['temp_max']
        hist.condition = data['condition']
        hist.precipitation = data['precipitation']
        hist.wind_speed = data['wind_speed']
    else:
        hist = WeatherHistory(
            user_id=user_id,
            city_name=city_name,
            date=date_obj,
            temp_avg=data['temp_avg'],
            temp_min=data['temp_min'],
            temp_max=data['temp_max'],
            condition=data['condition'],
            precipitation=data['precipitation'],
            wind_speed=data['wind_speed']
        )
        session.add(hist)
    await session.commit()

async def get_weekly_stats(session: AsyncSession, user_id: int, city_name: str):
    result = await session.execute(
        select(WeatherHistory)
        .where(WeatherHistory.user_id == user_id, WeatherHistory.city_name == city_name)
        .order_by(desc(WeatherHistory.date))
        .limit(7)
    )
    return result.scalars().all()

async def get_notification_preferences(session: AsyncSession, user_id: int):
    result = await session.execute(select(NotificationPreference).where(NotificationPreference.user_id == user_id))
    row = result.scalar_one_or_none()
    if not row:
        row = NotificationPreference(user_id=user_id)
        session.add(row)
        await session.commit()
    return row

async def update_notification_preference(session: AsyncSession, user_id: int, column: str, value):
    await session.execute(update(NotificationPreference).where(NotificationPreference.user_id == user_id).values({column: value}))
    await session.commit()

async def save_weather_snapshot(session: AsyncSession, user_id: int, city: str, temp: float, condition: str):
    snapshot = WeatherSnapshot(user_id=user_id, city_name=city, temp=temp, condition=condition)
    session.add(snapshot)
    # Cleanup > 48h
    cutoff = datetime.datetime.now() - datetime.timedelta(hours=48)
    await session.execute(delete(WeatherSnapshot).where(WeatherSnapshot.timestamp < cutoff))
    await session.commit()

async def get_weather_comparison(session: AsyncSession, user_id, city):
    # Simplified search for snapshot around 24h ago
    # In SQlite we use datetime('now', '-24 hours'). In SA we can use python datetime.
    target = datetime.datetime.now() - datetime.timedelta(hours=24)
    low = target - datetime.timedelta(hours=1)
    high = target + datetime.timedelta(hours=1)
    
    result = await session.execute(
        select(WeatherSnapshot)
        .where(WeatherSnapshot.user_id == user_id, WeatherSnapshot.city_name == city)
        .where(WeatherSnapshot.timestamp.between(low, high))
        .order_by(func.abs(func.julianday(WeatherSnapshot.timestamp) - func.julianday(target)))
        .limit(1)
    )
    return result.scalar_one_or_none()
