import json
import os
import random
import re
import tempfile
import time
from datetime import datetime
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import requests
except ImportError:
    requests = None

try:
    import tweepy
except ImportError:
    tweepy = None


class RubinAgent:
    def __init__(
        self,
        config_path: str = "config.json",
        system_prompt_path: str = "system_prompt.md",
        seeds_path: str = "seeds.json",
        journal_path: str = "journal.md",
    ):
        self.config = self._load_config(config_path)
        self.system_prompt = self._load_file(system_prompt_path)
        self.seeds = self._load_json(seeds_path)
        self.journal_path = journal_path

        self.openai_client = (
            OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            if OpenAI and os.getenv("OPENAI_API_KEY")
            else None
        )
        self.x_client = self._authenticate_x()

    def _load_config(self, path: str) -> dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_json(self, path: str) -> list[str]:
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
        if not tweepy:
            print("[WARN] Tweepy not installed. Posting disabled.")
            return None

        consumer_key = os.getenv("X_CONSUMER_KEY")
        consumer_secret = os.getenv("X_CONSUMER_SECRET")
        access_token = os.getenv("X_ACCESS_TOKEN")
        access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

        if not (consumer_key and consumer_secret and access_token and access_token_secret):
            print("[WARN] X credentials missing. Running in simulation mode.")
            return None

        try:
            client = tweepy.Client(
                consumer_key=consumer_key,
                consumer_secret=consumer_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
            )
            print("[INFO] Successfully authenticated with X (V2).")
            return client
        except Exception as e:
            print(f"[ERROR] Failed to authenticate with X (V2): {e}")
            return None

    def _authenticate_x_v1(self):
        if not tweepy:
            return None

        consumer_key = os.getenv("X_CONSUMER_KEY")
        consumer_secret = os.getenv("X_CONSUMER_SECRET")
        access_token = os.getenv("X_ACCESS_TOKEN")
        access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

        if not (consumer_key and consumer_secret and access_token and access_token_secret):
            return None

        try:
            auth = tweepy.OAuth1UserHandler(
                consumer_key,
                consumer_secret,
                access_token,
                access_token_secret,
            )
            api = tweepy.API(auth)
            print("[INFO] Successfully authenticated with X (V1.1).")
            return api
        except Exception as e:
            print(f"[ERROR] Failed to authenticate with X (V1.1): {e}")
            return None

    def _editorial_cfg(self) -> dict[str, Any]:
        return self.config.get("editorial_configuration", {})

    def _technical_cfg(self) -> dict[str, Any]:
        return self.config.get("technical_configuration", {})

    def _output_cfg(self) -> dict[str, Any]:
        return self.config.get("output_constraints", {})

    def _load_recent_journal_entries(self, limit: Optional[int] = None) -> list[dict[str, str]]:
        limit = limit or self._editorial_cfg().get("recent_memory_entries", 12)

        try:
            with open(self.journal_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
        except FileNotFoundError:
            return []

        if not content:
            return []

        raw_entries = re.split(r"(?m)^## ", content)
        entries: list[dict[str, str]] = []

        for raw in raw_entries:
            raw = raw.strip()
            if not raw:
                continue
            lines = raw.splitlines()
            if not lines:
                continue
            entries.append(
                {
                    "timestamp": lines[0].strip(),
                    "body": "\n".join(lines[1:]).strip(),
                }
            )

        return entries[-limit:]

    def _content_lines(self, body: str) -> list[str]:
        lines = []
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped or stripped == "[THREAD]" or stripped.startswith("[TOPIC]") or stripped.startswith("[STATUS]") or stripped.startswith("[TWEET IDS]") or stripped.startswith("[ERROR]"):
                continue
            lines.append(stripped)
        return lines

    def _recent_topics(self, entries: list[dict[str, str]]) -> list[str]:
        topics: list[str] = []
        for entry in entries:
            match = re.search(r"(?m)^\[TOPIC\]\s+(.+)$", entry["body"])
            if match:
                topics.append(match.group(1).strip())
        return topics

    def _recent_openings(self, entries: list[dict[str, str]], limit: int = 5) -> list[str]:
        openings: list[str] = []
        for entry in reversed(entries):
            lines = self._content_lines(entry["body"])
            if lines:
                openings.append(lines[0])
            if len(openings) >= limit:
                break
        return list(reversed(openings))

    def _recent_closings(self, entries: list[dict[str, str]], limit: int = 5) -> list[str]:
        closings: list[str] = []
        for entry in reversed(entries):
            lines = self._content_lines(entry["body"])
            if lines:
                closings.append(lines[-1])
            if len(closings) >= limit:
                break
        return list(reversed(closings))

    def _select_topic(self, preferred_topic: Optional[str] = None) -> str:
        if preferred_topic:
            return preferred_topic

        recent_entries = self._load_recent_journal_entries()
        recent_text = "\n".join(entry["body"].lower() for entry in recent_entries)
        recent_topics = {topic.lower() for topic in self._recent_topics(recent_entries)}

        scored_topics: list[tuple[int, float, str]] = []
        for seed in self.seeds:
            seed_lower = seed.lower()
            score = recent_text.count(seed_lower) + (2 if seed_lower in recent_topics else 0)
            scored_topics.append((score, random.random(), seed))

        scored_topics.sort(key=lambda item: (item[0], item[1]))
        best_score = scored_topics[0][0]
        shortlist = [topic for score, _, topic in scored_topics if score == best_score][:3]
        return random.choice(shortlist)

    def _memory_prompt(self, entries: list[dict[str, str]]) -> str:
        recent_topics = self._recent_topics(entries)
        openings = self._recent_openings(entries)
        closings = self._recent_closings(entries)

        sections: list[str] = []
        if recent_topics:
            sections.append(
                "Recent topics to avoid repeating too directly:\n- "
                + "\n- ".join(recent_topics[-5:])
            )
        if openings:
            sections.append(
                "Recent openings to avoid echoing:\n- "
                + "\n- ".join(openings)
            )
        if closings:
            sections.append(
                "Recent closings to avoid recycling:\n- "
                + "\n- ".join(closings)
            )
        return "\n\n".join(sections) if sections else "No recent journal memory available."

    def _chat(self, messages: list[dict[str, str]], max_tokens: int) -> str:
        if not self.openai_client:
            raise RuntimeError("OPENAI_API_KEY missing or OpenAI SDK unavailable.")

        response = self.openai_client.chat.completions.create(
            model=self._technical_cfg()["model"],
            messages=messages,
            temperature=self._technical_cfg().get("creativity_temperature", 0.65),
            max_tokens=max_tokens,
        )
        return (response.choices[0].message.content or "").strip()

    def _split_parts(self, text: str) -> list[str]:
        max_thread_len = self._output_cfg().get("max_thread_length", 1)
        parts = [part.strip().strip('"') for part in text.split("|||")]
        return [part for part in parts[:max_thread_len] if part]

    def _normalize_text(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r"https?://\S+|www\.\S+", "", text)
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _token_set(self, text: str) -> set[str]:
        normalized = self._normalize_text(text)
        return {token for token in normalized.split() if len(token) > 2}

    def _similarity(self, a: str, b: str) -> float:
        tokens_a = self._token_set(a)
        tokens_b = self._token_set(b)
        if not tokens_a or not tokens_b:
            return 0.0
        return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)

    def _contains_emoji(self, text: str) -> bool:
        emoji_ranges = (
            "\U0001F300-\U0001F5FF"
            "\U0001F600-\U0001F64F"
            "\U0001F680-\U0001F6FF"
            "\U0001F700-\U0001F77F"
            "\U0001F780-\U0001F7FF"
            "\U0001F800-\U0001F8FF"
            "\U0001F900-\U0001F9FF"
            "\U0001FA70-\U0001FAFF"
            "\u2600-\u26FF"
            "\u2700-\u27BF"
        )
        return bool(re.search(f"[{emoji_ranges}]", text))

    def _contains_banned_formatting(self, text: str) -> Optional[str]:
        if not self._output_cfg().get("allow_links", False):
            if re.search(r"https?://|www\.", text, flags=re.IGNORECASE):
                return "links are not allowed"

        if not self._output_cfg().get("allow_hashtags", False):
            if re.search(r"(^|\s)#\w+", text):
                return "hashtags are not allowed"

        if not self._output_cfg().get("allow_emojis", False):
            if self._contains_emoji(text):
                return "emojis are not allowed"

        if not self._output_cfg().get("allow_lists", False):
            if re.search(r"(?m)^\s*([-*•]|\d+[.)])\s+", text):
                return "list formatting is not allowed"

        return None

    def _validate_parts(
        self,
        parts: list[str],
        recent_entries: list[dict[str, str]],
    ) -> tuple[bool, str]:
        max_len = self._output_cfg()["max_length_chars"]
        similarity_threshold = self._editorial_cfg().get("similarity_threshold", 0.72)

        if not parts:
            return False, "no content returned after parsing"

        for index, part in enumerate(parts, start=1):
            if len(part) > max_len:
                return False, f"part {index} exceeds {max_len} characters"

            banned_reason = self._contains_banned_formatting(part)
            if banned_reason:
                return False, f"part {index} invalid: {banned_reason}"

        if len(parts) > 1:
            for current, nxt in zip(parts, parts[1:]):
                if self._similarity(current, nxt) >= 0.75:
                    return False, "adjacent thread parts are too similar"

        current_text = "\n".join(parts)
        closings = self._recent_closings(recent_entries, limit=8)
        if parts[-1] in closings:
            return False, "closing line repeats a recent ending"

        for entry in recent_entries:
            lines = self._content_lines(entry["body"])
            if not lines:
                continue
            score = self._similarity(current_text, "\n".join(lines))
            if score >= similarity_threshold:
                return False, f"too similar to recent journal entry ({score:.2f})"

        return True, "ok"

    def _build_draft_prompt(
        self,
        topic: str,
        recent_entries: list[dict[str, str]],
        previous_failure: Optional[str] = None,
    ) -> str:
        max_thread_len = self._output_cfg().get("max_thread_length", 1)
        prompt = [
            f"Topic: {topic}",
            "Write a fresh Rubin draft for X.",
            "Return 1 to 3 tweet parts separated strictly with '|||'.",
            "Do not number the tweets.",
            "Stay in English unless one brief Spanish line is absolutely necessary.",
            "Aim for one central idea, one clean reframe, and a hard landing.",
            self._memory_prompt(recent_entries),
        ]

        if previous_failure:
            prompt.append(f"Previous attempt failed because: {previous_failure}. Fix that.")

        if max_thread_len > 1:
            prompt.append(
                f"Use a thread only if the idea genuinely needs it. Maximum parts: {max_thread_len}."
            )

        return "\n\n".join(prompt)

    def _build_editorial_prompt(
        self,
        topic: str,
        draft: str,
        recent_entries: list[dict[str, str]],
        previous_failure: Optional[str] = None,
    ) -> str:
        prompt = [
            f"Topic: {topic}",
            "You are now in producer mode. Cut the draft into the final piece.",
            "Hard editorial rules:",
            "- One central idea only.",
            "- Do not explain the metaphor after using it.",
            "- Every next line must advance, not restate.",
            "- Cut at least 20% of unnecessary language when possible.",
            "- End on an inevitable line that can stand alone.",
            "- Avoid sounding like generic wisdom, therapy, or LinkedIn motivation.",
            "- Keep the piece native to X. No labels, no commentary, no quotes around the output.",
            self._memory_prompt(recent_entries),
            f"Draft:\n{draft}",
        ]

        if previous_failure:
            prompt.append(f"Previous attempt failed because: {previous_failure}. Fix that decisively.")

        prompt.append("Return only the final post text. Use '|||' only if it truly needs a thread.")
        return "\n\n".join(prompt)

    def generate_thought_package(self, topic: Optional[str] = None) -> Optional[dict[str, Any]]:
        selected_topic = self._select_topic(topic)
        print(f"Selected Topic: {selected_topic}")

        if not self.openai_client:
            print("[ERROR] OpenAI API key not found. Aborting instead of publishing filler.")
            return None

        recent_entries = self._load_recent_journal_entries()
        max_attempts = self._editorial_cfg().get("generation_attempts", 3)
        previous_failure: Optional[str] = None

        for attempt in range(1, max_attempts + 1):
            try:
                draft = self._chat(
                    [
                        {"role": "system", "content": self.system_prompt},
                        {
                            "role": "user",
                            "content": self._build_draft_prompt(
                                selected_topic,
                                recent_entries,
                                previous_failure,
                            ),
                        },
                    ],
                    max_tokens=700,
                )

                final_text = self._chat(
                    [
                        {"role": "system", "content": self.system_prompt},
                        {
                            "role": "user",
                            "content": self._build_editorial_prompt(
                                selected_topic,
                                draft,
                                recent_entries,
                                previous_failure,
                            ),
                        },
                    ],
                    max_tokens=500,
                )

                parts = self._split_parts(final_text)
                is_valid, reason = self._validate_parts(parts, recent_entries)
                if is_valid:
                    return {
                        "topic": selected_topic,
                        "parts": parts,
                        "draft": draft,
                        "final_text": final_text,
                    }

                previous_failure = reason
                print(f"[WARN] Editorial attempt {attempt} rejected: {reason}")
            except Exception as e:
                previous_failure = str(e)
                print(f"[ERROR] Editorial attempt {attempt} failed: {e}")

        print("[ERROR] Rubin could not produce a publishable piece after editorial retries.")
        return None

    def generate_image(self, thought: str) -> Optional[str]:
        img_cfg = self._technical_cfg().get("image_generation", {})
        if not img_cfg.get("enabled"):
            return None

        if not self.openai_client or not requests:
            print("[WARN] Image generation skipped: missing OpenAI client or requests.")
            return None

        print("[INFO] Generating image with DALL-E 3...")
        try:
            prompt = (
                f"{img_cfg['style']}\n\n"
                "Subject: Translate this thought into a symbolic, non-literal setting: "
                f"{thought[:300]}"
            )
            response = self.openai_client.images.generate(
                model=img_cfg["model"],
                prompt=prompt,
                size=img_cfg["size"],
                quality=img_cfg["quality"],
                n=1,
            )

            image_url = response.data[0].url
            img_data = requests.get(image_url, timeout=30).content
            file_path = os.path.join(tempfile.gettempdir(), "temp_thought.png")

            with open(file_path, "wb") as handler:
                handler.write(img_data)

            print(f"[SUCCESS] Image generated and saved to {file_path}")
            return file_path
        except Exception as e:
            print(f"[ERROR] Image generation failed: {e}")
            return None

    def _retry_cfg(self) -> tuple[int, float]:
        retries = self._technical_cfg().get("post_max_retries", 3)
        backoff = self._technical_cfg().get("retry_backoff_seconds", 2.5)
        return retries, backoff

    def _is_transient_x_error(self, error: Exception) -> bool:
        message = str(error).lower()
        transient_signals = [
            "429",
            "500",
            "502",
            "503",
            "504",
            "timeout",
            "temporarily unavailable",
            "service unavailable",
            "server error",
            "connection reset",
        ]
        return any(signal in message for signal in transient_signals)

    def _create_tweet_with_retry(self, **kwargs):
        retries, backoff = self._retry_cfg()
        last_error: Optional[Exception] = None

        for attempt in range(1, retries + 1):
            try:
                return self.x_client.create_tweet(**kwargs)
            except Exception as e:
                last_error = e
                if attempt >= retries or not self._is_transient_x_error(e):
                    raise

                sleep_for = backoff * (2 ** (attempt - 1)) + random.uniform(0.2, 0.9)
                print(
                    f"[WARN] X post attempt {attempt}/{retries} failed with transient error: {e}. "
                    f"Retrying in {sleep_for:.1f}s."
                )
                time.sleep(sleep_for)

        if last_error:
            raise last_error

    def _upload_media_with_retry(self, image_path: str) -> list[int]:
        retries, backoff = self._retry_cfg()
        v1_api = self._authenticate_x_v1()
        if not v1_api:
            return []

        last_error: Optional[Exception] = None
        for attempt in range(1, retries + 1):
            try:
                print(f"[INFO] Uploading image: {image_path}")
                media = v1_api.media_upload(filename=image_path)
                print(f"[SUCCESS] Media uploaded. ID: {media.media_id}")
                return [media.media_id]
            except Exception as e:
                last_error = e
                if attempt >= retries or not self._is_transient_x_error(e):
                    print(f"[WARN] Image upload failed permanently: {e}")
                    return []

                sleep_for = backoff * (2 ** (attempt - 1)) + random.uniform(0.2, 0.9)
                print(
                    f"[WARN] Media upload attempt {attempt}/{retries} failed: {e}. "
                    f"Retrying in {sleep_for:.1f}s."
                )
                time.sleep(sleep_for)

        if last_error:
            print(f"[WARN] Image upload failed after retries: {last_error}")
        return []

    def post_to_x(self, parts: list[str], image_path: Optional[str] = None) -> dict[str, Any]:
        if not self.x_client:
            print("[SIMULATION] Thread would be posted:")
            for i, part in enumerate(parts, start=1):
                print(f"   [{i}/{len(parts)}] > {part}")
            return {
                "success": True,
                "simulated": True,
                "tweet_ids": [],
                "used_image": False,
            }

        media_ids: list[int] = []
        tweet_ids: list[str] = []

        try:
            if image_path and os.path.exists(image_path):
                media_ids = self._upload_media_with_retry(image_path)

            previous_id: Optional[str] = None
            for index, text in enumerate(parts, start=1):
                payload: dict[str, Any] = {"text": text}
                if previous_id:
                    payload["in_reply_to_tweet_id"] = previous_id
                elif media_ids:
                    payload["media_ids"] = media_ids

                print(f"[INFO] Attempting to post part {index}/{len(parts)}: {text[:50]}...")
                try:
                    response = self._create_tweet_with_retry(**payload)
                except Exception as e:
                    if index == 1 and media_ids:
                        print(f"[WARN] Posting with media failed: {e}. Retrying text-only.")
                        payload.pop("media_ids", None)
                        media_ids = []
                        response = self._create_tweet_with_retry(**payload)
                    else:
                        raise

                previous_id = response.data["id"]
                tweet_ids.append(previous_id)
                print(f"[SUCCESS] Posted part {index}! Tweet ID: {previous_id}")
                time.sleep(0.5)

            return {
                "success": True,
                "simulated": False,
                "tweet_ids": tweet_ids,
                "used_image": bool(media_ids),
            }
        except Exception as e:
            print(f"[ERROR] Failed to post to X after retries: {e}")
            return {
                "success": False,
                "simulated": False,
                "tweet_ids": tweet_ids,
                "used_image": bool(media_ids),
                "error": str(e),
            }
        finally:
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except OSError:
                    pass

    def _log_to_journal(
        self,
        topic: str,
        parts: list[str],
        status: str,
        tweet_ids: Optional[list[str]] = None,
        error: Optional[str] = None,
    ):
        try:
            thought_text = "\n[THREAD]\n".join(parts)
            metadata_lines = [
                f"[TOPIC] {topic}",
                f"[STATUS] {status}",
            ]
            if tweet_ids:
                metadata_lines.append(f"[TWEET IDS] {', '.join(tweet_ids)}")
            if error:
                metadata_lines.append(f"[ERROR] {error}")

            entry = (
                f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                + "\n".join(metadata_lines)
                + "\n"
                + thought_text
                + "\n"
            )
            with open(self.journal_path, "a", encoding="utf-8") as f:
                f.write(entry)
            print("[Saved to journal.md]")
        except Exception as e:
            print(f"[WARN] Could not write to journal.md: {e}")

    def run_once(self):
        print(f"\n[RUN ONCE START] {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        package = self.generate_thought_package()
        if not package:
            print("[RUN ONCE ABORTED] No publishable content produced.")
            return None

        image_path = self.generate_image(package["parts"][0])
        post_result = self.post_to_x(package["parts"], image_path)

        status = "SIMULATED" if post_result.get("simulated") else "POSTED"
        if post_result.get("success"):
            self._log_to_journal(
                topic=package["topic"],
                parts=package["parts"],
                status=status,
                tweet_ids=post_result.get("tweet_ids"),
            )
            full_text = " ||| ".join(package["parts"])
            print("[RUN ONCE END]")
            return full_text

        self._log_to_journal(
            topic=package["topic"],
            parts=package["parts"],
            status="FAILED_POST",
            tweet_ids=post_result.get("tweet_ids"),
            error=post_result.get("error"),
        )
        print("[RUN ONCE END WITH FAILURE]")
        raise RuntimeError(post_result.get("error", "Unknown X posting failure"))

    def job(self):
        print(f"\n[DAEMON JOB START] {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        jitter = self._technical_cfg().get("jitter_minutes", 0)
        if jitter > 0:
            wait_min = random.uniform(0, jitter)
            print(f"Applying jitter: waiting {wait_min:.2f} minutes...")
            time.sleep(wait_min * 60)

        self.run_once()
        print("[DAEMON JOB END] Waiting for next cycle...")

    def run_schedule(self):
        import schedule

        cron = self._technical_cfg().get("schedule_cron", "0 12 * * *")
        parts = cron.split()

        print("Starting Rubin Agent (Daemon Mode)...")
        print(f"Schedule: {cron}")

        if len(parts) == 5 and parts[2:] == ["*", "*", "*"] and parts[0].isdigit() and parts[1].isdigit():
            minute = int(parts[0])
            hour = int(parts[1])
            schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(self.job)
        else:
            print("[WARN] Unsupported cron expression for local scheduler. Falling back to every 12 hours.")
            schedule.every(12).hours.do(self.job)

        print("Executing initial startup check...")
        self.job()

        print("Entering main loop. Press Ctrl+C to stop.")
        while True:
            schedule.run_pending()
            time.sleep(60)


if __name__ == "__main__":
    agent = RubinAgent()
    agent.run_schedule()
