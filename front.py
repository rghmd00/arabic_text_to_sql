import streamlit as st
import requests
from src.chat_bot_ui import render_hr_database_query

API_URL = "http://localhost:8000/query"

def main():
    render_hr_database_query()
    # =============================
    # User Input
    # =============================
    question = st.text_input("Enter your question:")

    # =============================
    # Submit Button
    # =============================
    if st.button("Run Query"):
        if not question.strip():
            st.warning("Please enter a question")
        else:
            with st.spinner("Querying database..."):
                try:
                    response = requests.post(
                        API_URL,
                        json={"question": question},
                        timeout=60
                    )

                    if response.status_code != 200:
                        st.error(f"API Error: {response.text}")
                    else:
                        data = response.json()

                        # =============================
                        # Display Answer
                        # =============================
                        st.success(data["answer"])

                        # =============================
                        # Display SQL
                        # =============================
                        st.subheader("Generated SQL")
                        st.code(data["sql_query"], language="sql")

                        # =============================
                        # Display Results
                        # =============================
                        st.subheader("Results")
                        if data["results"]:
                            st.dataframe(data["results"])
                        else:
                            st.info("No results returned")

                except requests.exceptions.RequestException as e:
                    st.error(f"Connection error: {e}")


if __name__ == "__main__":
    main()




# اعرض اسم القسم ومتوسط الرواتب فيه، لكن بس للأقسام اللي متوسط الرواتب أعلى من متوسط رواتب الشركة كلها
# مين الموظفين اللي اشتغلوا في نفس الوظيفة لمدة أطول من متوسط مدة الوظيفة لكل الموظفين؟
# اعرض الموظفين اللي تم تعيينهم قبل مديرهم
# اعرض الأقسام اللي ما فيهاش أي موظف راتبه أعلى من متوسط راتب الشركة
# اعرض متوسط المرتبات لكل Department، ورتّبهم من الأعلى للأقل.
#مين الموظفين اللي مرتباتهم أعلى من متوسط المرتبات في القسم بتاعهم؟

