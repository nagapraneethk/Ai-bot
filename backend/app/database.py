from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

# Get database URL and convert to async driver
database_url = settings.database_url

# Support both PostgreSQL and SQLite
if database_url.startswith("sqlite"):
    # SQLite with aiosqlite for local testing
    if ":///" in database_url and "+aiosqlite" not in database_url:
        database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    engine = create_async_engine(database_url, echo=settings.debug)
elif database_url.startswith("postgres://") or database_url.startswith("postgresql://"):
    # PostgreSQL with asyncpg for production
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(database_url, echo=settings.debug)
else:
    raise ValueError(f"Unsupported database URL: {database_url}")

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
