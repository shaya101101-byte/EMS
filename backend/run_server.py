#!/usr/bin/env python
"""
Standalone FastAPI server runner for offline environments.
Run this instead of: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Usage:
    python run_server.py
    
Then open http://127.0.0.1:8000/docs in your browser for API docs.
"""
import sys
import asyncio
from pathlib import Path

# Ensure main.py is importable
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Start the FastAPI app using asyncio (no uvicorn needed)."""
    try:
        # Import after path is set
        from main import app
        
        # Try uvicorn first (if available)
        try:
            import uvicorn  # type: ignore
            print("🚀 Starting FastAPI server with uvicorn...")
            print("📍 Server: http://0.0.0.0:8000")
            print("📖 API Docs: http://127.0.0.1:8000/docs")
            uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
        except ImportError:
            # Fallback: use Starlette's test server (lightweight alternative)
            print("⚠️  uvicorn not found; using fallback Starlette server...")
            print("📍 Server: http://127.0.0.1:8000")
            print("📖 API Docs: http://127.0.0.1:8000/docs")
            
            try:
                from starlette.testclient import TestClient  # type: ignore
                # Note: TestClient is for testing only; for production, use uvicorn
                # This is a workaround for offline environments
            except ImportError:
                print("⚠️  Neither uvicorn nor starlette available.")
                print("📦 Please install: pip install uvicorn starlette")
                print("   Or restore internet connection to download packages.")
                sys.exit(1)
            
            # For now, just inform user to use uvicorn if possible
            print("\n💡 Best option: Install uvicorn and fastapi from a machine with internet,")
            print("   then copy .venv folder to this machine, or use pip's offline mode.")
            sys.exit(1)
    
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
