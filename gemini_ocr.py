import datetime
import json
import os
from typing import List
from google import genai
from google.genai import types
from fastapi import FastAPI, UploadFile, File
from PIL import Image
import io
from pymongo import MongoClient

app = FastAPI()
client = genai.Client(api_key="YOUR_API_KEY_HERE")

# Connexion MongoDB
mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["ai_data"]
collection = db["tax_documents"]

# Define the specific schema you want Gemini to follow
# This ensures the output matches your existing MongoDB structure
TAX_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "documents": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "filename": {"type": "STRING"},
                    "info": {
                        "type": "OBJECT",
                        "properties": {
                            "name": {"type": "STRING"},
                            "ni_number": {"type": "STRING"},
                            "reference_number": {"type": "STRING"},
                            "date": {"type": "STRING"}
                        }
                    },
                    "tables": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "tax_year": {"type": "STRING"},
                                "data": {
                                    "type": "ARRAY",
                                    "items": {
                                        "type": "OBJECT",
                                        "properties": {
                                            "Employer/Pension provider": {"type": "STRING"},
                                            "Reference": {"type": "STRING"},
                                            "Start date": {"type": "STRING"},
                                            "End date": {"type": "STRING"},
                                            "Pay": {"type": "STRING"},
                                            "Tax": {"type": "STRING"},
                                            "Tax code": {"type": "STRING"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}


# Helper function to normalize dates
def normalize_date(date_str):
    if not date_str:
        return ""
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d %B %Y"):  # try multiple formats
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%d %B %Y")
        except:
            continue
    return date_str

@app.post("/process-document")
async def process_document(files: List[UploadFile] = File(...)):
    documents_array = []
    last_real_tax_year = None  # Tracks last valid tax year across pages

    for file in files:
        image_bytes = await file.read()
        img = Image.open(io.BytesIO(image_bytes))

        prompt = """
You are a professional tax document analyzer. I am providing ONE image from a multi-page tax document.

1. Extract the primary individual's name, NI number, and reference number.
2. A row belongs to a tax year ONLY if it is physically located directly beneath that tax year's header.
3. If a tax year header exists but has no rows beneath it, the "data" array for that year MUST be [].
4. IMPORTANT - CONTINUATION RULE:
   - If a table contains rows but NO tax year header So put it without tax year
5. DO NOT hallucinate tax years.
6. DO NOT move rows between tax years.
7. Normalize all dates and tax years to 'DD Month YYYY'.

Return ONLY valid JSON strictly following the provided schema.
"""

        # Gemini API call
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[img, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=TAX_SCHEMA
            )
        )

        

        extracted_data = json.loads(response.text)
        gemini_docs = extracted_data.get("documents", [])
        first_doc = gemini_docs[0] if gemini_docs else {}

        # Process tables
        for table in first_doc.get("tables", []):
            # Normalize table tax year
            if table.get("tax_year"):
                last_real_tax_year = table["tax_year"]
            # If tax year is missing but rows exist, assign last_real_tax_year
            if not table.get("tax_year") and table.get("data"):
                print("hi")
                if last_real_tax_year:
                    table["tax_year"] = last_real_tax_year
            # Normalize dates in rows
            for row in table.get("data", []):
                row["Start date"] = normalize_date(row.get("Start date", ""))
                row["End date"] = normalize_date(row.get("End date", ""))

        print(last_real_tax_year)
        # Append document
        documents_array.append({
            "filename": file.filename,
            "info": first_doc.get("info", {}),
            "tables": first_doc.get("tables", [])
        })

    # Store in MongoDB
    final_architecture = {
        "documents": documents_array
    }
    result = collection.insert_one(final_architecture)
    final_architecture.pop("_id", None)

    return {
        "id_database": str(result.inserted_id),
        "data": final_architecture
    }