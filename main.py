import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from database import create_document, get_documents
from schemas import Lead

app = FastAPI(title="PAYLOT API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"name": "PAYLOT", "message": "Forex rebate platform backend is running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from PAYLOT backend API"}

class LeadResponse(BaseModel):
    id: str
    name: str
    email: str
    broker: Optional[str] = None
    expected_monthly_volume: Optional[float] = None
    message: Optional[str] = None
    consent: bool

@app.post("/api/leads", response_model=dict)
def create_lead(lead: Lead):
    try:
        lead_id = create_document("lead", lead)
        return {"status": "success", "id": lead_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/leads", response_model=List[LeadResponse])
def list_leads(limit: int = 20):
    try:
        docs = get_documents("lead", {}, limit)
        out: List[LeadResponse] = []
        for d in docs:
            out.append(LeadResponse(
                id=str(d.get("_id")),
                name=d.get("name"),
                email=d.get("email"),
                broker=d.get("broker"),
                expected_monthly_volume=d.get("expected_monthly_volume"),
                message=d.get("message"),
                consent=d.get("consent", True)
            ))
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        from database import db
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
