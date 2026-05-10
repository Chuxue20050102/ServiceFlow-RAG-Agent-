from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.serviceflow import KnowledgeChunk, KnowledgeDocument
from app.services.vector_service import add_rule_chunks_to_vector_store
from app.utils.file_parser import parse_knowledge_file, split_text


def upload_knowledge_document(
    db: Session,
    document_name: str,
    document_type: str,
    file: UploadFile,
) -> KnowledgeDocument:
    settings = get_settings()
    upload_dir = Path(settings.upload_dir) / "knowledge"
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{uuid4().hex}_{file.filename or 'document.txt'}"
    file_path = upload_dir / safe_name
    file_path.write_bytes(file.file.read())

    document = KnowledgeDocument(
        document_name=document_name,
        document_type=document_type,
        file_name=file.filename or safe_name,
        file_path=str(file_path),
        status="processing",
    )
    db.add(document)
    db.flush()

    text = parse_knowledge_file(file_path)
    chunks = split_text(text)
    chunk_models: list[KnowledgeChunk] = []
    for index, chunk in enumerate(chunks):
        chunk_model = KnowledgeChunk(
            document_id=document.id,
            chunk_index=index,
            content=chunk,
        )
        db.add(chunk_model)
        chunk_models.append(chunk_model)

    document.chunk_count = len(chunks)
    document.status = "vectorized"
    db.flush()
    add_rule_chunks_to_vector_store(chunk_models)
    db.commit()
    db.refresh(document)

    return document


def list_knowledge_documents(db: Session) -> list[KnowledgeDocument]:
    return list(
        db.scalars(
            select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc())
        )
    )
