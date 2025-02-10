
# Invoice Processing System / Rechnungserfassungssystem

## Overview / Überblick

This project is a Flask-based application that fetches emails from Gmail, extracts invoice details (including attachments), processes them, and stores the data in a PostgreSQL database. It also provides a simple dashboard to view stored invoices.

Dieses Projekt ist eine Flask-basierte Anwendung, die E-Mails von Gmail abruft, Rechnungsdetails (einschließlich Anhänge) extrahiert, sie verarbeitet und die Daten in einer PostgreSQL-Datenbank speichert. Zudem stellt es ein einfaches Dashboard zur Anzeige der gespeicherten Rechnungen bereit.

## Features / Funktionen

- Authenticate with Gmail API to read emails.  
  **Authentifizierung mit der Gmail API zur E-Mail-Abfrage.**
- Extract invoice details from email body and attachments (PDFs).  
  **Extrahiert Rechnungsdetails aus dem E-Mail-Text und Anhängen (PDFs).**
- Use OCR (pytesseract) to extract text from PDF invoices.  
  **Verwendet OCR (pytesseract), um Text aus PDF-Rechnungen zu extrahieren.**
- Store extracted invoice details in a PostgreSQL database.  
  **Speichert extrahierte Rechnungsdetails in einer PostgreSQL-Datenbank.**
- Provide a simple web dashboard to view stored invoices.  
  **Stellt ein einfaches Web-Dashboard zur Anzeige der gespeicherten Rechnungen bereit.**
- Ensure duplicate invoices are not stored multiple times.  
  **Stellt sicher, dass doppelte Rechnungen nicht mehrfach gespeichert werden.**

## Invoice Extraction Regex Patterns / Rechnungsextraktionsmuster

This document contains the accepted phrases and explanations for the following invoice extraction patterns:

Dieses Dokument enthält die akzeptierten Phrasen und Erklärungen für die folgenden Rechnungsextraktionsmuster:

### 1. Invoice Number Pattern / Rechnungsnummer Muster

#### Regex Pattern:


#### Accepted Phrases / Akzeptierte Phrasen:
- **Bill No / Rechnungs-Nr.**  
- **Invoice Number / Rechnungsnummer**  
- **Invoice No / Rechnung Nr.**  
- **Invoice # / Rechnung #**  
- **Bill # / Beleg-Nr.**  

#### Example Matches / Beispielhafte Treffer:
- **Bill No 003932234291**  
- **Invoice No: INV-12345**  
- **Invoice No: A412345**  
- **Invoice # 123456**  
- **Bill No 004005310604**  

### 2. Due Date Pattern / Fälligkeitsdatum Muster

#### Regex Pattern:

#### Accepted Phrases / Akzeptierte Phrasen:
- **Due Date / Fälligkeitsdatum**  
- **Payment Due Date / Zahlungsfälligkeitsdatum**  
- **Invoice Due Date / Rechnungsfälligkeit**  
- **Due By / Fällig bis**  
- **Pay By / Zahlung bis**  

#### Example Matches / Beispielhafte Treffer:
- **Due Date: 2023-12-31**  
- **Payment Due Date: 12/31/2023**  
- **Invoice Due Date: 31-12-2023**  
- **Due By: December 31, 2023**  
- **Pay By: 15 JUL 2024**  

### 3. Total Amount Pattern / Gesamtbetrag Muster

#### Regex Pattern:


#### Accepted Phrases / Akzeptierte Phrasen:
- **Total Amount / Gesamtbetrag**  
- **Amount Due / Fälliger Betrag**  
- **Total / Gesamt**  
- **Grand Total / Gesamtsumme**  
- **Invoice Total / Rechnungsbetrag**  
- **Balance Due / Offener Betrag**  

#### Example Matches / Beispielhafte Treffer:
- **Total Amount: $3183.25**  
- **Amount Due: €150.50**  
- **Total: 2500.75**  
- **Grand Total: £3200.00**  
- **Invoice Total: 5000.99**  

## Setup Instructions / Installationsanleitung

### 1. Clone the Repository / Klonen des Repositorys

```bash
git clone https://github.com/osamaalschame/invoices-extractor.git
cd <invoices-extractor>
```

### 2. (Optional) Create a Python Virtual Environment / (Optional) Erstellen einer Python-Umgebung
It is recommended to use a virtual environment to manage dependencies.

Es wird empfohlen, eine virtuelle Umgebung zu verwenden, um Abhängigkeiten zu verwalten.

# Create a virtual environment
```
python -m venv env
```

# Activate virtual environment (Windows)
```
env\\Scripts\\activate

```

# Activate virtual environment (Mac/Linux)
```
source env/bin/activate

```

### 2. Install Dependencies / Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables / Umgebungsvariablen einrichten

Create a `.env` file in the project root and add the following:

Eine `.env`-Datei im Projektverzeichnis erstellen und folgendes hinzufügen:

```env
dbname=your_database_name
user=your_database_user
password=your_database_password
host=your_database_host
port=your_database_port
```

### 4. Configure Gmail API / Gmail API einrichten

- Create credentials from the Google Cloud Console.  
  **Erstellen Sie Anmeldeinformationen in der Google Cloud Console.**  
- Download the credential JSON file and name it as `credentials.json`, then place it in the `Gmail API Credential` folder.  
  **Laden Sie die JSON-Datei herunter, benennen Sie sie als `credentials.json` und platzieren Sie sie im Ordner `Gmail API Credential`.**  
- Follow this video tutorial for step-by-step setup:  
  **Folgen Sie diesem Video-Tutorial für die Schritt-für-Schritt-Einrichtung:**  
  [How to Set Up Google Cloud Credentials](https://www.youtube.com/watch?v=1Ua0Eplg75M&ab_channel=OutrightSystems) 

### 5. Start the Flask App / Starten der Flask-App

```bash
python app.py
```

## Troubleshooting / Fehlerbehebung

- **Missing libraries?** Ensure all libraries are installed.  
  **Fehlende Bibliotheken? Stellen Sie sicher, dass alle Bibliotheken installiert sind.**  
- **Error: `token.json` not found?** Run the app once to generate it.  
  **Fehler: `token.json` nicht gefunden? Führen Sie die App einmal aus, um sie zu generieren.**  
- **Database connection issues?** Ensure PostgreSQL is running and credentials are correct.  
  **Probleme mit der Datenbankverbindung? Stellen Sie sicher, dass PostgreSQL läuft und die Anmeldeinformationen korrekt sind.**  
