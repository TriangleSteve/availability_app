import streamlit as st
import pandas as pd
import sqlitecloud

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
    """Find the best two meeting times ensuring each person can attend."""
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

    # Sort times by number of attendees
    sorted_times = sorted(attendees.items(), key=lambda x: len(x[1]), reverse=True)
    
    # Get the top two times
    best_times = sorted_times[:2]
    return best_times, {time: names for time, names in best_times}

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
        for time, names in best_times:
            st.write(f"**Best Meeting Time:** {time} UTC")
            st.write("**Attendees:**", ", ".join(names))
    else:
        st.warning("No responses available yet.")

elif page == "Admin":
    st.title("Admin Panel")
    
    if st.button("Clear Database"):
        clear_database()
        st.success("Database cleared successfully!")
