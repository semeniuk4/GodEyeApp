import streamlit as st
import os
from god_eye_core import generate_sql_and_results
from dotenv import load_dotenv
from analyse_data import analyse_and_format  # <-- Add this import
from chart_agent import run_chart_agent, wants_chart  # <-- Import the chart agent
# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# Set page config
st.set_page_config(
    page_title="GodEye",
    page_icon="🦾",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Sidebar with instructions
with st.sidebar:
    st.title("🦾 GodEye")
    st.markdown(
        """
        **Instructions:**
        - Enter a natural language question about your data.
        - The assistant will generate an SQL query and show the results.
        - Make sure your database connection is configured.
        """
    )
    st.markdown("---")
    st.subheader("Custom Database Connection")
    use_custom_db = st.checkbox("Connect to your own database")
    db_params = {}
    connection_status = None
    if use_custom_db:
        db_params["host"] = st.text_input("Host", value="localhost")
        db_params["port"] = st.text_input("Port", value="5432")
        db_params["dbname"] = st.text_input("Database Name", value="postgres")
        db_params["user"] = st.text_input("User", value="myuser")
        db_params["password"] = st.text_input("Password", type="password")
        if st.button("Connect"):
            import psycopg2
            try:
                conn = psycopg2.connect(**db_params)
                conn.close()
                connection_status = "✅ Connected successfully!"
            except Exception as e:
                connection_status = f"❌ Connection failed: {e}"
        if connection_status:
            st.info(connection_status)

    


# Main title and description
st.markdown(
    "<h1 style='text-align: center; color: #4F8BF9;'>GodEye</h1>",
    unsafe_allow_html=True
)
st.markdown(
    "<p style='text-align: center; color: #555;'>Ask questions about your data in plain English. Get instant SQL and results!</p>",
    unsafe_allow_html=True
)

# Input box with placeholder
with st.form('chat_input_form'):
    col1, col2 = st.columns([9, 1.1])
    with col1:
        user_input = st.text_input(
            "Ask a question about your data:",
            placeholder="e.g., Show me the top 10 customers by sales",
            label_visibility='collapsed'
        )
    with col2:
        submitted = st.form_submit_button('Send')



# Main logic
if user_input and submitted:
    with st.spinner("Generating SQL and fetching results..."):
        sql_query, results, error = generate_sql_and_results(user_input, openai_api_key, db_params if use_custom_db else None)
    
    # st.markdown("#### Generated SQL Query")
    
    # st.code(sql_query, language="sql")
    if error:
        st.error(f"❌ {error}")
    elif results is not None:
        
        
        # Add analysis and formatting
        with st.spinner("Analysing and formatting results..."):
            df, analysis = analyse_and_format(user_input, sql_query, results, openai_api_key)
        if df is not None:
            
            
            if wants_chart(user_input):
                st.markdown("#### Chart Visualization")
                
                df_chart = df.reset_index(drop=True)
                # Call the chart agent
                chart_info = run_chart_agent(user_input, df_chart, openai_api_key)
                chart_type = chart_info.get("chart_type", "bar")
                x = chart_info.get("x", df_chart.columns[0])
                y = chart_info.get("y", df_chart.columns[1])
                
                try:
                # Render the chart
                    if chart_type == "bar":
                        st.bar_chart(df_chart.set_index(x)[y])
                    elif chart_type == "line":
                        st.line_chart(df_chart.set_index(x)[y])
                    elif chart_type == "pie":
                        import matplotlib.pyplot as plt
                        fig, ax = plt.subplots()
                        ax.pie(df_chart[y], labels=df_chart[x], autopct='%1.1f%%')
                        st.pyplot(fig)
                    elif chart_type == "scatter":
                        st.scatter_chart(df_chart, x=x, y=y)
                    else:
                        st.write("Chart type not supported.")
                except Exception as e:
                    st.error(f"Error rendering chart: {e}")
                
            
        else:
            st.write("No tabular results to display.")
        
        st.markdown("#### Analysis")
        st.write(analysis)
        if df is not None:
            st.dataframe(df, use_container_width=True)
        
        st.markdown("#### Generated SQL Query")
    
        st.code(sql_query, language="sql")
    else:
        st.info("No results found. Try a different question.")


# Ensure the DataFrame persists and update the chart


