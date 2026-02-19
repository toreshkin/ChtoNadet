from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config import DATABASE_PATH

# Handle different database types
if DATABASE_PATH.startswith("postgres"):
    # Convert postgres:// to postgresql+asyncpg:// for SQLAlchemy async support
    # Handle both common variants (postgres:// and postgresql://)
    DB_URL = DATABASE_PATH.replace("postgres://", "postgresql+asyncpg://", 1)
    if not DB_URL.startswith("postgresql+asyncpg://"):
         DB_URL = DB_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif not DATABASE_PATH.startswith("sqlite"):
    DB_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"
else:
    DB_URL = DATABASE_PATH

engine = create_async_engine(DB_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
