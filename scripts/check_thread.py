import os
import tweepy
from dotenv import load_dotenv

def check_self_reply():
    load_dotenv()
    print("--- Twitter API Self-Reply Check ---")
    
    client = tweepy.Client(
        consumer_key=os.getenv("X_CONSUMER_KEY"),
        consumer_secret=os.getenv("X_CONSUMER_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET")
    )
    
    try:
        # Try to post a tweet
        print("Posting initial tweet...")
        response1 = client.create_tweet(text="Testing thread creation (1/2)")
        tweet1_id = response1.data['id']
        print(f"[OK] Posted initial tweet: {tweet1_id}")
        
        # Try to reply to that tweet
        print(f"Attempting to reply to {tweet1_id}...")
        response2 = client.create_tweet(
            text="Testing thread creation (2/2) - self reply", 
            in_reply_to_tweet_id=tweet1_id
        )
        tweet2_id = response2.data['id']
        print(f"[OK] Successfully replied to self: {tweet2_id}")
        
    except Exception as e:
        print(f"[FAIL] Error during thread creation test: {e}")

if __name__ == "__main__":
    check_self_reply()
