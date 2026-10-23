from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from backend.config import EMBEDDING_DIMENSIONS
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


class ProcedureChunk(Base):
    """A piece of a procedure's official source text, used as citable evidence."""

    __tablename__ = "procedure_chunks"
    __table_args__ = (UniqueConstraint("procedure_id", "chunk_index"),)

    id = Column(Integer, primary_key=True)
    procedure_id = Column(
        Integer,
        ForeignKey("procedures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIMENSIONS), nullable=False)
