import os
import tweepy
from dotenv import load_dotenv

def test_twitter_auth():
    print("--- Twitter API Diagnostic Script ---")
    load_dotenv()
    
    consumer_key = os.getenv("X_CONSUMER_KEY")
    consumer_secret = os.getenv("X_CONSUMER_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
    
    print(f"X_CONSUMER_KEY: {'[SET]' if consumer_key else '[MISSING]'}")
    print(f"X_CONSUMER_SECRET: {'[SET]' if consumer_secret else '[MISSING]'}")
    print(f"X_ACCESS_TOKEN: {'[SET]' if access_token else '[MISSING]'}")
    print(f"X_ACCESS_TOKEN_SECRET: {'[SET]' if access_token_secret else '[MISSING]'}")
    
    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        print("\n[ERROR] One or more credentials are missing in .env")
        return

    try:
        print("\nAttempting to authenticate...")
        client = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # In V2, we can use get_me() to verify credentials
        me = client.get_me()
        if me and me.data:
            print(f"\n[SUCCESS] Authenticated as: @{me.data.username} (ID: {me.data.id})")
            print("Permissions seem correct for reading profile.")
            print("\nNOTE: To verify WRITE permissions, you would need to attempt a manual tweet.")
            print("Check your App settings at developer.twitter.com to ensure 'Read and Write' is enabled.")
        else:
            print("\n[ERROR] Authentication succeeded but could not retrieve user data.")
            
    except Exception as e:
        print(f"\n[ERROR] Failed to authenticate or communicate with X API: {e}")
        if "403" in str(e):
            print("Tip: 403 usually means your App's permissions are limited (e.g., Read-only) or the endpoint is not available for your plan.")
        elif "401" in str(e):
            print("Tip: 401 usually means your API Keys or Access Tokens are incorrect.")

if __name__ == "__main__":
    test_twitter_auth()
