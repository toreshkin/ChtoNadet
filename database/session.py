from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config import DATABASE_PATH

# Handle different database types
if DATABASE_PATH.startswith("postgres"):
    # Fix Railway's "postgres://" -> "postgresql+asyncpg://"
    curr_url = DATABASE_PATH
    if curr_url.startswith("postgres://"):
        curr_url = curr_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif curr_url.startswith("postgresql://"):
        curr_url = curr_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif not curr_url.startswith("postgresql+asyncpg://"):
        # Just in case it's something else
        curr_url = curr_url.replace("://", "+asyncpg://", 1)
    DB_URL = curr_url
    
    # Log the connection (hiding password)
    import re
    masked_url = re.sub(r':([^/@]+)@', ':****@', DB_URL)
    print(f"🔌 Connecting to database: {masked_url}")
elif not DATABASE_PATH.startswith("sqlite"):
    DB_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"
else:
    DB_URL = DATABASE_PATH

engine = create_async_engine(DB_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
