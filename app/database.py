import sqlite3
from datetime import datetime

DB_NAME = "data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Table for zones
    c.execute('''CREATE TABLE IF NOT EXISTS zones 
                 (id INTEGER PRIMARY KEY, name TEXT, lat REAL, lon REAL)''')
    # Table for alert logs
    c.execute('''CREATE TABLE IF NOT EXISTS alerts 
                 (id INTEGER PRIMARY KEY, timestamp TEXT, zone_name TEXT, 
                  temp REAL, humidity REAL, wind REAL, aqi INTEGER, uv REAL, noise REAL, reason TEXT)''')
    conn.commit()
    conn.close()

def add_zone(name, lat, lon):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("INSERT INTO zones (name, lat, lon) VALUES (?, ?, ?)", (name, lat, lon))
    conn.commit()
    conn.close()

def log_alert(zone_name, m, reason):
    conn = sqlite3.connect(DB_NAME)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("INSERT INTO alerts VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (timestamp, zone_name, m['temp'], m['humidity'], 
               m['wind'], m['aqi'], m['uv'], m['noise'], reason))
    conn.commit()
    conn.close()