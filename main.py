import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

from database import create_document, get_documents, db
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

@app.get("/api/dashboard", response_model=Dict[str, Any])
def dashboard_summary():
    """Return high-level metrics and a 12-month volume series for the dashboard.
    If database is unavailable, return safe defaults.
    """
    try:
        if db is None:
            # Database not configured
            return {
                "totals": {
                    "total_leads": 0,
                    "total_volume": 0.0,
                    "conversion_rate": 0.0,
                    "active_brokers": 0,
                },
                "series": [],
                "note": "Database not configured. Set DATABASE_URL and DATABASE_NAME to enable metrics."
            }

        # Totals
        total_leads = db["lead"].count_documents({})
        # Sum expected_monthly_volume (handle missing/null)
        agg_volume = list(db["lead"].aggregate([
            {"$group": {"_id": None, "sum": {"$sum": {"$ifNull": ["$expected_monthly_volume", 0]}}}}
        ]))
        total_volume = float(agg_volume[0]["sum"]) if agg_volume else 0.0

        # Active brokers (distinct non-empty)
        brokers = db["lead"].distinct("broker", {"broker": {"$ne": None, "$ne": ""}})
        active_brokers = len([b for b in brokers if b])

        # Simple conversion rate heuristic (placeholder): if we had stages we could compute
        # For now, derive from leads that provided expected_monthly_volume
        with_volume = db["lead"].count_documents({"expected_monthly_volume": {"$gt": 0}})
        conversion_rate = (with_volume / total_leads * 100.0) if total_leads else 0.0

        # 12-month volume timeseries by created_at month
        now = datetime.utcnow()
        start_dt = datetime(now.year - 1 if now.month != 12 else now.year, ((now.month % 12) + 1), 1)
        pipeline = [
            {"$match": {"created_at": {"$gte": start_dt}}},
            {"$project": {
                "ym": {"$dateToString": {"format": "%Y-%m", "date": "$created_at"}},
                "expected_monthly_volume": 1
            }},
            {"$group": {
                "_id": "$ym",
                "volume": {"$sum": {"$ifNull": ["$expected_monthly_volume", 0]}}
            }},
            {"$sort": {"_id": 1}}
        ]
        monthly = {d["_id"]: float(d["volume"]) for d in db["lead"].aggregate(pipeline)}

        # Build full 12-month series including months with zero
        series = []
        year = now.year
        month = now.month
        for i in range(11, -1, -1):
            y = year
            m = month - i
            while m <= 0:
                y -= 1
                m += 12
            key = f"{y:04d}-{m:02d}"
            series.append({
                "month": key,
                "volume": monthly.get(key, 0.0)
            })

        return {
            "totals": {
                "total_leads": total_leads,
                "total_volume": round(total_volume, 2),
                "conversion_rate": round(conversion_rate, 2),
                "active_brokers": active_brokers,
            },
            "series": series
        }
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
