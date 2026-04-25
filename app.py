from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).parent
PROFILE_PATH = BASE_DIR / "data" / "expo_profile.json"
LEADS_PATH = BASE_DIR / "data" / "leads.csv"
ROWS = ["A", "B", "C", "D", "E"]
COLUMNS = list(range(1, 11))
STATUS_ORDER = ["Booked", "Reserved", "Available"]
STATUS_COLORS = {
    "Booked": "#C24D2C",
    "Reserved": "#D9A404",
    "Available": "#2E8B57",
}
ZONE_SCORES = {"Diamond": 95, "Prime": 80, "Standard": 65}


def load_profile() -> dict:
    with PROFILE_PATH.open("r", encoding="utf-8") as profile_file:
        return json.load(profile_file)


def load_seed_leads() -> pd.DataFrame:
    leads = pd.read_csv(LEADS_PATH)
    leads["budget_inr"] = leads["budget_inr"].astype(int)
    return leads


def build_seed_stalls(profile: dict) -> pd.DataFrame:
    booked_clients = {
        "A01": ("Metro Retail Labs", "Retail Tech", "Mumbai"),
        "A02": ("FreshRoot Foods", "FMCG", "Pune"),
        "A03": ("Orbit Displays", "Visual Merchandising", "Delhi"),
        "A04": ("Zenith Beauty", "Beauty", "Bengaluru"),
        "B01": ("RapidKart", "Retail", "Noida"),
        "B02": ("Nova Pack Systems", "Packaging", "Ahmedabad"),
        "B03": ("Warehouse Hub", "Logistics", "Hyderabad"),
        "B04": ("Mercato POS", "Retail Tech", "Gurugram"),
        "B05": ("Casa Loom", "Home Decor", "Jaipur"),
        "C01": ("Glow Foods", "FMCG", "Indore"),
        "C02": ("Circuit Avenue", "Consumer Electronics", "Chennai"),
        "D01": ("Swift Ship India", "Logistics", "Surat"),
        "D02": ("Craft Colony", "Lifestyle", "Kolkata"),
    }
    reserved_clients = {
        "A05": ("Urban Threads", "D2C Fashion", "Bengaluru"),
        "A06": ("Lotus Home Decor", "Home Decor", "Delhi"),
        "B06": ("GreenShelf Organics", "FMCG", "Chandigarh"),
        "C03": ("Merchant Stack", "Retail Tech", "Gurugram"),
        "C04": ("FreshBite Foods", "FMCG", "Pune"),
        "D03": ("Swift Logistics", "Logistics", "Hyderabad"),
    }

    stalls: list[dict] = []
    for row_name in ROWS:
        zone = zone_from_row(row_name)
        multiplier = profile["zone_multipliers"][zone]
        price = int(round(profile["base_stall_price_inr"] * multiplier, -3))
        for column_number in COLUMNS:
            stall_id = f"{row_name}{column_number:02d}"
            status = "Available"
            client = "Open Inventory"
            category = "Open"
            city = "Pan India"

            if stall_id in booked_clients:
                status = "Booked"
                client, category, city = booked_clients[stall_id]
            elif stall_id in reserved_clients:
                status = "Reserved"
                client, category, city = reserved_clients[stall_id]

            stalls.append(
                {
                    "stall_id": stall_id,
                    "row": row_name,
                    "column": column_number,
                    "zone": zone,
                    "status": status,
                    "client": client,
                    "category": category,
                    "city": city,
                    "area_sqft": profile["stall_area_sqft"],
                    "price_inr": price,
                    "footfall_score": ZONE_SCORES[zone],
                }
            )

    return pd.DataFrame(stalls)


def zone_from_row(row_name: str) -> str:
    if row_name == "A":
        return "Diamond"
    if row_name in {"B", "C"}:
        return "Prime"
    return "Standard"


def initialize_state(profile: dict) -> None:
    if "stalls_df" not in st.session_state:
        st.session_state.stalls_df = build_seed_stalls(profile)
    if "leads_df" not in st.session_state:
        st.session_state.leads_df = load_seed_leads()


def reset_demo_data(profile: dict) -> None:
    st.session_state.stalls_df = build_seed_stalls(profile)
    st.session_state.leads_df = load_seed_leads()


def format_inr(value: float) -> str:
    return f"Rs. {value:,.0f}"


def calculate_metrics(stalls: pd.DataFrame) -> dict:
    total_stalls = len(stalls)
    booked = int((stalls["status"] == "Booked").sum())
    reserved = int((stalls["status"] == "Reserved").sum())
    available = int((stalls["status"] == "Available").sum())
    confirmed_sales = int(stalls.loc[stalls["status"] == "Booked", "price_inr"].sum())
    hot_pipeline = int(stalls.loc[stalls["status"] == "Reserved", "price_inr"].sum())
    committed_area = int(stalls.loc[stalls["status"] != "Available", "area_sqft"].sum())
    occupancy = ((booked + reserved) / total_stalls) * 100

    return {
        "booked": booked,
        "reserved": reserved,
        "available": available,
        "confirmed_sales": confirmed_sales,
        "hot_pipeline": hot_pipeline,
        "committed_area": committed_area,
        "occupancy": occupancy,
        "total_stalls": total_stalls,
    }


def render_stall_grid(stalls: pd.DataFrame, selected_stall: str) -> str:
    ordered_stalls = stalls.sort_values(by=["row", "column"])
    cards = []
    for _, stall in ordered_stalls.iterrows():
        status_class = stall["status"].lower()
        selected_class = " selected" if stall["stall_id"] == selected_stall else ""
        cards.append(
            dedent(
                f"""
                <div class="stall-card {status_class}{selected_class}">
                    <span class="stall-id">{stall["stall_id"]}</span>
                    <span class="stall-zone">{stall["zone"]}</span>
                    <span class="stall-client">{stall["client"]}</span>
                </div>
                """
            ).strip()
        )

    return f'<div class="stall-grid">{"".join(cards)}</div>'


def add_booking(
    stall_id: str,
    company: str,
    city: str,
    industry: str,
    booking_stage: str,
    note: str,
) -> None:
    stalls_df = st.session_state.stalls_df.copy()
    stall_index = stalls_df.index[stalls_df["stall_id"] == stall_id]
    if stall_index.empty:
        return

    row_index = stall_index[0]
    stalls_df.loc[row_index, "status"] = booking_stage
    stalls_df.loc[row_index, "client"] = company.strip() or "Pending client"
    stalls_df.loc[row_index, "city"] = city.strip() or "TBD"
    stalls_df.loc[row_index, "category"] = industry.strip() or "General"
    st.session_state.stalls_df = stalls_df

    leads_df = st.session_state.leads_df.copy()
    lead_status = "Won" if booking_stage == "Booked" else "Proposal Sent"
    next_action = note.strip() or "Call back with pricing and branding deck"
    next_lead_number = len(leads_df) + 1
    new_lead = pd.DataFrame(
        [
            {
                "lead_id": f"L{next_lead_number:03d}",
                "company": company.strip() or "Pending client",
                "industry": industry.strip() or "General",
                "city": city.strip() or "TBD",
                "interested_zone": stalls_df.loc[row_index, "zone"],
                "desired_stalls": 1,
                "status": lead_status,
                "budget_inr": int(stalls_df.loc[row_index, "price_inr"]),
                "next_action": next_action,
            }
        ]
    )
    st.session_state.leads_df = pd.concat([leads_df, new_lead], ignore_index=True)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top right, rgba(217, 164, 4, 0.12), transparent 24%),
                linear-gradient(180deg, #f6efe3 0%, #efe5d6 100%);
        }
        .main .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }
        h1, h2, h3 {
            font-family: Georgia, serif;
            letter-spacing: -0.02em;
        }
        .hero-panel {
            display: grid;
            grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.95fr);
            align-items: start;
            gap: 1.25rem;
            padding: 1.6rem 1.8rem;
            border-radius: 22px;
            background: linear-gradient(135deg, #1f2328 0%, #393e46 100%);
            color: #f9f5ef;
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 20px 45px rgba(31, 35, 40, 0.15);
            margin-bottom: 1.1rem;
        }
        .hero-copy {
            min-width: 0;
            max-width: 780px;
        }
        .hero-panel h1 {
            margin: 0 0 0.55rem;
            font-size: clamp(2rem, 3.1vw, 3.15rem);
            line-height: 1.02;
            text-wrap: balance;
        }
        .hero-panel p {
            margin: 0;
            color: rgba(249, 245, 239, 0.84);
        }
        .hero-panel p + p {
            margin-top: 0.55rem;
        }
        .eyebrow {
            text-transform: uppercase;
            letter-spacing: 0.18em;
            font-size: 0.72rem;
            margin-bottom: 0.7rem;
        }
        .hero-stat {
            width: 100%;
            min-width: 0;
            padding: 1rem 1.1rem;
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.08);
        }
        .hero-stat strong {
            display: block;
            font-size: 1.7rem;
            color: #ffd88a;
        }
        .metric-card {
            padding: 1rem 1.05rem;
            border-radius: 18px;
            background: rgba(255, 249, 240, 0.95);
            border: 1px solid rgba(31, 35, 40, 0.08);
            box-shadow: 0 10px 30px rgba(31, 35, 40, 0.06);
        }
        .metric-card span {
            display: block;
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #7a6753;
        }
        .metric-card strong {
            display: block;
            margin-top: 0.35rem;
            font-size: 1.55rem;
        }
        .panel-shell {
            padding: 1.1rem;
            border-radius: 18px;
            background: rgba(255, 249, 240, 0.88);
            border: 1px solid rgba(31, 35, 40, 0.08);
        }
        [data-testid="column"] {
            min-width: 0;
        }
        .stall-grid {
            display: grid;
            width: 100%;
            grid-template-columns: repeat(auto-fit, minmax(104px, 1fr));
            gap: 0.75rem;
            align-items: stretch;
        }
        .stall-card {
            min-width: 0;
            min-height: 104px;
            border-radius: 16px;
            padding: 0.8rem;
            border: 1px solid transparent;
            color: #1f2328;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.4);
            overflow: hidden;
        }
        .stall-card.available {
            background: linear-gradient(180deg, #dff5e8 0%, #bfe7cd 100%);
        }
        .stall-card.reserved {
            background: linear-gradient(180deg, #fff2c9 0%, #f0d580 100%);
        }
        .stall-card.booked {
            background: linear-gradient(180deg, #ffd3c2 0%, #f3aa8f 100%);
        }
        .stall-card.selected {
            border-color: #1f2328;
            transform: translateY(-2px);
        }
        .stall-id {
            font-weight: 700;
            font-size: 1rem;
        }
        .stall-zone {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        .stall-client {
            font-size: 0.85rem;
            line-height: 1.35;
            color: rgba(31, 35, 40, 0.82);
            overflow-wrap: anywhere;
        }
        .legend-chip {
            display: inline-block;
            margin-right: 0.55rem;
            padding: 0.3rem 0.6rem;
            border-radius: 999px;
            font-size: 0.8rem;
        }
        .legend-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-bottom: 0.35rem;
        }
        .legend-row .legend-chip {
            margin-right: 0;
        }
        .legend-booked {
            background: rgba(194, 77, 44, 0.15);
        }
        .legend-reserved {
            background: rgba(217, 164, 4, 0.18);
        }
        .legend-available {
            background: rgba(46, 139, 87, 0.15);
        }
        @media (max-width: 900px) {
            .main .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }
            .hero-panel {
                grid-template-columns: 1fr;
                padding: 1.2rem 1.15rem;
            }
            .hero-stat {
                max-width: none;
            }
            [data-baseweb="tab-list"] {
                gap: 0.35rem;
                overflow-x: auto;
                scrollbar-width: none;
                padding-bottom: 0.2rem;
            }
            [data-baseweb="tab-list"]::-webkit-scrollbar {
                display: none;
            }
            button[role="tab"] {
                white-space: nowrap;
                padding-left: 0.85rem;
                padding-right: 0.85rem;
            }
            .stall-grid {
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 0.6rem;
            }
        }
        @media (max-width: 760px) {
            .main .block-container [data-testid="stHorizontalBlock"] {
                flex-direction: column;
                gap: 0.85rem;
            }
            .main .block-container [data-testid="stHorizontalBlock"] > [data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
            }
        }
        @media (max-width: 640px) {
            .main .block-container {
                padding-top: 1rem;
                padding-left: 0.9rem;
                padding-right: 0.9rem;
            }
            .hero-panel h1 {
                font-size: 1.85rem;
            }
            .hero-panel p {
                font-size: 0.95rem;
            }
            .metric-card {
                padding: 0.9rem;
            }
            .metric-card strong {
                font-size: 1.35rem;
            }
            .panel-shell {
                padding: 0.95rem;
            }
            .stall-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .stall-card {
                min-height: 96px;
                padding: 0.7rem;
            }
            .stall-id {
                font-size: 0.95rem;
            }
            .stall-zone {
                font-size: 0.72rem;
            }
            .stall-client {
                font-size: 0.8rem;
                line-height: 1.25;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def make_price_book(
    profile: dict,
    base_price: int,
    diamond_uplift: float,
    prime_uplift: float,
) -> pd.DataFrame:
    prices = [
        {"zone": "Diamond", "stall_price_inr": int(round(base_price * diamond_uplift, -3))},
        {"zone": "Prime", "stall_price_inr": int(round(base_price * prime_uplift, -3))},
        {"zone": "Standard", "stall_price_inr": int(round(base_price, -3))},
    ]
    price_book = pd.DataFrame(prices)
    price_book["zone_count"] = price_book["zone"].map({"Diamond": 10, "Prime": 20, "Standard": 20})
    price_book["sellout_revenue_inr"] = price_book["stall_price_inr"] * price_book["zone_count"]
    return price_book


def build_revenue_scenarios(
    price_book: pd.DataFrame,
    service_revenue_per_stall: int,
    operating_cost: int,
) -> pd.DataFrame:
    scenarios = []
    for label, occupancy in [("Launch", 0.60), ("Momentum", 0.80), ("Sell-out", 1.00)]:
        ticket_revenue = int((price_book["sellout_revenue_inr"] * occupancy).sum())
        booked_stalls = int(round(price_book["zone_count"].sum() * occupancy))
        add_on_revenue = booked_stalls * service_revenue_per_stall
        gross_revenue = ticket_revenue + add_on_revenue
        scenarios.append(
            {
                "scenario": label,
                "occupancy_pct": int(occupancy * 100),
                "booked_stalls": booked_stalls,
                "ticket_revenue_inr": ticket_revenue,
                "add_on_revenue_inr": add_on_revenue,
                "gross_revenue_inr": gross_revenue,
                "projected_margin_inr": gross_revenue - operating_cost,
            }
        )
    return pd.DataFrame(scenarios)


def main() -> None:
    st.set_page_config(
        page_title="Expo Space Marketplace",
        page_icon="E",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_styles()

    profile = load_profile()
    initialize_state(profile)

    stalls_df = st.session_state.stalls_df.copy()
    leads_df = st.session_state.leads_df.copy()
    metrics = calculate_metrics(stalls_df)

    st.markdown(
        f"""
        <div class="hero-panel">
            <div class="hero-copy">
                <p class="eyebrow">Expo Space Selling Desk</p>
                <h1>{profile["expo_name"]}</h1>
                <p>Convert one large offline exhibition allocation into a tightly managed online stall-selling operation.</p>
                <p>{profile["host_city"]} | {profile["event_dates"]} | {profile["total_area_sqft"]:,} sq ft inventory</p>
            </div>
            <div class="hero-stat">
                <span>Target industries</span>
                <strong>{", ".join(profile["target_industries"][:3])}</strong>
                <p>Use the sidebar booking form to move a stall from open inventory to reserved or booked in seconds.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.header("Control Tower")
    st.sidebar.caption("Use filters to scan availability and capture fresh bookings during sales calls.")
    status_filter = st.sidebar.multiselect(
        "Stall status",
        options=STATUS_ORDER,
        default=STATUS_ORDER,
    )
    zone_filter = st.sidebar.multiselect(
        "Zone",
        options=["Diamond", "Prime", "Standard"],
        default=["Diamond", "Prime", "Standard"],
    )
    selected_stall = st.sidebar.selectbox(
        "Focus stall",
        options=stalls_df["stall_id"].tolist(),
        index=0,
    )

    with st.sidebar.form("booking_form", clear_on_submit=True):
        st.subheader("Reserve or close a stall")
        stall_to_update = st.selectbox("Stall", options=stalls_df["stall_id"].tolist(), index=0)
        company = st.text_input("Company")
        city = st.text_input("City")
        industry = st.text_input("Industry")
        booking_stage = st.selectbox("Booking stage", options=["Reserved", "Booked"])
        note = st.text_area("Next step or call note")
        submitted = st.form_submit_button("Save booking")

    if submitted:
        add_booking(stall_to_update, company, city, industry, booking_stage, note)
        st.success(f"{stall_to_update} moved to {booking_stage}.")
        st.rerun()

    if st.sidebar.button("Reset demo data"):
        reset_demo_data(profile)
        st.sidebar.success("Demo data restored.")
        st.rerun()

    filtered_stalls = stalls_df[
        stalls_df["status"].isin(status_filter) & stalls_df["zone"].isin(zone_filter)
    ].copy()

    metric_columns = st.columns(4)
    metric_payload = [
        ("Confirmed sales", format_inr(metrics["confirmed_sales"])),
        ("Hot pipeline", format_inr(metrics["hot_pipeline"])),
        ("Committed area", f'{metrics["committed_area"]:,} sq ft'),
        ("Occupancy", f'{metrics["occupancy"]:.0f}%'),
    ]
    for column, (label, value) in zip(metric_columns, metric_payload):
        column.markdown(
            f"""
            <div class="metric-card">
                <span>{label}</span>
                <strong>{value}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

    dashboard_tab, layout_tab, pipeline_tab, revenue_tab = st.tabs(
        ["Sales Command", "Expo Map", "Lead Pipeline", "Revenue Engine"]
    )

    with dashboard_tab:
        left_column, right_column = st.columns([1.2, 1])
        with left_column:
            st.subheader("Inventory pulse")
            status_summary = (
                stalls_df.groupby("status")["stall_id"]
                .count()
                .reindex(STATUS_ORDER, fill_value=0)
                .rename("stall_count")
            )
            st.bar_chart(status_summary)

            zone_summary = (
                stalls_df.groupby(["zone", "status"])["stall_id"]
                .count()
                .unstack(fill_value=0)
                .reindex(index=["Diamond", "Prime", "Standard"], fill_value=0)
            )
            st.subheader("Zone-by-zone mix")
            st.dataframe(zone_summary, use_container_width=True)

        with right_column:
            st.subheader("Current inventory")
            st.caption(f"{len(filtered_stalls)} stalls visible under the current filters.")
            inventory_view = filtered_stalls[
                ["stall_id", "zone", "status", "client", "category", "city", "price_inr"]
            ].copy()
            inventory_view["price_inr"] = inventory_view["price_inr"].map(format_inr)
            st.dataframe(inventory_view, use_container_width=True, hide_index=True)

        booked_categories = (
            stalls_df.loc[stalls_df["status"] == "Booked"]
            .groupby("category")["stall_id"]
            .count()
            .sort_values(ascending=False)
        )
        st.subheader("Booked category mix")
        st.bar_chart(booked_categories)

    with layout_tab:
        expo_left, expo_right = st.columns([1.95, 1], gap="large")
        with expo_left:
            st.subheader("50-stall expo layout")
            st.markdown(
                """
                <div class="legend-row">
                    <span class="legend-chip legend-booked">Booked</span>
                    <span class="legend-chip legend-reserved">Reserved</span>
                    <span class="legend-chip legend-available">Available</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(render_stall_grid(stalls_df, selected_stall), unsafe_allow_html=True)

        with expo_right:
            stall_details = stalls_df.set_index("stall_id").loc[selected_stall]
            st.subheader(f"Stall {selected_stall}")
            st.markdown(
                f"""
                <div class="panel-shell">
                    <p><strong>Status:</strong> {stall_details["status"]}</p>
                    <p><strong>Zone:</strong> {stall_details["zone"]}</p>
                    <p><strong>Client:</strong> {stall_details["client"]}</p>
                    <p><strong>Industry:</strong> {stall_details["category"]}</p>
                    <p><strong>City:</strong> {stall_details["city"]}</p>
                    <p><strong>Rate:</strong> {format_inr(stall_details["price_inr"])}</p>
                    <p><strong>Footfall score:</strong> {stall_details["footfall_score"]}/100</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            same_zone_options = stalls_df[
                (stalls_df["zone"] == stall_details["zone"]) & (stalls_df["status"] == "Available")
            ][["stall_id", "price_inr"]].head(5)
            st.subheader("Open options in the same zone")
            if same_zone_options.empty:
                st.info("No open stalls remain in this zone.")
            else:
                same_zone_options["price_inr"] = same_zone_options["price_inr"].map(format_inr)
                st.dataframe(same_zone_options, use_container_width=True, hide_index=True)

    with pipeline_tab:
        lead_metrics = st.columns(3)
        live_opportunities = int(leads_df["status"].isin(["Negotiation", "Qualified", "Proposal Sent"]).sum())
        pipeline_sqft = int(leads_df["desired_stalls"].sum() * profile["stall_area_sqft"])
        average_budget = int(leads_df["budget_inr"].mean())
        lead_metrics[0].metric("Open opportunities", live_opportunities)
        lead_metrics[1].metric("Requested inventory", f"{pipeline_sqft:,} sq ft")
        lead_metrics[2].metric("Average budget", format_inr(average_budget))

        st.subheader("Lead desk")
        leads_view = leads_df.sort_values(by="budget_inr", ascending=False).copy()
        leads_view["budget_inr"] = leads_view["budget_inr"].map(format_inr)
        st.dataframe(leads_view, use_container_width=True, hide_index=True)

        zone_demand = leads_df.groupby("interested_zone")["desired_stalls"].sum().reindex(
            ["Diamond", "Prime", "Standard"], fill_value=0
        )
        st.subheader("Demand by preferred zone")
        st.bar_chart(zone_demand)

    with revenue_tab:
        st.subheader("Pricing and margin simulator")
        simulator_left, simulator_right = st.columns([1, 1.1])
        with simulator_left:
            base_price = st.number_input(
                "Standard zone price per 100 sq ft stall",
                min_value=50000,
                max_value=400000,
                value=int(profile["base_stall_price_inr"]),
                step=5000,
            )
            diamond_uplift = st.slider(
                "Diamond zone multiplier",
                min_value=1.05,
                max_value=1.80,
                value=float(profile["zone_multipliers"]["Diamond"]),
                step=0.05,
            )
            prime_uplift = st.slider(
                "Prime zone multiplier",
                min_value=1.00,
                max_value=1.50,
                value=float(profile["zone_multipliers"]["Prime"]),
                step=0.05,
            )
            service_revenue = st.number_input(
                "Branding and utility upsell per sold stall",
                min_value=0,
                max_value=100000,
                value=18000,
                step=2000,
            )
            operating_cost = st.number_input(
                "Total expo operating cost",
                min_value=500000,
                max_value=10000000,
                value=3600000,
                step=100000,
            )

        with simulator_right:
            price_book = make_price_book(profile, base_price, diamond_uplift, prime_uplift)
            price_book_view = price_book.copy()
            price_book_view["stall_price_inr"] = price_book_view["stall_price_inr"].map(format_inr)
            price_book_view["sellout_revenue_inr"] = price_book_view["sellout_revenue_inr"].map(format_inr)
            st.markdown("#### Zone price book")
            st.dataframe(price_book_view, use_container_width=True, hide_index=True)

            scenarios = build_revenue_scenarios(price_book, service_revenue, operating_cost)
            full_sellout_margin = int(
                scenarios.loc[scenarios["scenario"] == "Sell-out", "projected_margin_inr"].iloc[0]
            )
            st.metric("Projected sell-out margin", format_inr(full_sellout_margin))

        scenario_view = scenarios.copy()
        money_columns = [
            "ticket_revenue_inr",
            "add_on_revenue_inr",
            "gross_revenue_inr",
            "projected_margin_inr",
        ]
        for column_name in money_columns:
            scenario_view[column_name] = scenario_view[column_name].map(format_inr)
        st.markdown("#### Revenue scenarios")
        st.dataframe(scenario_view, use_container_width=True, hide_index=True)
        st.line_chart(scenarios.set_index("scenario")["gross_revenue_inr"])


if __name__ == "__main__":
    main()
