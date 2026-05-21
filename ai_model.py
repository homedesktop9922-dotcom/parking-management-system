import sqlite3
import pandas as pd
import numpy as np

def predict_next_hours():
    conn = sqlite3.connect("parking.db")
    df = pd.read_sql_query("SELECT entry_time FROM bookings", conn)

    if len(df) < 10:
        return [5]*24

    df['entry_time'] = pd.to_datetime(df['entry_time'])
    df['hour'] = df['entry_time'].dt.hour

    hourly_counts = df.groupby('hour').size()

    predictions = []

    for h in range(24):
        if h in hourly_counts:
            val = hourly_counts[h]
        else:
            val = 0

        # smoothing
        val = val + np.random.randint(0, 3)

        predictions.append(int(val))

    return predictions