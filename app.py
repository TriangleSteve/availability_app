import streamlit as st
import pandas as pd
import sqlitecloud
from itertools import combinations

# SQLite Cloud connection
def get_connection():
    return sqlitecloud.connect(st.secrets["sqlite_cloud"]["url"])

# Generate half-hour time slots
utc_slots = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]

def save_response(name, selected_times):
    """Save user availability to SQLite Cloud."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO availability (name, times)
        VALUES (?, ?)""", 
        (name, ",".join(selected_times))
    )
    conn.commit()
    conn.close()

def load_responses():
    """Load responses from SQLite Cloud into a Pandas DataFrame."""
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM availability", conn)
    conn.close()
    return df if not df.empty else None

def find_best_meeting_times():
    """Find the best two meeting times ensuring each person can attend without repeats."""
    df = load_responses()
    if df is None:
        return None, {}, []

    attendees = {}
    for i, row in df.iterrows():
        times = row["times"].split(",")
        for time in times:
            if time not in attendees:
                attendees[time] = []
            attendees[time].append(row["name"])

    best_combination = None
    max_unique_attendees = 0
    best_attendees = {}

    # Check all combinations of two time slots
    for time1, time2 in combinations(attendees.keys(), 2):
        unique_attendees = set(attendees[time1]) | set(attendees[time2])
        if len(unique_attendees) > max_unique_attendees:
            max_unique_attendees = len(unique_attendees)
            best_combination = (time1, time2)
            best_attendees = {time1: attendees[time1], time2: attendees[time2]}

    return best_combination, best_attendees

def clear_database():
    """Clear the database table."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM availability")
    conn.commit()
    conn.close()

# Streamlit App
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Submit Availability", "View Best Times", "Admin"])

if page == "Submit Availability":
    st.title("Submit Your Availability")

    name = st.text_input("Your Name")

    st.subheader("Select your available half-hour slots for the day (Time in UTC):")
    selected_times = []
    for slot in utc_slots:
        if st.checkbox(slot):
            selected_times.append(slot)

    if st.button("Submit"):
        if name and selected_times:
            save_response(name, selected_times)
            st.success("Response saved successfully!")
        else:
            st.error("Please fill out all fields.")

elif page == "View Best Times":
    st.title("Optimal Meeting Times")
    
    best_times, attendees = find_best_meeting_times()

    if best_times:
        time1, time2 = best_times
        st.write(f"**Best Meeting Time 1:** {time1} UTC")
        st.write(f"**Best Meeting Time 2:** {time2} UTC")

        # Create a DataFrame for display
        df_display = pd.DataFrame({
            time1: attendees[time1],
            time2: attendees[time2]
        })

        # Display the DataFrame in two columns
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Attendees for {time1}**")
            st.dataframe(df_display[[time1]].rename(columns={time1: "Names"}))
        with col2:
            st.write(f"**Attendees for {time2}**")
            st.dataframe(df_display[[time2]].rename(columns={time2: "Names"}))
    else:
        st.warning("No responses available yet.")

elif page == "Admin":
    st.title("Admin Panel")
    
    if st.button("Clear Database"):
        clear_database()
        st.success
