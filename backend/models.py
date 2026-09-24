from sqlalchemy import Column, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB

from backend.database import Base


class Procedure(Base):
    __tablename__ = "procedures"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    department = Column(Text, nullable=True)
    jurisdiction = Column(Text, nullable=True)
    summary = Column(Text, nullable=False)
    source_url = Column(Text, nullable=False, unique=True)
    source_text = Column(Text, nullable=False)
    structured_data = Column(JSONB, nullable=False)
