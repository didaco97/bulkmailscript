# Bulk Email Sender

A lightweight, automated Python script to send personalized bulk emails using Gmail SMTP. It supports beautifully designed HTML email templates with a plain-text fallback and gracefully handles rate limits and configuration errors.

## Features
- **Personalized Emails:** Automatically replaces `{name}` in the HTML and text templates with the recipient's name.
- **HTML & Plain Text Support:** Sends a primary HTML email along with a plain-text fallback to ensure compatibility with all email clients.
- **Smart Delay:** Includes a configurable delay between emails to avoid hitting Gmail's spam filters and rate limits.
- **Detailed Logging:** Generates a full `send_log.txt` output detailing successes and errors for each recipient.
- **Graceful Error Handling:** Skips invalid addresses without stopping the entire bulk job.

## Setup Instructions

### 1. Install Dependencies
Make sure you have Python 3 installed. Then, install the required packages:
```bash
pip install -r requirements.txt
```

### 2. Configure Credentials
Copy the `.env.example` file to a new file named `.env`:
```bash
cp .env.example .env
```
Open `.env` and fill in your Gmail credentials. **Note:** You must use an [App Password](https://myaccount.google.com/apppasswords), not your regular Gmail password.

### 3. Add Recipients
Create a file named `recipients.csv` in the root directory (you can use `recipients.example.csv` as a template). 
Ensure it has a header row exactly like this:
```csv
name,email
John Doe,john@example.com
Jane Smith,jane@example.com
```

### 4. Customize the Email Content
- **HTML Template:** Edit `email_template.html` to design your email. Make sure to use table-based layouts with inline CSS for the best compatibility across mobile email clients. 
- **Plain Text Template:** Open `bulk_email_sender.py` and modify the `html_to_plain()` function to match your HTML content.

*Tip: Anywhere you place `{name}` in your templates will be replaced with the name from the CSV!*

## Usage
Run the script from your terminal:
```bash
python bulk_email_sender.py
```
The script will load the recipients, display a summary of what it's about to do, and wait for you to type `yes` before proceeding.

## Important Notes on Privacy
- Your `.env` and `recipients.csv` files are automatically ignored by Git (via `.gitignore`) to prevent accidental leaks of credentials or personal email lists.
- A `send_log.txt` is generated locally on every run but is also ignored by Git for privacy.
