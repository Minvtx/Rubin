import os
import tweepy
from dotenv import load_dotenv

def check_capabilities():
    load_dotenv()
    print("--- Twitter API Capabilities Check ---")
    
    client = tweepy.Client(
        consumer_key=os.getenv("X_CONSUMER_KEY"),
        consumer_secret=os.getenv("X_CONSUMER_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET")
    )
    
    try:
        # 1. Check self
        me = client.get_me()
        print(f"[OK] Can read self: @{me.data.username}")
        
        # 2. Check mentions (Self ID)
        try:
            mentions = client.get_users_mentions(id=me.data.id, max_results=5)
            print(f"[OK] Can read mentions.")
        except Exception as e:
            print(f"[FAIL] Cannot read mentions: {e}")
            
        # 3. Check another user (e.g., @mykemykelson)
        target_username = "mykemykelson"
        try:
            user = client.get_user(username=target_username)
            if user.data:
                print(f"[OK] Can lookup user @{target_username} (ID: {user.data.id})")
                # Try reading their tweets
                tweets = client.get_users_tweets(id=user.data.id, max_results=5)
                print(f"[OK] Can read tweets from @{target_username}")
            else:
                print(f"[FAIL] User @{target_username} not found or invisible.")
        except Exception as e:
            print(f"[FAIL] Cannot read tweets from others: {e}")

    except Exception as e:
        print(f"[ERROR] Basic 'get_me' failed: {e}")

if __name__ == "__main__":
    check_capabilities()
