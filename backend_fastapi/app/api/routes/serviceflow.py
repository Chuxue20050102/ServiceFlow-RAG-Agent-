from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.database.session import SessionLocal, get_db
from app.models.serviceflow import TicketBatch
from app.schemas.serviceflow import (
    AnalyzeResponse,
    KnowledgeSearchResponse,
    KnowledgeDocumentResponse,
    TicketBatchResponse,
    TicketItemResponse,
    TicketReportResponse,
    TicketSummaryResponse,
)
from app.services.knowledge_service import (
    list_knowledge_documents,
    upload_knowledge_document,
)
from app.services.rag_service import (
    generate_ticket_report,
    get_analysis_status,
    get_latest_report,
    get_ticket_summary,
    run_ticket_analysis,
)
from app.services.ticket_service import (
    get_ticket_batch,
    list_ticket_items,
    upload_ticket_batch,
)
from app.services.vector_service import search_rule_chunks


router = APIRouter()

MAX_UPLOAD_SIZE = 10 * 1024 * 1024
KNOWLEDGE_EXTENSIONS = {".txt", ".md"}
TICKET_EXTENSIONS = {".csv", ".xls", ".xlsx"}


def validate_upload_file(file: UploadFile, allowed_extensions: set[str]) -> None:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {allowed}")
    if file.size is not None and file.size > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File is too large. Max size is 10 MB.")


@router.get("/ping")
def ping() -> dict[str, str]:
    return {"message": "serviceflow api is ready"}


@router.post("/knowledge/upload", response_model=KnowledgeDocumentResponse)
def upload_knowledge(
    document_name: str = Form(...),
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    validate_upload_file(file, KNOWLEDGE_EXTENSIONS)
    try:
        return upload_knowledge_document(db, document_name, document_type, file)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/knowledge", response_model=list[KnowledgeDocumentResponse])
def get_knowledge_documents(db: Session = Depends(get_db)):
    return list_knowledge_documents(db)


@router.get("/knowledge/search", response_model=KnowledgeSearchResponse)
def search_knowledge(query: str = Query(..., min_length=2, max_length=500)):
    return KnowledgeSearchResponse(query=query, matches=search_rule_chunks(query))


@router.post("/tickets/upload", response_model=TicketBatchResponse)
def upload_tickets(
    batch_name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    validate_upload_file(file, TICKET_EXTENSIONS)
    try:
        batch = upload_ticket_batch(db, batch_name, file)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return TicketBatchResponse(
        batch_id=batch.id,
        batch_name=batch.batch_name,
        file_name=batch.file_name,
        total_count=batch.total_count,
        status=batch.status,
    )


@router.post("/tickets/{batch_id}/analyze", response_model=AnalyzeResponse)
def analyze_tickets(
    batch_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    batch = get_ticket_batch(db, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Ticket batch not found.")

    if batch.status == "processing":
        result = get_analysis_status(db, batch_id)
        return AnalyzeResponse(
            batch_id=batch_id,
            status=batch.status,
            analyzed_count=result.analyzed_count,
            failed_count=result.failed_count,
            total_count=result.total_count,
            progress_percent=result.progress_percent,
        )

    batch.status = "processing"
    db.commit()
    background_tasks.add_task(run_ticket_analysis_background, batch_id)

    return AnalyzeResponse(
        batch_id=batch_id,
        status=batch.status,
        analyzed_count=0,
        failed_count=0,
        total_count=batch.total_count,
        progress_percent=0,
    )


@router.get("/tickets/{batch_id}/analyze/status", response_model=AnalyzeResponse)
def get_analyze_status(batch_id: int, db: Session = Depends(get_db)):
    batch = get_ticket_batch(db, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Ticket batch not found.")

    result = get_analysis_status(db, batch_id)
    return AnalyzeResponse(
        batch_id=batch_id,
        status=batch.status,
        analyzed_count=result.analyzed_count,
        failed_count=result.failed_count,
        total_count=result.total_count,
        progress_percent=result.progress_percent,
    )


def run_ticket_analysis_background(batch_id: int) -> None:
    db = SessionLocal()
    try:
        run_ticket_analysis(db, batch_id)
    except Exception:
        batch = db.get(TicketBatch, batch_id)
        if batch:
            batch.status = "failed"
            db.commit()
        raise
    finally:
        db.close()


@router.get("/tickets/{batch_id}/summary", response_model=TicketSummaryResponse)
def get_summary(batch_id: int, db: Session = Depends(get_db)):
    if not get_ticket_batch(db, batch_id):
        raise HTTPException(status_code=404, detail="Ticket batch not found.")
    return get_ticket_summary(db, batch_id)


@router.get("/tickets/{batch_id}/items", response_model=list[TicketItemResponse])
def get_items(batch_id: int, db: Session = Depends(get_db)):
    if not get_ticket_batch(db, batch_id):
        raise HTTPException(status_code=404, detail="Ticket batch not found.")

    items = []
    for ticket in list_ticket_items(db, batch_id):
        analysis = ticket.analysis
        items.append(
            TicketItemResponse(
                id=ticket.id,
                ticket_id=ticket.ticket_id,
                user_id=ticket.user_id,
                content=ticket.content,
                source=ticket.source,
                ticket_type=analysis.ticket_type if analysis else None,
                severity=analysis.severity if analysis else None,
                responsible_team=analysis.responsible_team if analysis else None,
                summary=analysis.summary if analysis else None,
                suggestion=analysis.suggestion if analysis else None,
                reply_template=analysis.reply_template if analysis else None,
                matched_rules=analysis.matched_rules.split("\n---\n")
                if analysis and analysis.matched_rules
                else [],
                raw_ai_result=analysis.raw_ai_result if analysis else None,
                parse_success=analysis.parse_success if analysis else None,
                parse_error=analysis.parse_error if analysis else None,
            )
        )
    return items


@router.post("/tickets/{batch_id}/report", response_model=TicketReportResponse)
def create_report(batch_id: int, db: Session = Depends(get_db)):
    if not get_ticket_batch(db, batch_id):
        raise HTTPException(status_code=404, detail="Ticket batch not found.")

    report = generate_ticket_report(db, batch_id)
    return TicketReportResponse(
        report_id=report.id,
        title=report.title,
        content=report.content,
    )


@router.get("/tickets/{batch_id}/report", response_model=TicketReportResponse)
def get_report(batch_id: int, db: Session = Depends(get_db)):
    report = get_latest_report(db, batch_id)
    if not report:
        raise HTTPException(status_code=404, detail="Ticket report not found.")
    return TicketReportResponse(
        report_id=report.id,
        title=report.title,
        content=report.content,
    )
