from fastapi import FastAPI, Request
from analyse_data import analyse_and_format
from dotenv import load_dotenv
import os
import requests
from god_eye_core import generate_sql_and_results
import openai
import re

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

app = FastAPI()

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    try:
        # Latest current year for dataset
        DATASET_CURRENT_YEAR = 1998
        LATEST_ORDER_DATE = "1998-05-06"

        # If user asks for a year after 1998, reply with a warning
        year_matches = re.findall(r"\b(20\d{2}|19\d{2})\b", text)
        if year_matches and any(int(year) > DATASET_CURRENT_YEAR for year in year_matches):
            reply = f"Sorry, the dataset does not have data more recent than {DATASET_CURRENT_YEAR}."
        elif text:
             # If user asks for "last 12 months", instruct LLM to use last 12 months up to LATEST_ORDER_DATE
            if re.search(r"(last|recent|previous)\s*12\s*months?", text, re.IGNORECASE):
                text += (
                    f"\n# NOTE: The latest order data in the dataset is from {LATEST_ORDER_DATE}. "
                    "Use the last 12 months up to this date in your SQL query, not the current date."
                )
            # If user asks for "last 6 months" or "6 months before that", instruct LLM to use the last 6 months up to LATEST_ORDER_DATE and the 6 months before that
            if re.search(r"(last|recent|previous)\s*6\s*months?", text, re.IGNORECASE) or re.search(r"6 months before", text, re.IGNORECASE):
                text += (
                    f"\n# NOTE: The latest order data in the dataset is from {LATEST_ORDER_DATE}. "
                    "For 'last 6 months', use the period from 1997-11-06 to 1998-05-06. "
                    "For 'the 6 months before that', use the period from 1997-05-06 to 1997-11-05. "
                    "Do NOT use NOW(), CURRENT_DATE, or intervals based on today."
                )
            # If user asks for "this year" or "last year", instruct LLM to use 1998 and 1997
            if re.search(r"\b(this|last|previous)\s+year\b", text, re.IGNORECASE):
                text += (
                    "\n# NOTE: The latest year in the dataset is 1998. "
                    "Treat 1998 as 'this year' and 1997 as 'last year' in your SQL query. "
                    "Do NOT use CURRENT_DATE or EXTRACT(YEAR FROM CURRENT_DATE)."
                )
            sql_query, results, error = generate_sql_and_results(text, openai_api_key)
            if error:
                reply = error
            elif results:
                # Shorten results if too long
                reply_lines = []
                total_len = 0
                MAX_MSG_LEN = 2000  # Leave space for analysis text
                for row in results:
                    line = str(row) + "\n"
                    if total_len + len(line) > MAX_MSG_LEN:
                        reply_lines.append("...result is shortened...")
                        break
                    reply_lines.append(line)
                    total_len += len(line)
                # Prepare a shortened results list for analysis
                if isinstance(results, list) and len(reply_lines) < len(results):
                    # Only pass the rows that fit
                    short_results = results[:len(reply_lines)-1]  # -1 for the "shortened" line
                else:
                    short_results = results
                reply = analyse_and_format(text, sql_query, short_results, openai_api_key)
            else:
                reply = "There is no data available in the dataset for this specific request."
        else:
            reply = "Please ask a valid question."
    except Exception as e:
        reply = "There is no data available in the dataset for your request. Please try again with a different question."

    if chat_id:
        requests.post(TELEGRAM_API_URL, json={
            "chat_id": chat_id,
            "text": reply
        })
    return {"ok": True}