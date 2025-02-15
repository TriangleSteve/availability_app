import streamlit as st
import pandas as pd
import pytz
from datetime import datetime
import sqlitecloud
import matplotlib.pyplot as plt
import seaborn as sns

# SQLite Cloud connection
def get_connection():
    return sqlitecloud.connect(st.secrets["sqlite_cloud"]["url"])


def plot_availability_heatmap():
    df = load_responses()
    if df is None:
        st.warning("No responses available yet.")
        return

    # Create a DataFrame to count occurrences of each time slot
    availability_counts = pd.DataFrame(0, index=utc_slots, columns=["Day 1", "Day 2"])

    for _, row in df.iterrows():
        for time in row["times_day1"].split(","):
            if time in availability_counts.index:
                availability_counts.loc[time, "Day 1"] += 1
        for time in row["times_day2"].split(","):
            if time in availability_counts.index:
                availability_counts.loc[time, "Day 2"] += 1

    # Plot the heatmap
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.heatmap(availability_counts.T, cmap="Blues", linewidths=0.5, annot=True, fmt="d", ax=ax)
    plt.xlabel("UTC Time Slots")
    plt.ylabel("Day")
    plt.title("Availability Heatmap")

    st.pyplot(fig)


# Generate half-hour time slots
utc_slots = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]
days = ["Day 1", "Day 2"]

def convert_to_utc(selected_times, timezone):
    """Convert user-selected times from their timezone to UTC."""
    user_tz = pytz.timezone(timezone)
    utc_times = {}

    for day, times in selected_times.items():
        utc_times[day] = []
        for time in times:
            if time:  # Ensure time is valid
                local_time = datetime.strptime(time, "%H:%M")
                local_time = user_tz.localize(local_time)
                utc_time = local_time.astimezone(pytz.UTC).strftime("%H:%M")
                utc_times[day].append(utc_time)
    return {day: ",".join(times) for day, times in utc_times.items()}

def save_response(name, timezone, selected_times):
    """Save user availability to SQLite Cloud."""
    utc_times = convert_to_utc(selected_times, timezone)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO availability (name, timezone, times_day1, times_day2)
        VALUES (?, ?, ?, ?)""", 
        (name, timezone, utc_times.get("Day 1", ""), utc_times.get("Day 2", ""))
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
    """Find the best two meeting times ensuring each person can attend at least one."""
    df = load_responses()
    if df is None:
        return None, None, {}, {}

    # Convert stored string times into lists
    availability_day1 = pd.DataFrame({time: [0] * len(df) for time in utc_slots})
    availability_day2 = pd.DataFrame({time: [0] * len(df) for time in utc_slots})
    attendees_day1 = {time: [] for time in utc_slots}
    attendees_day2 = {time: [] for time in utc_slots}

    for i, row in df.iterrows():
        for time in row["times_day1"].split(","):
            if time and time in attendees_day1:
                availability_day1.at[i, time] = 1
                attendees_day1[time].append(row["name"])

        for time in row["times_day2"].split(","):
            if time and time in attendees_day2:
                availability_day2.at[i, time] = 1
                attendees_day2[time].append(row["name"])


    # Combine both days to find the best time slots
    total_availability = availability_day1.add(availability_day2, fill_value=0)
    best_time_1 = total_availability.sum().idxmax()

    # Remove attendees from the first best time
    attendees_1 = set(attendees_day1[best_time_1] + attendees_day2[best_time_1])
    reduced_df = total_availability.copy()
    for i, row in df.iterrows():
        if row["name"] in attendees_1:
            reduced_df.loc[i] = 0

    best_time_2 = reduced_df.sum().idxmax() if not reduced_df.empty else None

    return best_time_1, best_time_2, attendees_day1, attendees_day2

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
    timezone = st.selectbox("Your Timezone", pytz.all_timezones, None)

    st.subheader("Select your available half-hour slots for each day:")
    selected_times = {
        "Day 1": st.multiselect("Choose time slots for Day 1", utc_slots, key="day1"),
        "Day 2": st.multiselect("Choose time slots for Day 2", utc_slots, key="day2")
    }


    if st.button("Submit"):
        if name and timezone and any(selected_times.values()):
            save_response(name, timezone, selected_times)
            st.success("Response saved successfully!")
        else:
            st.error("Please fill out all fields.")


# Add the heatmap to the "View Best Times" page
elif page == "View Best Times":
    st.title("Optimal Meeting Times")
    
    best_time_1, best_time_2, attendees_day1, attendees_day2 = find_best_meeting_times()

    if best_time_1:
        st.write(f"**Best Meeting Time #1:** {best_time_1} UTC")
        st.write("**Attendees:**", ", ".join(attendees_day1[best_time_1] + attendees_day2[best_time_1]))

        if best_time_2:
            st.write(f"\n**Best Meeting Time #2:** {best_time_2} UTC")
            st.write("**Attendees:**", ", ".join(attendees_day1[best_time_2] + attendees_day2[best_time_2]))
        else:
            st.write("\nNo second optimal time found.")
    else:
        st.warning("No responses available yet.")

    # Display the heatmap
    st.subheader("Time Slot Popularity Heatmap")
    plot_availability_heatmap()


elif page == "Admin":
    st.title("Admin Panel")
    
    if st.button("Clear Database"):
        clear_database()
        st.success("Database cleared successfully!")
