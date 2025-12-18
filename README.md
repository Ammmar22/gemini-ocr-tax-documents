# Gemini OCR Tax Documents

This project is a FastAPI service that processes tax documents using the Google Gemini AI API and stores the extracted data in MongoDB. It can handle multi-page documents and correctly assigns tax years to continuation rows.

## Features

- Extracts name, NI number, reference number, and income/tax details.
- Handles multi-page documents with continuation rules for tax years.
- Normalizes all dates to `DD Month YYYY`.
- Stores results in MongoDB for easy retrieval.

## Requirements

- Python 3.12+
- MongoDB running locally or remotely
- Google Gemini AI API Key

## Installation

1. Clone the repository:

```bash
git clone https://github.com/Ammmar22/gemini-ocr-tax-documents.git
cd gemini-ocr-tax-documents
