import aiosqlite
import logging
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

async def init_db():
    """Initializes the database and performs migrations."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # 1. Ensure basic table exists
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                city TEXT,
                latitude REAL,
                longitude REAL,
                notification_time TEXT DEFAULT '07:00',
                temperature_sensitivity TEXT DEFAULT 'normal',
                timezone TEXT DEFAULT 'Europe/Moscow',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_notification TIMESTAMP
            )
        """)
        
        # 2. Migrations for 'users' table columns
        try:
            await db.execute("ALTER TABLE users ADD COLUMN user_name TEXT DEFAULT 'друг'")
        except Exception:
            pass # Column likely exists
            
        try:
            await db.execute("ALTER TABLE users ADD COLUMN alerts_enabled BOOLEAN DEFAULT 1")
        except Exception:
            pass # Column likely exists

        try:
            await db.execute("ALTER TABLE users ADD COLUMN timezone TEXT DEFAULT 'Europe/Moscow'")
        except Exception:
            pass # Column likely exists
            
        try:
            await db.execute("ALTER TABLE users ADD COLUMN timezone_initialized BOOLEAN DEFAULT 0")
        except Exception:
            pass # Column likely exists

        # 3. Create 'cities' table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                city_name TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                is_primary BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        # 4. Create 'weather_history' table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS weather_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                city_name TEXT NOT NULL,
                date DATE NOT NULL,
                temp_avg REAL,
                temp_min REAL,
                temp_max REAL,
                condition TEXT,
                precipitation REAL,
                wind_speed REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                UNIQUE(user_id, city_name, date)
            )
        """)
        
        await db.commit()
        
        # 5. Migrate existing user cities to 'cities' table
        await migrate_cities(db)
        
        # 6. Initialize new features tables
        await create_notification_preferences_table()
        await create_snapshots_table()
        
        logger.info("Database initialized and migrated successfully.")

async def migrate_cities(db):
    """Moves legacy city data from users table to cities table."""
    async with db.execute("SELECT user_id, city, latitude, longitude FROM users") as cursor:
        users = await cursor.fetchall()
        
    for u in users:
        user_id, city, lat, lon = u
        if city:
            # Check if user already has cities
            async with db.execute("SELECT count(*) FROM cities WHERE user_id = ?", (user_id,)) as c:
                count = await c.fetchone()
                if count[0] == 0:
                    # Move legacy city to cities table as primary
                    await db.execute("""
                        INSERT INTO cities (user_id, city_name, latitude, longitude, is_primary)
                        VALUES (?, ?, ?, ?, 1)
                    """, (user_id, city, lat, lon))
                    logger.info(f"Migrated legacy city {city} for user {user_id}")
    await db.commit()

# --- CRUD Operations ---

async def upsert_user(user_id: int, username: str, user_name: str = "друг", timezone: str = 'Europe/Moscow'):
    """Registered or updates a user base info."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
            exists = await cursor.fetchone()
        
        if exists:
            await db.execute("UPDATE users SET username = ?, timezone = ? WHERE user_id = ?", (username, timezone, user_id))
        else:
            await db.execute("""
                INSERT INTO users (user_id, username, user_name, timezone, is_active, alerts_enabled)
                VALUES (?, ?, ?, ?, 1, 1)
            """, (user_id, username, user_name, timezone))
        await db.commit()

async def update_user_field(user_id: int, field: str, value):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        query = f"UPDATE users SET {field} = ? WHERE user_id = ?"
        await db.execute(query, (value, user_id))
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_all_active_users():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE is_active = 1") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def update_last_notification(user_id: int):
        await db.execute("UPDATE users SET last_notification = CURRENT_TIMESTAMP WHERE user_id = ?", (user_id,))
        await db.commit()

async def update_user_timezone(user_id: int, timezone: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE users SET timezone = ?, timezone_initialized = 1 WHERE user_id = ?", (timezone, user_id))
        await db.commit()

async def get_users_needing_timezone_init():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        # check for users who haven't initialized timezone or have null timezone
        async with db.execute("SELECT user_id FROM users WHERE timezone_initialized = 0 OR timezone IS NULL") as cursor:
            rows = await cursor.fetchall()
            return [row['user_id'] for row in rows]

async def mark_timezone_initialized(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE users SET timezone_initialized = 1 WHERE user_id = ?", (user_id,))
        await db.commit()

# --- City Management ---

async def add_city(user_id: int, city_name: str, lat: float, lon: float, is_primary: bool = False):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # If making primary, unset others
        if is_primary:
            await db.execute("UPDATE cities SET is_primary = 0 WHERE user_id = ?", (user_id,))
            
        # Check if already exists (simple name check for UX, or just insert)
        # We allow duplicates if coords differ, but simplest is just insert
        
        # If this is the FIRST city, make it primary automatically
        async with db.execute("SELECT count(*) FROM cities WHERE user_id = ?", (user_id,)) as c:
            count = await c.fetchone()
            if count[0] == 0:
                is_primary = True

        await db.execute("""
            INSERT INTO cities (user_id, city_name, latitude, longitude, is_primary)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, city_name, lat, lon, 1 if is_primary else 0))
        await db.commit()

async def get_user_cities(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM cities WHERE user_id = ? ORDER BY is_primary DESC, id ASC", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_primary_city(user_id: int):
    cities = await get_user_cities(user_id)
    for c in cities:
        if c['is_primary']:
            return c
    return cities[0] if cities else None

async def remove_city(user_id: int, city_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM cities WHERE id = ? AND user_id = ?", (city_id, user_id))
        # Ensure there's still a primary city
        await db.commit()
        # Re-check primary
        cities = await get_user_cities(user_id)
        if cities and not any(c['is_primary'] for c in cities):
             # Make the first one primary
             await db.execute("UPDATE cities SET is_primary = 1 WHERE id = ?", (cities[0]['id'],))
             await db.commit()

async def set_primary_city(user_id: int, city_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE cities SET is_primary = 0 WHERE user_id = ?", (user_id,))
        await db.execute("UPDATE cities SET is_primary = 1 WHERE id = ? AND user_id = ?", (city_id, user_id))
        await db.commit()

# --- History & Stats ---

async def save_weather_history(user_id: int, city_name: str, date: str, data: dict):
    """
    data should have keys: temp_avg, temp_min, temp_max, condition, precipitation, wind_speed
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO weather_history 
            (user_id, city_name, date, temp_avg, temp_min, temp_max, condition, precipitation, wind_speed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, city_name, date, data['temp_avg'], data['temp_min'], data['temp_max'], 
              data['condition'], data['precipitation'], data['wind_speed']))
        await db.commit()

async def get_weekly_stats(user_id: int, city_name: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Get last 7 days
        query = """
            SELECT * FROM weather_history 
            WHERE user_id = ? AND city_name = ? 
            ORDER BY date DESC LIMIT 7
        """
        async with db.execute(query, (user_id, city_name)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def create_notification_preferences_table():
    """Create table for granular notification settings."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS notification_preferences (
                user_id INTEGER PRIMARY KEY,
                daily_forecast BOOLEAN DEFAULT 1,
                rain_alerts BOOLEAN DEFAULT 1,
                temp_change_alerts BOOLEAN DEFAULT 1,
                uv_alerts BOOLEAN DEFAULT 1,
                air_quality_alerts BOOLEAN DEFAULT 1,
                perfect_weather_alerts BOOLEAN DEFAULT 1,
                severe_weather_alerts BOOLEAN DEFAULT 1,
                last_rain_alert TIMESTAMP,
                last_temp_alert TIMESTAMP,
                last_uv_alert TIMESTAMP,
                last_air_quality_alert TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Populate for existing users if missing
        await db.execute("""
            INSERT OR IGNORE INTO notification_preferences (user_id)
            SELECT user_id FROM users
        """)
        await db.commit()

async def get_notification_preferences(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM notification_preferences WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                # Create default if missing
                await db.execute("INSERT INTO notification_preferences (user_id) VALUES (?)", (user_id,))
                await db.commit()
                # Fetch again
                async with db.execute("SELECT * FROM notification_preferences WHERE user_id = ?", (user_id,)) as cursor2:
                    row = await cursor2.fetchone()
            return dict(row)

async def update_notification_preference(user_id: int, column: str, value):
    # Security check to prevent injection
    allowed_cols = [
        'daily_forecast', 'rain_alerts', 'temp_change_alerts', 
        'uv_alerts', 'air_quality_alerts', 'perfect_weather_alerts', 
        'severe_weather_alerts', 'last_rain_alert', 
        'last_temp_alert', 'last_uv_alert', 'last_air_quality_alert'
    ]
    if column not in allowed_cols:
        return
        
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(f"UPDATE notification_preferences SET {column} = ? WHERE user_id = ?", (value, user_id))
        await db.commit()

# --- Weather Snapshots for comparison (finer grain than history) ---
# We can reuse weather_history for daily trends, but for "yesterday this time" 
# we might need a separate table or just rely on daily avg?
# User requested "save_weather_snapshot". Let's create a table for hourly snapshots?
# Or just a simple table to store "last 24-48 hours" of snapshots?
# Let's create a 'weather_snapshots' table.

async def create_snapshots_table():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS weather_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                city_name TEXT,
                temp REAL,
                condition TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        # Cleanup old snapshots trigger/logic could be added, but manual cleanup is safer for now.
        await db.commit()

async def save_weather_snapshot(user_id, city, temp, condition):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO weather_snapshots (user_id, city_name, temp, condition, timestamp)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (user_id, city, temp, condition))
        # Cleanup old > 48h
        await db.execute("""
            DELETE FROM weather_snapshots 
            WHERE timestamp < datetime('now', '-48 hours')
        """)
        await db.commit()

async def get_weather_comparison(user_id, city):
    """
    Returns data to compare current (assumed just fetched) with ~24h ago.
    Actually returns the snapshot from ~24 hours ago.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Find snapshot closest to 24h ago
        # 24h ago is datetime('now', '-1 day')
        # We look for a record between 23h and 25h ago?
        # Or just the single closest record within reason.
        query = """
            SELECT * FROM weather_snapshots 
            WHERE user_id = ? AND city_name = ? 
            AND timestamp BETWEEN datetime('now', '-25 hours') AND datetime('now', '-23 hours')
            ORDER BY ABS(strftime('%s', timestamp) - strftime('%s', datetime('now', '-24 hours'))) ASC
            LIMIT 1
        """
        async with db.execute(query, (user_id, city)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_weekly_temperature_trend(user_id, city):
    # Uses weather_history
    return await get_weekly_stats(user_id, city)
