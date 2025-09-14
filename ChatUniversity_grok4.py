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
    # Handle CSV
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file, low_memory=False)
        # Try type inference for numeric columns
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except Exception:
                pass

    # Handle Excel
    elif uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)

    # Create DuckDB connection
    conn = duckdb.connect(database=":memory:")
    conn.register("unis", df)

    st.success("✅ Data loaded and registered in DuckDB!")

    # Show preview
    st.write("### Data Preview", df.head())

    # Get available columns
    all_columns = list(df.columns)

    # User question
    question = st.text_area("Ask a question about the data")

    if st.button("Generate SQL with Groq") and question.strip():
        # Build prompt
        prompt = f"""
        You are a SQL assistant. The table is named "unis". 
        Available columns are: {all_columns}.

        Convert the following question into a valid DuckDB SQL query:
        Question: {question}

        Only return the SQL query. Do not add ```sql or extra formatting.
        """

        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            sql_query = response.choices[0].message.content.strip()

            # Clean formatting
            sql_query = re.sub(r"^```sql|```$", "", sql_query).strip()

            # Auto-quote problematic column names
            for col in all_columns:
                if not col.isidentifier() or col[0].isdigit():
                    pattern = r'\b' + re.escape(col) + r'\b'
                    sql_query = re.sub(pattern, f'"{col}"', sql_query)

            st.code(sql_query, language="sql")

            # Run query immediately
            try:
                result = conn.execute(sql_query).fetchdf()
                st.success("✅ Query executed successfully")
                st.dataframe(result)

                # Optional: plot numeric results
                if len(result.columns) >= 2:
                    numeric_cols = result.select_dtypes(include=["int", "float"]).columns
                    if len(numeric_cols) >= 1:
                        st.bar_chart(result.set_index(result.columns[0])[numeric_cols])
            except Exception as e:
                st.error(f"❌ Error executing query: {e}")

        except Exception as e:
            st.error(f"❌ Groq API error: {e}")
