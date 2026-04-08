from app import create_app
from extensions import db, socketio
import os

app = create_app()

with app.app_context():
    db.create_all()
    print("[OK] Database Created Successfully")

if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False,
        allow_unsafe_werkzeug=True
    )
