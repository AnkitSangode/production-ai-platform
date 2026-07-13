from app.core.config import settings
from sqlalchemy import create_engine

engine = create_engine(settings.database_url)

with engine.connect() as connection:
    print("✅ Connected to PostgreSQL successfully!")