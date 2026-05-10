from datetime import datetime

from pydantic import BaseModel


class KnowledgeDocumentResponse(BaseModel):
    id: int
    document_name: str
    document_type: str
    file_name: str
    chunk_count: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TicketBatchResponse(BaseModel):
    batch_id: int
    batch_name: str
    file_name: str
    total_count: int
    status: str


class AnalyzeResponse(BaseModel):
    batch_id: int
    status: str
    analyzed_count: int
    failed_count: int


class TicketAnalysisResult(BaseModel):
    ticket_type: str
    severity: str
    responsible_team: str
    summary: str
    suggestion: str
    reply_template: str
    matched_rules: list[str] = []
    raw_ai_result: str | None = None
    parse_success: bool = True
    parse_error: str | None = None


class TicketItemResponse(BaseModel):
    id: int
    ticket_id: str
    user_id: str
    content: str
    source: str | None
    ticket_type: str | None
    severity: str | None
    responsible_team: str | None
    summary: str | None
    suggestion: str | None
    reply_template: str | None
    matched_rules: list[str]
    raw_ai_result: str | None = None
    parse_success: bool | None = None
    parse_error: str | None = None


class KeywordStat(BaseModel):
    name: str
    value: int


class TicketSummaryResponse(BaseModel):
    total_count: int
    high_severity_count: int
    top_ticket_type: str
    top_responsible_team: str
    type_stats: dict[str, int]
    severity_stats: dict[str, int]
    team_stats: dict[str, int]


class TicketReportResponse(BaseModel):
    report_id: int
    title: str
    content: str
