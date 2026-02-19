import logging
import datetime
from sqlalchemy import select, update, delete, desc, func
from .session import AsyncSessionLocal
from .models import User, City, WeatherHistory, NotificationPreference, WeatherSnapshot, WardrobeItem
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

async def init_db():
    """Initializes the database and performs migrations."""
    from .session import engine
    from .models import Base
    async with engine.begin() as conn:
        # This will create tables if they don't exist
        # Useful for fresh deployments on Railway
        await conn.run_sync(Base.metadata.create_all)
    logger.info("🗄 База данных инициализирована (таблицы проверены/созданы)")

async def upsert_user(user_id: int, username: str, user_name: str = "друг", timezone: str = 'Europe/Moscow'):
    async with AsyncSessionLocal() as session:
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
            prefs = NotificationPreference(user_id=user_id)
            session.add(prefs)
        await session.commit()

async def update_user_field(user_id: int, field: str, value):
    async with AsyncSessionLocal() as session:
        await session.execute(update(User).where(User.user_id == user_id).values({field: value}))
        await session.commit()

async def get_user(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if user:
            return {c.name: getattr(user, c.name) for c in user.__table__.columns}
        return None

async def get_all_active_users():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.is_active == True))
        users = result.scalars().all()
        return [{c.name: getattr(u, c.name) for c in u.__table__.columns} for u in users]

async def update_last_notification(user_id: int):
    async with AsyncSessionLocal() as session:
        await session.execute(update(User).where(User.user_id == user_id).values(last_notification=func.now()))
        await session.commit()

async def update_user_timezone(user_id: int, timezone: str):
    async with AsyncSessionLocal() as session:
        await session.execute(update(User).where(User.user_id == user_id).values(timezone=timezone, timezone_initialized=1))
        await session.commit()

async def add_city(user_id: int, city_name: str, lat: float, lon: float, is_primary: bool = False):
    async with AsyncSessionLocal() as session:
        if is_primary:
            await session.execute(update(City).where(City.user_id == user_id).values(is_primary=False))
        
        count_result = await session.execute(select(func.count(City.id)).where(City.user_id == user_id))
        count = count_result.scalar()
        if count == 0:
            is_primary = True

        new_city = City(user_id=user_id, city_name=city_name, latitude=lat, longitude=lon, is_primary=is_primary)
        session.add(new_city)
        await session.commit()

async def get_user_cities(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(City)
            .where(City.user_id == user_id)
            .order_by(desc(City.is_primary), City.id)
        )
        cities = result.scalars().all()
        return [{c.name: getattr(city, c.name) for c in city.__table__.columns} for city in cities]

async def get_primary_city(user_id: int):
    cities = await get_user_cities(user_id)
    for c in cities:
        if c['is_primary']:
            return c
    return cities[0] if cities else None

async def remove_city(user_id: int, city_id: int):
    async with AsyncSessionLocal() as session:
        await session.execute(delete(City).where(City.id == city_id, City.user_id == user_id))
        await session.commit()
        cities = await get_user_cities(user_id)
        if cities and not any(c['is_primary'] for c in cities):
             await session.execute(update(City).where(City.id == cities[0]['id']).values(is_primary=True))
             await session.commit()

async def set_primary_city(user_id: int, city_id: int):
    async with AsyncSessionLocal() as session:
        await session.execute(update(City).where(City.user_id == user_id).values(is_primary=False))
        await session.execute(update(City).where(City.id == city_id, City.user_id == user_id).values(is_primary=True))
        await session.commit()

async def save_weather_history(user_id: int, city_name: str, date: str, data: dict):
    async with AsyncSessionLocal() as session:
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

async def get_weekly_stats(user_id: int, city_name: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(WeatherHistory)
            .where(WeatherHistory.user_id == user_id, WeatherHistory.city_name == city_name)
            .order_by(desc(WeatherHistory.date))
            .limit(7)
        )
        hists = result.scalars().all()
        return [{c.name: getattr(h, c.name) for c in h.__table__.columns} for h in hists]

async def get_notification_preferences(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(NotificationPreference).where(NotificationPreference.user_id == user_id))
        row = result.scalar_one_or_none()
        if not row:
            row = NotificationPreference(user_id=user_id)
            session.add(row)
            await session.commit()
            return {c.name: getattr(row, c.name) for c in row.__table__.columns}
        return {c.name: getattr(row, c.name) for c in row.__table__.columns}

async def update_notification_preference(user_id: int, column: str, value):
    async with AsyncSessionLocal() as session:
        await session.execute(update(NotificationPreference).where(NotificationPreference.user_id == user_id).values({column: value}))
        await session.commit()

async def save_weather_snapshot(user_id, city, temp, condition):
    async with AsyncSessionLocal() as session:
        snapshot = WeatherSnapshot(user_id=user_id, city_name=city, temp=temp, condition=condition)
        session.add(snapshot)
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=48)
        await session.execute(delete(WeatherSnapshot).where(WeatherSnapshot.timestamp < cutoff))
        await session.commit()

async def get_weather_comparison(user_id, city):
    async with AsyncSessionLocal() as session:
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
        row = result.scalar_one_or_none()
        return {c.name: getattr(row, c.name) for c in row.__table__.columns} if row else None

async def save_wardrobe_item(user_id: int, photo_id: str, data: dict):
    async with AsyncSessionLocal() as session:
        item = WardrobeItem(
            user_id=user_id,
            photo_file_id=photo_id,
            clothing_type=data.get('clothing_type'),
            material=data.get('material'),
            warmth_level=data.get('warmth_level'),
            suitable_temp_min=data.get('suitable_temp_min'),
            suitable_temp_max=data.get('suitable_temp_max'),
            style=data.get('style'),
            description=data.get('description')
        )
        session.add(item)
        await session.commit()

async def get_users_with_null_timezone():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User.user_id).where(User.timezone == None, User.timezone_initialized == 0))
        return [row[0] for row in result.fetchall()]

async def mark_timezone_initialized(user_id: int):
    async with AsyncSessionLocal() as session:
        await session.execute(update(User).where(User.user_id == user_id).values(timezone_initialized=1))
        await session.commit()

async def get_admin_stats():
    async with AsyncSessionLocal() as session:
        stats = {}
        stats['total_users'] = (await session.execute(select(func.count(User.user_id)))).scalar()
        stats['active_users'] = (await session.execute(select(func.count(User.user_id)).where(User.is_active == True))).scalar()
        stats['total_cities'] = (await session.execute(select(func.count(City.id)))).scalar()
        stats['history_records'] = (await session.execute(select(func.count(WeatherHistory.id)))).scalar()
        return stats
