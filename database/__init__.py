from .db import engine, SessionLocal
from .models import Base

# Create all tables in the database (useful during development)
def init_db():
    Base.metadata.create_all(bind=engine)
