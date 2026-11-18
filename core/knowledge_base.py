# =============================================================================
# core/knowledge_base.py — Project Knowledge Base
#
# LEARNING NOTE — Why Qdrant alongside PostgreSQL?
#
# PostgreSQL stores STRUCTURED data — rows, columns, exact values.
# Great for "give me all vulnerabilities with severity=critical".
#
# Qdrant stores VECTOR EMBEDDINGS — numerical representations of meaning.
# Great for "find conversations similar in meaning to this question"
# even if the exact words don't match.
#
# Example: User asks "what date bugs have we found?"
# A SQL query needs exact keyword matching. A vector search understands
# that "date bugs" relates to "future_date_bypass" even without exact
# keyword overlap, because they are semantically similar.
#
# This file wraps both databases behind simple functions so agent code
# never has to deal with SQL or vector math directly.
# =============================================================================

import json
import uuid
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import os
from dotenv import load_dotenv

from core.database import SessionLocal, DomainModel, Project, Conversation, Vulnerability

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

qdrant = QdrantClient(url=QDRANT_URL)

COLLECTION_NAME = "project_knowledge"
EMBEDDING_DIM = 384  # matches the embedding model used below


def ensure_collection_exists():
    """
    Creates the Qdrant collection if it doesn't already exist.
    Call this once at startup.
    """
    collections = [c.name for c in qdrant.get_collections().collections]
    if COLLECTION_NAME not in collections:
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        print(f"[Knowledge Base] Created Qdrant collection '{COLLECTION_NAME}'")


def get_embedding(text: str) -> list[float]:
    """
    Converts text into a vector embedding for semantic search.

    Uses a lightweight local embedding model (sentence-transformers)
    so this works completely free, no API calls needed.
    """
    from sentence_transformers import SentenceTransformer

    # Cached after first load — subsequent calls are fast
    if not hasattr(get_embedding, "_model"):
        get_embedding._model = SentenceTransformer("all-MiniLM-L6-v2")

    return get_embedding._model.encode(text).tolist()


# -----------------------------------------------------------------------------
# Domain model storage (PostgreSQL — structured data)
# -----------------------------------------------------------------------------

def save_domain_model(project_id: str, domain_model: dict) -> str:
    """
    Saves a new version of the domain model for a project.
    Each save creates a new version row — never overwrites history.

    Args:
        project_id: UUID of the project
        domain_model: dict with keys matching DomainModel columns
                       (domain, purpose, business_rules, input_schema,
                        output_schema, weak_points, tech_stack)

    Returns:
        The new domain_model record's id
    """
    db = SessionLocal()
    try:
        # Find current highest version for this project
        latest = (
            db.query(DomainModel)
            .filter(DomainModel.project_id == project_id)
            .order_by(DomainModel.version.desc())
            .first()
        )
        next_version = (latest.version + 1) if latest else 1

        new_model = DomainModel(
            project_id=project_id,
            domain=domain_model.get("domain", ""),
            purpose=domain_model.get("purpose", ""),
            business_rules=domain_model.get("business_rules", []),
            input_schema=domain_model.get("input_schema", {}),
            output_schema=domain_model.get("output_schema", {}),
            weak_points=domain_model.get("weak_points", []),
            tech_stack=domain_model.get("tech_stack", {}),
            version=next_version,
        )
        db.add(new_model)
        db.commit()
        db.refresh(new_model)

        # Also index into Qdrant for semantic search later
        _index_domain_model(project_id, new_model.id, domain_model)

        print(f"[Knowledge Base] Saved domain model v{next_version} for project {project_id}")
        return new_model.id
    finally:
        db.close()


def get_latest_domain_model(project_id: str) -> dict | None:
    """
    Returns the most recent domain model for a project, or None if
    this project has never been analysed.
    """
    db = SessionLocal()
    try:
        latest = (
            db.query(DomainModel)
            .filter(DomainModel.project_id == project_id)
            .order_by(DomainModel.version.desc())
            .first()
        )
        if not latest:
            return None

        return {
            "domain": latest.domain,
            "purpose": latest.purpose,
            "business_rules": latest.business_rules,
            "input_schema": latest.input_schema,
            "output_schema": latest.output_schema,
            "weak_points": latest.weak_points,
            "tech_stack": latest.tech_stack,
            "version": latest.version,
        }
    finally:
        db.close()


# -----------------------------------------------------------------------------
# Semantic indexing (Qdrant — vector data)
# -----------------------------------------------------------------------------

def _index_domain_model(project_id: str, domain_model_id: str, domain_model: dict):
    """
    Internal — indexes a domain model into Qdrant so it can be
    semantically searched later (e.g. "what rules did we find about dates?")
    """
    text_repr = json.dumps(domain_model)
    vector = get_embedding(text_repr)

    qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "project_id": project_id,
                    "type": "domain_model",
                    "domain_model_id": domain_model_id,
                    "content": text_repr,
                    "created_at": datetime.utcnow().isoformat(),
                },
            )
        ],
    )


def index_conversation(project_id: str, org_id: str, user_id: str, role: str, content: str):
    """
    Saves a conversation message to both PostgreSQL (structured log)
    and Qdrant (semantic search).
    """
    db = SessionLocal()
    try:
        msg = Conversation(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            role=role,
            content=content,
        )
        db.add(msg)
        db.commit()
    finally:
        db.close()

    vector = get_embedding(content)
    qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "project_id": project_id,
                    "type": "conversation",
                    "role": role,
                    "content": content,
                    "created_at": datetime.utcnow().isoformat(),
                },
            )
        ],
    )


def semantic_search(project_id: str, query: str, limit: int = 5) -> list[dict]:
    """
    Searches across a project's full knowledge base (domain models,
    conversations, vulnerabilities) using semantic similarity.

    Usage:
        results = semantic_search(project_id, "what date validation bugs have we found?")

    Returns:
        List of matching items sorted by relevance, with their content
        and metadata.
    """
    vector = get_embedding(query)

    results = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=vector,
        query_filter={
            "must": [{"key": "project_id", "match": {"value": project_id}}]
        },
        limit=limit,
    )

    return [
        {
            "type": r.payload.get("type"),
            "content": r.payload.get("content"),
            "score": r.score,
            "created_at": r.payload.get("created_at"),
        }
        for r in results
    ]


# -----------------------------------------------------------------------------
# Conversation history retrieval (for PM agent context)
# -----------------------------------------------------------------------------

def get_conversation_history(project_id: str, limit: int = 50) -> list[dict]:
    """
    Returns recent conversation history for a project, oldest first.
    Used to give the PM agent context about past interactions.
    """
    db = SessionLocal()
    try:
        messages = (
            db.query(Conversation)
            .filter(Conversation.project_id == project_id)
            .order_by(Conversation.created_at.desc())
            .limit(limit)
            .all()
        )
        # Reverse to get chronological order
        messages = list(reversed(messages))
        return [{"role": m.role, "content": m.content} for m in messages]
    finally:
        db.close()
