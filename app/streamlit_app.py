"""PitWall entry point:  streamlit run app/streamlit_app.py"""
import streamlit as st

st.set_page_config(page_title="PitWall: live F1 race intelligence", page_icon="🏁", layout="wide",
                   initial_sidebar_state="expanded")

pages = [
    st.Page("views/championship.py", title="Championship", default=True),
    st.Page("views/race_lab.py", title="Race Lab"),
    st.Page("views/drivers.py", title="Drivers"),
    st.Page("views/teams.py", title="Teams"),
    st.Page("views/eras.py", title="Eras"),
    st.Page("views/method.py", title="Method and data"),
]
st.navigation(pages).run()
