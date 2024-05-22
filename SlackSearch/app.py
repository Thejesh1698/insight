import os
from flask import Flask, jsonify, request
from slack_bolt import App
import xml.etree.ElementTree as ET
from slack_bolt.adapter.flask import SlackRequestHandler
from googleapiclient.discovery import build
from TokenManager import TokenManager

import numpy as np
from anthropic import Anthropic
parent_folder = './Recommendations/slackSearch/'
tree = ET.parse(parent_folder + '/conf/application.run.xml')
root = tree.getroot()
envs_element = root.find('./configuration/envs')
for variable in envs_element.findall('env'):
    name = variable.get('name')
    value = variable.get('value')
    os.environ[name] = value
# Initialize the Flask app
app = Flask(__name__)


# Initialize the Slack app
slack_app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
)

# Initialize the TokenManager
token_manager = TokenManager(
    client_secret_path="client_secret.json",
    scopes=["https://www.googleapis.com/auth/drive.readonly"],
    db_credentials={
        "host": os.environ.get("DB_HOST"),
        "database": os.environ.get("DB_NAME"),
        "user": os.environ.get("DB_USER"),
        "password": os.environ.get("DB_PASSWORD"),
    },
)

# Slack command handler
@slack_app.command("/fetch-gdocs")
def fetch_gdocs(ack, body, respond):
    ack()

    user_id = body["user_id"]
    access_token = token_manager.validate_token(user_id)

    if access_token:
        try:
            drive_service = build('drive', 'v3', credentials=access_token)
            results = drive_service.files().list(
                fields="nextPageToken, files(id, name, mimeType)",
                pageSize=100,
                spaces='drive',
                q="mimeType='application/vnd.google-apps.document'"
            ).execute()
            items = results.get('files', [])

            if not items:
                respond("No Google Docs found.")
            else:
                doc_list = [f"{item['name']} ({item['mimeType']})" for item in items]
                respond("\n".join(doc_list))
        except Exception as e:
            respond(f"An error occurred: {str(e)}")
    else:
        auth_url = token_manager.get_auth_url()
        respond(f"Please visit the following URL to authorize access to your Google Drive: {auth_url}")


# Slack OAuth flow handler
@app.route("/slack/oauth", methods=["GET"])
def slack_oauth():
    code = request.args.get("code")
    user_id = request.args.get("state")
    if code and user_id:
        token_manager.exchange_code_for_tokens(code, user_id)
        return "Authorization successful! You can now use the /fetch-gdocs command in Slack."
    else:
        return "Authorization failed."

# Mount the Slack app
handler = SlackRequestHandler(slack_app)


# Start the Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)