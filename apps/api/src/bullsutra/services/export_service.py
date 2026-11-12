import io
import csv
import json
import uuid
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from jinja2 import Environment, FileSystemLoader

from bullsutra.core.constants import DISCLAIMER_TEXT
from bullsutra.core.errors import NotFound, BriefNotFound
from bullsutra.db.repositories import briefs, backtests

TEMPLATE_DIR = Path(__file__).parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

async def export_brief_json(db: AsyncSession, brief_id: uuid.UUID) -> Tuple[Dict[str, Any], str]:
    rec = await briefs.get_brief_by_id(db, brief_id)
    if not rec:
        raise BriefNotFound(f"Brief '{brief_id}' not found")
    
    brief_data = rec.brief
    symbol = brief_data.get("symbol", "UNKNOWN")
    as_of = brief_data.get("as_of", str(rec.as_of))
    filename = f"bullsutra_{symbol}_{as_of}.json"
    return brief_data, filename

async def export_brief_csv(db: AsyncSession, brief_id: uuid.UUID) -> Tuple[str, str]:
    rec = await briefs.get_brief_by_id(db, brief_id)
    if not rec:
        raise BriefNotFound(f"Brief '{brief_id}' not found")

    b = rec.brief
    symbol = b.get("symbol", "")
    as_of = b.get("as_of", str(rec.as_of))
    signal = b.get("signal", {})
    label = signal.get("label", rec.label or "")
    consensus_score = signal.get("score", rec.consensus_score or 0.0)
    confidence = signal.get("confidence", rec.confidence or 0.0)

    agents = b.get("agents", {})
    agent_order = ["news", "fundamentals", "technicals", "risk"]

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    writer.writerow([
        "symbol", "as_of", "label", "consensus_score", "confidence",
        "agent", "agent_score", "agent_confidence", "top_driver", "top_risk"
    ])

    for agent_name in agent_order:
        sig = agents.get(agent_name, {})
        agent_score = sig.get("score", 0.0)
        agent_conf = sig.get("confidence", 0.0)
        drivers = sig.get("drivers", [])
        top_driver = drivers[0].get("note", "") if drivers else ""
        risks = sig.get("risks", [])
        top_risk = risks[0] if risks else ""

        writer.writerow([
            symbol, as_of, label, consensus_score, confidence,
            agent_name, agent_score, agent_conf, top_driver, top_risk
        ])

    filename = f"bullsutra_{symbol}_{as_of}.csv"
    return output.getvalue(), filename

async def export_brief_pdf(db: AsyncSession, brief_id: uuid.UUID) -> Tuple[bytes, str]:
    rec = await briefs.get_brief_by_id(db, brief_id)
    if not rec:
        raise BriefNotFound(f"Brief '{brief_id}' not found")

    brief_data = rec.brief
    symbol = brief_data.get("symbol", "UNKNOWN")
    as_of = brief_data.get("as_of", str(rec.as_of))
    filename = f"bullsutra_{symbol}_{as_of}.pdf"

    # Attempt WeasyPrint first
    try:
        import weasyprint
        template = jinja_env.get_template("brief.html.j2")
        html_out = template.render(brief=brief_data, disclaimer=DISCLAIMER_TEXT)
        pdf_bytes = weasyprint.HTML(string=html_out).write_pdf()
        return pdf_bytes, filename
    except Exception:
        # Fallback to reportlab
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        styles = getSampleStyleSheet()
        normal = styles["Normal"]
        title_style = ParagraphStyle(
            "TitleStyle",
            parent=normal,
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#111827")
        )
        h2_style = ParagraphStyle(
            "H2Style",
            parent=normal,
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#111827"),
            spaceBefore=10,
            spaceAfter=4
        )
        body_style = ParagraphStyle(
            "BodyStyle",
            parent=normal,
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#374151")
        )
        footer_style = ParagraphStyle(
            "FooterStyle",
            parent=normal,
            fontName="Helvetica-Oblique",
            fontSize=6,
            leading=8,
            textColor=colors.HexColor("#6b7280")
        )

        elements = []
        # Header
        elements.append(Paragraph(f"BullSutra &mdash; {symbol} ({brief_data.get('company_name', '')})", title_style))
        elements.append(Paragraph(f"Sector: {brief_data.get('sector', '')} | As of: {as_of} | Brief ID: {brief_id}", body_style))
        elements.append(Spacer(1, 10))

        # Signal badge
        signal = brief_data.get("signal", {})
        label = signal.get("label", "HOLD")
        conf = signal.get("confidence", 0.0)
        badge_text = f"<b>SIGNAL: {label}</b> (Confidence: {conf*100:.1f}%)"
        elements.append(Paragraph(badge_text, ParagraphStyle("Badge", parent=title_style, fontSize=14, leading=16)))
        elements.append(Spacer(1, 10))

        # Summary
        if brief_data.get("summary"):
            elements.append(Paragraph(f"<i>{brief_data['summary']}</i>", body_style))
            elements.append(Spacer(1, 8))

        # Agents table
        elements.append(Paragraph("Specialist Agents", h2_style))
        agents = brief_data.get("agents", {})
        table_data = [["Agent", "Score", "Confidence", "Key Drivers"]]
        for ag in ["news", "fundamentals", "technicals", "risk"]:
            sig = agents.get(ag, {})
            score = f"{sig.get('score', 0.0):.2f}"
            c = f"{sig.get('confidence', 0.0)*100:.1f}%"
            d_notes = [d.get("note", "") for d in sig.get("drivers", [])[:2]]
            table_data.append([ag.capitalize(), score, c, "\n".join(d_notes)])

        t = Table(table_data, colWidths=[80, 50, 65, 320])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f3f4f6")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#111827")),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 10))

        # Drivers
        if brief_data.get("drivers"):
            elements.append(Paragraph("Key Drivers", h2_style))
            for d in brief_data["drivers"][:5]:
                elements.append(Paragraph(f"&bull; <b>[{d.get('kind', '').capitalize()}]</b> {d.get('note', '')}", body_style))
            elements.append(Spacer(1, 6))

        # Risks
        if brief_data.get("risks"):
            elements.append(Paragraph("Risks", h2_style))
            for r in brief_data["risks"]:
                elements.append(Paragraph(f"&bull; {r}", body_style))
            elements.append(Spacer(1, 6))

        # Footer
        elements.append(Spacer(1, 14))
        elements.append(Paragraph(DISCLAIMER_TEXT, footer_style))

        doc.build(elements)
        return buffer.getvalue(), filename

async def export_backtest_trades_csv(db: AsyncSession, backtest_id: uuid.UUID, strategy: str = "full") -> Tuple[str, str]:
    trades = await backtests.get_trades(db, backtest_id, strategy_key=strategy)
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([
        "symbol", "entry_date", "exit_date", "entry_price", "exit_price",
        "shares", "gross_pnl", "costs", "tax", "net_pnl", "return_pct",
        "holding_days", "exit_reason"
    ])
    for t in trades:
        writer.writerow([
            t.symbol, t.entry_date, t.exit_date, t.entry_price, t.exit_price,
            t.shares, t.gross_pnl, t.costs, t.tax, t.net_pnl, t.return_pct,
            t.holding_days, t.exit_reason
        ])
    filename = f"backtest_{backtest_id}_trades_{strategy}.csv"
    return output.getvalue(), filename

async def export_backtest_equity_csv(db: AsyncSession, backtest_id: uuid.UUID) -> Tuple[str, str]:
    equity_rows = await backtests.get_equity_all_strategies(db, backtest_id)
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["date", "strategy_key", "equity", "drawdown"])
    for eq in equity_rows:
        writer.writerow([eq.trade_date, eq.strategy_key, eq.equity, eq.drawdown])
    filename = f"backtest_{backtest_id}_equity.csv"
    return output.getvalue(), filename
