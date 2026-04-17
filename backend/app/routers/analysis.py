"""
Analysis Router for SupplyChainIQ
Handles supply chain risk analysis endpoints and file uploads.
"""

import ast
import json
import uuid
import io
import logging
import pandas as pd
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..database import get_db, SessionDB, MessageDB, AnalysisResultDB, UserDB
from ..dependencies import get_current_user
from ..models import (
    SupplyChainInput,
    FollowUpInput,
    RiskAnalysisResponse,
    FollowUpResponse,
    RiskNode,
    RiskLevel,
    RiskCategory,
    LLMMetadata,
    ScenarioInput,
    ScenarioResult,
    ScenarioSnapshot,
    ScenarioAffectedNode,
    ScenarioTradeoffs,
    ScenarioVerdict,
    ScenarioType,
)
from ..services import rag_service, llm_service

logger = logging.getLogger("supplychainiq.analysis")

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])

# Allowed upload extensions — anything else is rejected with 415
_ALLOWED_UPLOAD_EXTS = {".csv", ".xlsx", ".xls", ".txt", ".pdf"}


def _normalize_assistant_content(raw: str) -> Optional[Dict[str, Any]]:
    """
    Try to recover a structured analysis/followup dict from a stored
    assistant message. Handles both new (json.dumps) and legacy
    (str(dict) — Python repr) formats. Returns None if neither works.
    """
    if not raw or not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text or text[0] not in "{[":
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    try:
        result = ast.literal_eval(text)
        if isinstance(result, dict):
            return result
    except Exception:
        pass
    return None


# ----------------------------------------------------------------------
# Supply chain graph fallback synthesizer
# ----------------------------------------------------------------------

# Role lookup for known regions, used when the LLM didn't return a graph.
# Same role taxonomy as the mock provider so the UI is consistent.
_REGION_ROLE: Dict[str, str] = {
    # suppliers (raw materials, components, primary production)
    "Taiwan": "supplier", "China": "supplier", "Bangladesh": "supplier",
    "India": "supplier", "Indonesia": "supplier", "Brazil": "supplier",
    # factories (assembly / manufacturing hubs)
    "Vietnam": "factory", "Thailand": "factory", "Malaysia": "factory",
    "Mexico": "factory", "Japan": "factory", "South Korea": "factory",
    # ports / transit
    "Singapore": "port", "Red Sea": "port", "Suez Canal": "port",
    "Panama Canal": "port",
    # destinations
    "United States": "destination", "Europe": "destination",
    "Germany": "destination",
}


def _slugify(label: str) -> str:
    out = []
    for ch in label.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in (" ", "-", "_", "/"):
            out.append("_")
    slug = "".join(out).strip("_")
    return slug or "node"


def _synthesize_graph_from_entities(
    entities: Dict[str, Any],
    risk_nodes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build a directed supply chain graph from detected regions when the
    LLM didn't return one. Roles inferred from _REGION_ROLE; unknown
    regions default to 'supplier' to keep them on the diagram.
    """
    regions = (entities or {}).get("regions") or []
    nodes: List[Dict[str, Any]] = []
    seen = set()

    for region in regions:
        role = _REGION_ROLE.get(region, "supplier")
        node_id = _slugify(f"{region}_{role}")
        if node_id in seen:
            continue
        seen.add(node_id)
        nodes.append({
            "id": node_id,
            "label": region,
            "role": role,
            "location": region,
        })

    # If we still have nothing, fall back to a generic 4-node chain so
    # the graph view always has something to render.
    if not nodes:
        nodes = [
            {"id": "generic_supplier", "label": "Primary Supplier", "role": "supplier", "location": "Origin"},
            {"id": "generic_factory", "label": "Assembly Plant", "role": "factory", "location": "Region"},
            {"id": "generic_port", "label": "Transit Hub", "role": "port", "location": "Port"},
            {"id": "generic_dest", "label": "Target Market", "role": "destination", "location": "Destination"},
        ]

    role_order = ["supplier", "factory", "port", "destination"]
    by_role: Dict[str, List[str]] = {r: [] for r in role_order}
    for n in nodes:
        by_role.setdefault(n["role"], []).append(n["id"])

    edges: List[Dict[str, Any]] = []
    active_roles = [r for r in role_order if by_role.get(r)]
    for a, b in zip(active_roles, active_roles[1:]):
        for s in by_role[a]:
            for t in by_role[b]:
                edges.append({"from": s, "to": t})

    return {"nodes": nodes, "edges": edges}


def _coerce_graph(raw_graph: Any) -> Optional[Dict[str, Any]]:
    """
    Validate / normalize an LLM-emitted graph dict. Returns None if it
    doesn't have the minimum shape so the caller can fall back to synth.
    Tolerates 'source/target' as alternate edge keys.
    """
    if not isinstance(raw_graph, dict):
        return None
    nodes = raw_graph.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return None

    valid_roles = {"supplier", "factory", "port", "destination", "other"}
    out_nodes: List[Dict[str, Any]] = []
    seen_ids = set()
    for n in nodes:
        if not isinstance(n, dict):
            continue
        node_id = str(n.get("id") or "").strip() or _slugify(str(n.get("label") or ""))
        if not node_id or node_id in seen_ids:
            continue
        role = str(n.get("role") or "other").lower()
        if role not in valid_roles:
            role = "other"
        out_nodes.append({
            "id": node_id,
            "label": str(n.get("label") or node_id),
            "role": role,
            "location": n.get("location"),
        })
        seen_ids.add(node_id)

    if not out_nodes:
        return None

    out_edges: List[Dict[str, Any]] = []
    for e in raw_graph.get("edges") or []:
        if not isinstance(e, dict):
            continue
        src = str(e.get("from") or e.get("source") or "").strip()
        tgt = str(e.get("to") or e.get("target") or "").strip()
        if not src or not tgt or src not in seen_ids or tgt not in seen_ids:
            continue
        out_edges.append({"from": src, "to": tgt, "label": e.get("label")})

    return {"nodes": out_nodes, "edges": out_edges}


@router.post("/upload-context")
async def upload_context(
    background_file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload an Excel, CSV, TXT, or PDF file to provide deeper context
    for a risk analysis. Returns a session_id usable in /analyze.
    """
    content = await background_file.read()
    filename = (background_file.filename or "upload").lower()
    ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""

    if ext not in _ALLOWED_UPLOAD_EXTS:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type '{ext}'. "
                f"Allowed: {', '.join(sorted(_ALLOWED_UPLOAD_EXTS))}"
            ),
        )

    extracted_text = ""
    try:
        if ext == ".csv":
            df = pd.read_csv(io.BytesIO(content))
            extracted_text = df.to_string(index=False)
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(io.BytesIO(content))
            extracted_text = df.to_string(index=False)
        elif ext == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            pages = []
            for page in reader.pages:
                try:
                    pages.append(page.extract_text() or "")
                except Exception as page_err:
                    logger.warning(f"PDF page extract failed: {page_err}")
            extracted_text = "\n\n".join(pages).strip()
            if not extracted_text:
                extracted_text = "(PDF contained no extractable text — likely scanned/image-only.)"
        else:  # .txt
            extracted_text = content.decode("utf-8", errors="ignore")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")
        
    if not session_id:
        session_id = str(uuid.uuid4())
        session = SessionDB(id=session_id, user_id=user.user_id, context_data={"files": [f"File {filename} content:\n{extracted_text}"]})
        db.add(session)
    else:
        stmt = select(SessionDB).where(SessionDB.id == session_id, SessionDB.user_id == user.user_id)
        result = await db.execute(stmt)
        session = result.scalars().first()
        if not session:
            session = SessionDB(id=session_id, user_id=user.user_id, context_data={"files": [f"File {filename} content:\n{extracted_text}"]})
            db.add(session)
        else:
            ctx = session.context_data or {"files": []}
            if "files" not in ctx:
                ctx["files"] = []
            ctx["files"].append(f"File {filename} content:\n{extracted_text}")
            session.context_data = ctx
            
    await db.commit()
    return {"session_id": session_id, "status": "success", "filename": filename}


@router.post("/analyze", response_model=RiskAnalysisResponse)
async def analyze_supply_chain(
    input_data: SupplyChainInput,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    x_preferred_provider: Optional[str] = Header(None, alias="X-Preferred-Provider"),
) -> RiskAnalysisResponse:
    try:
        session_id = input_data.session_id or str(uuid.uuid4())
        
        # Load or create session
        stmt = select(SessionDB).where(SessionDB.id == session_id)
        result = await db.execute(stmt)
        session_obj = result.scalars().first()
        
        if not session_obj:
            session_obj = SessionDB(id=session_id, user_id=user.user_id, description=input_data.description)
            db.add(session_obj)
        else:
            session_obj.description = input_data.description
            
        await db.commit()
        await db.refresh(session_obj)

        # Resolve focus_country: explicit input wins, else fall back to
        # the user's profile country_type/company_name hint, else None
        # (the RAG layer will infer from detected entities).
        local_focus = bool(input_data.intra_country_focus)
        focus_country = input_data.focus_country
        if local_focus and not focus_country:
            # Best-effort: if the user's profile mentions a country, use it.
            # company_type is free-text in this build so we just substring-check.
            profile_blob = f"{user.company_name or ''} {user.company_type or ''}".lower()
            for candidate in ("india", "united states", "usa", "uk", "united kingdom", "germany", "china"):
                if candidate in profile_blob:
                    focus_country = candidate.title() if candidate != "usa" else "United States"
                    break

        # Retrieve RAG context
        context = rag_service.retrieve_context(
            input_data.description,
            intra_country_focus=local_focus,
            focus_country=focus_country,
        )
        formatted_context = rag_service.format_context_for_llm(context)
        
        # Append User profile info for industry personalization
        profile_context = f"\n\n## USER PROFILE\nCompany Name: {user.company_name or 'N/A'}\nIndustry Type: {user.company_type or 'General'}\n"
        formatted_context += profile_context
        
        # Append any uploaded files to context
        if session_obj.context_data and "files" in session_obj.context_data:
            formatted_context += "\n\n## UPLOADED CONTEXT FILES\n"
            for f_text in session_obj.context_data["files"]:
                formatted_context += f"{f_text}\n\n"
        
        # Retrieve Conversation History
        stmt_msgs = select(MessageDB).where(MessageDB.session_id == session_id).order_by(MessageDB.created_at.asc())
        msgs_result = await db.execute(stmt_msgs)
        db_messages = msgs_result.scalars().all()
        conversation_history = [{"role": msg.role, "content": msg.content} for msg in db_messages]
        
        # Analyze using LLM Service
        analysis = await llm_service.analyze_supply_chain(
            supply_chain_description=input_data.description,
            retrieved_context=formatted_context,
            conversation_history=conversation_history,
            preferred_provider=x_preferred_provider,
            user_id=user.user_id,
            local_focus=local_focus,
        )

        # Supply chain graph: prefer the LLM's structured graph, fall back
        # to a deterministic synthesis from detected entities. Inject back
        # into the analysis dict BEFORE message save so replay restores it.
        graph_dict = _coerce_graph(analysis.get("supply_chain_graph"))
        if not graph_dict:
            graph_dict = _synthesize_graph_from_entities(
                context.get("entities", {}),
                analysis.get("risk_nodes", []),
            )
        analysis["supply_chain_graph"] = graph_dict

        # Save Messages — store assistant content as JSON so replay can rehydrate
        # the structured Risk Brief instead of showing a Python repr blob.
        db.add(MessageDB(session_id=session_id, role="user", content=input_data.description))
        db.add(MessageDB(
            session_id=session_id,
            role="assistant",
            content=json.dumps(analysis, default=str),
        ))
        
        # Parse and save Analysis Result
        risk_nodes = []
        for node_data in analysis.get("risk_nodes", []):
            try:
                ev = node_data.get("evidence")
                if ev is not None and not isinstance(ev, list):
                    ev = [str(ev)]
                risk_nodes.append(RiskNode(
                    node=node_data.get("node", "Unknown"),
                    risk_level=RiskLevel(node_data.get("risk_level", "Medium")),
                    cause=node_data.get("cause", ""),
                    recommended_action=node_data.get("recommended_action", ""),
                    confidence_score=float(node_data.get("confidence_score", 0.5)),
                    category=RiskCategory(node_data.get("category", "supplier")),
                    evidence=ev,
                ))
            except Exception:
                continue
                
        # Clear existing analysis result for this session if it exists to replace it
        stmt_del = select(AnalysisResultDB).where(AnalysisResultDB.session_id == session_id)
        old_analysis = (await db.execute(stmt_del)).scalars().first()
        if old_analysis:
            await db.delete(old_analysis)
            
        analysis_result = AnalysisResultDB(
            session_id=session_id,
            risk_nodes=analysis.get("risk_nodes", []),
            overall_risk_level=analysis.get("overall_risk_level", "Medium"),
            summary=analysis.get("summary", ""),
            entities=context.get("entities", {})
        )
        db.add(analysis_result)
        await db.commit()

        meta = analysis.get("_meta") or {}
        provider_meta = LLMMetadata(
            provider_used=meta.get("provider_used", "unknown"),
            is_mock=bool(meta.get("is_mock", False)),
        )

        return RiskAnalysisResponse(
            session_id=session_id,
            risk_nodes=risk_nodes,
            overall_risk_level=RiskLevel(analysis.get("overall_risk_level", "Medium")),
            summary=analysis.get("summary", ""),
            follow_up_suggestions=analysis.get("follow_up_suggestions", []),
            entities_detected=context.get("entities", {}),
            supply_chain_graph=analysis.get("supply_chain_graph"),
            provider_meta=provider_meta,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/followup", response_model=FollowUpResponse)
async def handle_followup(
    input_data: FollowUpInput,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    x_preferred_provider: Optional[str] = Header(None, alias="X-Preferred-Provider"),
) -> FollowUpResponse:
    stmt = select(SessionDB).where(SessionDB.id == input_data.session_id, SessionDB.user_id == user.user_id)
    session_obj = (await db.execute(stmt)).scalars().first()
    
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found.")
        
    try:
        # Re-fetch previous analysis
        stmt_analysis = select(AnalysisResultDB).where(AnalysisResultDB.session_id == session_obj.id)
        analysis_db = (await db.execute(stmt_analysis)).scalars().first()
        previous_analysis = {}
        if analysis_db:
            previous_analysis = {
                "risk_nodes": analysis_db.risk_nodes,
                "overall_risk_level": analysis_db.overall_risk_level,
                "summary": analysis_db.summary
            }
            
        context = rag_service.retrieve_context(f"{session_obj.description} {input_data.question}")
        formatted_context = rag_service.format_context_for_llm(context)
        
        if session_obj.context_data and "files" in session_obj.context_data:
            formatted_context += "\n\n## UPLOADED CONTEXT FILES\n"
            for f_text in session_obj.context_data["files"]:
                formatted_context += f"{f_text}\n\n"
        
        response = await llm_service.handle_followup(
            question=input_data.question,
            previous_analysis=previous_analysis,
            retrieved_context=formatted_context,
            preferred_provider=x_preferred_provider,
            user_id=user.user_id
        )
        
        # Save messages — JSON-encoded for clean replay
        db.add(MessageDB(session_id=session_obj.id, role="user", content=input_data.question))
        db.add(MessageDB(
            session_id=session_obj.id,
            role="assistant",
            content=json.dumps(response, default=str),
        ))
        await db.commit()

        meta = response.get("_meta") or {}
        provider_meta = LLMMetadata(
            provider_used=meta.get("provider_used", "unknown"),
            is_mock=bool(meta.get("is_mock", False)),
        )

        return FollowUpResponse(
            session_id=session_obj.id,
            response_type=response.get("response_type", "general"),
            message=response.get("message", ""),
            suggestions=response.get("suggestions"),
            follow_up_suggestions=response.get("follow_up_suggestions", []),
            provider_meta=provider_meta,
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Follow-up failed: {str(e)}")


@router.post("/scenario", response_model=ScenarioResult)
async def simulate_scenario(
    input_data: ScenarioInput,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    x_preferred_provider: Optional[str] = Header(None, alias="X-Preferred-Provider"),
) -> ScenarioResult:
    """
    Run a what-if scenario against an existing analysis.
    Does not modify the saved analysis — purely an exploratory delta.
    """
    stmt = select(SessionDB).where(
        SessionDB.id == input_data.session_id,
        SessionDB.user_id == user.user_id,
    )
    session_obj = (await db.execute(stmt)).scalars().first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found.")

    stmt_analysis = select(AnalysisResultDB).where(
        AnalysisResultDB.session_id == session_obj.id
    )
    analysis_db = (await db.execute(stmt_analysis)).scalars().first()
    if not analysis_db:
        raise HTTPException(
            status_code=400,
            detail="No analysis exists for this session yet — run an analysis first.",
        )

    previous_analysis = {
        "risk_nodes": analysis_db.risk_nodes,
        "overall_risk_level": analysis_db.overall_risk_level,
        "summary": analysis_db.summary,
    }

    try:
        scenario = await llm_service.simulate_scenario(
            previous_analysis=previous_analysis,
            scenario_type=input_data.scenario_type.value,
            parameters=input_data.parameters or {},
            preferred_provider=x_preferred_provider,
            user_id=user.user_id,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Scenario simulation failed: {str(e)}")

    # Defensive coercion — LLMs occasionally drop fields. Guarantee a
    # valid ScenarioResult so the frontend always renders something.
    def _snapshot(raw: Any, fallback_overall: str) -> ScenarioSnapshot:
        if not isinstance(raw, dict):
            raw = {}
        try:
            overall = RiskLevel(raw.get("overall_risk_level", fallback_overall))
        except ValueError:
            overall = RiskLevel(fallback_overall)
        nodes_out: List[ScenarioAffectedNode] = []
        for n in raw.get("affected_nodes") or []:
            if not isinstance(n, dict):
                continue
            try:
                nodes_out.append(ScenarioAffectedNode(
                    node=str(n.get("node", "Unknown")),
                    risk_level=RiskLevel(n.get("risk_level", "Medium")),
                    delta_explanation=n.get("delta_explanation"),
                ))
            except Exception:
                continue
        return ScenarioSnapshot(overall_risk_level=overall, affected_nodes=nodes_out)

    raw_tradeoffs = scenario.get("tradeoffs") or {}
    tradeoffs = ScenarioTradeoffs(
        latency=str(raw_tradeoffs.get("latency", "Unchanged"))[:120],
        cost=str(raw_tradeoffs.get("cost", "Unchanged"))[:120],
        risk=str(raw_tradeoffs.get("risk", "Unchanged"))[:120],
    )

    try:
        verdict = ScenarioVerdict(scenario.get("verdict", "neutral"))
    except ValueError:
        verdict = ScenarioVerdict.NEUTRAL

    fallback_overall = previous_analysis.get("overall_risk_level") or "Medium"
    before = _snapshot(scenario.get("before"), fallback_overall)
    after = _snapshot(scenario.get("after"), fallback_overall)

    meta = scenario.get("_meta") or {}
    provider_meta = LLMMetadata(
        provider_used=meta.get("provider_used", "unknown"),
        is_mock=bool(meta.get("is_mock", False)),
    )

    return ScenarioResult(
        session_id=session_obj.id,
        scenario_type=input_data.scenario_type,
        scenario_label=str(scenario.get("scenario_label", "Scenario simulation"))[:200],
        verdict=verdict,
        narrative=str(scenario.get("narrative", ""))[:1000],
        tradeoffs=tradeoffs,
        before=before,
        after=after,
        provider_meta=provider_meta,
    )


@router.get("/personas")
async def list_personas():
    """
    Demo personas — one-click presets that pre-fill an industry profile
    and a rich supply chain description for the welcome screen.
    """
    from ..data.personas import get_personas
    return {"personas": get_personas()}


@router.get("/alerts")
async def list_alerts(limit: int = 8):
    """
    Live risk intelligence feed for the sidebar.
    Tries the live RSS news service first; falls back to mock data
    if the live fetch returns nothing (e.g. no network).
    """
    from ..services.news_service import get_live_alerts
    from ..data.mock_risk_data import get_all_risks

    live = []
    try:
        live = await get_live_alerts(limit=limit)
    except Exception as exc:
        logger.warning("Live news fetch failed, using mock data: %s", exc)

    if live:
        # Ensure link field is preserved
        return {"alerts": [{**a} for a in live[:limit]], "count": len(live), "source": "live"}

    # Fallback: mock data sorted newest-first
    risks = get_all_risks()
    risks_sorted = sorted(
        risks,
        key=lambda r: r.get("last_updated") or "",
        reverse=True,
    )
    out = []
    for r in risks_sorted[:max(1, min(limit, 20))]:
        out.append({
            "id": r.get("id"),
            "title": r.get("title"),
            "region": r.get("region"),
            "category": r.get("category"),
            "risk_level": r.get("risk_level"),
            "description": r.get("description"),
            "last_updated": r.get("last_updated"),
            "sources": r.get("sources", []),
        })
    return {"alerts": out, "count": len(out), "source": "mock"}



@router.get("/session/{session_id}")
async def get_session(
    session_id: str,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(SessionDB).where(SessionDB.id == session_id, SessionDB.user_id == user.user_id)
    session_obj = (await db.execute(stmt)).scalars().first()
    
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")
        
    stmt_msgs = select(MessageDB).where(MessageDB.session_id == session_id).order_by(MessageDB.created_at.asc())
    msgs = (await db.execute(stmt_msgs)).scalars().all()

    # One-shot legacy migration: any assistant message stored as str(dict)
    # (Python repr) gets recovered via ast.literal_eval and rewritten as JSON
    # so future replays render the rich Risk Brief.
    migrated = False
    for m in msgs:
        if m.role != "assistant":
            continue
        content = m.content or ""
        if not content or content[0] not in "{[":
            continue
        try:
            json.loads(content)
            continue  # already valid JSON
        except Exception:
            pass
        recovered = _normalize_assistant_content(content)
        if isinstance(recovered, dict):
            m.content = json.dumps(recovered, default=str)
            migrated = True
    if migrated:
        await db.commit()
    
    stmt_analysis = select(AnalysisResultDB).where(AnalysisResultDB.session_id == session_id)
    analysis_db = (await db.execute(stmt_analysis)).scalars().first()
    
    # Check if there are context files
    files = []
    if session_obj.context_data and "files" in session_obj.context_data:
        files = [{"info": "Uploaded file"} for _ in session_obj.context_data["files"]]
    
    return {
        "session_id": session_obj.id,
        "description": session_obj.description,
        "entities": analysis_db.entities if analysis_db else {},
        "analysis_summary": analysis_db.summary if analysis_db else "",
        "message_count": len(msgs),
        "history": [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in msgs],
        "analysis": {
            "risk_nodes": analysis_db.risk_nodes if analysis_db else [],
            "overall_risk_level": analysis_db.overall_risk_level if analysis_db else "Medium",
            "summary": analysis_db.summary if analysis_db else ""
        },
        "has_uploaded_files": len(files) > 0
    }

@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(SessionDB).where(SessionDB.id == session_id, SessionDB.user_id == user.user_id)
    session_obj = (await db.execute(stmt)).scalars().first()
    if session_obj:
        await db.delete(session_obj)
        await db.commit()
    return {"status": "deleted", "session_id": session_id}
