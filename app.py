from utils import get_gmail_service,fetch_emails,save_to_database,\
    analyze_email,extract_from_email_body,extract_from_pdf,fetch_invoices_from_db,\
    update_invoice_in_db

from flask import Flask, jsonify, request, render_template
from datetime import datetime

# Flask App
app = Flask(__name__)
@app.route("/")
def dashboard():
    """Render the dashboard with all invoices."""
    invoices = fetch_invoices_from_db()
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

    update_invoice_in_db(sender, invoice_number, invoice_amount, formatted_due_date, invoice_id)

    return jsonify({"message": "Invoice updated successfully!"}), 200
#
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
    # fetch_and_store_emails()
    app.run(debug=True)