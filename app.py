import streamlit as st
import pandas as pd
import sqlitecloud

# SQLite Cloud connection
def get_connection():
    return sqlitecloud.connect(st.secrets["sqlite_cloud"]["url"])

# Generate half-hour time slots
utc_slots = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]

def save_response(name, selected_time):
    """Save user availability to SQLite Cloud."""

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO availability (name, times)
        VALUES (?, ?)""", 
        (name, selected_time)
    )
    conn.commit()
    conn.close()

def load_responses():
    """Load responses from SQLite Cloud into a Pandas DataFrame."""
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM availability", conn)
    conn.close()
    return df if not df.empty else None

def find_best_meeting_time():
    """Find the best meeting time ensuring each person can attend."""
    df = load_responses()
    if df is None:
        return None, {}

    attendees = {}
    for i, row in df.iterrows():
        time = row["times"]
        if time:
            if time not in attendees:
                attendees[time] = []
            attendees[time].append(row["name"])

    best_time = max(attendees, key=lambda k: len(attendees[k]), default=None)
    return best_time, attendees.get(best_time, [])

def clear_database():
    """Clear the database table."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM availability")
    conn.commit()
    conn.close()

# Streamlit App
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Submit Availability", "View Best Time", "Admin"])

if page == "Submit Availability":
    st.title("Submit Your Availability")

    name = st.text_input("Your Name")

    st.subheader("Select your available half-hour slot for the day:")
    selected_time = st.selectbox("Choose a time slot", utc_slots)

    if st.button("Submit"):
        if name and selected_time:
            save_response(name, selected_time)
            st.success("Response saved successfully!")
        else:
            st.error("Please fill out all fields.")

elif page == "View Best Time":
    st.title("Optimal Meeting Time")
    
    best_time, attendees = find_best_meeting_time()

    if best_time:
        st.write(f"**Best Meeting Time:** {best_time} UTC")
        st.write("**Attendees:**", ", ".join(attendees))
    else:
        st.warning("No responses available yet.")

elif page == "Admin":
    st.title("Admin Panel")
    
    if st.button("Clear Database"):
        clear_database()
        st.success("Database cleared successfully!")
