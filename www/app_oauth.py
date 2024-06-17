import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError

def create_credentials(session_info):
    """Create credentials from session data."""
    return Credentials(
        token=session_info['token'],
        refresh_token=session_info['refresh_token'],
        token_uri=session_info['token_uri'],
        client_id=session_info['client_id'],
        client_secret=session_info['client_secret'],
        scopes=session_info['scopes']
    )

def refresh_credentials_if_expired(credentials):
    """Refresh the credentials if expired."""
    if credentials.expired:
        request = google.auth.transport.requests.Request()
        try:
            credentials.refresh(request)
            print("Token refreshed successfully.")
            return credentials
        except RefreshError:
            print("Failed to refresh token.")
            return None
    return credentials
