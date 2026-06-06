import argparse
import flwr as fl
import time
import socket
from client.client import StudentFLClient

def main():
    parser = argparse.ArgumentParser(description="Run simulated school FL client")
    parser.add_argument(
        "--school", 
        type=str, 
        required=True, 
        choices=["school_alpha", "school_beta", "school_gamma"], 
        help="Name of the school node"
    )
    parser.add_argument(
        "--server", 
        type=str, 
        default="127.0.0.1:8088", 
        help="Flower server address"
    )
    args = parser.parse_args()
    
    # Parse host and port
    host, port_str = args.server.split(":")
    port = int(port_str)
    
    print(f"[{args.school}] Waiting for Flower server at {host}:{port} to start...")
    
    # Wait for the server port to open
    while True:
        try:
            with socket.create_connection((host, port), timeout=2.0):
                print(f"[{args.school}] Flower server detected! Initiating client connection...")
                break
        except (ConnectionRefusedError, socket.timeout, OSError):
            time.sleep(2.0)
            
    # Initialize and start the client
    client = StudentFLClient(args.school)
    
    # Loop connection to allow running multiple simulations without restarting containers
    while True:
        try:
            fl.client.start_numpy_client(
                server_address=args.server,
                client=client
            )
            print(f"[{args.school}] Round session completed successfully. Re-waiting for next session...")
        except Exception as e:
            print(f"[{args.school}] Client connection ended or server stopped: {e}")
            
        # Wait for server to reappear before attempting reconnect
        time.sleep(3.0)
        while True:
            try:
                with socket.create_connection((host, port), timeout=2.0):
                    break
            except (ConnectionRefusedError, socket.timeout, OSError):
                time.sleep(2.0)

if __name__ == "__main__":
    main()
