from collections import Counter
from dataclasses import dataclass

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.serviceflow import TicketAnalysis, TicketBatch, TicketItem, TicketReport
from app.schemas.serviceflow import TicketAnalysisResult
from app.services.ai_client import chat_completion
from app.services.vector_service import search_rule_chunks


@dataclass
class AnalysisRunResult:
    analyzed_count: int
    failed_count: int = 0


def run_ticket_analysis(db: Session, batch_id: int) -> AnalysisRunResult:
    batch = db.get(TicketBatch, batch_id)
    if not batch:
        raise ValueError("Ticket batch not found.")

    batch.status = "processing"
    db.commit()

    tickets = list(
        db.scalars(
            select(TicketItem)
            .options(joinedload(TicketItem.analysis))
            .where(TicketItem.batch_id == batch_id)
            .order_by(TicketItem.id.asc())
        )
    )

    failed_count = 0
    for ticket in tickets:
        result = analyze_single_ticket(ticket.content)
        if not result.parse_success:
            failed_count += 1
        save_ticket_analysis(db, ticket, result)

    batch.status = "completed"
    db.commit()
    return AnalysisRunResult(analyzed_count=len(tickets), failed_count=failed_count)


def analyze_single_ticket(content: str) -> TicketAnalysisResult:
    matched_rules = search_rule_chunks(content)
    prompt = build_analysis_prompt(content, matched_rules)
    ai_text = chat_completion(prompt)
    json_text = extract_json_text(ai_text)

    try:
        result = TicketAnalysisResult.model_validate_json(json_text)
        result.parse_success = True
    except ValidationError as error:
        result = TicketAnalysisResult(
            ticket_type="其他",
            severity="中",
            responsible_team="客服团队",
            summary=f"模型输出解析失败，需人工复核：{content[:80]}",
            suggestion="建议客服查看 Agent Trace 中的模型原始输出后人工处理。",
            reply_template="您好，我们已收到您的问题，客服会尽快核实后回复您。",
            parse_success=False,
            parse_error=str(error),
        )

    result.matched_rules = matched_rules
    result.raw_ai_result = ai_text
    return result


def save_ticket_analysis(
    db: Session,
    ticket: TicketItem,
    result: TicketAnalysisResult,
) -> None:
    if ticket.analysis:
        analysis = ticket.analysis
    else:
        analysis = TicketAnalysis(ticket_item_id=ticket.id)
        db.add(analysis)

    analysis.ticket_type = result.ticket_type
    analysis.severity = result.severity
    analysis.responsible_team = result.responsible_team
    analysis.summary = result.summary
    analysis.suggestion = result.suggestion
    analysis.reply_template = result.reply_template
    analysis.matched_rules = "\n---\n".join(result.matched_rules)
    analysis.raw_ai_result = result.raw_ai_result
    analysis.parse_success = result.parse_success
    analysis.parse_error = result.parse_error


def build_analysis_prompt(content: str, matched_rules: list[str]) -> str:
    rule_text = "\n\n".join(matched_rules) if matched_rules else "暂无匹配规则。"

    return f"""
请根据售后规则和用户工单内容，分析这条工单。

售后规则：
{rule_text}

用户工单：
{content}

只能从以下范围选择：
- ticket_type: 支付/到账异常、退款售后、账号登录问题、功能使用问题、发票问题、服务投诉、技术故障、其他
- severity: 高、中、低
- responsible_team: 客服团队、技术团队、财务团队、售后团队、运营团队，或者多个团队组合

请只返回 JSON，不要返回 Markdown，不要解释。

JSON 格式如下：
{{
  "ticket_type": "支付/到账异常",
  "severity": "高",
  "responsible_team": "技术团队 / 客服团队",
  "summary": "用户反馈付款后会员未到账",
  "suggestion": "建议先核查支付记录，再检查会员状态同步",
  "reply_template": "您好，我们已收到您的问题，会优先为您核查付款记录和会员状态，请您稍等。"
}}
""".strip()


def extract_json_text(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return text
    return text[start : end + 1]


def get_ticket_summary(db: Session, batch_id: int) -> dict:
    analyses = list(
        db.scalars(
            select(TicketAnalysis)
            .join(TicketItem)
            .where(TicketItem.batch_id == batch_id)
            .order_by(TicketAnalysis.id.asc())
        )
    )

    type_counter = Counter(item.ticket_type for item in analyses)
    severity_counter = Counter(item.severity for item in analyses)
    team_counter = Counter(item.responsible_team for item in analyses)

    return {
        "total_count": len(analyses),
        "high_severity_count": severity_counter.get("高", 0),
        "top_ticket_type": top_name(type_counter),
        "top_responsible_team": top_name(team_counter),
        "type_stats": dict(type_counter),
        "severity_stats": dict(severity_counter),
        "team_stats": dict(team_counter),
    }


def generate_ticket_report(db: Session, batch_id: int) -> TicketReport:
    batch = db.get(TicketBatch, batch_id)
    if not batch:
        raise ValueError("Ticket batch not found.")

    summary = get_ticket_summary(db, batch_id)
    high_tickets = list(
        db.scalars(
            select(TicketItem)
            .join(TicketAnalysis)
            .where(TicketItem.batch_id == batch_id, TicketAnalysis.severity == "高")
            .limit(5)
        )
    )

    report = TicketReport(
        batch_id=batch_id,
        title=f"{batch.batch_name}客服工单分析日报",
        content=build_report_markdown(summary, high_tickets),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_latest_report(db: Session, batch_id: int) -> TicketReport | None:
    return db.scalar(
        select(TicketReport)
        .where(TicketReport.batch_id == batch_id)
        .order_by(TicketReport.created_at.desc())
    )


def build_report_markdown(summary: dict, high_tickets: list[TicketItem]) -> str:
    high_lines = "\n".join(
        f"- {ticket.ticket_id}: {ticket.content}" for ticket in high_tickets
    )
    if not high_lines:
        high_lines = "- 暂无高优先级工单。"

    return f"""## 一、本批工单概况

本批共分析 {summary["total_count"]} 条工单，高优先级工单 {summary["high_severity_count"]} 条。

## 二、高频问题类型

最多的问题类型是：{summary["top_ticket_type"]}。

## 三、高优先级工单

{high_lines}

## 四、责任部门分布

主要责任部门是：{summary["top_responsible_team"]}。

## 五、典型问题

建议客服优先关注高优先级工单，并对重复问题沉淀标准回复模板。

## 六、处理建议

客服团队可先使用系统生成的回复模板安抚用户，再根据责任部门完成转派和跟进。
"""


def top_name(counter: Counter[str]) -> str:
    if not counter:
        return "暂无"
    return counter.most_common(1)[0][0]

