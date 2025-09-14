import os
import io
import duckdb
import pandas as pd
import streamlit as st
from groq import Groq

# ----------------------------
# Load Groq API key securely
# ----------------------------
api_key = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=api_key)

# ----------------------------
# Streamlit UI
# ----------------------------
st.title("📊 Ask Questions About Your Data (Groq + DuckDB + Streamlit)")

uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])

if uploaded_file:
    # ----------------------------
    # Load data
    # ----------------------------
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:  # Excel
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"❌ Error reading file: {e}")
        st.stop()

    # ----------------------------
    # Auto-cast numeric columns
    # ----------------------------
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="ignore")

    st.subheader("Preview of uploaded data")
    st.dataframe(df.head())

    # Register dataframe in DuckDB
    con = duckdb.connect(database=":memory:")
    con.register("unis", df)

    # ----------------------------
    # Ask natural language question
    # ----------------------------
    user_question = st.text_area("💬 Ask a question about the data")

    if st.button("Run Query"):
        if not user_question.strip():
            st.warning("⚠️ Please enter a question.")
        else:
            # ----------------------------
            # Generate SQL with Groq
            # ----------------------------
            try:
                schema_description = ", ".join([f'"{c}"' for c in df.columns])
                prompt = f"""
                You are a SQL expert. 
                The table is called "unis" with columns: {schema_description}.
                Generate a SQL query (DuckDB syntax) to answer:
                {user_question}
                Only return the SQL, no explanation or formatting.
                """

                response = client.chat.completions.create(
                    model="llama-3.1-70b-specdec",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                )

                sql_query = response.choices[0].message.content.strip()

                st.code(sql_query, language="sql")

                # ----------------------------
                # Run query in DuckDB
                # ----------------------------
                try:
                    result = con.execute(sql_query).fetchdf()
                    st.success("✅ Query executed successfully!")
                    st.dataframe(result)
                except Exception as e:
                    st.error(f"❌ Error executing query: {e}")

            except Exception as e:
                st.error(f"❌ Groq API error: {e}")
