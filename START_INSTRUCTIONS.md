**How to start backend and frontend (Windows)**

- **One-step (recommended)**: double-click `start_servers.bat` in the repository root. This opens two command windows: backend (FastAPI) and frontend (Node static server).

- **PowerShell**: run the PowerShell helper which opens two PowerShell windows:
  - `.\\start_servers.ps1`

- **Manual commands** (if you prefer separate terminals):
  - Backend (from repo root):
    - `cd backend`
    - `python run_server.py`
    - Or with uvicorn explicitly: `uvicorn main:app --host 127.0.0.1 --port 8000`
  - Frontend (from repo root):
    - `cd 7_frontend_dashboard`
    - `npm install` (first time only)
    - `npm start`  OR `node server.js`

**Important notes / root causes for errors you saw**
- `0.0.0.0` is a bind address, not a client URL. In a browser use `http://localhost:8000` or `http://127.0.0.1:8000`. Using `http://0.0.0.0:8000` in your browser causes ERR_ADDRESS_INVALID.
- `npm start` and `npm install` run in the current working directory. If you run them from the wrong folder (for example from `backend`), npm will look for `package.json` in that folder and fail. Always `cd` into `7_frontend_dashboard` before running npm commands.
- Starting both servers in the same shell without keeping them running (or starting them incorrectly) can cause one process to exit or block the shell. The helper scripts open separate windows so both remain running.
- When automation/tools launch servers from other working directories, they may start and then immediately exit if the current working directory is wrong or required resources are missing.

**Quick checks**
- Verify backend listening: `Test-NetConnection -ComputerName localhost -Port 8000` (PowerShell) or open `http://localhost:8000/docs` in browser.
- Verify frontend listening: open `http://localhost:3000` in browser.
