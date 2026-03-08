import os
from dotenv import load_dotenv
load_dotenv()  # loads .env file locally; no effect in Railway (env vars set directly)

from flask import Flask, request, session, flash, redirect, url_for
from routes import init_routes
from db import is_branch_active

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "liceo_secret_key_dev")

@app.before_request
def check_branch_active_status():
    if request.method in ['POST', 'PUT', 'DELETE']:
        if request.endpoint and (request.endpoint.startswith('auth.') or request.endpoint.startswith('super_admin.')):
            return
            
        branch_id = session.get('branch_id')
        if branch_id:
            if not is_branch_active(branch_id):
                flash("This branch is currently deactivated. You cannot perform this action.", "error")
                # Need to return a response to block the request. Redirect back or to a safe page.
                # Assuming most forms are submitted from a GET page, request.referrer usually works.
                # Otherwise, fallback to a safe default like the user's dashboard based on role.
                role = session.get('role')
                fallback = '/'
                if role == 'branch_admin':
                    fallback = url_for('branch_admin.dashboard')
                elif role == 'cashier':
                    fallback = url_for('cashier.dashboard')
                elif role == 'registrar':
                    fallback = url_for('registrar.dashboard')
                elif role == 'teacher':
                    fallback = url_for('teacher.teacher_dashboard')
                elif role == 'student':
                    fallback = url_for('student_portal.dashboard')
                
                return redirect(request.referrer or fallback)

@app.context_processor
def inject_is_branch_active():
    branch_id = session.get('branch_id')
    is_active = True
    if branch_id and session.get('role') != 'super_admin':
        is_active = is_branch_active(branch_id)
    return dict(is_branch_active_status=is_active)

# initialize all routes (register blueprints + uploads route)
init_routes(app)

if __name__ == "__main__":
    app.run(debug=True)

