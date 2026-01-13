import streamlit as st
import pandas as pd



@st.cache_data
def get_tables_overview(_engine):
    """Cached tables overview - runs once"""
    tables_query = """
    SELECT table_name as name, comments as description 
    FROM user_tab_comments WHERE table_type = 'TABLE'
    UNION ALL
    SELECT table_name, NULL FROM user_tables 
    WHERE table_name NOT IN (SELECT table_name FROM user_tab_comments WHERE table_type = 'TABLE')
    AND table_name NOT LIKE 'BIN$%' ORDER BY name
    """
    tables_df = pd.read_sql(tables_query, _engine)
    tables_df['الجدول'] = tables_df['name']
    tables_df['الوصف'] = tables_df['description'].fillna('لا يوجد وصف')
    return tables_df[['الجدول', 'الوصف']]

@st.cache_data
def get_tables_list(_engine):
    """Cached tables list - runs once"""
    tables_list_query = "SELECT table_name FROM user_tables WHERE table_name NOT LIKE 'BIN$%' ORDER BY table_name"
    tables_df_list = pd.read_sql(tables_list_query, _engine)
    return tables_df_list.iloc[:, 0].str.upper().tolist()

@st.cache_data
def get_table_columns(_engine, table_name):
    """Cached columns per table"""
    cols_query = f"""
    SELECT utc.column_name as name, 
           utc.data_type || CASE 
             WHEN utc.data_length IS NOT NULL AND utc.data_precision IS NULL THEN 
               '(' || utc.data_length || ')'
             WHEN utc.data_precision IS NOT NULL THEN 
               '(' || utc.data_precision || ',' || NVL(utc.data_scale, 0) || ')'
             ELSE '' END as type_name
    FROM user_tab_columns utc
    WHERE utc.table_name = UPPER('{table_name}')
    ORDER BY utc.column_id
    """
    cols_df = pd.read_sql(cols_query, _engine)
    cols_df['العمود'] = cols_df['name']
    cols_df['النوع'] = cols_df['type_name']
    return cols_df[['العمود', 'النوع']]

# INTEGRATED SIDEBAR - Zero re-runs!
def sidebar_schema(engine):
    st.markdown("## 📋 قاعدة البيانات")
    # st.markdown("**اكتشف الجداول والأعمدة**")
    
    # Tables overview - cached!
    try:
        tables_df = get_tables_overview(engine)
        st.dataframe(tables_df, width="stretch", hide_index=True)
    except:
        st.info(" قم بزيارة الدردشة أولاً للاتصال")
    

    
    # st.markdown("---")
    # st.markdown("### 🔍 جدول مفصل")
    
    # Tables list - cached!
    # try:
    #     tables_list = get_tables_list(engine)
    #     selected_table = st.selectbox("اختر جدول:", tables_list, key="sidebar_table")
        
    #     if selected_table:
    #         # Columns - cached per table!
    #         cols_df = get_table_columns(engine, selected_table)
    #         st.dataframe(cols_df, width="stretch", hide_index=True)
    # except:
    #     st.info("📊 الجداول ستظهر بعد الاتصال")


    

def render_sidebar(engine):
    with st.sidebar:
        sidebar_schema(engine)