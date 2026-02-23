import requests
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from openai import OpenAI

# Internal Imports - Now importing directly from the root
import database as db
from database import seed_zones
from model import generate_synthetic_data, evaluate_alerts

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Initializing EcoWatcher Engine...")
    # FIRST: Create the tables
    db.init_db() 
    # SECOND: Seed the data (Pins your zones automatically)
    seed_zones()
    yield
    print("🛑 Shutting down EcoWatcher Engine...")

app = FastAPI(lifespan=lifespan)

# --- FIX 1: Look for index.html in the root directory instead of /templates ---
templates = Jinja2Templates(directory=".")

# --- UI Routes ---

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main view: Shows featured zones and recent alert history"""
    all_zones = db.get_zones()
    recent_alerts = db.get_recent_alerts(15)
    
    featured_zones = [z for z in all_zones if z.get('featured') == 1][:5]
    
    dashboard_data = []
    for zone in featured_zones:
        data = generate_synthetic_data()
        reason = evaluate_alerts(data)
        if reason:
            db.log_alert(zone['name'], data, reason)
        dashboard_data.append({"info": zone, "metrics": data})

    alerts_from_db = db.get_recent_alerts(100)
    problematic_zones = {a['zone_name'] for a in alerts_from_db}
    
    # Renders index.html from the root
    return templates.TemplateResponse("index.html", {
        "request": request,
        "zones": all_zones,
        "dashboard_zones": dashboard_data,
        "alerts": recent_alerts,
        "total_zones": len(all_zones),
        "breached_zones_count": len(problematic_zones)
    })

# --- Management Routes ---

@app.get("/pin_zone/{zone_id}")
async def pin_zone(zone_id: int):
    success = db.toggle_zone_featured(zone_id)
    if not success:
        return RedirectResponse(url="/?error=limit_reached", status_code=303)
    return RedirectResponse(url="/", status_code=303)

@app.post("/add_zone")
async def add_new_zone(name: str = Form(...), lat: float = Form(...), lon: float = Form(...)):
    db.add_zone(name, lat, lon)
    return RedirectResponse(url="/", status_code=303)

@app.get("/delete_zone/{zone_id}")
async def delete_zone(zone_id: int):
    db.remove_zone(zone_id)
    return RedirectResponse(url="/", status_code=303)

# --- API & AI Routes ---

@app.get("/api/update")
async def get_live_updates():
    zones = db.get_zones()
    updates = []
    for zone in zones:
        data = generate_synthetic_data()
        reason = evaluate_alerts(data)
        if reason:
            db.log_alert(zone['name'], data, reason)
        updates.append({"zone": zone['name'], "metrics": data, "alert": reason})
    return updates

load_dotenv()

# INITIALIZE CLIENT
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.getenv("HF_API_KEY") 
)

@app.post("/api/chat")
async def eco_chat(request: Request):
    try:
        body = await request.json()
        user_query = body.get("query")
        session_id = str(body.get("session_id", "default_user"))
        selected_id = body.get("selected_alert_id")

        priority_context = ""
        if selected_id:
            alert = db.get_alert_by_id(selected_id)
            if alert:
                priority_context = (
                    f"STRICT FOCUS DATA for Alert ID {alert['id']}:\n"
                    f"- Zone: {alert['zone_name']}\n"
                    f"- Breach Reason: {alert['reason']}\n"
                    f"- AQI: {alert['aqi']}, Temp: {alert['temp']}°C, UV: {alert['uv']}\n"
                    f"- Recorded at: {alert['timestamp']}\n\n"
                )

        recent_alerts = db.get_recent_alerts(5)
        general_context = "SYSTEM HISTORY:\n" + "\n".join(
            [f"ID: {a['id']} | {a['zone_name']} | {a['reason']}" for a in recent_alerts]
        )

        history = db.get_chat_history(session_id)
        
        messages = [{
            "role": "system",
            "content": f"""
        You are EcoWatcher AI. Provide a technical environmental risk assessment.

        STRICT RULES:
        - Only use the provided metrics.
        - If Alert ID is mentioned, analyze ONLY that data.
        - Keep answers under 120 words.
        - Use simple Markdown for formatting (bolding, short tables).

        {priority_context}
        {general_context}
        """
        }]
        messages.extend(history)
        messages.append({"role": "user", "content": user_query})

        response = client.chat.completions.create(
            model="Qwen/Qwen3-Coder-Next:novita", 
            messages=messages,
            temperature=0.1 # Low temperature for factual accuracy
        )
        ai_reply = response.choices[0].message.content
        
        db.save_chat_message(session_id, "user", user_query)
        db.save_chat_message(session_id, "assistant", ai_reply)
        
        return {"response": ai_reply}

    except Exception as e:
        return {"response": f"Error: {str(e)}"}
    
@app.get("/api/system/reset", response_class=RedirectResponse)
async def system_reset():
    """One-click URL to factory reset the application data."""
    db.reset_and_reseed()
    print("🧹 Database Factory Reset Successful.")
    # Redirect back to dashboard with a success message
    return RedirectResponse(url="/?msg=system_reset_complete", status_code=303)
    
if __name__ == "__main__":
    db.init_db()
    import uvicorn
    # Local fallback
    uvicorn.run(app, host="127.0.0.1", port=8000)