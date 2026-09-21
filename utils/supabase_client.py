import os

import streamlit as st
from supabase import Client, create_client


@st.cache_resource
def get_supabase_client() -> Client | None:
    url = key = None
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
    except Exception:
        pass
    url = url or os.environ.get("SUPABASE_URL")
    key = key or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)
