import json
import os
import time
import random
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import tweepy
except ImportError:
    tweepy = None

class RubinAgent:
    def __init__(self, config_path: str = "config.json", system_prompt_path: str = "system_prompt.md", seeds_path: str = "seeds.json"):
        self.config = self._load_config(config_path)
        self.system_prompt = self._load_file(system_prompt_path)
        self.seeds = self._load_json(seeds_path)
        
        # Initialize OpenAI Client
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if OpenAI and os.getenv("OPENAI_API_KEY") else None
        
        # Initialize X Client
        self.x_client = self._authenticate_x()

    def _load_config(self, path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_json(self, path: str) -> list:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"[WARN] {path} not found. Using default seeds.")
            return ["Silence", "Code", "Nature"]

    def _load_file(self, path: str) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _authenticate_x(self):
        """Authenticates with X API V2."""
        if not tweepy:
            print("[WARN] Tweepy not installed. Posting disabled.")
            return None
            
        consumer_key = os.getenv("X_CONSUMER_KEY")
        consumer_secret = os.getenv("X_CONSUMER_SECRET")
        access_token = os.getenv("X_ACCESS_TOKEN")
        access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

        if not (consumer_key and consumer_secret and access_token and access_token_secret):
            print("[WARN] X Credentials missing. Running in simulation mode.")
            return None

        try:
            client = tweepy.Client(
                consumer_key=consumer_key,
                consumer_secret=consumer_secret,
                access_token=access_token,
                access_token_secret=access_token_secret
            )
            print("[INFO] Successfully authenticated with X (V2).")
            return client
        except Exception as e:
            print(f"[ERROR] Failed to authenticate with X (V2): {e}")
            return None

    def _authenticate_x_v1(self):
        """Authenticates with X API V1.1 (Required for Media Upload)."""
        if not tweepy: return None
        consumer_key = os.getenv("X_CONSUMER_KEY")
        consumer_secret = os.getenv("X_CONSUMER_SECRET")
        access_token = os.getenv("X_ACCESS_TOKEN")
        access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
        
        if not (consumer_key and consumer_secret and access_token and access_token_secret):
            return None
            
        try:
            auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret, access_token, access_token_secret)
            api = tweepy.API(auth)
            print("[INFO] Successfully authenticated with X (V1.1).")
            return api
        except Exception as e:
            print(f"[ERROR] Failed to authenticate with X (V1.1): {e}")
            return None

    def generate_thought(self, topic: Optional[str] = None) -> list[str]:
        """
        Generates a thought based on the system prompt and constraints.
        """
        selected_topic = topic if topic else random.choice(self.seeds)
        print(f"Selected Topic: {selected_topic}")

        if not self.openai_client:
            print("[WARN] OpenAI API Key not found. Returning mock response.")
            return self._mock_response(selected_topic)

        max_thread_len = self.config["output_constraints"].get("max_thread_length", 1)
        
        user_content = f"Topic: {selected_topic}"
        if max_thread_len > 1:
            user_content += f"\n\nIf the thought requires more depth, you may generate a thread up to {max_thread_len} parts.\nSeparate each part strictly with '|||'.\nDo not number the tweets."
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.config["technical_configuration"]["model"],
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=self.config["technical_configuration"]["creativity_temperature"],
                max_tokens=600 if max_thread_len > 1 else 200, 
            )
            content = response.choices[0].message.content.strip()
            return self._enforce_constraints(content)
        except Exception as e:
            print(f"[ERROR] OpenAI extraction failed: {e}")
            return self._mock_response(selected_topic)

    def _mock_response(self, topic: str | None) -> list[str]:
        """Fallback for when API is not available."""
        return [f"The silence of {topic} speaks louder than code. (Mock Output)"]

    def _enforce_constraints(self, text: str) -> list[str]:
        """Strictly enforces output constraints, parses threads."""
        max_len = self.config["output_constraints"]["max_length_chars"]
        max_thread_len = self.config["output_constraints"].get("max_thread_length", 1)
        
        # Parse thread parts
        parts = [p.strip().strip('"') for p in text.split("|||")]
        valid_parts = []
        
        for part in parts[:max_thread_len]: # Enforce max thread length
            if not part: continue
            
            if len(part) > max_len:
                print(f"[WARN] Part exceeded {max_len} chars. Truncating.")
                valid_parts.append(part[:max_len-3] + "...")
            else:
                valid_parts.append(part)
        
        return valid_parts

    def _log_to_journal(self, parts: list[str]):
        """Appends the thought to journal.md with a timestamp."""
        thought_text = "\n[THREAD]\n".join(parts)
        entry = f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M')}\n{thought_text}\n"
        with open("journal.md", "a", encoding="utf-8") as f:
            f.write(entry)
        print("[Saved to journal.md]")

    def generate_image(self, thought: str) -> Optional[str]:
        """Generates an image using DALL-E 3 based on the thought."""
        img_cfg = self.config["technical_configuration"].get("image_generation", {})
        if not img_cfg.get("enabled") or not self.openai_client:
            return None
        
        print("[INFO] Generating image with DALL-E 3...")
        try:
            import requests
            prompt = f"{img_cfg['style']}\n\nSubject: Translate this thought into a symbolic, non-literal setting: {thought[:300]}"
            
            response = self.openai_client.images.generate(
                model=img_cfg["model"],
                prompt=prompt,
                size=img_cfg["size"],
                quality=img_cfg["quality"],
                n=1,
            )
            
            image_url = response.data[0].url
            img_data = requests.get(image_url).content
            file_path = "temp_thought.png"
            with open(file_path, 'wb') as handler:
                handler.write(img_data)
            
            print(f"[SUCCESS] Image generated and saved to {file_path}")
            return file_path
        except Exception as e:
            print(f"[ERROR] Image generation failed: {e}")
            return None

    def post_to_x(self, parts: list[str], image_path: Optional[str] = None):
        """Posts the thought to Twitter/X. Handles threads and optional image."""
        if not self.x_client:
            print("[SIMULATION] Thread would be posted:")
            for i, p in enumerate(parts):
                print(f"   [{i+1}/{len(parts)}] > {p}")
            return

        try:
            media_ids = []
            if image_path and os.path.exists(image_path):
                v1_api = self._authenticate_x_v1()
                if v1_api:
                    print(f"[INFO] Uploading image: {image_path}")
                    media = v1_api.media_upload(filename=image_path)
                    media_ids = [media.media_id]
                    print(f"[SUCCESS] Media uploaded. ID: {media_ids[0]}")

            previous_id = None
            for i, text in enumerate(parts):
                print(f"[INFO] Attempting to post part {i+1}/{len(parts)}: {text[:50]}...")
                
                if i == 0 and media_ids:
                    # Attach image to first tweet
                    response = self.x_client.create_tweet(text=text, media_ids=media_ids)
                elif previous_id:
                    response = self.x_client.create_tweet(text=text, in_reply_to_tweet_id=previous_id)
                else:
                    response = self.x_client.create_tweet(text=text)
                     
                previous_id = response.data['id']
                print(f"[SUCCESS] Posted part {i+1}! Tweet ID: {previous_id}")
                time.sleep(0.5)
                
            # Cleanup
            if image_path and os.path.exists(image_path):
                os.remove(image_path)
                
        except Exception as e:
            print(f"[ERROR] Failed to post to X: {e}")

    def run_once(self):
        """Runs the generation and posting logic a single time."""
        print(f"\n[RUN ONCE START] {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        parts = self.generate_thought()
        if not parts:
            print("[ERROR] No content generated.")
            return None
            
        # Generate image based on the core thought (first part)
        image_path = self.generate_image(parts[0])
            
        self._log_to_journal(parts)
        self.post_to_x(parts, image_path)
        
        full_text = " ||| ".join(parts)
        print("[RUN ONCE END]")
        return full_text

    def job(self):
        """The job to be executed in daemon mode (with jitter)."""
        print(f"\n[DAEMON JOB START] {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        # Apply Jitter (wait before posting)
        jitter = self.config["technical_configuration"]["jitter_minutes"]
        wait_min = random.uniform(0, jitter)
        print(f"Applying Jitter: Waiting {wait_min:.2f} minutes...")
        time.sleep(wait_min * 60)
        
        self.run_once()
        print("[DAEMON JOB END] Waiting for next cycle...")

    def run_schedule(self):
        """
        Runs the agent in an infinite loop using the 'schedule' library.
        """
        import schedule # Import here to avoid global dependency issues if not installed

        print(f"Starting Rubin Agent (Daemon Mode)...")
        print(f"Schedule: {self.config['technical_configuration']['schedule_cron']}")
        
        # Schedule the job
        # Note: The cron expression in config is '0 */12 * * *' which means every 12 hours.
        # Python 'schedule' library is simpler, so we'll map it to 'every 12 hours'.
        schedule.every(12).hours.do(self.job)
        
        # Run immediately on start for verification? 
        # Better: run one job immediately so we know it works, then waiting.
        print("Executing initial startup check...")
        self.job()

        print("Entering main loop. Press Ctrl+C to stop.")
        while True:
            schedule.run_pending()
            time.sleep(60) # Chill for 1 min


if __name__ == "__main__":
    agent = RubinAgent()
    agent.run_schedule()
