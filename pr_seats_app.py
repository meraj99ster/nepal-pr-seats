import requests
from collections import Counter
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup


PARTIES_URL = "https://election.onlinekhabar.com/parties"

st.set_page_config(
    page_title="Nepal PR Seat Calculator",
    page_icon="🇳🇵",
    layout="centered",
)


@st.cache_data(ttl=120)
def fetch_parties_df():
    resp = requests.get(PARTIES_URL, timeout=20)
    resp.raise_for_status()
    html = resp.text

    soup = BeautifulSoup(html, "html.parser")

    records = []

    cards = soup.select(".okel-candidate-card")
    for card in cards:
        # Party name: bold link inside the square
        square = card.select_one(".candidate-card-square")
        name = None
        if square:
            name_link = square.select_one("a.line-clamp-1")
            if name_link:
                name = name_link.get_text(strip=True)

        # Party logo
        logo_tag = card.select_one(".candidate-image-holder img")
        logo = logo_tag["src"] if logo_tag and logo_tag.has_attr("src") else None

        # समानुपातिक मत (PR votes)
        pr_votes = 0
        pr_label = card.find(string=lambda t: "समानुपातिक मत" in t)
        if pr_label:
            pr_box = pr_label.find_parent("div", class_="bg-[#F1F1F4]")
            if pr_box:
                num_tag = pr_box.find("h5")
                if num_tag:
                    raw = num_tag.get_text(strip=True)
                    raw = raw.replace(",", "").replace(" ", "").replace("٬", "")
                    nepali_digits = "०१२३४५६७८९"
                    for d, nd in enumerate(nepali_digits):
                        raw = raw.replace(nd, str(d))
                    try:
                        pr_votes = int(raw)
                    except ValueError:
                        pr_votes = 0

        if name is not None:
            records.append(
                {
                    "FullName": name,
                    "Logo": logo,
                    "Votes": pr_votes,
                }
            )

    df = pd.DataFrame(records)
    if df.empty:
        raise ValueError("Scraper found 0 parties – HTML structure may have changed.")

    fetched_at = datetime.now(timezone.utc)
    return df, fetched_at


def sainte_lague_from_df(df, total_seats=110):
    # Key directly by party name
    votes = {name: int(v) for name, v in zip(df["FullName"], df["Votes"])}

    quotients = []
    for name, v in votes.items():
        if v <= 0:
            continue
        for k in range(total_seats * 3):
            d = 2 * k + 1
            quotients.append((v / d, name))

    if not quotients:
        return Counter()

    quotients.sort(reverse=True, key=lambda x: x[0])
    top = quotients[:total_seats]

    seat_counts = Counter(name for _, name in top)
    return seat_counts


def main():
    total_seats = 110

    st.markdown(
        """
        <style>
        .main { background: #0e1117; }

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

        .party-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.5rem;
            padding: 0.45rem 0.4rem;
            border-radius: 8px;
            background-color: #ffffff;
            margin-bottom: 0.35rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.10);
        }
        .party-left {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            min-width: 0;
            flex: 1 1 auto;
        }
        .party-logo img {
            width: 30px;
            height: 30px;
            object-fit: contain;
        }
        .party-text {
            display: flex;
            flex-direction: column;
            min-width: 0;
        }
        .party-name {
            font-weight: 600;
            font-size: 0.9rem;
            color: #111827;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .party-votes {
            font-size: 0.8rem;
            color: #4b5563;
        }
        .party-right {
            text-align: right;
            margin-left: 0.4rem;
            flex: 0 0 auto;
            font-weight: 700;
            font-size: 0.9rem;
            color: #111827;
            white-space: nowrap;
        }

        @media (max-width: 480px) {
            .party-row {
                padding: 0.35rem 0.3rem;
            }
            .party-name {
                max-width: 120px;
            }
            .party-logo img {
                width: 26px;
                height: 26px;
            }
            .party-right {
                font-size: 0.85rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="nepal-header">
          <h1>Nepal PR Seat Calculator</h1>
          <p>Proportional seats from OnlineKhabar party list (HTML scraped, 3% threshold)</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.spinner("Fetching party-wise proportional votes from OnlineKhabar..."):
        try:
            df_all, fetched_at_utc = fetch_parties_df()
        except Exception as e:
            st.error(f"Error fetching/scraping votes: {e}")
            return

    if df_all.empty:
        st.error("No party vote data found on the page. HTML structure may have changed.")
        return

    # Apply 3% national threshold
    total_valid_votes = df_all["Votes"].sum()
    threshold_votes = 0.03 * total_valid_votes
    eligible = df_all[df_all["Votes"] >= threshold_votes].copy()

    # Convert to Nepal time (UTC+5:45)
    nepal_offset_minutes = 5 * 60 + 45
    fetched_local = fetched_at_utc + pd.Timedelta(minutes=nepal_offset_minutes)
    as_of_str = fetched_local.strftime("%Y-%m-%d %H:%M:%S")

    # Allocate seats only among eligible parties
    seat_counts = sainte_lague_from_df(eligible, int(total_seats))
    df_all["Seats"] = df_all["FullName"].map(seat_counts).fillna(0).astype(int)
    df_all["PartyDisplay"] = df_all["FullName"]

    df_view = df_all.copy()
    df_view = df_view.sort_values(
        ["Seats", "Votes"], ascending=[False, False]
    ).reset_index(drop=True)
    df_view["VotesFormatted"] = df_view["Votes"].map(lambda x: f"{x:,}")
    df_view["SeatsFormatted"] = df_view["Seats"].map(lambda x: f"{x:,}")

    st.markdown(f"**As of:** {as_of_str}")
    st.markdown(
        f"**Total valid PR votes:** {total_valid_votes:,} &nbsp;&nbsp; "
        f"**3% threshold:** {int(threshold_votes):,} votes"
    )

    st.subheader("Proportional seats by party")

    for _, row in df_view.iterrows():
        logo_html = ""
        if isinstance(row["Logo"], str) and row["Logo"]:
            logo_html = f'<img src="{row["Logo"]}" alt="logo">'

        st.markdown(
            f"""
            <div class="party-row">
              <div class="party-left">
                <div class="party-logo">
                  {logo_html}
                </div>
                <div class="party-text">
                  <div class="party-name">{row['PartyDisplay']}</div>
                  <div class="party-votes">Votes: {row['VotesFormatted']}</div>
                </div>
              </div>
              <div class="party-right">
                Seats: {row['SeatsFormatted']}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    total_allocated = df_all["Seats"].sum()
    st.markdown(
        f"<p style='margin-top:0.8rem;font-weight:600;'>Total seats allocated: "
        f"<span style='color:#DC143C;'>{total_allocated:,}</span></p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
