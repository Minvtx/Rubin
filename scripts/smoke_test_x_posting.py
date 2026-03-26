import argparse
import base64
import os
import tempfile
from datetime import datetime

from dotenv import load_dotenv

try:
    import tweepy
except ImportError:
    tweepy = None


PNG_1X1_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/w8AAgMBgNn14uoAAAAASUVORK5CYII="
)


def build_v2_client():
    if not tweepy:
        raise RuntimeError("Tweepy is not installed.")

    consumer_key = os.getenv("X_CONSUMER_KEY")
    consumer_secret = os.getenv("X_CONSUMER_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        raise RuntimeError("Missing X credentials in environment.")

    return tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )


def build_v1_api():
    if not tweepy:
        raise RuntimeError("Tweepy is not installed.")

    consumer_key = os.getenv("X_CONSUMER_KEY")
    consumer_secret = os.getenv("X_CONSUMER_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        raise RuntimeError("Missing X credentials in environment.")

    auth = tweepy.OAuth1UserHandler(
        consumer_key,
        consumer_secret,
        access_token,
        access_token_secret,
    )
    return tweepy.API(auth)


def create_temp_png() -> str:
    data = base64.b64decode(PNG_1X1_BASE64)
    path = os.path.join(tempfile.gettempdir(), "rubin_smoke_test.png")
    with open(path, "wb") as f:
        f.write(data)
    return path


def smoke_text(client) -> tuple[bool, str | None]:
    stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    text = f"[Rubin smoke:text] {stamp} Base tweet path verification."
    print(f"[TEXT] Posting: {text}")
    response = client.create_tweet(text=text, user_auth=True)
    tweet_id = response.data["id"]
    print(f"[TEXT] Success. Tweet ID: {tweet_id}")
    return True, str(tweet_id)


def smoke_image(client, media_api) -> tuple[bool, str | None]:
    stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    image_path = create_temp_png()
    try:
        print(f"[IMAGE] Uploading smoke test image: {image_path}")
        media = media_api.media_upload(filename=image_path)
        text = f"[Rubin smoke:image] {stamp} Media attachment path verification."
        print(f"[IMAGE] Posting with media_id={media.media_id}: {text}")
        response = client.create_tweet(
            text=text,
            media_ids=[media.media_id],
            user_auth=True,
        )
        tweet_id = response.data["id"]
        print(f"[IMAGE] Success. Tweet ID: {tweet_id}")
        return True, str(tweet_id)
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)


def smoke_thread(client) -> tuple[bool, tuple[str, str] | None]:
    stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    root_text = f"[Rubin smoke:thread root] {stamp} Root tweet verification."
    reply_text = f"[Rubin smoke:thread reply] {stamp} Reply path verification."

    print(f"[THREAD] Posting root: {root_text}")
    root_response = client.create_tweet(text=root_text, user_auth=True)
    root_id = str(root_response.data["id"])
    print(f"[THREAD] Root success. Tweet ID: {root_id}")

    print(f"[THREAD] Posting reply to {root_id}: {reply_text}")
    reply_response = client.create_tweet(
        text=reply_text,
        in_reply_to_tweet_id=root_id,
        user_auth=True,
    )
    reply_id = str(reply_response.data["id"])
    print(f"[THREAD] Reply success. Tweet ID: {reply_id}")
    return True, (root_id, reply_id)


def run_scenarios(scenario: str) -> int:
    load_dotenv()
    client = build_v2_client()
    media_api = build_v1_api()

    selected = ["text", "image", "thread"] if scenario == "all" else [scenario]
    failures: list[str] = []

    for item in selected:
        try:
            if item == "text":
                smoke_text(client)
            elif item == "image":
                smoke_image(client, media_api)
            elif item == "thread":
                smoke_thread(client)
            else:
                raise ValueError(f"Unknown scenario: {item}")
        except Exception as e:
            failures.append(f"{item}: {e}")
            print(f"[{item.upper()}] FAILURE: {e}")

    if failures:
        print("\n[SUMMARY] Smoke test failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\n[SUMMARY] All selected smoke tests passed.")
    return 0


def parse_args():
    parser = argparse.ArgumentParser(description="Smoke test X posting paths for Rubin.")
    parser.add_argument(
        "--scenario",
        choices=["all", "text", "image", "thread"],
        default="all",
        help="Which posting scenario to test.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(run_scenarios(args.scenario))
