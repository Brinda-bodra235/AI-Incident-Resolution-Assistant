from fastapi import FastAPI
from app.routers import auth, incidents, escalations

app = FastAPI(
    title="AI Incident Resolution Assistant",
    description="IT/ops AI agent for analyzing logs and resolving incidents",
    version="1.0.0"
)

# Include Routers
app.include_router(auth.router)
app.include_router(incidents.router)
app.include_router(escalations.router)

@app.get("/health")
def healthcheck():
    return {"status": "healthy"}
