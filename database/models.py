from sqlalchemy import Column, String, Text, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class JobListing(Base):
    __tablename__ = 'job_listings'

    # Define columns
    job_id = Column(String, primary_key=True, index=True)
    job_link = Column(String, index=True)
    title = Column(String)
    company = Column(String)
    category = Column(String)
    description = Column(Text)
    locations = Column(JSON)  # For storing JSON arrays
    qualifications = Column(JSON)  # For storing JSON arrays
    responsibilities = Column(JSON)  # For storing JSON arrays
    miscellaneous = Column(Text)
