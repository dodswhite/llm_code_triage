import os
import pickle
import time
from requests_oauthlib import OAuth2Session
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Schwab OAuth 2.0 setup (replace with your actual details)
SCHWAB_AUTH_URL = 'https://www.schwab.com/oauth2/authorize'  # Placeholder, adjust according to Schwab API docs
SCHWAB_TOKEN_URL = 'https://www.schwab.com/oauth2/token'      # Placeholder
CLIENT_ID = os.getenv('SCHWAB_CLIENT_ID')
CLIENT_SECRET = os.getenv('SCHWAB_CLIENT_SECRET')
REDIRECT_URI = 'http://localhost:8000/callback'               # Placeholder, change this according to your app
SCOPE = ['some_scope']                                        # Placeholder for required scopes

# Directory for saving OAuth pickle file
PICKLE_FILE = 'schwab_oauth.pickle'

# Function to perform OAuth 2.0 authentication
def authenticate():
    # Start the selenium webdriver (Chrome)
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Optional: Remove this line if you want to see the browser window for debugging
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    oauth_session = OAuth2Session(client_id=CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPE)

    # Get the authorization URL
    authorization_url, state = oauth_session.authorization_url(SCHWAB_AUTH_URL)

    # Open the browser and navigate to the authorization URL
    print(f"Opening browser for authorization: {authorization_url}")
    driver.get(authorization_url)
    
    # Wait for user to manually log in and complete MFA (text verification code)
    while "callback" not in driver.current_url:
        time.sleep(1)

    # Extract the authorization response URL from the browser
    authorization_response = driver.current_url
    driver.quit()

    # Fetch the token
    token = oauth_session.fetch_token(SCHWAB_TOKEN_URL,
                                      authorization_response=authorization_response,
                                      client_secret=CLIENT_SECRET)

    # Save the session into a pickle file
    with open(PICKLE_FILE, 'wb') as f:
        pickle.dump(oauth_session, f)
    
    print(f"Authentication successful. OAuth session saved in {PICKLE_FILE}")

if __name__ == "__main__":
    authenticate()