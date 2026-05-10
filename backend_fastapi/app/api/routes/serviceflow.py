from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.serviceflow import (
    AnalyzeResponse,
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
    get_latest_report,
    get_ticket_summary,
    run_ticket_analysis,
)
from app.services.ticket_service import (
    get_ticket_batch,
    list_ticket_items,
    upload_ticket_batch,
)


router = APIRouter()


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
    return upload_knowledge_document(db, document_name, document_type, file)


@router.get("/knowledge", response_model=list[KnowledgeDocumentResponse])
def get_knowledge_documents(db: Session = Depends(get_db)):
    return list_knowledge_documents(db)


@router.post("/tickets/upload", response_model=TicketBatchResponse)
def upload_tickets(
    batch_name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    batch = upload_ticket_batch(db, batch_name, file)
    return TicketBatchResponse(
        batch_id=batch.id,
        batch_name=batch.batch_name,
        file_name=batch.file_name,
        total_count=batch.total_count,
        status=batch.status,
    )


@router.post("/tickets/{batch_id}/analyze", response_model=AnalyzeResponse)
def analyze_tickets(batch_id: int, db: Session = Depends(get_db)):
    batch = get_ticket_batch(db, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Ticket batch not found.")

    result = run_ticket_analysis(db, batch_id)
    batch = get_ticket_batch(db, batch_id)
    return AnalyzeResponse(
        batch_id=batch_id,
        status=batch.status,
        analyzed_count=result.analyzed_count,
        failed_count=result.failed_count,
    )


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
