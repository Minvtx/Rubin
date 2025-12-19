# Deploying Rubin Agent to Railway

This agent is configured to run on [Railway](https://railway.app), which is excellent for persistent python scripts.

## Prerequisites
1.  A GitHub account.
2.  A Railway account (login with GitHub).
3.  [Optional] GitHub Desktop or CLI to push this code.

## Step 1: Push to GitHub
Since I initialized the git repository locally, you need to push it to a new repository on your GitHub.

1.  Create a **New Repository** on GitHub (e.g., `rubin-agent`).
2.  Run these commands in your project folder (or terminal):
    ```bash
    git remote add origin https://github.com/YOUR_USERNAME/rubin-agent.git
    git branch -M main
    git push -u origin main
    ```

## Step 2: Create Project on Railway
1.  Go to **Railway Dashboard**.
2.  Click **"New Project"** -> **"Deploy from GitHub repo"**.
3.  Select the `rubin-agent` repository you just pushed.
4.  Railway will detect the `Procfile` and creating the service.

## Step 3: Configure Variables
**CRITICAL:** The bot will fail if you don't add the environment variables.

1.  Click on the new service in Railway.
2.  Go to the **Variables** tab.
3.  Add the following keys (copy them from your local `.env`):
    -   `OPENAI_API_KEY`
    -   `X_CONSUMER_KEY`
    -   `X_CONSUMER_SECRET`
    -   `X_ACCESS_TOKEN`
    -   `X_ACCESS_TOKEN_SECRET`

## Step 4: Verify
1.  Go to the **Deployments** tab.
2.  Click "View Logs".
3.  You should see:
    > `Starting Rubin Agent (Daemon Mode)...`
    > `Executing initial startup check...`

The agent is now alive and will tweet every 12 hours.
