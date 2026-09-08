# 🌱 BhoomiMitra AI

AI-powered agricultural land verification
and decision-support platform.

## Features

- Seller land listing
- Document upload
- Gemini AI document extraction
- Cross-source verification
- Deterministic verification score
- Risk detection
- AI-generated explanation
- Buyer marketplace
- AI property assistant
- Explainable verification pipeline

## Architecture

Seller
↓
Document
↓
Gemini AI
↓
Structured Land Data
↓
Verification Engine
↓
Reference Records
↓
Risk Detection
↓
Gemini Explanation
↓
Buyer Decision Support

## Technology

- Python
- Flask
- Google Gemini API
- HTML
- CSS
- JavaScript
- PyMuPDF
- Gunicorn
- Render

## Run Locally

Create virtual environment:

python -m venv venv

Activate on Windows:

venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt

Create `.env`:

GEMINI_API_KEY=your_key_here
FLASK_SECRET_KEY=your_secret

Run:

python app.py

Open:

http://127.0.0.1:5000

## Demo Reference Data

The included reference dataset is synthetic
demo data for demonstration purposes.

It is not a live government database.

## Disclaimer

BhoomiMitra AI is a decision-support prototype.
It does not replace government verification,
survey authorities, title verification,
or professional legal advice.