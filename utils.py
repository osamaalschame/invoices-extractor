import os
import base64
import re
import logging
import pytesseract
from pdf2image import convert_from_path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from psycopg2 import pool

# Gmail API Config
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
TOKEN_FILE = "Gmail API Credential/token.json"
CREDENTIALS_FILE = "Gmail API Credential/credentials.json"
# extraction patterns
invoice_number_pattern = r"(?:Bill\s*No|Invoice\s*(?:Number|No\.|#))\s*[:\s]*([A-Z0-9\-]{5,})"
due_date_pattern = r"(?:Due\s*Date|Payment\s*Due\s*Date|Invoice\s*Due\s*Date|Due\s*By|Pay\s*By)[:\s-]*([\d]{4}-[\d]{2}-[\d]{2}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4}|\d{1,2}\s+[A-Za-z]+\s+\d{4}|\d{2}/\d{2}/\d{2})"
total_amount_pattern = r"(?:Total Amount|Amount Due|Total|Grand Total|Invoice Total|Balance Due)[:\s]*[\$€£]?\s*([\d,]+\.\d{2})"  # Matches amounts like "$123.45"

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

# Save Attachment
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

# Extract Email Body
def extract_email_body(msg):
    """Retrieve email body content."""
    if 'parts' in msg['payload']:
        for part in msg['payload']['parts']:
            if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                data = part['body']['data']
                return base64.urlsafe_b64decode(data).decode('utf-8')
    return ""   

# Extract Field
def extract_field(pattern, text, is_float=False):
    """Extracts a field from text using regex."""
    match = re.search(pattern, text, re.IGNORECASE)  # Case-insensitive matching
    return float(match.group(1)) if is_float and match else match.group(1) if match else None

# Extract Invoice Details from Email Body
def extract_from_email_body(body):
    """Extract invoice details from plain text email body."""
    return {
        "invoice_number": extract_field(invoice_number_pattern, body),
        "invoice_amount": normalize_amount(extract_field(total_amount_pattern, body)),
        "due_date": extract_field(due_date_pattern, body)
    }

# Analyze_email
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
    
# normalize_amount
def normalize_amount(amount_str):
    """Normalize amount by removing commas and currency symbols."""
    if not amount_str:
        return None
    return float(amount_str.replace(",", "").replace("$", "").replace("€", "").replace("£", ""))

# Extract from PDF
def extract_from_pdf(pdf_path):
    """Extract invoice details from a PDF using OCR."""
    try:
        # Convert PDF pages to images
        pages = convert_from_path(pdf_path,dpi=300)
        extracted_text = "\n".join(pytesseract.image_to_string(page, config="--psm 6 --oem 3") for page in pages)

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
                data.get("invoice_number"),  
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

# fetch_invoices_from_db
def fetch_invoices_from_db():
    """Fetch invoices from the database and remove duplicates."""
    conn = DB_POOL.getconn()
    cursor = conn.cursor()
    
    # Fetch all rows from the invoices table
    cursor.execute("SELECT * FROM invoices")
    rows = cursor.fetchall()
    
    # Use a set to track seen unique identifiers and a list to store unique invoices
    seen = set()
    unique_invoices = []
    
    for row in rows:
        # Define a unique key based on sender, invoice_amount, and due_date
        unique_key = (row[1],row[2],row[3], row[4], row[5])  # (sender,invoice_number,invoice_pdf, invoice_amount, due_date)
        
        # Check if the key has already been seen
        if unique_key not in seen:
            seen.add(unique_key)  # Mark this key as seen
            unique_invoices.append({
                "id": row[0],
                "sender": row[1],
                "invoice_number": row[2],
                "pdf_path": row[3],
                "invoice_amount": row[4] if row[4] is not None else 0.00,  # Replace None with 0.00
                "due_date": row[5].strftime("%Y-%m-%d") if row[5] else None
            })
    
    cursor.close()
    DB_POOL.putconn(conn)
    
    return unique_invoices

# update_invoice_in_db
def update_invoice_in_db(sender, invoice_number, invoice_amount, formatted_due_date, invoice_id):
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