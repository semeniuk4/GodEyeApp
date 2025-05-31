import openai
import pandas as pd

def analyse_and_format(user_request, sql_query, results, openai_api_key):
    if not results:
        return None, "No results found."

    # Convert results to DataFrame for pretty display
    if isinstance(results, list) and results and isinstance(results[0], dict):
        df = pd.DataFrame(results)
        table = df.head(20).to_markdown(index=False)  # Show up to 20 rows
    else:
        df = None
        table = str(results)

    prompt = (
        f"The user asked: \"{user_request}\"\n"
        f"The following SQL query was used to get the data:\n{sql_query}\n"
        f"The latest financial data in the dataset is from 1998.\n"
        f"Here are the results:\n{table}\n"
        "Please explain in plain English:\n"
        "- What the data shows in response to the user's request\n"
        "- How the result was calculated\n"
        "- Mention that the latest financial data is from 1998\n"
        "Keep it concise and readable for a non-technical user."
    )

    openai.api_key = openai_api_key
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    explanation = response.choices[0].message.content.strip()
    return df, explanation