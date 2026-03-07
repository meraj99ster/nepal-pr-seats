import requests
from collections import Counter

import pandas as pd
import streamlit as st

API_URL = (
    "https://election.onlinekhabar.com/wp-json/okelapi/v1/2082/home/"
    "election-results?limit=10"
)


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
                "ShortName": p["party_nickname"],
                "Logo": p["party_image"],
                "Votes": int(p["samanupatik"]),
            }
        )

    return pd.DataFrame(records)


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
    st.set_page_config(page_title="Nepal PR Seat Calculator", layout="centered")

    st.markdown(
        """
        <style>
        .main { background: #f8f9ff; }
        .nepal-header {
            padding: 1rem 1.5rem;
            border-radius: 10px;
            background: linear-gradient(90deg, #DC143C, #002B7F);
            color: white;
            margin-bottom: 1.5rem;
        }
        .nepal-header h1 { font-size: 1.8rem; margin: 0; }
        .nepal-header p { margin: 0.2rem 0 0; font-size: 0.9rem; opacity: 0.9; }
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

    with st.sidebar:
        st.markdown("### Settings")
        total_seats = st.number_input(
            "Total proportional seats",
            min_value=1,
            max_value=500,
            value=110,
            step=1,
        )
        run_btn = st.button("Fetch & calculate")

    if not run_btn:
        st.info("Set total seats on the left and click **Fetch & calculate**.")
        return

    try:
        df_all = fetch_parties_df()
    except Exception as e:
        st.error(f"Error fetching votes: {e}")
        return

    seat_counts = sainte_lague_from_df(df_all, int(total_seats))
    df_all["Seats"] = df_all["Slug"].map(seat_counts).fillna(0).astype(int)

    # Only full name for display
    df_all["PartyDisplay"] = df_all["FullName"]

    # We are keeping independents; no filtering
    df_view = df_all.copy()

    df_view = df_view.sort_values(
        ["Seats", "Votes"], ascending=[False, False]
    ).reset_index(drop=True)
    df_view["VotesFormatted"] = df_view["Votes"].map(lambda x: f"{x:,}")
    df_view["SeatsFormatted"] = df_view["Seats"].map(lambda x: f"{x:,}")

    st.subheader("Proportional seats by party")

    # Build a simple table with logos
    for _, row in df_view.iterrows():
        cols = st.columns([1, 4, 2, 2])
        with cols[0]:
            st.image(row["Logo"], width=40)
        with cols[1]:
            st.markdown(f"**{row['PartyDisplay']}**")
        with cols[2]:
            st.markdown(f"Votes: {row['VotesFormatted']}")
        with cols[3]:
            st.markdown(f"Seats: {row['SeatsFormatted']}")

    total_allocated = df_all["Seats"].sum()
    st.markdown(
        f"<p style='margin-top:0.8rem;font-weight:600;'>Total seats allocated: "
        f"<span style='color:#DC143C;'>{total_allocated:,}</span></p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
