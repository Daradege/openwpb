"""OpenWPB project by Ali Safamanesh (daradege)"""
from typing import Dict
import os
import json
from flask import Flask, render_template, session, redirect, url_for, request, jsonify
import requests
import pyrobale

URL = "https://tapi.bale.ai/bot"


def _make_request(
        token: str,
        request_method: str,
        method: str = "post",
        **params) -> Dict:
    """Make HTTP request to Bale API."""
    try:
        response = requests.request(
            method.lower(),
            f"{URL}{token}/{request_method}",
            **params
        )
        print(response.content)

        if response.status_code == 200:
            return response.json() if response.content else {'ok': True}
        else:
            print(response.content, response.status_code)
            try:
                return response.json()
            except BaseException:
                return response.content
    except (requests.exceptions.JSONDecodeError, requests.exceptions.RequestException) as e:
        print(f"Error: {str(e)}")
        return


def correct_token(token: str) -> bool:
    """Verify if the token is valid."""
    return _make_request(token, "getMe", method="get").get('ok', False)


app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))
print(app.secret_key)


@app.route('/')
def index_route():
    if "token" not in session:
        return render_template('login.html')

    if not correct_token(session['token']):
        session.pop('token', None)
        return render_template('login.html', error='Invalid token')
    client = pyrobale.Client(session['token'])
    return render_template('index.html', token=session['token'], bot=client)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        token = request.form.get('token')
        if token and correct_token(token):
            session['token'] = token
            return redirect(url_for('index_route'))
        return render_template('login.html', error='Invalid token')
    return render_template('login.html')


@app.route("/manage/<method>/<token>", methods=['POST'])
def manage(method: str, token: str):
    method = method.lower()
    if method != 'sendmessage':
        return 'Invalid method', 400

    try:
        to_id = int(request.form.get('to_id', ''))
        reply_to = int(request.form.get('reply_to')
                       ) if request.form.get('reply_to') else None
        message = request.form.get('text', '')
        components = request.form.get('components')
        keyboard = json.loads(components) if components else None

        data = {
            "chat_id": to_id,
            "text": message,
            "parse_mode": "HTML"
        }
        if keyboard:
            if isinstance(
                    keyboard, dict) and (
                    'inline_keyboard' in keyboard or 'keyboard' in keyboard):
                data["reply_markup"] = json.dumps(keyboard)
            else:
                return jsonify(
                    {'ok': False, 'error': 'Invalid keyboard format'})
        if reply_to:
            data["reply_to_message_id"] = reply_to

        print(data)
        response = _make_request(token, "sendMessage", data=data)
        r = response.get('ok', False)
        if r:
            return jsonify(response), 200
        return jsonify(response), 400

    except (ValueError, json.JSONDecodeError) as e:
        print(f"Error in manage route: {str(e)}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route("/manage/media/<method>/<token>", methods=['POST'])
def manage_media(method: str, token: str):
    try:
        to_id = int(request.form.get('to_id', ''))
        reply_to = int(request.form.get('reply_to')
                       ) if request.form.get('reply_to') else None
        caption = request.form.get('caption', '')
        components = request.form.get('components')
        keyboard = json.loads(components) if components else None
        file = request.files.get('media')

        if not file:
            return jsonify({'ok': False, 'error': 'No file provided'})

        content_type = file.content_type
        if content_type.startswith('image/'):
            method = 'sendPhoto'
        elif content_type.startswith('video/'):
            method = 'sendVideo'
        else:
            method = 'sendDocument'

        data = {
            "chat_id": to_id,
            "caption": caption,
            "parse_mode": "HTML"
        }

        if keyboard:
            if isinstance(
                    keyboard, dict) and (
                    'inline_keyboard' in keyboard or 'keyboard' in keyboard):
                data["reply_markup"] = json.dumps(keyboard)

        if reply_to:
            data["reply_to_message_id"] = reply_to

        files = {
            method.lower().replace('send', ''): file
        }

        response = _make_request(token, method, files=files, data=data)
        r = response.get('ok', False)
        if r:
            return jsonify(response), 200
        return jsonify(response), 400

    except (ValueError, json.JSONDecodeError) as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('token', None)
    return redirect(url_for('index_route'))
