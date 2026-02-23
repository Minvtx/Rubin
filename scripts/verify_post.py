import os
import tweepy
from datetime import datetime
from dotenv import load_dotenv

def verify_post():
    print("--- Twitter Write Permission Verification ---")
    load_dotenv()
    
    consumer_key = os.getenv("X_CONSUMER_KEY")
    consumer_secret = os.getenv("X_CONSUMER_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
    
    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        print("\n[ERROR] Credentials missing.")
        return

    try:
        client = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        test_text = f"Diagnostic test at {timestamp}. Rubin Agent is verifying signal flow."
        
        print(f"\nAttempting to post test tweet: '{test_text}'")
        response = client.create_tweet(text=test_text)
        
        if response.data and 'id' in response.data:
            print(f"\n[SUCCESS] Tweet posted successfully! ID: {response.data['id']}")
            print(f"View it here: https://x.com/i/web/status/{response.data['id']}")
        else:
            print("\n[ERROR] Tweet post attempt returned no data.")
            
    except Exception as e:
        print(f"\n[ERROR] Failed to post tweet: {e}")
        if "403" in str(e):
            print("\n[CRITICAL] 403 Forbidden. This usually means:")
            print("1. Your App is set to 'Read-only'. Go to developer.twitter.com -> App Settings -> User authentication settings and change App Permissions to 'Read and Write'.")
            print("2. After changing permissions, you MUST REGENERATE the Access Token and Secret.")
        elif "429" in str(e):
            print("\n[WARNING] Rate limit reached. Wait 15 minutes.")

if __name__ == "__main__":
    verify_post()
