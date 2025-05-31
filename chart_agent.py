import streamlit as st
import pandas as pd
from groq import Groq
import openai
import matplotlib.pyplot as plt
import os
from dotenv import load_dotenv



load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


client = Groq(api_key=GROQ_API_KEY)

def wants_chart(user_input: str) -> bool:
    """
    Detects if the user input contains keywords indicating a request for a chart/visualization.
    """
    chart_keywords = [
        "show", "visualize", "draw", "plot", "chart", "graph", "diagram", "display", "illustrate", "scatter", "bar", "line", "pie"
    ]
    user_input_lower = user_input.lower()
    return any(word in user_input_lower for word in chart_keywords)




def run_chart_agent(user_input, df, openai_api_key, use_groq=False, groq_client=None):
    # Detect if user specified a chart type in their input
    chart_types = ["bar", "line", "pie", "scatter", "area", "histogram"]
    user_chart_type = None
    for ct in chart_types:
        if ct in user_input.lower():
            user_chart_type = ct
            break

    prompt = f"""
    The user asked: "{user_input}"
    The data columns are: {list(df.columns)}
    IMPORTANT: You must be VERY sensitive to the exact spelling and capitalization (case) of the column names.
    Only select columns from the provided list, matching their register exactly.
    Do NOT invent or hallucinate any column names.
    If the user specified a chart type (bar, line, pie, scatter, area, histogram), you MUST use that chart type exactly.
    Suggest the most suitable chart type (bar, line, pie, scatter, etc.) and which columns to use for x and y axes (or values/labels for pie).
    Respond as JSON: {{"chart_type": "...", "x": "...", "y": "..."}}
    """
    import json

    if use_groq and groq_client is not None:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant specialized in chart generation."},
                {"role": "user", "content": prompt}
            ],
            model='llama-3.1-8b-instant',
        )
        content = chat_completion.choices[0].message.content
    else:
        client = openai.OpenAI(api_key=openai_api_key)
        chat_completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        content = chat_completion.choices[0].message.content

    try:
        chart_info = json.loads(content)
        columns = list(df.columns)
        # Validate x and y
        x = chart_info.get("x")
        y = chart_info.get("y")
        if x not in columns:
            x = columns[0]
        if y not in columns:
            y = columns[1] if len(columns) > 1 else columns[0]
        # If user specified a chart type, override
        if user_chart_type:
            chart_info["chart_type"] = user_chart_type
        chart_info["x"] = x
        chart_info["y"] = y
        return chart_info
    except Exception:
        columns = list(df.columns)
        fallback_chart = user_chart_type if user_chart_type else "bar"
        return {"chart_type": fallback_chart, "x": columns[0], "y": columns[1] if len(columns) > 1 else columns[0]}