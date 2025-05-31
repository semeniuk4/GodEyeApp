import os
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from god_eye_core import generate_sql_and_results
import slack
from analyse_data import analyse_and_format  
import time
from fastapi.responses import JSONResponse
from threading import Thread
from chart_agent import wants_chart, run_chart_agent
import matplotlib.pyplot as plt
import tempfile
import time


load_dotenv()
SLACK_BOT_TOKEN = os.getenv("SLACK_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = slack.WebClient(token=SLACK_BOT_TOKEN)
app = FastAPI()
# ...existing code...

# Set this in your .env or fetch at startup
BOT_USER_ID = os.getenv("BOT_USER_ID") # Set this in your .env or fetch at startup


bot_info = client.auth_test()
print("Bot user ID:", bot_info["user_id"])


# Temporary in-memory store (use Redis or similar in production)
recent_event_ids = {}

def cleanup_old_event_ids(ttl=60):
    now = time.time()
    for eid in list(recent_event_ids):
        if now - recent_event_ids[eid] > ttl:
            del recent_event_ids[eid]

@app.post("/slack/events")
async def slack_events(request: Request):
    data = await request.json()
    print(data)

    if data.get("type") == "url_verification":
        return {"challenge": data["challenge"]}

    event = data.get("event", {})
    event_id = data.get("event_id")

    # Deduplicate event
    if event_id in recent_event_ids:
        print(f"Ignoring duplicate event: {event_id}")
        return {"ok": True}

    recent_event_ids[event_id] = time.time()
    cleanup_old_event_ids()

    # Acknowledge first to avoid Slack retries
    Thread(target=handle_message_event, args=(event,)).start()
    return JSONResponse(content={"ok": True}, status_code=200)

def handle_message_event(event):
    if event.get("type") == "message" and "subtype" not in event:
        if event.get("user") == BOT_USER_ID or event.get("bot_id"):
            print("Ignoring message from bot itself")
            return

        channel = event["channel"]
        user_text = event.get("text", "")

        if user_text:
            sql_query, results, error = generate_sql_and_results(user_text, OPENAI_API_KEY)
            blocks = [

            ]
            if error:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":x: *Error:*\n{error}"
                    }
                })
            elif results is not None:
                df, analysis = analyse_and_format(user_text, sql_query, results, OPENAI_API_KEY)
                result_text = df.head(20).to_markdown(index=False) if df is not None else str(results)

                if df is not None and wants_chart(user_text):
                    chart_info = run_chart_agent(user_text, df, OPENAI_API_KEY)
                    chart_type = chart_info.get("chart_type", "bar")
                    x = chart_info.get("x")
                    y = chart_info.get("y")
                    
                    plt.figure()
                    if chart_type == "bar":
                        df.plot.bar(x=x, y=y)
                    elif chart_type == "line":
                        df.plot.line(x=x, y=y)
                    elif chart_type == "pie":
                        df.set_index(x)[y].plot.pie(autopct='%1.1f%%')
                    elif chart_type == "scatter":
                        df.plot.scatter(x=x, y=y)
                    elif chart_type == "histogram":
                        df[y].plot.hist()
                    else:
                        df.plot.bar(x=x, y=y)

                    plt.title(f"{chart_type.title()} Chart of {y} vs {x}")
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
                        plt.savefig(tmpfile.name)
                        plt.close()
                        client.files_upload_v2(
                            channel=channel,
                            file=tmpfile.name,
                            title="Chart",
                            initial_comment="\n*Visualization of the data based on your request:*"
                        )
                        time.sleep(1)  # Ensure file upload completes before continuing

                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Analysis:*\n{analysis}"
                    }
                })

                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"\n```{result_text}```"
                    }
                })
                
                blocks.append(                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*SQL QUERY:*\n```{}```".format(sql_query)
                    }
                })
            else:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "_No results found._"
                    }
                })
            client.chat_postMessage(channel=channel, blocks=blocks, text="SQL Query and Answer")
