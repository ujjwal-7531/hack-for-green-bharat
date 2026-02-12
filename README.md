# 🌍 EcoWatcher | Green Bharat Hackathon

**Project Goal:** A real-time environmental monitoring system that tracks critical parameters across multiple zones to ensure public safety and environmental compliance.

---

## 🚀 Presentation Features (Feb 16th Prototype)
- **Synthetic Data Engine:** Simulates real-world sensor data for Temperature, Humidity, Wind Speed, AQI, UV Exposure, and Noise Levels.
- **Dynamic Alerting:** Automatically detects and logs incidents when parameters cross safety thresholds.
- **Geospatial Visualization:** Integrated map widget showing zone distribution.
- **Real-time Toasts:** Instant UI notifications when a simulated "incident" occurs.
- **Persistent Logging:** Every alert is stored in a SQLite database with a precise timestamp and environmental snapshot.

---

## 🛠️ Tech Stack
- **Backend:** Python 3.x, FastAPI
- **Database:** SQLite3 (Zero-config, modular)
- **Frontend:** Jinja2 Templates, Tailwind CSS (for modern UI)
- **Monitoring:** JavaScript (Asynchronous background polling)

---

Follow these steps to get the project running on your local machine:

### 1. Clone the repository
```bash
git clone https://github.com/ujjwal-7531/hack-for-green-bharat.git
cd EcoWatcher
```

### 2. Setup Virtual Environment
```bash
# Create the environment named 'myenv'
python -m venv myenv

# Activate the environment
# Windows:
myenv\Scripts\activate
# Mac/Linux:
source myenv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python main.py
```