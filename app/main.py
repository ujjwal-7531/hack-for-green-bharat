import random
from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import database as db
import requests
import json
from contextlib import asynccontextmanager
from database import seed_zones

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Initializing EcoWatcher Engine...")
    
    # Call the function directly (no 'db.' prefix needed if imported this way)
    seed_zones() 
    
    yield
    print("🛑 Shutting down EcoWatcher Engine...")

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

# --- Threshold Configuration ---
# You can adjust these for your presentation demo
THRESHOLDS = {
    "temp": 40.0,       # °C
    "aqi": 150,         # Index
    "uv": 8.0,          # Index
    "noise": 85.0,      # dB
    "wind_speed": 20.0  # km/h
}

def generate_synthetic_data():
    """Generates the 6 required environmental parameters"""
    return {
        "temp": round(random.uniform(20, 45), 2),
        "humidity": round(random.uniform(30, 90), 2),
        "wind_speed": round(random.uniform(5, 30), 2),
        "aqi": random.randint(50, 300),
        "uv": round(random.uniform(0, 11), 1),
        "noise": round(random.uniform(40, 100), 1)
    }

def evaluate_alerts(data):
    """
    Evaluates telemetry data against centralized thresholds.
    Returns a combined string of breaches or None.
    """
    alerts = []
    
    # 2. Dynamic Comparison
    if data["aqi"] > THRESHOLDS["aqi"]: 
        alerts.append("High Pollution")
    if data["temp"] > THRESHOLDS["temp"]: 
        alerts.append("Extreme Heat")
    if data["uv"] > THRESHOLDS["uv"]: 
        alerts.append("High UV Radiation")
    if data["noise"] > THRESHOLDS["noise"]: 
        alerts.append("Noise Violation")
    if data["wind_speed"] > THRESHOLDS["wind_speed"]: 
        alerts.append("High Wind Speed")
    
    # 3. Join logic for combined reporting
    return ", ".join(alerts) if alerts else None

# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    all_zones = db.get_zones()
    recent_alerts = db.get_recent_alerts(15)
    
    # Filter for Featured zones (limit to 5)
    featured_zones = [z for z in all_zones if z.get('featured') == 1][:5]
    
    dashboard_data = []
    for zone in featured_zones:
        data = generate_synthetic_data()
        reason = evaluate_alerts(data)
        if reason:
            db.log_alert(zone['name'], data, reason)
        dashboard_data.append({"info": zone, "metrics": data})

    # Simple Counter logic
    alerts_from_db = db.get_recent_alerts(100)
    problematic_zones = {a['zone_name'] for a in alerts_from_db}
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "zones": all_zones,
        "dashboard_zones": dashboard_data,
        "alerts": recent_alerts,
        "total_zones": len(all_zones),
        "breached_zones_count": len(problematic_zones)
    })

# Add the route to handle the pinning action
@app.get("/pin_zone/{zone_id}")
async def pin_zone(zone_id: int):
    success = db.toggle_zone_featured(zone_id)
    if not success:
        # Redirect with a simple error flag in the URL
        return RedirectResponse(url="/?error=limit_reached", status_code=303)
    return RedirectResponse(url="/", status_code=303)

@app.post("/add_zone")
async def add_new_zone(name: str = Form(...), lat: float = Form(...), lon: float = Form(...)):
    db.add_zone(name, lat, lon)
    return RedirectResponse(url="/", status_code=303)

@app.get("/delete_zone/{zone_id}")
async def delete_zone(zone_id: int):
    db.remove_zone(zone_id) # Call the new function we added to database.py
    return RedirectResponse(url="/", status_code=303)

@app.get("/api/update")
async def get_live_updates():
    """Returns new synthetic data for all zones without reloading the page"""
    zones = db.get_zones()
    updates = []
    for zone in zones:
        data = generate_synthetic_data()
        reason = evaluate_alerts(data)
        if reason:
            db.log_alert(zone['name'], data, reason)
        updates.append({
            "zone": zone['name'],
            "metrics": data,
            "alert": reason
        })
    return updates

# Ollama model

@app.post("/api/chat")
async def eco_chat(request: Request):
    body = await request.json()
    user_query = body.get("query")
    
    # 1. RETRIEVAL (The 'R' in RAG)
    # Get all current data to give the AI 'Context'
    zones = db.get_zones()
    context_data = "CURRENT ENVIRONMENTAL SNAPSHOT:\n"
    context_data += "-----------------------------------\n"
    for z in zones:
        d = generate_synthetic_data() 
        context_data += (
            f"LOCATION: {z['name']}\n"
            f"- Air Quality (AQI): {d['aqi']}\n"
            f"- Temperature: {d['temp']}°C\n"
            f"- Wind Speed: {d['wind_speed']}km/h\n"
            f"- UV Index: {d['uv']}\n"
            f"- Ambient Noise: {d['noise']}dB\n"
            "-----------------------------------\n"
        )

    # 2. PROMPT ENGINEERING
    prompt = f"""
    <start_of_turn>user
    ROLE: You are the EcoWatcher Strategic Analyst. 
    CONTEXT: Use the following live telemetry for 6 parameters:
    {context_data}

    SAFETY CRITERIA:
    - AQI > 150: High Pollution
    - Temp > 40: Extreme Heat
    - Wind > 20: High Wind
    - UV > 8: Dangerous Radiation
    - Noise > 85: Noise Pollution
    - Humidity: Monitor for extreme dryness or saturation.

    INSTRUCTIONS:
    1. Scan ALL 6 parameters for the requested zone(s).
    2. If ANY parameter exceeds safety criteria, give alert and solution regarding in formatted manner:
       "ALERT: [Zone Name] is experiencing [Issue].
       RECOMMENDATION: [Actionable Advice]."
    3. Be clinical and precise. No conversational fluff.
    4. If the query is non-environmental, respond: "Unauthorized Query: Outside Monitoring Scope."

    QUERY: {user_query}
    <end_of_turn>
    <start_of_turn>model
    """

    # 3. OLLAMA CALL
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "gemma3:4b", 
                "prompt": prompt,
                "stream": False
            },
            timeout=10
        )
        return {"response": response.json().get("response")}
    except Exception as e:
        return {"response": "I'm having trouble connecting to the local sensor intelligence. Is Ollama running?"}

if __name__ == "__main__":
    db.init_db()
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
    
##commit test