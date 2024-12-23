import requests
from datetime import datetime, timezone

def validate_google_id_token(id_token, client_id):
    """
    Validates a Google ID token and checks if it is expired.

    :param id_token: The Google ID token to validate.
    :param client_id: Your Google app's client ID.
    :return: A dictionary containing the status, user info, and expiration info.
    """
    try:
        # Call Google API to validate the token
        response = requests.get('https://oauth2.googleapis.com/tokeninfo', params={'id_token': id_token})
        if response.status_code != 200:
            return {"status": "error", "message": "Invalid token", "details": response.json()}

        data = response.json()

        # Check the audience
        if data.get("aud") != client_id:
            return {"status": "error", "message": "Audience mismatch", "details": data}

        # Check token expiration
        exp_timestamp = int(data.get("exp", 0))
        exp_time = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        current_time = datetime.now(timezone.utc)

        if exp_time > current_time:
            return {
                "status": "valid",
                "message": "Token is valid",
                "user_info": data,
                "expires_at": exp_time,
            }
        else:
            return {
                "status": "expired",
                "message": "Token is expired",
                "user_info": data,
                "expired_at": exp_time,
            }
    except Exception as e:
        return {"status": "error", "message": "An error occurred", "details": str(e)}

