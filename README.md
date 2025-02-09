# Invoice Processing System

## Overview

This project is a Flask-based application that fetches emails from Gmail, extracts invoice details (including attachments), processes them, and stores the data in a PostgreSQL database. It also provides a simple dashboard to view stored invoices.

## Features

- Authenticate with Gmail API to read emails.
- Extract invoice details from email body and attachments (PDFs).
- Use OCR (pytesseract) to extract text from PDF invoices.
- Store extracted invoice details in a PostgreSQL database.
- Provide a simple web dashboard to view stored invoices.
- Ensure duplicate invoices are not stored multiple times.

## Project Structure
```
│── templates
│── Gmail API Credential
│───── credential.json
│── static
│───── attachments
│── app.py
│── utils.py
│── .env
│── requirements.txt
```

## Prerequisites

Ensure you have the following installed:

- Python 3.8+
- PostgreSQL database
- Gmail API credentials

## Setup

### 1. Clone the Repository

```bash
git clone <repo-url>
cd <repo-directory>
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

Create a `.env` file in the project root and add the following:

```env
dbname=your_database_name
user=your_database_user
password=your_database_password
host=your_database_host
port=your_database_port
```

### 4. Configure Gmail API

- Create credentials from the Google Cloud Console.
- Download `credentials.json` and place it in the project root.
- Run the app once to generate `token.json` (OAuth authentication).

### 5. Initialize Database

Ensure PostgreSQL is running and execute:

```sql
CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    sender TEXT,
    invoice_number TEXT,
    pdf_path TEXT,
    invoice_amount FLOAT,
    due_date DATE,
    UNIQUE (sender, invoice_amount, due_date)
);
```

## Running the Application

### 1. Start the Flask App

```bash
python app.py
```

### 2. Fetch and Store Emails Manually

You can trigger email fetching by running:

```bash
python -c "from app import fetch_and_store_emails; fetch_and_store_emails()"
```

## API Endpoints

### 1. Fetch Dashboard (View Invoices)

```
GET /
```

Renders the invoice dashboard.

### 2. Update Invoice

```
POST /update-invoice
```

#### Request Body (JSON):

```json
{
  "id": 1,
  "sender": "example@example.com",
  "invoice_number": "INV-1234",
  "invoice_amount": 120.50,
  "due_date": "2025-02-01"
}
```

#### Response:

```json
{
  "message": "Invoice updated successfully!"
}
```

## Logging

Logs are displayed in the console. To enable file logging, update the `logging.basicConfig` configuration in `app.py`.

## Troubleshooting

- **Error: `token.json` not found?** Run the app once to generate it.
- **Emails not fetching?** Check if Gmail API credentials are valid.
- **Database connection issues?** Ensure PostgreSQL is running and credentials are correct.

## License

This project is licensed under the MIT License.

