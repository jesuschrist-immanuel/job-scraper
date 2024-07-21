from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.secrets import DATABASE_URL

# Create an engine that connects to the database
engine = create_engine(DATABASE_URL, echo=True)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
