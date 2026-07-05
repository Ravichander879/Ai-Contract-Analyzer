import os
import sys
import subprocess
import time
from dotenv import load_dotenv

load_dotenv()

def start_services():
    """
    Spawns the FastAPI backend server and Streamlit frontend application concurrently.
    """
    port = os.getenv("PORT", "8000")
    backend_url = f"http://127.0.0.1:{port}"
    os.environ["BACKEND_URL"] = backend_url
    
    print("=" * 60)
    print("🚀 AI CONTRACT ANALYZER MVP RUNNER 🚀")
    print("=" * 60)
    
    # 1. Start FastAPI backend
    print(f"[*] Starting FastAPI backend on {backend_url}...")
    backend_cmd = [
        sys.executable, "-m", "uvicorn", "backend.app:app", 
        "--host", "127.0.0.1", "--port", port
    ]
    
    # We pipe outputs nicely or print them
    backend_proc = subprocess.Popen(
        backend_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Give uvicorn a brief moment to boot and verify it started
    print("[*] Waiting for backend to initialize...")
    time.sleep(3)
    
    if backend_proc.poll() is not None:
        print("[!] FastAPI backend failed to start! Output logs:")
        print(backend_proc.stdout.read())
        sys.exit(1)
        
    print("[OK] Backend started successfully.")
    
    # 2. Start Streamlit frontend
    print("[*] Starting Streamlit frontend on http://localhost:8501...")
    frontend_cmd = [
        sys.executable, "-m", "streamlit", "run", "frontend/app.py", 
        "--server.port", "8501", "--server.headless", "false"
    ]
    
    frontend_proc = subprocess.Popen(
        frontend_cmd
    )
    
    print("\n" + "=" * 60)
    print("AI Contract Analyzer is running!")
    print("• Backend API Docs: http://localhost:8000/docs")
    print("• Streamlit UI:     http://localhost:8501")
    print("Press Ctrl+C to terminate both servers.")
    print("=" * 60 + "\n")
    
    try:
        # Keep runner alive and log backend output
        while True:
            # Check backend output to print warning logs if any
            line = backend_proc.stdout.readline()
            if line:
                print(f"[Backend] {line.strip()}")
                
            # If either process exits, terminate the other
            if backend_proc.poll() is not None:
                print("[!] Backend process exited unexpectedly.")
                break
            if frontend_proc.poll() is not None:
                print("[!] Frontend process exited.")
                break
                
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n[!] KeyboardInterrupt received. Stopping servers...")
    finally:
        # Graceful shutdown of child processes
        print("[*] Terminating processes...")
        backend_proc.terminate()
        frontend_proc.terminate()
        
        # Give them a moment to close, then kill if necessary
        time.sleep(1)
        if backend_proc.poll() is None:
            backend_proc.kill()
        if frontend_proc.poll() is None:
            frontend_proc.kill()
            
        print("[OK] Clean shutdown complete.")

if __name__ == "__main__":
    start_services()
