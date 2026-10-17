"""Start Misstep:  python app.py   ->   http://localhost:7860"""

import os
import webbrowser

import uvicorn

from misstep.server import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f"Misstep çalışıyor: http://localhost:{port}")
    if not os.environ.get("MISSTEP_NO_BROWSER"):
        webbrowser.open(f"http://localhost:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
