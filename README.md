# Auto Bidding Bot

## Objective

This project aims to detect posts on LinkedIn and X (formerly Twitter) where users are looking for freelancers/developers and automatically generate and post personalized bid comments. The bot is designed to simulate human behavior with random delays and session persistence.

## Tech Stack

- Python
- Playwright
- n8n
- SQLite
- Groq API
- OpenRouter (fallback API)

## Project Structure

```
auto-bid-bot/
├── linkedin_bot.py
├── twitter_bot.py
├── commenter.py
├── db.py
├── config.py
├── utils.py
├── main.py
├── requirements.txt
├── .env.example
├── workflow.json
├── README.md
├── session/             # Stores browser session data (cookies, local storage)
├── data/                # Stores SQLite database (bids.db)
└── logs/                # Stores dry_run.log
```

## Setup and Installation

1.  **Clone the repository (or create the files manually):**

    ```bash
    git clone <repository_url>
    cd auto-bid-bot
    ```

2.  **Create a virtual environment and install dependencies:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    playwright install
    ```

3.  **Configure environment variables:**

    Copy the `.env.example` file to `.env` and fill in your credentials and settings:

    ```bash
    cp .env.example .env
    ```

    Edit the `.env` file:

    ```ini
    # API Keys
    GROQ_API_KEY="your_groq_api_key"
    OPENROUTER_API_KEY="your_openrouter_api_key"

    # LinkedIn Credentials
    LINKEDIN_EMAIL="your_linkedin_email"
    LINKEDIN_PASSWORD="your_linkedin_password"

    # X (Twitter) Credentials
    TWITTER_EMAIL="your_twitter_email"
    TWITTER_PASSWORD="your_twitter_password"

    # Playwright Settings
    HEADLESS="True" # Set to "False" to see the browser UI

    # Dry Run Mode
    DRY_RUN="True" # Set to "True" to prevent actual posting, "False" to enable posting
    ```

## Dry Run Mode

To test the bot's functionality without actually posting comments, set `DRY_RUN="True"` in your `.env` file. In dry run mode:

-   The bot will navigate to the post URL.
-   It will simulate typing the comment.
-   It will **not** click the submit button.
-   A screenshot of the comment ready to be posted will be saved in the `session/` directory.
-   A log entry will be added to `logs/dry_run.log` with the timestamp, platform, post ID, and generated comment.
-   Terminal output will indicate "DRY RUN: Ready to submit".

This allows you to verify the generated comments and bot behavior before live deployment.

## Run Commands

To run the main script:

```bash
python3 main.py
```

## n8n Setup

1.  **Import the workflow:**

    Open your n8n instance, go to "Workflows", and click "New". Then, click on the three dots menu and select "Import from JSON". Paste the content of `workflow.json`.

2.  **Configure the Cron Trigger:**

    The workflow is set to run every 2 hours during business hours (9 AM to 6 PM). You can adjust the cron expression in the "Cron Trigger" node as needed.

3.  **Configure the "Execute Command" node:**

    Ensure the `command` field is set to `python3 /home/ubuntu/auto-bid-bot/main.py` (adjust the path if your project is in a different location).

4.  **Optional: Google Sheets Backup:**

    If you wish to back up logs to Google Sheets, configure the "Google Sheets Backup (Optional)" node with your Google Sheets credentials and the desired spreadsheet/sheet name. The workflow is currently set to append the `stdout` from the `Execute Main Script` node.

5.  **Activate the workflow:**

    Save and activate the n8n workflow.
