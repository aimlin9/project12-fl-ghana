import subprocess
import sys
import os

def main():
    print("======================================================================")
    print("Starting Cross-School Federated Learning Server & Web Dashboard...")
    print("Please open http://127.0.0.1:8000 in your web browser.")
    print("To end the simulation server, press Ctrl+C.")
    print("======================================================================")
    
    # Set PYTHONPATH to root directory to allow local imports
    os.environ["PYTHONPATH"] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    python_exe = sys.executable
    server_path = os.path.join("server", "main.py")
    
    try:
        subprocess.run([python_exe, server_path], check=True)
    except KeyboardInterrupt:
        print("\nSimulation server stopped by user.")
    except Exception as e:
        print(f"Error starting simulation server: {e}")

if __name__ == "__main__":
    main()
