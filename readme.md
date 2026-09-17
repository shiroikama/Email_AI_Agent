# AI Sales Assistant

AI-powered email assistant that processes incoming Gmail messages, classifies customer requests, retrieves product information from a local database, generates a response with OpenAI, and creates a Gmail draft reply.

The project is designed as a prototype of an AI sales assistant for handling customer product inquiries.

## How it works

The main processing pipeline is:

Incoming Gmail message
        ↓
Read email content
        ↓
AI email classification
        ↓
Decision logic
        ↓
Retrieve product data from SQLite
        ↓
Build factual business payload
        ↓
AI generates reply
        ↓
Create Gmail draft
        ↓
Mark email as processed


The assistant does **not automatically send emails**. It creates a draft in Gmail so that a human can review the generated response before sending it.

## Main Features

- Gmail integration through the Gmail API
- OAuth 2.0 authentication
- AI-based email classification
- Decision logic for determining whether an email should be processed
- Product lookup using SQLite and SQLAlchemy
- Product data used as a factual source for AI-generated responses
- AI-generated customer replies
- Automatic Gmail draft creation
- Gmail labels for processing state and errors
- FastAPI endpoints for basic application and OpenAI API testing

## Architecture

### Gmail Agent

`gmail_agent_runner.py` contains the main processing loop.

The agent:

1. Connects to Gmail.
2. Looks for inbox messages that have not been processed.
3. Reads the sender, subject and message body.
4. Sends the email to the AI classifier.
5. Uses decision logic to determine whether the email should be processed.
6. Retrieves relevant product information from the SQLite database.
7. Builds a business payload without using AI to invent product information.
8. Sends the factual payload to the AI reply generator.
9. Creates a Gmail draft reply.
10. Marks the original message as processed.

The agent polls Gmail every 30 seconds by default and processes up to 10 candidate messages per batch.

### Processing labels

The agent uses Gmail labels to track processing state:

- `AI_PROCESSED` — the message has been processed successfully or intentionally skipped.
- `AI_ERROR` — an error occurred while processing the message.
- `HUMAN_ONLY` — the message should not be processed by the AI agent.

A message is marked `AI_PROCESSED` only after a draft has been successfully created when processing is required.

## Product Database

The project uses SQLite with SQLAlchemy.

The database is stored in app.db

The product model contains:

- SKU
- product name
- price
- lead time
- description

Prices are stored as integer cents rather than floating-point values to avoid floating-point precision issues.

The repository includes a sample `app.db` containing fictional/test product data.

Example products include:


DISP-001 — Drink Dispenser Basic
DISP-002 — Drink Dispenser Pro
DISP-003 — Drink Dispenser Ultra


`seed_products.py` can be used to recreate the sample product data.

## Project Structure

```text
.
├── app.py
├── gmail_agent_runner.py
├── gmail_auth_test.py
│
├── gmail_full_ai_reply_preview.py
├── gmail_create_draft_from_latest.py
├── gmail_classify_latest.py
├── gmail_create_draft_test.py
├── gmail_reply_draft_test.py
├── gmail_read_test.py
├── gmail_mark_processed_test.py
├── gmail_decide_test.py
│
├── decision_from_classification_test.py
├── build_business_payload.py
├── build_business_payload_test.py
│
├── db.py
├── models.py
├── product_service.py
├── products_context.py
├── seed_products.py
├── init_db.py
│
├── app.db
├── requirements.txt
└── .gitignore
```

The project contains several individual test and development scripts used while building and validating different parts of the pipeline.

## Technologies

- Python
- FastAPI
- Uvicorn
- OpenAI API
- Gmail API
- Google OAuth 2.0
- SQLAlchemy
- SQLite
- Pydantic
- python-dotenv

## Requirements

- Python 3.10+ recommended
- A Google account with Gmail
- A Google Cloud project with the Gmail API enabled
- Gmail OAuth client credentials
- An OpenAI API key

## Installation

Clone the repository:

```bash
git clone https://github.com/shiroikama/Email_AI_Agent.git
cd Email_AI_Agent
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it.

### macOS / Linux

```bash
source .venv/bin/activate
```

### Windows

```powershell
.venv\Scripts\activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

## OpenAI Configuration

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key
```

The `.env` file is intentionally excluded from Git.

## Gmail OAuth Configuration

The Gmail integration uses OAuth 2.0.

The required Gmail scopes are:

```text
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.compose
https://www.googleapis.com/auth/gmail.modify
```

### 1. Create Google OAuth credentials

Create OAuth credentials for a desktop application in Google Cloud and download the credentials JSON file.

Rename the downloaded file to:

```text
credentials.json
```

Place it in the root directory of the project:

```text
Email_AI_Agent/
├── credentials.json
├── app.py
├── gmail_auth_test.py
└── ...
```

### 2. First authentication

Run:

```bash
python gmail_auth_test.py
```

On the first run, the application opens a browser window and asks you to authorize access to the Gmail account.

After successful authentication, the OAuth token is stored locally as:

```text
token.json
```

On subsequent runs, the existing token is reused and refreshed when necessary.

Both `credentials.json` and `token.json` are excluded from Git.

## Running the FastAPI application

`app.py` provides two basic endpoints.

Start the application with:

```bash
python app.py
```

The server runs on:

```text
http://127.0.0.1:8000
```

### Health check

Open:

```text
http://127.0.0.1:8000/health
```

The endpoint reports the application status and whether an OpenAI API key is present in the environment.

### OpenAI test

Open:

```text
http://127.0.0.1:8000/test_ai
```

This endpoint makes a test request to the OpenAI API.

## Running the Gmail Agent

After configuring Gmail OAuth and the required environment variables:

```bash
python gmail_agent_runner.py
```

The agent continuously polls the Gmail inbox.

Default configuration:

```text
Poll interval: 30 seconds
Batch size:    10 messages
```

The process can be stopped with:

```text
Ctrl+C
```

## Database Setup

The repository already contains `app.db` with sample product data.

To initialize the database schema:

```bash
python init_db.py
```

To populate the database with the sample products:

```bash
python seed_products.py
```

The seed script clears the existing product table before inserting the sample products, so it can be safely rerun during development.

## Security

The following files contain credentials, tokens, or local environment data and are intentionally excluded from Git:

```text
.env
credentials.json
token.json
.venv/
__pycache__/
.DS_Store
```

Never commit API keys, OAuth client secrets, or OAuth tokens to the repository.

The included `app.db` contains fictional/test product data and does not contain real customer credentials.

## Project Status

This repository represents a working prototype developed to explore an AI-assisted sales email workflow.

The current implementation focuses on:

- Gmail integration
- AI email classification
- deterministic product data retrieval
- AI response generation
- human-reviewed Gmail drafts
- basic processing and error tracking

The project is intentionally kept as a prototype rather than a production-ready deployment.

## License

No license has currently been specified for this repository.