from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class College(Base):
    """College model storing basic college info and scrape status."""
    
    __tablename__ = "colleges"
    
    id = Column(Integer, primary_key=True, index=True)
    college_name = Column(String(500), nullable=False)
    official_domain = Column(String(500), nullable=False, unique=True)
    scraped = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    pages = relationship("CollegePage", back_populates="college", cascade="all, delete-orphan")


class CollegePage(Base):
    """Scraped page content from college website."""
    
    __tablename__ = "college_pages"
    
    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    page_type = Column(String(100), nullable=False)  # about, admissions, fees, etc.
    content_text = Column(Text, nullable=False)
    source_url = Column(String(1000), nullable=False)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    
    college = relationship("College", back_populates="pages")
