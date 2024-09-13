#import os
import pickle
import time
import requests
import pandas as pd
from datetime import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from requests_oauthlib import OAuth2Session
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Configuration for market hours
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 16
TIMEZONE = 'America/New_York'

# Schwab OAuth 2.0 setup
SCHWAB_AUTH_URL = 'https://www.schwab.com/oauth2/authorize'  # Placeholder, adjust according to Schwab API docs
SCHWAB_TOKEN_URL = 'https://www.schwab.com/oauth2/token'      # Placeholder
CLIENT_ID = os.getenv('SCHWAB_CLIENT_ID')
CLIENT_SECRET = os.getenv('SCHWAB_CLIENT_SECRET')
REDIRECT_URI = 'http://localhost:8000/callback'               # Placeholder, change this according to your app
SCOPE = ['some_scope']                                        # Placeholder for required scopes

# Directory for saving OAuth pickle file
PICKLE_FILE = 'schwab_oauth.pickle'

# Directory where HDF5 files will be saved
OUTPUT_DIR = 'options_data'

# Function to check if the current time is within market hours
def is_market_open():
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    if now.weekday() >= 5:  # Saturday, Sunday
        return False
    open_time = tz.localize(datetime(now.year, now.month, now.day, MARKET_OPEN_HOUR, MARKET_OPEN_MINUTE))
    close_time = tz.localize(datetime(now.year, now.month, now.day, MARKET_CLOSE_HOUR, 0))
    return open_time <= now <= close_time

# Function to authenticate using OAuth 2.0 and handle MFA
def authenticate():
    if os.path.exists(PICKLE_FILE):
        with open(PICKLE_FILE, 'rb') as f:
            oauth_session = pickle.load(f)
            # Check if token is expired
            if oauth_session.token['expires_at'] > time.time():
                return oauth_session
    
    # If no valid pickle file, perform authentication
    print("Performing OAuth authentication...")
    
    # Start the selenium webdriver
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Remove this option to see the browser window for debugging
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    oauth_session = OAuth2Session(client_id=CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPE)

    # Get the authorization URL
    authorization_url, state = oauth_session.authorization_url(SCHWAB_AUTH_URL)

    # Open the browser and navigate to the authorization URL
    driver.get(authorization_url)
    
    # Wait for user to manually log in and complete MFA (text verification code)
    while "callback" not in driver.current_url:
        time.sleep(1)

    # Extract the authorization response URL from the browser
    authorization_response = driver.current_url
    driver.quit()

    # Fetch the token
    oauth_session.fetch_token(SCHWAB_TOKEN_URL,
                              authorization_response=authorization_response,
                              client_secret=CLIENT_SECRET)

    # Save the session into a pickle file
    with open(PICKLE_FILE, 'wb') as f:
        pickle.dump(oauth_session, f)

    return oauth_session

# Function to get options chain data from Schwab API
def get_options_chain(symbol, oauth_session):
    try:
        url = f"https://api.schwab.com/options-chain/{symbol}"  # Placeholder
        headers = {
            'Authorization': f"Bearer {oauth_session.token['access_token']}",
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
        
        return response.json()  # Assuming the response is in JSON format
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None

# Function to save options chain data to HDF5
def save_to_hdf5(symbol, options_chain_data):
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = os.path.join(OUTPUT_DIR, f"{symbol}_options_data.h5")

    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Convert options data to pandas DataFrame
    try:
        options = options_chain_data['options']  # Assuming 'options' is the key for the option chain data
        df = pd.DataFrame(options)

        # Save to HDF5 format, appending to the file
        df.to_hdf(filename, key=symbol, mode='a', append=True, format='table', data_columns=True)
        print(f"Data saved for {symbol} at {timestamp}")
    
    except Exception as e:
        print(f"Error saving data for {symbol}: {e}")

# Function to read stock symbols from a text file
def read_symbols(file_path):
    try:
        with open(file_path, 'r') as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError as e:
        print(f"Error: {file_path} not found: {e}")
        return []

# Main function to collect and store options chain data
def collect_data(symbols, oauth_session):
    if is_market_open():
        for symbol in symbols:
            options_chain_data = get_options_chain(symbol, oauth_session)
            if options_chain_data:
                save_to_hdf5(symbol, options_chain_data)
            else:
                print(f"No data for {symbol}. Skipping...")
    else:
        print("Market is closed. Skipping data collection.")

# Scheduler function to run every 5 minutes during market hours
def schedule_data_collection(symbols, oauth_session):
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: collect_data(symbols, oauth_session), 'interval', minutes=5)
    scheduler.start()

    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

# Main script
if __name__ == "__main__":
    # Read the list of symbols from a text file
    symbols_file = 'symbols.txt'
    symbols = read_symbols(symbols_file)

    # Authenticate with Schwab and get the OAuth session
    oauth_session = authenticate()

    # Start collecting data only during market hours
    if not symbols:
        print("No symbols found in the input file.")
    else:
        print(f"Starting data collection for: {symbols}")
        schedule_data_collection(symbols, oauth_session)coded by chatgpt. needs testing

