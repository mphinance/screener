"""Launch the Scanline backend.

Run with: python run.py
Serves the API and static frontend on http://127.0.0.1:8000
"""

import uvicorn

HOST = "127.0.0.1"
PORT = 8000

if __name__ == "__main__":
    print(f"Scanline running at http://{HOST}:{PORT}")
    print(f"API docs at http://{HOST}:{PORT}/docs")
    uvicorn.run("backend.app:app", host=HOST, port=PORT, reload=False)
