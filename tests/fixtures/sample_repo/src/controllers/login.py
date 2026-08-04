"""Login controller exposing the authentication HTTP routes."""

from flask import Flask, request

from src.services.auth_service import authenticate

app = Flask(__name__)


@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    if authenticate(username, password):
        return {"status": "ok"}
    return {"status": "denied"}, 401


@app.route("/health")
def health():
    return {"status": "up"}
