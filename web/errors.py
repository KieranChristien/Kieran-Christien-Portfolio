from flask import flash, redirect, request
from werkzeug.exceptions import RequestEntityTooLarge

def register_error_handlers(app):
    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(e):
        flash("Uploaded file is too large. Maximum file size is 16MB.", "error")
        return redirect(request.url)