"""Seabot unified process runner (Offline resilient)."""
import subprocess
import sys
import os
import time
import urllib.request
import urllib.error

PYTHON_EXE = r"C:\Users\Sunit Kamble\AppData\Local\Programs\Python\Python311\python.exe"
NODE_EXE = r"C:\Users\Sunit Kamble\.gemini\antigravity\scratch\node-v20.18.0-win-x64\node.exe"
OLLAMA_EXE = r"C:\Users\Sunit Kamble\AppData\Local\Programs\Ollama\ollama.exe"

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
VITE_BIN = os.path.join(FRONTEND_DIR, "node_modules", "vite", "bin", "vite.js")


def check_ollama():
    """Verify Ollama is reachable; start it if not."""
    print("[1/3] Checking Ollama service...")
    try:
        req = urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2)
        if req.status == 200:
            print("  ✓ Ollama is already active on http://127.0.0.1:11434")
            return None
    except Exception:
        pass

    print("  Starting Ollama daemon in background...")
    proc = subprocess.Popen([OLLAMA_EXE, "serve"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    for _ in range(15):
        time.sleep(1)
        try:
            req = urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2)
            if req.status == 200:
                print("  ✓ Ollama started successfully!")
                return proc
        except Exception:
            pass
    print("  ⚠ Ollama launched, continuing...")
    return proc


def free_port(port: int):
    """Kill any zombie processes listening on port."""
    if os.name == "nt":
        try:
            cmd = f'powershell -Command "Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }}"'
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


def main():
    print("=======================================================")
    print("⚓ Launching Seabot (Air-Gapped Maritime AI System)")
    print("=======================================================\n")

    ollama_proc = check_ollama()

    # Free ports if occupied
    free_port(8001)
    free_port(3000)

    print("\n[2/3] Starting Seabot backend on port 8001...")
    backend_proc = subprocess.Popen(
        [PYTHON_EXE, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8001"],
        cwd=BACKEND_DIR,
    )

    print("[3/3] Starting Seabot frontend on port 3000...")
    frontend_proc = subprocess.Popen(
        [NODE_EXE, VITE_BIN, "--port", "3000", "--host", "0.0.0.0"],
        cwd=FRONTEND_DIR,
    )

    print("\n=======================================================")
    print("⚓ Seabot is LIVE & 100% OFFLINE READY!")
    print("   Browser Access: http://127.0.0.1:3000")
    print("   (Note: Use 127.0.0.1:3000 when Wi-Fi is disconnected)")
    print("   Backend API:    http://127.0.0.1:8001/api")
    print("=======================================================\n")

    try:
        while True:
            b_code = backend_proc.poll()
            f_code = frontend_proc.poll()
            if b_code is not None:
                print(f"Backend process exited with code {b_code}!")
                break
            if f_code is not None:
                print(f"Frontend process exited with code {f_code}!")
                break
            time.sleep(1)
    finally:
        print("Shutting down processes...")
        backend_proc.terminate()
        frontend_proc.terminate()
        if ollama_proc is not None:
            ollama_proc.terminate()


if __name__ == "__main__":
    main()
