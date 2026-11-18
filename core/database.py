# =============================================================================
# core/database.py — Database Models and Connection
#
# LEARNING NOTE — SQLAlchemy ORM
#
# Instead of writing raw SQL, we define Python classes that represent
# database tables. SQLAlchemy translates these into actual SQL behind
# the scenes. This is called an ORM (Object-Relational Mapper).
#
# Each class below = one table. Each class attribute = one column.
# =============================================================================

import os
import uuid
from datetime import datetime
from dotenv import load_dotenv

from sqlalchemy import create_engine, Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://shadowops:shadowops_dev_password@localhost:5432/shadowops")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())


# -----------------------------------------------------------------------------
# Organisations
# -----------------------------------------------------------------------------

class Organisation(Base):
    __tablename__ = "organisations"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    plan = Column(String, default="free")
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="organisation")
    projects = relationship("Project", back_populates="organisation")


# -----------------------------------------------------------------------------
# Users
# -----------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False)
    name = Column(String)
    hashed_password = Column(String, nullable=False)
    org_id = Column(UUID(as_uuid=False), ForeignKey("organisations.id"))
    role = Column(String, default="engineer")  # admin | engineer | viewer
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)

    organisation = relationship("Organisation", back_populates="users")


# -----------------------------------------------------------------------------
# Projects
# -----------------------------------------------------------------------------

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    org_id = Column(UUID(as_uuid=False), ForeignKey("organisations.id"))
    name = Column(String, nullable=False)
    repo_url = Column(String)
    branch = Column(String, default="main")
    stack = Column(String)
    domain = Column(String)
    status = Column(String, default="active")  # active | archived
    last_synced = Column(DateTime)
    created_by = Column(UUID(as_uuid=False), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    organisation = relationship("Organisation", back_populates="projects")
    domain_models = relationship("DomainModel", back_populates="project")
    test_runs = relationship("TestRun", back_populates="project")


# -----------------------------------------------------------------------------
# Domain models — one per project, versioned
# -----------------------------------------------------------------------------

class DomainModel(Base):
    __tablename__ = "domain_models"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"))
    domain = Column(String)
    purpose = Column(Text)
    business_rules = Column(JSON, default=list)
    input_schema = Column(JSON, default=dict)
    output_schema = Column(JSON, default=dict)
    weak_points = Column(JSON, default=list)
    tech_stack = Column(JSON, default=dict)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="domain_models")


# -----------------------------------------------------------------------------
# Test runs
# -----------------------------------------------------------------------------

class TestRun(Base):
    __tablename__ = "test_runs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"))
    triggered_by = Column(UUID(as_uuid=False), ForeignKey("users.id"))
    trigger_type = Column(String, default="manual")  # manual | scheduled | cicd
    status = Column(String, default="running")  # running | complete | failed
    attacks_launched = Column(Integer, default=0)
    resiliency_score = Column(Integer)
    total_cost = Column(Float, default=0.0)
    duration_ms = Column(Integer)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    project = relationship("Project", back_populates="test_runs")
    attacks = relationship("Attack", back_populates="run")
    vulnerabilities = relationship("Vulnerability", back_populates="run")


# -----------------------------------------------------------------------------
# Individual attacks
# -----------------------------------------------------------------------------

class Attack(Base):
    __tablename__ = "attacks"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    run_id = Column(UUID(as_uuid=False), ForeignKey("test_runs.id"))
    attack_category = Column(String)
    chaos_input = Column(Text)
    agent_response = Column(Text)
    passed = Column(Boolean)
    violated_rule = Column(String)
    response_time_ms = Column(Integer)
    cost_estimate = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("TestRun", back_populates="attacks")


# -----------------------------------------------------------------------------
# Vulnerabilities
# -----------------------------------------------------------------------------

class Vulnerability(Base):
    __tablename__ = "vulnerabilities"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"))
    run_id = Column(UUID(as_uuid=False), ForeignKey("test_runs.id"))
    attack_id = Column(UUID(as_uuid=False), ForeignKey("attacks.id"))
    bug_type = Column(String)
    severity = Column(String)  # low | medium | critical
    root_cause = Column(Text)
    affected_function = Column(String)
    affected_field = Column(String)
    status = Column(String, default="found")
    assigned_to = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    run = relationship("TestRun", back_populates="vulnerabilities")
    patch = relationship("Patch", back_populates="vulnerability", uselist=False)


# -----------------------------------------------------------------------------
# Patches
# -----------------------------------------------------------------------------

class Patch(Base):
    __tablename__ = "patches"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    vulnerability_id = Column(UUID(as_uuid=False), ForeignKey("vulnerabilities.id"))
    original_code = Column(Text)
    patched_code = Column(Text)
    patch_reason = Column(Text)
    confidence = Column(String)  # high | medium | low
    side_effects = Column(Text)
    status = Column(String, default="pending")  # pending | approved | rejected
    reviewed_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    vulnerability = relationship("Vulnerability", back_populates="patch")


# -----------------------------------------------------------------------------
# Agent usage — for cost tracking
# -----------------------------------------------------------------------------

class AgentUsage(Base):
    __tablename__ = "agent_usage"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    org_id = Column(UUID(as_uuid=False), ForeignKey("organisations.id"))
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=True)
    run_id = Column(UUID(as_uuid=False), ForeignKey("test_runs.id"), nullable=True)
    agent_name = Column(String)
    model_used = Column(String)
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    duration_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


# -----------------------------------------------------------------------------
# Environment variables (encrypted)
# -----------------------------------------------------------------------------

class EnvVar(Base):
    __tablename__ = "env_vars"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"))
    key_name = Column(String)
    encrypted_value = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# -----------------------------------------------------------------------------
# Conversations — PM agent chat history
# -----------------------------------------------------------------------------

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=True)
    org_id = Column(UUID(as_uuid=False), ForeignKey("organisations.id"))
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"))
    role = Column(String)  # user | assistant
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------

def get_db():
    """
    FastAPI dependency — provides a database session per request.

    Usage in API routes:
        from fastapi import Depends
        from core.database import get_db

        @app.get("/projects")
        def list_projects(db: Session = Depends(get_db)):
            return db.query(Project).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Creates all tables in the database based on the models above.
    Run this once when setting up the project for the first time.

    Usage: python -c "from core.database import init_db; init_db()"
    """
    Base.metadata.create_all(bind=engine)
    print("[Database] All tables created successfully.")


if __name__ == "__main__":
    init_db()
