import sqlite3
from datetime import datetime

DB_NAME = "data.db"

def init_db():
    """Creates tables if they don't exist"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS zones 
                 (id INTEGER PRIMARY KEY, name TEXT, lat REAL, lon REAL, featured INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS alerts 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, zone_name TEXT, 
                  temp REAL, humidity REAL, wind REAL, aqi INTEGER, uv REAL, noise REAL, reason TEXT)''')
    
    # New table for chat memory persistence
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content TEXT, timestamp DATETIME)''')
    conn.commit()
    conn.close()

def seed_zones():
    """Populates the database with initial Indian city data if empty"""
    existing_zones = get_zones() 
    if not existing_zones:
        default_zones = [
            {"name": "Mumbai Central", "lat": 18.96, "lon": 72.82},
            {"name": "Delhi Tech Zone", "lat": 28.61, "lon": 77.20},
            {"name": "Bangalore SEZ", "lat": 12.97, "lon": 77.59},
            {"name": "Kolkata Hub", "lat": 22.57, "lon": 88.36},
            {"name": "Chennai Port", "lat": 13.08, "lon": 80.27},
            {"name": "Hyderabad Hitech", "lat": 17.38, "lon": 78.48},
            {"name": "Pune Smart City", "lat": 18.52, "lon": 73.85},
            {"name": "Ahmedabad West", "lat": 23.02, "lon": 72.57},
            {"name": "Jaipur North", "lat": 26.91, "lon": 75.78},
            {"name": "Surat Industrial", "lat": 21.17, "lon": 72.83}
        ]
        for z in default_zones:
            add_zone(z['name'], z['lat'], z['lon'])
        print(f"✅ Successfully seeded {len(default_zones)} default zones.")

def toggle_zone_featured(zone_id):
    """Pins or unpins a zone for the dashboard view"""
    conn = sqlite3.connect(DB_NAME)
    current = conn.execute("SELECT featured FROM zones WHERE id = ?", (zone_id,)).fetchone()[0]
    
    if current == 0: 
        count = conn.execute("SELECT COUNT(*) FROM zones WHERE featured = 1").fetchone()[0]
        if count >= 5:
            conn.close()
            return False 
            
    conn.execute("UPDATE zones SET featured = 1 - featured WHERE id = ?", (zone_id,))
    conn.commit()
    conn.close()
    return True

def add_zone(name, lat, lon):
    """Inserts a new zone and auto-pins if under the limit"""
    conn = sqlite3.connect(DB_NAME)
    count = conn.execute("SELECT COUNT(*) FROM zones WHERE featured = 1").fetchone()[0]
    is_featured = 1 if count < 5 else 0
    conn.execute("INSERT INTO zones (name, lat, lon, featured) VALUES (?, ?, ?, ?)", (name, lat, lon, is_featured))
    conn.commit()
    conn.close()

def log_alert(zone_name, m, reason):
    """Saves a threshold breach incident to the history table"""
    conn = sqlite3.connect(DB_NAME)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("INSERT INTO alerts VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (timestamp, zone_name, m['temp'], m['humidity'], m['wind_speed'], m['aqi'], m['uv'], m['noise'], reason))
    conn.commit()
    conn.close()

def get_zones():
    """Retrieves all registered zones"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    zones = conn.execute("SELECT * FROM zones").fetchall()
    conn.close()
    return [dict(z) for z in zones]

def get_recent_alerts(n):
    """Retrieves the last N alerts for the logs table"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    res = conn.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (n,)).fetchall()
    conn.close()
    return [dict(r) for r in res]

def remove_zone(zone_id):
    """Deletes a zone by its ID"""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("DELETE FROM zones WHERE id = ?", (zone_id,))
    conn.commit()
    conn.close()

# Helper to save and load history
def save_chat_message(session_id, role, content):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("INSERT INTO chat_history (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                 (session_id, role, content, datetime.now()))
    conn.commit()
    conn.close()

def get_chat_history(session_id, limit=10):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    res = conn.execute("SELECT role, content FROM chat_history WHERE session_id = ? ORDER BY timestamp ASC LIMIT ?", 
                       (session_id, limit)).fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in res]

def get_alert_by_id(alert_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    # Use the primary key 'id' we added earlier
    res = conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
    conn.close()
    return dict(res) if res else None

def reset_and_reseed():
    """Wipes the entire database and restarts from scratch."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # 1. Drop all tables
    c.execute("DROP TABLE IF EXISTS zones")
    c.execute("DROP TABLE IF EXISTS alerts")
    c.execute("DROP TABLE IF EXISTS chat_history")
    conn.commit()
    conn.close()
    
    # 2. Re-initialize and Re-seed
    init_db()
    seed_zones()