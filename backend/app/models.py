"""
Pydantic models for SupplyChainIQ API
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class RiskCategory(str, Enum):
    GEOPOLITICAL = "geopolitical"
    CLIMATE = "climate"
    LOGISTICS = "logistics"
    SUPPLIER = "supplier"


class GraphNodeRole(str, Enum):
    SUPPLIER = "supplier"
    FACTORY = "factory"
    PORT = "port"
    DESTINATION = "destination"
    OTHER = "other"


class GraphNode(BaseModel):
    """A node in the supply chain graph"""
    id: str = Field(..., description="Unique identifier for the node")
    label: str = Field(..., description="Display label, e.g. 'Taiwan Semiconductors'")
    role: GraphNodeRole = Field(..., description="Role in the supply chain")
    location: Optional[str] = Field(None, description="Country / region")


class GraphEdge(BaseModel):
    """A directed edge between two graph nodes"""
    source: str = Field(..., alias="from", description="Source node id")
    target: str = Field(..., alias="to", description="Target node id")
    label: Optional[str] = Field(None, description="Optional edge label, e.g. 'Container shipping'")

    model_config = {"populate_by_name": True}


class SupplyChainGraph(BaseModel):
    """A directed supply chain graph extracted from the analysis"""
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)


# Request Models

class SupplyChainInput(BaseModel):
    """Input model for supply chain description"""
    description: str = Field(
        ...,
        description="Natural language description of the supply chain",
        min_length=10,
        max_length=5000,
        examples=["We source chips from Taiwan, assemble in Vietnam, and ship to the US through Singapore."]
    )
    session_id: Optional[str] = Field(
        None,
        description="Session ID for conversation continuity"
    )
    intra_country_focus: Optional[bool] = Field(
        False,
        description="If true, pivot the analysis to intra-country logistics & regional intelligence instead of cross-border trade risks."
    )
    focus_country: Optional[str] = Field(
        None,
        description="Optional explicit country to focus on when intra_country_focus is enabled (e.g. 'India', 'United States'). If omitted, the system infers from the description / user profile."
    )


class FollowUpInput(BaseModel):
    """Input model for follow-up questions"""
    question: str = Field(
        ...,
        description="Follow-up question about the analysis",
        min_length=3,
        max_length=1000
    )
    session_id: str = Field(
        ...,
        description="Session ID from previous analysis"
    )


class ScenarioType(str, Enum):
    SUPPLIER_SWITCH = "supplier_switch"
    ROUTE_CHANGE = "route_change"
    INVENTORY_BUFFER = "inventory_buffer"


class ScenarioVerdict(str, Enum):
    IMPROVED = "improved"
    NEUTRAL = "neutral"
    WORSENED = "worsened"


class ScenarioInput(BaseModel):
    """Input for a what-if scenario simulation"""
    session_id: str = Field(..., description="Session ID with an existing analysis")
    scenario_type: ScenarioType = Field(..., description="Type of scenario to simulate")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Free-form parameters specific to the scenario type"
    )


# Response Models

class LLMMetadata(BaseModel):
    """Metadata about which LLM provider was used"""
    provider_used: str = Field(..., description="Which LLM provider generated this response")
    is_mock: bool = Field(..., description="Whether the response came from mock fallback")


class RiskNode(BaseModel):
    """Individual risk node in the supply chain"""
    node: str = Field(..., description="Supply chain node being assessed")
    risk_level: RiskLevel = Field(..., description="Risk severity level")
    cause: str = Field(..., description="Cause of the risk, grounded in context")
    recommended_action: str = Field(..., description="Specific mitigation action")
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in this assessment"
    )
    category: RiskCategory = Field(..., description="Risk category")
    evidence: Optional[List[str]] = Field(
        default=None,
        description="1-3 short bullets citing the specific data points that ground this risk"
    )


class RiskAnalysisResponse(BaseModel):
    """Complete risk analysis response"""
    session_id: str = Field(..., description="Session ID for conversation continuity")
    risk_nodes: List[RiskNode] = Field(..., description="Individual risk assessments")
    overall_risk_level: RiskLevel = Field(..., description="Overall supply chain risk")
    summary: str = Field(..., description="Plain-language summary for SME owners")
    follow_up_suggestions: List[str] = Field(
        ...,
        description="Suggested follow-up questions"
    )
    entities_detected: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Entities extracted from supply chain description"
    )
    supply_chain_graph: Optional[Dict[str, Any]] = Field(
        None,
        description="Directed supply chain graph for visualization (nodes/edges as plain dicts)"
    )
    provider_meta: Optional[LLMMetadata] = Field(
        None,
        description="Which LLM provider produced this analysis"
    )


class FollowUpResponse(BaseModel):
    """Response to follow-up questions"""
    session_id: str
    response_type: str
    message: str
    suggestions: Optional[List[Dict[str, Any]]] = None
    follow_up_suggestions: List[str]
    provider_meta: Optional[LLMMetadata] = None


class ScenarioAffectedNode(BaseModel):
    """A node referenced in a scenario before/after snapshot"""
    node: str
    risk_level: RiskLevel
    delta_explanation: Optional[str] = None


class ScenarioSnapshot(BaseModel):
    """Before / after snapshot for a scenario"""
    overall_risk_level: RiskLevel
    affected_nodes: List[ScenarioAffectedNode] = Field(default_factory=list)


class ScenarioTradeoffs(BaseModel):
    """Latency / cost / risk tradeoff narrative chips"""
    latency: str = Field(..., description="e.g. '+12 days' or 'unchanged'")
    cost: str = Field(..., description="e.g. '+15% freight' or 'unchanged'")
    risk: str = Field(..., description="e.g. 'Critical → Medium for chip supply'")


class ScenarioResult(BaseModel):
    """Response for a scenario simulation"""
    session_id: str
    scenario_type: ScenarioType
    scenario_label: str = Field(..., description="Short human-readable label")
    verdict: ScenarioVerdict
    narrative: str = Field(..., description="2-3 sentence prose explanation of the tradeoff")
    tradeoffs: ScenarioTradeoffs
    before: ScenarioSnapshot
    after: ScenarioSnapshot
    provider_meta: Optional[LLMMetadata] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    services: Dict[str, str]


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None
    code: str


class UserProfileUpdate(BaseModel):
    company_name: Optional[str] = None
    company_type: Optional[str] = None


class UserProfileResponse(BaseModel):
    user_id: str
    company_name: Optional[str] = None
    company_type: Optional[str] = None


class SessionSummary(BaseModel):
    id: str
    description: Optional[str]
    overall_risk_level: Optional[str]
    created_at: str


class SessionListResponse(BaseModel):
    sessions: List[SessionSummary]
