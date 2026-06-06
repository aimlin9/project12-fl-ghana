import os
import json
import threading
import time
import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import flwr as fl

from server.strategy import telemetry_data, PaillierFedAvg
from client.client import StudentFLClient

app = FastAPI(title="Cross-School Federated Learning Dashboard")

class ConfigModel(BaseModel):
    use_dp: str
    use_paillier: str
    local_epochs: int
    lr: float
    total_rounds: int

# Route to serve the dashboard UI
@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard():
    template_path = os.path.join(os.path.dirname(__file__), "templates", "dashboard.html")
    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail="Dashboard template not found")
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return html_content

# Get telemetry data
@app.get("/api/telemetry")
def get_telemetry():
    return JSONResponse(content=telemetry_data)

# Update configuration
@app.post("/api/config")
def update_config(config: ConfigModel):
    if telemetry_data["simulation_running"]:
        raise HTTPException(status_code=400, detail="Cannot update configuration while simulation is running")
    
    telemetry_data["config"]["use_dp"] = config.use_dp
    telemetry_data["config"]["use_paillier"] = config.use_paillier
    telemetry_data["config"]["local_epochs"] = config.local_epochs
    telemetry_data["config"]["lr"] = config.lr
    telemetry_data["config"]["total_rounds"] = config.total_rounds
    return {"status": "success", "config": telemetry_data["config"]}

# Get client status
@app.get("/api/client/{school_name}/status")
def get_client_status(school_name: str):
    if school_name not in telemetry_data["clients"]:
        raise HTTPException(status_code=404, detail="School node not found")
    return {"status": telemetry_data["clients"][school_name]["status"]}

# Toggle client status (Online/Offline)
@app.post("/api/client/{school_name}/toggle")
def toggle_client_status(school_name: str):
    if school_name not in telemetry_data["clients"]:
        raise HTTPException(status_code=404, detail="School node not found")
    
    current_status = telemetry_data["clients"][school_name]["status"]
    if current_status == "Offline":
        # Turn online (idle)
        telemetry_data["clients"][school_name]["status"] = "Idle"
    else:
        # Turn offline
        telemetry_data["clients"][school_name]["status"] = "Offline"
        
    return {"status": "success", "client": school_name, "new_status": telemetry_data["clients"][school_name]["status"]}

# Helper function to run Flower Server and Clients in background
def run_fl_simulation():
    telemetry_data["simulation_running"] = True
    telemetry_data["rounds"] = []  # Clear previous simulation rounds
    
    # Initialize all non-offline clients to Idle status
    for school in telemetry_data["clients"]:
        if telemetry_data["clients"][school]["status"] not in ["Offline", "Idle"]:
            telemetry_data["clients"][school]["status"] = "Idle"
            
    print("[Simulation] Starting Flower server on port 8088...")
    strategy = PaillierFedAvg()
    
    def start_server_thread():
        try:
            fl.server.start_server(
                server_address="127.0.0.1:8088",
                config=fl.server.ServerConfig(num_rounds=int(telemetry_data["config"]["total_rounds"])),
                strategy=strategy
            )
        except Exception as e:
            print("[Simulation Server Error]", e)
            
    server_thread = threading.Thread(target=start_server_thread, daemon=True)
    server_thread.start()
    
    # Give the server a moment to start listening
    time.sleep(2.0)
    
    print("[Simulation] Launching clients...")
    client_threads = []
    
    def start_client_thread(school_name):
        try:
            # Client connects to local FL server
            client = StudentFLClient(school_name)
            fl.client.start_numpy_client(
                server_address="127.0.0.1:8088",
                client=client
            )
        except Exception as e:
            print(f"[Simulation Client Error - {school_name}]", e)
            # Update status to Offline / Failed
            if telemetry_data["clients"][school_name]["status"] != "Offline":
                telemetry_data["clients"][school_name]["status"] = "Failed"
                
    for school in telemetry_data["clients"]:
        # If client is set to Offline by the user, we DO NOT launch it!
        # This simulates a client that is shut down or has no connection.
        # But even if it is online, it might be toggled offline during execution, 
        # which is handled inside client.py's status checks!
        if telemetry_data["clients"][school]["status"] != "Offline":
            t = threading.Thread(target=start_client_thread, args=(school,), daemon=True)
            t.start()
            client_threads.append(t)
            
    # Wait for the server thread to finish (it finishes when rounds complete)
    server_thread.join()
    
    # Reset all statuses that are not Offline
    for school in telemetry_data["clients"]:
        if telemetry_data["clients"][school]["status"] != "Offline":
            telemetry_data["clients"][school]["status"] = "Offline"
            
    telemetry_data["simulation_running"] = False
    print("[Simulation] Ended.")

# Endpoint to start simulation
@app.post("/api/start")
def start_simulation(background_tasks: BackgroundTasks):
    if telemetry_data["simulation_running"]:
        raise HTTPException(status_code=400, detail="Simulation is already running")
        
    background_tasks.add_task(run_fl_simulation)
    return {"status": "started"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
