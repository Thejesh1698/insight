import os
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import psycopg2
import httplib2
import requests


class TokenManager:
    def __init__(self):
        pass

    @staticmethod
    def refresh_access_token(refresh_token, client_id, client_secret):
        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            'refresh_token': refresh_token,
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'refresh_token'
        }
        response = requests.post(token_url, data=payload)
        if response.status_code == 200:
            return response.json().get('access_token')
        else:
            print(f"Error refreshing access token: {response.json()}")
            return None


    def get_auth_url(self):
        auth_url, _ = self.flow.authorization_url(prompt="consent")
        return auth_url

    def exchange_code_for_tokens(self, code, user_id):
        creds = self.flow.fetch_token(code=code)
        access_token = creds.token
        refresh_token = creds.refresh_token
        token_expiry = creds.expiry

        self.store_tokens(user_id, access_token, refresh_token, token_expiry)

    def store_tokens(self, user_id, access_token, refresh_token, token_expiry):
        conn = psycopg2.connect(**self.db_credentials)
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO user_auth_tokens (user_id, access_token, refresh_token, token_expiry) "
            "VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (user_id) DO UPDATE SET "
            "access_token = %s, refresh_token = %s, token_expiry = %s",
            (user_id, access_token, refresh_token, token_expiry, access_token, refresh_token, token_expiry),
        )

        conn.commit()
        cur.close()
        conn.close()

    def get_tokens(self, user_id):
        conn = psycopg2.connect(**self.db_credentials)
        cur = conn.cursor()

        cur.execute(
            "SELECT access_token, refresh_token, token_expiry FROM user_auth_tokens WHERE user_id = %s",
            (user_id,),
        )
        result = cur.fetchone()

        cur.close()
        conn.close()

        if result:
            access_token, refresh_token, token_expiry = result
            return access_token, refresh_token, token_expiry
        else:
            return None, None, None

    def refresh_tokens(self, user_id):
        access_token, refresh_token, token_expiry = self.get_tokens(user_id)

        if refresh_token:
            creds = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.flow.client_config["client_id"],
                client_secret=self.flow.client_config["client_secret"],
            )

            creds.refresh(Request())  # Use Request() instead of httplib2.Http()

            new_access_token = creds.token
            new_token_expiry = creds.expiry

            self.store_tokens(user_id, new_access_token, refresh_token, new_token_expiry)

            return new_access_token, new_token_expiry

        return None, None

    def validate_token(self, user_id):
        access_token, refresh_token, token_expiry = self.get_tokens(user_id)

        if token_expiry and token_expiry > datetime.now():
            return access_token

        new_access_token, new_token_expiry = self.refresh_tokens(user_id)

        if new_access_token:
            return new_access_token

        return None

