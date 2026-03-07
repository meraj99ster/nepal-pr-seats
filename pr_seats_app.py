import requests
from collections import Counter
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

API_URL = (
    "https://election.onlinekhabar.com/wp-json/okelapi/v1/2082/home/"
    "election-results?limit=10"
)

st.set_page_config(
    page_title="Nepal PR Seat Calculator",
    page_icon="https://upload.wikimedia.org/wikipedia/commons/thumb/9/9b/Flag_of_Nepal.svg/64px-Flag_of_Nepal.svg.png",
    layout="centered",
)



@st.cache_data(ttl=60)
def fetch_parties_df():
    resp = requests.get(API_URL, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    parties = data["data"]["party_results"]

    records = []
    for p in parties:
        records.append(
            {
                "Slug": p["party_slug"],
                "FullName": p["party_name"],
                "Logo": p["party_image"],
                "Votes": int(p["samanupatik"]),
            }
        )

    df = pd.DataFrame(records)
    fetched_at = datetime.now(timezone.utc)
    return df, fetched_at


def sainte_lague_from_df(df, total_seats=110):
    votes = dict(zip(df["Slug"], df["Votes"]))

    quotients = []
    for slug, v in votes.items():
        for k in range(total_seats * 3):
            d = 2 * k + 1
            quotients.append((v / d, slug))

    quotients.sort(reverse=True, key=lambda x: x[0])
    top = quotients[:total_seats]

    seat_counts = Counter(s for _, s in top)
    return seat_counts


def main():
    total_seats = 110

    st.markdown(
        """
        <style>
        .main { background: #f8f9ff; }
        .nepal-header {
            padding: 1rem 1.5rem;
            border-radius: 10px;
            background: linear-gradient(90deg, #DC143C, #002B7F);
            color: white;
            margin-bottom: 1.0rem;
        }
        .nepal-header h1 { font-size: 1.4rem; margin: 0; }
        .nepal-header p { margin: 0.2rem 0 0; font-size: 0.8rem; opacity: 0.9; }
        @media (min-width: 768px) {
            .nepal-header h1 { font-size: 1.8rem; }
            .nepal-header p { font-size: 0.9rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="nepal-header">
          <h1>Nepal PR Seat Calculator</h1>
          <p>Live proportional seat estimate from Onlinekhabar results</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Loading screen
    with st.spinner("Fetching latest proportional results..."):
        try:
            df_all, fetched_at_utc = fetch_parties_df()
        except Exception as e:
            st.error(f"Error fetching votes: {e}")
            return

    # Convert to Nepal time (UTC+5:45) for display
    nepal_offset_minutes = 5 * 60 + 45
    fetched_local = fetched_at_utc + pd.Timedelta(minutes=nepal_offset_minutes)
    as_of_str = fetched_local.strftime("%Y-%m-%d %H:%M:%S")

    seat_counts = sainte_lague_from_df(df_all, int(total_seats))
    df_all["Seats"] = df_all["Slug"].map(seat_counts).fillna(0).astype(int)
    df_all["PartyDisplay"] = df_all["FullName"]

    df_view = df_all.copy()
    df_view = df_view.sort_values(
        ["Seats", "Votes"], ascending=[False, False]
    ).reset_index(drop=True)
    df_view["VotesFormatted"] = df_view["Votes"].map(lambda x: f"{x:,}")
    df_view["SeatsFormatted"] = df_view["Seats"].map(lambda x: f"{x:,}")

    st.markdown(f"**As of:** {as_of_str}")

    st.subheader("Proportional seats by party")

    for _, row in df_view.iterrows():
        cols = st.columns([1, 3, 2])
        with cols[0]:
            st.image(row["Logo"], width=40)
        with cols[1]:
            st.markdown(f"**{row['PartyDisplay']}**")
            st.markdown(
                f"<span style='font-size:0.85rem;'>Votes: {row['VotesFormatted']}</span>",
                unsafe_allow_html=True,
            )
        with cols[2]:
            st.markdown(
                f"<span style='font-size:0.9rem;font-weight:600;'>Seats: {row['SeatsFormatted']}</span>",
                unsafe_allow_html=True,
            )

    total_allocated = df_all["Seats"].sum()
    st.markdown(
        f"<p style='margin-top:0.8rem;font-weight:600;'>Total seats allocated: "
        f"<span style='color:#DC143C;'>{total_allocated:,}</span></p>",
        unsafe_allow_html=True,
    )


main()
