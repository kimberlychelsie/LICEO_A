import os
from dotenv import load_dotenv
load_dotenv()  # loads .env file locally; no effect in Railway (env vars set directly)

from flask import Flask
from routes import init_routes

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "liceo_secret_key_dev")

# initialize all routes (register blueprints + uploads route)
init_routes(app)

if __name__ == "__main__":
    app.run(debug=True)

