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
            missing = []
            if not consumer_key: missing.append("X_CONSUMER_KEY")
            if not consumer_secret: missing.append("X_CONSUMER_SECRET")
            if not access_token: missing.append("X_ACCESS_TOKEN")
            if not access_token_secret: missing.append("X_ACCESS_TOKEN_SECRET")
            print(f"[WARN] X Credentials missing in .env: {', '.join(missing)}. Running in simulation mode.")
            return None

        try:
            client = tweepy.Client(
                consumer_key=consumer_key,
                consumer_secret=consumer_secret,
                access_token=access_token,
                access_token_secret=access_token_secret
            )
            print("[INFO] Successfully authenticated with X.")
            return client
        except Exception as e:
            print(f"[ERROR] Failed to authenticate with X: {e}")
            return None

    def generate_thought(self, topic: Optional[str] = None) -> str:
        """
        Generates a thought based on the system prompt and constraints.
        If no topic is provided, picks a random seed.
        """
        selected_topic = topic if topic else random.choice(self.seeds)
        print(f"Selected Topic: {selected_topic}")

        if not self.openai_client:
            print("[WARN] OpenAI API Key not found. Returning mock response.")
            return self._mock_response(selected_topic)

        max_thread_len = self.config["output_constraints"].get("max_thread_length", 1)
        
        user_content = f"Topic: {selected_topic}"
        if max_thread_len > 1:
            user_content += f"\n\nIf the thought requires more depth (e.g., for a 'Manifiesto Corto' or 'Observación de Tendencia' sequence), you may generate a thread up to {max_thread_len} parts.\nSeparate each part of the thread strictly with the delimiter '|||'.\nDo not number the tweets manually (e.g. no '1/3'), they will be posted as a thread sequentially."
        
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
        if topic == "Garbage Collection":
            return ["To create the new, you must first destroy the old.", "Let the collector run."]
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

    def post_to_x(self, parts: list[str]):
        """Posts the thought to Twitter/X. Handles threads if list has >1 item."""
        if not self.x_client:
            print("[SIMULATION] Thread would be posted:")
            for i, p in enumerate(parts):
                print(f"   [{i+1}/{len(parts)}] > {p}")
            return

        try:
            previous_id = None
            for i, text in enumerate(parts):
                print(f"[INFO] Attempting to post part {i+1}/{len(parts)}: {text[:50]}...")
                
                if previous_id:
                     response = self.x_client.create_tweet(text=text, in_reply_to_tweet_id=previous_id)
                else:
                     response = self.x_client.create_tweet(text=text)
                     
                previous_id = response.data['id']
                print(f"[SUCCESS] Posted part {i+1}! Tweet ID: {previous_id}")
                if i == 0:
                    print(f"[INFO] Thread started at: https://x.com/i/web/status/{previous_id}")
                time.sleep(0.5) # Smaller delay for serverless efficiency
                
        except Exception as e:
            print(f"[ERROR] Failed to post to X: {e}")
            if "403" in str(e):
                print("[ERROR] 403 Forbidden: Check if your App has 'Read and Write' permissions enabled in Twitter Developer Portal.")
            elif "429" in str(e):
                print("[ERROR] 429 Too Many Requests: Rate limit exceeded.")

    def run_once(self):
        """Runs the generation and posting logic a single time (for serverless/cron)."""
        print(f"\n[RUN ONCE START] {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        parts = self.generate_thought()
        if not parts:
            print("[ERROR] No content generated.")
            return None
            
        self._log_to_journal(parts)
        self.post_to_x(parts)
        
        print("\n[METADATA]:")
        full_text = " ||| ".join(parts)
        print(f"Total parts: {len(parts)}, Total length: {len(full_text)}")
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
