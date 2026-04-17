"""
SupplyChainIQ - AI-Powered Supply Chain Risk Advisor
FastAPI Backend Application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import analysis_router, keys_router, user_router
from .models import HealthResponse
from .services import llm_service
from .database import init_db
from contextlib import asynccontextmanager

# Application metadata
APP_TITLE = "SupplyChainIQ API"
APP_DESCRIPTION = """
## AI-Powered Supply Chain Risk Intelligence for SMEs v3.0

SupplyChainIQ helps small and mid-sized manufacturers predict and mitigate 
supply chain risks using conversational AI and real-time intelligence.

### Features
- **Natural Language Input**: Describe your supply chain in plain English.
- **AI Risk Analysis**: Get instant risk assessments grounded in real-world data.
- **Interactive Graph Viz**: Explore your supply chain dependencies visually with node heatmapping.
- **RAG-Powered Intelligence**: Risks are identified using current geopolitical, climate, and logistics data.
- **Live RSS News Monitor**: Filtered global news signals specific to your supply chain.
- **Scenario Simulation**: "What-if" modelling for port closures, logistics delays, and more.
- **Actionable Recommendations**: Detailed mitigation strategies for identified nodes.

### API Endpoints
- `POST /api/v1/analysis/analyze` - Perform detailed supply chain risk assessment.
- `POST /api/v1/analysis/followup` - Deep-dive into specific risks with conversational AI.
- `POST /api/v1/analysis/scenario` - Model disruptions and stress-test your network.
- `GET /api/v1/analysis/alerts` - Retrieve live supply chain intelligence feed.
"""
APP_VERSION = "3.0.0"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the database on startup
    await init_db()
    yield

# Initialize FastAPI app
app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"  # For demo - restrict in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analysis_router)
app.include_router(keys_router)
app.include_router(user_router)


@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": APP_TITLE,
        "version": APP_VERSION,
        "description": "AI-Powered Supply Chain Risk Advisor for SMEs",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Health check endpoint"""
    available = llm_service.get_available_providers()
    return HealthResponse(
        status="healthy",
        version=APP_VERSION,
        services={
            "api": "operational",
            "rag": "operational",
            "llm": "operational",
            "llm_providers": ", ".join(available),
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)

