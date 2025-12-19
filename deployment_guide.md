# Rubin Agent Deployment Guide

This guide explains how to get the necessary keys and run your agent live on Twitter.

## 1. OpenAI API Key (The Brain)
1.  Go to [platform.openai.com](https://platform.openai.com/api-keys).
2.  Create a new secret key.
3.  Copy it.

## 2. Twitter/X API Keys (The Mouth)
You need a **Basic** tier developer account (approx $100/mo) or a **Free** tier (limited posting) if available/eligible.
1.  Go to [developer.twitter.com](https://developer.twitter.com/en/portal/dashboard).
2.  Create a new **Project** and **App**.
3.  In "User authentication settings":
    -   Select **Read and Write** permissions.
    -   Type of App: **Web App, Automated App or Bot**.
    -   Callback URI / Website URL: You can use `http://localhost` if you don't have one.
4.  Go to the **Keys and Tokens** tab of your App.
5.  Generate:
    -   **API Key and Secret** (Consumer Key/Secret).
    -   **Access Token and Secret** (Make sure you generated them *after* setting Read/Write permissions).

## 3. Configuration
1.  Rename `.env.example` to `.env`.
2.  Paste your keys into `.env`:
    ```env
    OPENAI_API_KEY=sk-your-key
    X_CONSUMER_KEY=your-consumer-key
    X_CONSUMER_SECRET=your-consumer-secret
    X_ACCESS_TOKEN=your-access-token
    X_ACCESS_TOKEN_SECRET=your-access-secret
    ```

## 4. Running Live
1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Run the agent:
    ```bash
    python main.py
    ```

**Note:** The agent is configured to run on a loop (every 6 hours). Keep the terminal open or deploy it to a server (VPS, Heroku, Railway, etc.).
