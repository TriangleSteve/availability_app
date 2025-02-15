import streamlit as st
import pandas as pd
import sqlitecloud
from itertools import combinations

# SQLite Cloud connection
def get_connection():
    return sqlitecloud.connect(st.secrets["sqlite_cloud"]["url"])

# Generate half-hour time slots
utc_slots = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]

# Define the admin password
ADMIN_PASSWORD = "toronto"  # Change this to your desired password

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

def delete_responses(names):
    """Delete user availability from SQLite Cloud."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executemany("DELETE FROM availability WHERE name = ?", [(name,) for name in names])
    conn.commit()
    conn.close()

def clear_database():
    """Clear the database table."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM availability")
    conn.commit()
    conn.close()

# Streamlit App
st.sidebar.title("Navigation")

# Password input for admin access
password = st.sidebar.text_input("Admin Password", type="password")

# Check if the entered password is correct
is_admin = password == ADMIN_PASSWORD

# Show navigation options based on admin status
if is_admin:
    page = st.sidebar.radio("Go to", ["Event Times Intake", "Analysis", "Admin"])
else:
    page = st.sidebar.radio("Go to", ["Event Times Intake"])

if page == "Event Times Intake":
    st.title("Event Times")

    name = st.text_input("Enter Username")

    st.subheader("Choose all times available for events (UTC time):")
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

elif page == "Analysis" and is_admin:
    st.title("Optimal Meeting Times")
    
    best_times, attendees = find_best_meeting_times()

    if best_times:
        time1, time2 = best_times
        st.write(f"**Best Meeting Time 1:** {time1} UTC")
        st.write(f"**Best Meeting Time 2:** {time2} UTC")

        # Create a DataFrame for display
        max_length = max(len(attendees[time1]), len(attendees[time2]))
        df_display = pd.DataFrame({
            time1: attendees[time1] + [None] * (max_length - len(attendees[time1])),
            time2: attendees[time2] + [None] * (max_length - len(attendees[time2]))
        })

        # Display the DataFrame in two columns without index
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Attendees for {time1}**")
            st.table(df_display[[time1]].rename(columns={time1: "Names"}))
        with col2:
            st.write(f"**Attendees for {time2}**")
            st.table(df_display[[time2]].rename(columns={time2: "Names"}))
    else:
        st.warning("No responses available yet.")

elif page == "Admin" and is_admin:
    st.title("Admin Panel")

    # Load responses
    df = load_responses()

    if df is None:
        st.write("No responses found.")
    else:
        st.subheader("Current Availability Records")

        # Add a selection column for deletion
        df["selected"] = False
        edited_df = st.data_editor(
            df,
            column_config={"selected": st.column_config.CheckboxColumn("Select")},
            disabled=["name", "times"],  # Prevent direct editing
            use_container_width=True,
        )

        # Get selected names
        selected_names = edited_df[edited_df["selected"]]["name"].tolist()

        # Delete button
        if st.button("Delete Selected Responses", type="primary", disabled=not selected_names):
            delete_responses(selected_names)
            st.success(f"Deleted {len(selected_names)} responses.")
            st.experimental_rerun()  # Refresh data after deletion

    # Option to clear all data
    if st.button("Clear Database", type="secondary"):
        clear_database()
        st.success("Database cleared successfully!")
        st.experimental_rerun()


