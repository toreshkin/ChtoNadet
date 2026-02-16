from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config import DATABASE_PATH

# If DATABASE_PATH doesn't start with sqlite+aiosqlite://, we should add it if it's a file
if not DATABASE_PATH.startswith("sqlite") and not DATABASE_PATH.startswith("postgresql"):
    DB_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"
else:
    DB_URL = DATABASE_PATH

engine = create_async_engine(DB_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
