import os
import base64
import re
import logging
import pytesseract
from pdf2image import convert_from_path
from flask import Flask, jsonify, request, render_template,send_file
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from psycopg2 import pool
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

# Logging Setup
logging.basicConfig(level=logging.INFO)

# PostgreSQL Connection Pool
DB_POOL = pool.SimpleConnectionPool(
    1, 10,
    dbname=os.getenv("dbname"),
    user=os.getenv("user"),
    password=os.getenv("password"),
    host=os.getenv("host"),
    port=os.getenv("port")
)

# Gmail API Config
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json"

# Flask App
app = Flask(__name__)

# Authenticate Gmail API
def get_gmail_service():
    """Authenticate and return Gmail API service."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

# Fetch Emails
def fetch_emails(service):
    """Retrieve all emails from the inbox."""
    results = service.users().messages().list(userId='me', labelIds=['INBOX']).execute()
    return results.get('messages', [])

def save_attachment(service, message_id, attachment_id, filename):
    """Save an email attachment to a temporary directory."""
    temp_dir = "static/attachments"  # Use /tmp for temporary storage
    os.makedirs(temp_dir, exist_ok=True)  # Ensure the directory exists
    file_path = os.path.join(temp_dir, filename)
    
    try:
        attachment = service.users().messages().attachments().get(
            userId='me',
            messageId=message_id,
            id=attachment_id
        ).execute()
        
        file_data = base64.urlsafe_b64decode(attachment['data'])
        with open(file_path, 'wb') as f:
            f.write(file_data)
        logging.info(f"Saved attachment: {file_path}")
        return file_path
    except Exception as e:
        logging.error(f"Failed to save attachment {filename}: {e}")
        return None
def analyze_email(service, message_id):
    """Extract email details and attachments."""
    try:
        # Fetch the email message
        msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
        headers = {header['name']: header['value'] for header in msg['payload']['headers']}
        
        subject = headers.get("Subject", "").lower()
        sender = headers.get("From", "").lower()
        attachments = []
        
        # Check for attachments
        if 'parts' in msg['payload']:
            for part in msg['payload']['parts']:
                if part['filename'] and part['filename'].endswith(".pdf"):
                    attachment_id = part['body'].get('attachmentId')
                    if attachment_id:
                        file_path = save_attachment(service, message_id, attachment_id, part['filename'])
                        if file_path:
                            attachments.append(file_path)
        
        return {
            "is_invoice": any(keyword in subject for keyword in ["invoice", "bill"]),
            "sender": sender,
            "attachments": attachments,
            "body": extract_email_body(msg)
        }
    except Exception as e:
        logging.error(f"Error analyzing email {message_id}: {e}")
        return {}

# Extract Email Body
def extract_email_body(msg):
    """Retrieve email body content."""
    if 'parts' in msg['payload']:
        for part in msg['payload']['parts']:
            if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                data = part['body']['data']
                return base64.urlsafe_b64decode(data).decode('utf-8')
    return ""

# Extract Invoice Details from Email Body
def extract_from_email_body(body):
    """Extract invoice details from plain text email body."""
    return {
        "invoice_number": extract_field(r"Invoice Number: (\d+)", body),
        "invoice_amount": extract_field(r"Amount: (\d+\.\d{2})", body, is_float=True),
        "due_date": extract_field(r"Due Date: (\d{4}-\d{2}-\d{2})", body)
    }

def extract_field(pattern, text, is_float=False):
    """Extracts a field from text using regex."""
    match = re.search(pattern, text, re.IGNORECASE)  # Case-insensitive matching
    return float(match.group(1)) if is_float and match else match.group(1) if match else None

def normalize_amount(amount_str):
    """Normalize amount by removing commas and currency symbols."""
    if not amount_str:
        return None
    return float(amount_str.replace(",", "").replace("$", "").replace("€", "").replace("£", ""))

def extract_from_pdf(pdf_path):
    """Extract invoice details from a PDF using OCR."""
    try:
        # Convert PDF pages to images
        pages = convert_from_path(pdf_path)
        extracted_text = "\n".join(pytesseract.image_to_string(page, config="--psm 6") for page in pages)
        
        
        
        # Improved regex patterns
        invoice_number_pattern = r"(?:Invoice\s*(?:Number|No\.|#))[:\s]*([A-Z0-9-]{5,})"
        due_date_pattern = r"Due\s*Date[:\s]*([\d-]+)"  # Matches "Due Date: YYYY-MM-DD" or "Due Date YYYY-MM-DD"
        total_amount_pattern = r"(?:Total Amount|Amount Due|Total|Grand Total|Invoice Total|Balance Due)[:\s]*[\$€£]?\s*([\d,]+\.\d{2})"  # Matches amounts like "$123.45"

        # Extract fields
        invoice_number = extract_field(invoice_number_pattern, extracted_text)
        due_date = extract_field(due_date_pattern, extracted_text)
        total_amount = normalize_amount(extract_field(total_amount_pattern, extracted_text))
        
        # Debugging: Check if invoice_number is valid
        if invoice_number and invoice_number.lower() == "invoice":
            logging.warning("Detected 'Invoice' as invoice number. Adjusting regex...")
            invoice_number = None  # Invalidate the result
        
        return {
            "invoice_number": invoice_number,
            "invoice_amount": total_amount,
            "due_date": due_date,
            "pdf_path": pdf_path
        }
    except Exception as e:
        logging.error(f"Error processing PDF {pdf_path}: {e}")
        return {}

# Save Invoice to Database
def save_to_database(data):
    """Insert invoice data into PostgreSQL."""
    conn = DB_POOL.getconn()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id SERIAL PRIMARY KEY,
        sender TEXT,
        invoice_number TEXT,
        pdf_path TEXT,
        invoice_amount FLOAT,
        due_date DATE,
        UNIQUE (sender, invoice_amount, due_date)  -- Composite unique constraint
            )
        """)
    conn.commit()

    try:
        cursor.execute("""
                INSERT INTO invoices (sender, invoice_number,pdf_path, invoice_amount, due_date)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (sender, invoice_amount, due_date) DO NOTHING
            """, (
                data["sender"],
                data.get("invoice_number"),  # Handle missing invoice_number
                data.get("pdf_path"),
                data.get("invoice_amount"),
                data.get("due_date")
            ))
        conn.commit()
    except Exception as e:
        logging.error(f"Error inserting data: {e}")
        conn.rollback()
    finally:
        cursor.close()
        DB_POOL.putconn(conn)

def is_recurring_invoice(data):
    """Check if an invoice is recurring based on sender, amount, and due date."""
    conn = DB_POOL.getconn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) FROM invoices
        WHERE sender = %s AND invoice_amount = %s AND due_date = %s
    """, (
        data["sender"],
        data.get("invoice_amount"),
        data.get("due_date")
    ))

    count = cursor.fetchone()[0]
    cursor.close()
    DB_POOL.putconn(conn)

    return count > 0



@app.route("/")
def dashboard():
    """Render invoice dashboard."""
    conn = DB_POOL.getconn()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM invoices")
    rows = cursor.fetchall()
    
    invoices = [{
        "id": row[0],
        "sender": row[1],
        "invoice_number": row[2],
        "pdf_path": row[3],
        "invoice_amount": row[4] if row[5] is not None else 0.00,  # Replace None with 0.00
        "due_date": row[5].strftime("%Y-%m-%d") if row[5] else None
    } for row in rows]
    
    cursor.close()
    DB_POOL.putconn(conn)
    return render_template("dashboard.html", invoices=invoices)

@app.route("/update-invoice", methods=["POST"])
def update_invoice():
    """Update an invoice in the database and save the updated PDF."""
    data = request.json
    invoice_id = data.get("id")
    sender = data.get("sender")
    invoice_number = data.get("invoice_number")
    invoice_amount = data.get("invoice_amount")
    due_date = data.get("due_date")
    
    # Ensure due_date is properly formatted
    if isinstance(due_date, str):
        # If due_date is already a string, use it directly
        formatted_due_date = due_date if due_date!='' else None
    elif isinstance(due_date, datetime):
        # If due_date is a datetime object, format it as YYYY-MM-DD
        formatted_due_date = due_date.strftime("%Y-%m-%d")
    else:
        # Handle invalid or missing due_date
        formatted_due_date = None

    # Update the invoice in the database
    conn = DB_POOL.getconn()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE invoices
        SET sender = %s, invoice_number = %s, invoice_amount = %s, due_date = %s
        WHERE id = %s
    """, (sender, invoice_number, invoice_amount, formatted_due_date, invoice_id))

    conn.commit()
    cursor.close()
    DB_POOL.putconn(conn)

    return jsonify({"message": "Invoice updated successfully!"}), 200
# 
# @app.before_first_request
def fetch_and_store_emails():
    service = get_gmail_service()
    for message in fetch_emails(service):
        analysis = analyze_email(service, message['id'])
        if analysis["is_invoice"]:
            extracted_data = extract_from_email_body(analysis["body"])
            for attachment in analysis["attachments"]:
                extracted_data.update(extract_from_pdf(attachment))
            extracted_data["sender"] = analysis["sender"]
            save_to_database(extracted_data)
            

if __name__ == "__main__":

    fetch_and_store_emails()
    app.run(debug=True)