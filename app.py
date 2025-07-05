import os
import json
import hmac
import hashlib
from datetime import datetime, timezone
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'github_webhooks')
COLLECTION_NAME = os.environ.get('COLLECTION_NAME', 'actions')
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'your-webhook-secret')

# MongoDB connection
try:
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]
    logger.info("Connected to MongoDB successfully")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise

# Verify signature
def verify_signature(payload_body, signature_header):
    if not signature_header:
        logger.warning("Missing signature header")
        return False

    expected_signature = 'sha256=' + hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        payload_body,
        hashlib.sha256
    ).hexdigest()

    logger.info(f"Expected Signature: {expected_signature}")
    logger.info(f"Received Signature: {signature_header}")

    return hmac.compare_digest(expected_signature, signature_header)

# Format timestamp
def format_timestamp(timestamp_str):
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%d %B %Y - %I:%M %p UTC')
    except:
        return timestamp_str

# Extract event data
def extract_event_data(payload, event_type):
    try:
        if event_type == 'push':
            return {
                'author': payload['pusher']['name'],
                'action': 'push',
                'from_branch': None,
                'to_branch': payload['ref'].split('/')[-1],
                'timestamp': payload['head_commit']['timestamp'],
                'request_id': payload['head_commit']['id']
            }

        elif event_type == 'pull_request':
            pr = payload['pull_request']
            return {
                'author': pr['user']['login'],
                'action': 'pull_request',
                'from_branch': pr['head']['ref'],
                'to_branch': pr['base']['ref'],
                'timestamp': pr['created_at'],
                'request_id': str(pr['id'])
            }

        elif event_type == 'pull_request' and payload['action'] == 'closed' and payload['pull_request']['merged']:
            pr = payload['pull_request']
            return {
                'author': pr['merged_by']['login'] if pr['merged_by'] else pr['user']['login'],
                'action': 'merge',
                'from_branch': pr['head']['ref'],
                'to_branch': pr['base']['ref'],
                'timestamp': pr['merged_at'],
                'request_id': str(pr['id'])
            }

        return None
    except KeyError as e:
        logger.error(f"Missing key in payload: {e}")
        return None

# Serve index
@app.route('/')
def index():
    return render_template('index.html')

# Webhook route
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return "GET not supported on /webhook. Use POST from GitHub.", 405

    try:
        signature = request.headers.get('X-Hub-Signature-256')
        event_type = request.headers.get('X-GitHub-Event')

        if not verify_signature(request.data, signature):
            logger.warning("Invalid webhook signature")
            return jsonify({'error': 'Invalid signature'}), 403

        payload = request.get_json()
        if not payload:
            return jsonify({'error': 'Invalid JSON payload'}), 400

        logger.info(f"📥 Received {event_type} event")

        event_data = None

        if event_type == 'push':
            event_data = extract_event_data(payload, 'push')
        elif event_type == 'pull_request':
            if payload['action'] == 'closed' and payload['pull_request']['merged']:
                event_data = extract_event_data(payload, 'pull_request')
                if event_data:
                    event_data['action'] = 'merge'
            elif payload['action'] == 'opened':
                event_data = extract_event_data(payload, 'pull_request')

        if event_data:
            result = collection.insert_one(event_data)
            logger.info(f"Stored event with ID: {result.inserted_id}")
            return jsonify({
                'success': True,
                'message': f'{event_data["action"]} event stored successfully',
                'id': str(result.inserted_id)
            }), 200
        else:
            logger.info(f"ℹ️ Event {event_type} not processed")
            return jsonify({'message': 'Event not processed'}), 200

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Fetch events API
@app.route('/api/events', methods=['GET'])
def get_events():
    try:
        events = list(collection.find().sort('timestamp', -1).limit(50))

        formatted_events = []
        for event in events:
            event['_id'] = str(event['_id'])
            author = event['author']
            timestamp = format_timestamp(event['timestamp'])

            if event['action'] == 'push':
                event['display_message'] = f'"{author}" pushed to "{event["to_branch"]}" on {timestamp}'
            elif event['action'] == 'pull_request':
                event['display_message'] = f'"{author}" submitted a pull request from "{event["from_branch"]}" to "{event["to_branch"]}" on {timestamp}'
            elif event['action'] == 'merge':
                event['display_message'] = f'"{author}" merged branch "{event["from_branch"]}" to "{event["to_branch"]}" on {timestamp}'

            formatted_events.append(event)

        return jsonify({'success': True, 'events': formatted_events}), 200

    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        return jsonify({'error': 'Failed to fetch events'}), 500

# Health check
@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        client.admin.command('ping')
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500

# Run the app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)