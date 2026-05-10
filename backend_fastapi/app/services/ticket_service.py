from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.models.serviceflow import TicketBatch, TicketItem
from app.utils.file_parser import parse_ticket_file


def upload_ticket_batch(db: Session, batch_name: str, file: UploadFile) -> TicketBatch:
    settings = get_settings()
    upload_dir = Path(settings.upload_dir) / "tickets"
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{uuid4().hex}_{file.filename or 'tickets.csv'}"
    file_path = upload_dir / safe_name
    file_path.write_bytes(file.file.read())

    rows = parse_ticket_file(file_path)
    batch = TicketBatch(
        batch_name=batch_name,
        file_name=file.filename or safe_name,
        total_count=len(rows),
        status="uploaded",
    )
    db.add(batch)
    db.flush()

    for row in rows:
        db.add(
            TicketItem(
                batch_id=batch.id,
                ticket_id=row["ticket_id"],
                user_id=row["user_id"],
                content=row["content"],
                source=row["source"],
                submitted_at=row["submitted_at"],
            )
        )

    db.commit()
    db.refresh(batch)
    return batch


def get_ticket_batch(db: Session, batch_id: int) -> TicketBatch | None:
    return db.get(TicketBatch, batch_id)


def list_ticket_items(db: Session, batch_id: int) -> list[TicketItem]:
    statement = (
        select(TicketItem)
        .options(joinedload(TicketItem.analysis))
        .where(TicketItem.batch_id == batch_id)
        .order_by(TicketItem.id.asc())
    )
    return list(db.scalars(statement))

