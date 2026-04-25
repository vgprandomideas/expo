from __future__ import annotations

import hashlib
import hmac
import json
import math
import secrets
from datetime import datetime
from pathlib import Path
from textwrap import dedent

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
APP_DATA_PATH = DATA_DIR / "app_data.json"
PROFILE_PATH = DATA_DIR / "expo_profile.json"
LEADS_PATH = DATA_DIR / "leads.csv"
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "ExpoAdmin@123"
DEFAULT_STALLS_PER_ROW = 10
STATUS_ORDER = ["Booked", "Reserved", "Available"]
ZONE_SCORES = {"Diamond": 95, "Prime": 80, "Standard": 65}
BOOKED_CLIENTS = {
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
RESERVED_CLIENTS = {
    "A05": ("Urban Threads", "D2C Fashion", "Bengaluru"),
    "A06": ("Lotus Home Decor", "Home Decor", "Delhi"),
    "B06": ("GreenShelf Organics", "FMCG", "Chandigarh"),
    "C03": ("Merchant Stack", "Retail Tech", "Gurugram"),
    "C04": ("FreshBite Foods", "FMCG", "Pune"),
    "D03": ("Swift Logistics", "Logistics", "Hyderabad"),
}
STALL_COLUMNS = [
    "stall_id",
    "zone",
    "status",
    "client",
    "category",
    "city",
    "contact_person",
    "phone",
    "email",
    "price_inr",
    "remarks",
]
LEAD_COLUMNS = [
    "lead_id",
    "company",
    "industry",
    "city",
    "interested_zone",
    "desired_stalls",
    "status",
    "budget_inr",
    "contact_person",
    "phone",
    "email",
    "owner",
    "next_action",
]


def now_timestamp() -> str:
    return datetime.now().strftime("%d %b %Y %I:%M %p")


def parse_multi_value(text: str) -> list[str]:
    cleaned = text.replace("\n", ",")
    values = [value.strip() for value in cleaned.split(",")]
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen


def format_inr(value: float) -> str:
    return f"Rs. {value:,.0f}"


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        180_000,
    ).hex()
    return salt, password_hash


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        180_000,
    ).hex()
    return hmac.compare_digest(candidate, password_hash)


def load_seed_profile() -> dict:
    with PROFILE_PATH.open("r", encoding="utf-8") as profile_file:
        return json.load(profile_file)


def load_seed_leads() -> list[dict]:
    leads_df = pd.read_csv(LEADS_PATH).fillna("")
    leads_df["budget_inr"] = leads_df["budget_inr"].astype(int)
    leads = leads_df.to_dict("records")
    for lead in leads:
        lead.setdefault("contact_person", "")
        lead.setdefault("phone", "")
        lead.setdefault("email", "")
        lead.setdefault("owner", "Sales Desk")
        lead.setdefault("created_at", now_timestamp())
    return leads


def number_to_letters(index: int) -> str:
    label = ""
    while True:
        index, remainder = divmod(index, 26)
        label = chr(65 + remainder) + label
        if index == 0:
            return label
        index -= 1


def zone_from_row_index(row_index: int, row_count: int) -> str:
    if row_count <= 1:
        return "Diamond"
    if row_count == 2:
        return "Diamond" if row_index == 0 else "Prime"
    if row_count == 3:
        return ["Diamond", "Prime", "Standard"][row_index]

    diamond_rows = max(1, math.ceil(row_count * 0.2))
    prime_rows = max(1, math.ceil(row_count * 0.4))
    standard_rows = row_count - diamond_rows - prime_rows
    if standard_rows < 1:
        prime_rows = max(1, prime_rows - (1 - standard_rows))

    if row_index < diamond_rows:
        return "Diamond"
    if row_index < diamond_rows + prime_rows:
        return "Prime"
    return "Standard"


def zone_price(expo: dict, zone: str) -> int:
    multiplier = float(expo["zone_multipliers"][zone])
    return int(round(expo["base_stall_price_inr"] * multiplier, -3))


def make_user_record(
    username: str,
    full_name: str,
    password: str,
    role: str = "sales",
    active: bool = True,
) -> dict:
    normalized_username = username.strip().lower()
    salt, password_hash = hash_password(password)
    return {
        "username": normalized_username,
        "full_name": full_name.strip() or normalized_username,
        "role": role,
        "active": active,
        "password_salt": salt,
        "password_hash": password_hash,
        "created_at": now_timestamp(),
        "updated_at": now_timestamp(),
    }


def default_stall_record(expo: dict, stall_id: str, row_label: str, column_number: int, zone: str) -> dict:
    return {
        "stall_id": stall_id,
        "row": row_label,
        "column": column_number,
        "zone": zone,
        "status": "Available",
        "client": "Open Inventory",
        "category": "Open",
        "city": "Pan India",
        "contact_person": "",
        "phone": "",
        "email": "",
        "remarks": "",
        "area_sqft": expo["stall_area_sqft"],
        "price_inr": zone_price(expo, zone),
        "rate_locked": False,
        "footfall_score": ZONE_SCORES[zone],
        "last_updated_at": now_timestamp(),
        "last_updated_by": "System",
    }


def merge_stall_record(base: dict, existing: dict | None) -> dict:
    if not existing:
        return base

    merged = base.copy()
    merged.update(
        {
            "status": existing.get("status", base["status"]),
            "client": existing.get("client", base["client"]),
            "category": existing.get("category", base["category"]),
            "city": existing.get("city", base["city"]),
            "contact_person": existing.get("contact_person", ""),
            "phone": existing.get("phone", ""),
            "email": existing.get("email", ""),
            "remarks": existing.get("remarks", ""),
            "rate_locked": existing.get("rate_locked", False),
            "last_updated_at": existing.get("last_updated_at", base["last_updated_at"]),
            "last_updated_by": existing.get("last_updated_by", base["last_updated_by"]),
        }
    )

    existing_price = int(existing.get("price_inr", base["price_inr"]))
    if merged["status"] != "Available" or merged["rate_locked"]:
        merged["price_inr"] = existing_price
    return merged


def generate_stalls(expo: dict, existing_stalls: list[dict] | None = None) -> list[dict]:
    total_stalls = int(expo["total_stalls"])
    stalls_per_row = int(expo.get("stalls_per_row", DEFAULT_STALLS_PER_ROW))
    row_count = max(1, math.ceil(total_stalls / stalls_per_row))
    existing_by_id = {stall["stall_id"]: stall for stall in existing_stalls or []}

    generated_stalls: list[dict] = []
    stall_counter = 0
    for row_index in range(row_count):
        row_label = number_to_letters(row_index)
        zone = zone_from_row_index(row_index, row_count)
        for column_number in range(1, stalls_per_row + 1):
            stall_counter += 1
            if stall_counter > total_stalls:
                break

            stall_id = f"{row_label}{column_number:02d}"
            base_stall = default_stall_record(expo, stall_id, row_label, column_number, zone)
            generated_stalls.append(merge_stall_record(base_stall, existing_by_id.get(stall_id)))

    committed_removed = [
        stall["stall_id"]
        for stall in existing_stalls or []
        if stall["status"] != "Available" and stall["stall_id"] not in {item["stall_id"] for item in generated_stalls}
    ]
    if committed_removed:
        raise ValueError(
            "Cannot reduce the layout because these stalls already have commitments: "
            + ", ".join(committed_removed[:8])
        )

    return generated_stalls


def apply_seed_assignments(stalls: list[dict]) -> list[dict]:
    stall_map = {stall["stall_id"]: stall for stall in stalls}
    for stall_id, details in BOOKED_CLIENTS.items():
        if stall_id in stall_map:
            client, category, city = details
            stall_map[stall_id].update(
                {
                    "status": "Booked",
                    "client": client,
                    "category": category,
                    "city": city,
                    "contact_person": "Sales Desk",
                    "remarks": "Seeded confirmed booking",
                    "last_updated_at": now_timestamp(),
                    "last_updated_by": "System Seed",
                }
            )
    for stall_id, details in RESERVED_CLIENTS.items():
        if stall_id in stall_map:
            client, category, city = details
            stall_map[stall_id].update(
                {
                    "status": "Reserved",
                    "client": client,
                    "category": category,
                    "city": city,
                    "contact_person": "Sales Desk",
                    "remarks": "Seeded hot pipeline reservation",
                    "last_updated_at": now_timestamp(),
                    "last_updated_by": "System Seed",
                }
            )
    return list(stall_map.values())


def build_seed_expo(profile: dict) -> dict:
    expo = {
        "expo_id": "EXPO-001",
        "expo_name": profile["expo_name"],
        "host_city": profile["host_city"],
        "venue_name": "Bombay Exhibition Centre",
        "event_dates": profile["event_dates"],
        "organizer_name": "Verslan Exhibitions",
        "status": "Selling",
        "contact_email": "ops@verslan.in",
        "contact_phone": "+91 98765 43210",
        "total_area_sqft": int(profile["total_area_sqft"]),
        "stall_area_sqft": int(profile["stall_area_sqft"]),
        "total_stalls": int(profile["total_stalls"]),
        "stalls_per_row": DEFAULT_STALLS_PER_ROW,
        "base_stall_price_inr": int(profile["base_stall_price_inr"]),
        "organizer_margin_goal_inr": int(profile["organizer_margin_goal_inr"]),
        "operating_cost_inr": 3_600_000,
        "zone_multipliers": profile["zone_multipliers"],
        "target_industries": profile["target_industries"],
        "services": ["Shell scheme", "Power connection", "Branding fascia", "Visitor promotions"],
        "notes": "Seed expo for managing offline inventory as structured stalls.",
        "created_at": now_timestamp(),
        "updated_at": now_timestamp(),
        "created_by": DEFAULT_ADMIN_USERNAME,
    }
    expo["stalls"] = apply_seed_assignments(generate_stalls(expo))
    expo["leads"] = load_seed_leads()
    return expo


def seed_app_data() -> dict:
    profile = load_seed_profile()
    return {
        "users": [
            make_user_record(DEFAULT_ADMIN_USERNAME, "Expo Administrator", DEFAULT_ADMIN_PASSWORD, role="admin")
        ],
        "expos": [build_seed_expo(profile)],
        "meta": {
            "default_credentials": {
                "username": DEFAULT_ADMIN_USERNAME,
                "password": DEFAULT_ADMIN_PASSWORD,
            }
        },
    }


def write_app_data(app_data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    APP_DATA_PATH.write_text(json.dumps(app_data, indent=2), encoding="utf-8")


def load_app_data() -> dict:
    if not APP_DATA_PATH.exists():
        app_data = seed_app_data()
        write_app_data(app_data)
        return app_data

    with APP_DATA_PATH.open("r", encoding="utf-8") as data_file:
        return json.load(data_file)


def get_user(app_data: dict, username: str | None) -> dict | None:
    if not username:
        return None
    for user in app_data["users"]:
        if user["username"] == username.strip().lower():
            return user
    return None


def authenticate_user(app_data: dict, username: str, password: str) -> dict | None:
    user = get_user(app_data, username)
    if not user or not user.get("active", True):
        return None
    if verify_password(password, user["password_salt"], user["password_hash"]):
        return user
    return None


def get_expo(app_data: dict, expo_id: str) -> dict:
    for expo in app_data["expos"]:
        if expo["expo_id"] == expo_id:
            return expo
    raise KeyError(f"Expo not found: {expo_id}")


def next_expo_id(app_data: dict) -> str:
    max_numeric = 0
    for expo in app_data["expos"]:
        numeric = "".join(ch for ch in expo["expo_id"] if ch.isdigit())
        max_numeric = max(max_numeric, int(numeric or 0))
    return f"EXPO-{max_numeric + 1:03d}"


def next_lead_id(expo: dict) -> str:
    max_numeric = 0
    for lead in expo.get("leads", []):
        numeric = "".join(ch for ch in str(lead.get("lead_id", "")) if ch.isdigit())
        max_numeric = max(max_numeric, int(numeric or 0))
    return f"L{max_numeric + 1:03d}"


def stalls_df_from_expo(expo: dict) -> pd.DataFrame:
    stalls_df = pd.DataFrame(expo.get("stalls", []))
    if stalls_df.empty:
        return pd.DataFrame(columns=STALL_COLUMNS)
    stalls_df["price_inr"] = stalls_df["price_inr"].astype(int)
    stalls_df["area_sqft"] = stalls_df["area_sqft"].astype(int)
    stalls_df["column"] = stalls_df["column"].astype(int)
    stalls_df["footfall_score"] = stalls_df["footfall_score"].astype(int)
    return stalls_df


def leads_df_from_expo(expo: dict) -> pd.DataFrame:
    leads_df = pd.DataFrame(expo.get("leads", []))
    if leads_df.empty:
        return pd.DataFrame(columns=LEAD_COLUMNS)
    leads_df["budget_inr"] = leads_df["budget_inr"].astype(int)
    leads_df["desired_stalls"] = leads_df["desired_stalls"].astype(int)
    return leads_df


def calculate_metrics(stalls: pd.DataFrame) -> dict:
    total_stalls = len(stalls)
    booked = int((stalls["status"] == "Booked").sum())
    reserved = int((stalls["status"] == "Reserved").sum())
    available = int((stalls["status"] == "Available").sum())
    confirmed_sales = int(stalls.loc[stalls["status"] == "Booked", "price_inr"].sum())
    hot_pipeline = int(stalls.loc[stalls["status"] == "Reserved", "price_inr"].sum())
    committed_area = int(stalls.loc[stalls["status"] != "Available", "area_sqft"].sum())
    occupancy = ((booked + reserved) / total_stalls) * 100 if total_stalls else 0
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
    cards: list[str] = []
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


def upsert_lead_from_stall(expo: dict, stall: dict, next_action: str, owner_name: str) -> None:
    normalized_company = stall["client"].strip().lower()
    matching_lead = None
    for lead in expo.get("leads", []):
        if lead["company"].strip().lower() == normalized_company:
            matching_lead = lead
            break

    lead_payload = {
        "company": stall["client"],
        "industry": stall["category"],
        "city": stall["city"],
        "interested_zone": stall["zone"],
        "desired_stalls": 1,
        "status": "Won" if stall["status"] == "Booked" else "Proposal Sent",
        "budget_inr": int(stall["price_inr"]),
        "contact_person": stall.get("contact_person", ""),
        "phone": stall.get("phone", ""),
        "email": stall.get("email", ""),
        "owner": owner_name,
        "next_action": next_action or "Follow up on stall commitment and branding details",
        "updated_at": now_timestamp(),
    }

    if matching_lead:
        matching_lead.update(lead_payload)
    else:
        lead_payload["lead_id"] = next_lead_id(expo)
        lead_payload["created_at"] = now_timestamp()
        expo.setdefault("leads", []).append(lead_payload)


def update_stall(
    expo: dict,
    stall_id: str,
    status: str,
    company: str,
    city: str,
    industry: str,
    contact_person: str,
    phone: str,
    email: str,
    remarks: str,
    price_inr: int,
    actor_name: str,
) -> None:
    stall = next(item for item in expo["stalls"] if item["stall_id"] == stall_id)
    auto_price = zone_price(expo, stall["zone"])
    cleaned_company = company.strip()

    if status == "Available":
        stall.update(
            {
                "status": "Available",
                "client": "Open Inventory",
                "category": "Open",
                "city": "Pan India",
                "contact_person": "",
                "phone": "",
                "email": "",
                "remarks": remarks.strip(),
                "price_inr": auto_price,
                "rate_locked": False,
                "last_updated_at": now_timestamp(),
                "last_updated_by": actor_name,
            }
        )
        return

    stall.update(
        {
            "status": status,
            "client": cleaned_company or "Pending client",
            "category": industry.strip() or "General",
            "city": city.strip() or "TBD",
            "contact_person": contact_person.strip(),
            "phone": phone.strip(),
            "email": email.strip(),
            "remarks": remarks.strip(),
            "price_inr": int(price_inr),
            "rate_locked": int(price_inr) != auto_price,
            "last_updated_at": now_timestamp(),
            "last_updated_by": actor_name,
        }
    )
    upsert_lead_from_stall(expo, stall, stall["remarks"], actor_name)


def add_manual_lead(
    expo: dict,
    company: str,
    industry: str,
    city: str,
    interested_zone: str,
    desired_stalls: int,
    status: str,
    budget_inr: int,
    contact_person: str,
    phone: str,
    email: str,
    owner: str,
    next_action: str,
) -> None:
    expo.setdefault("leads", []).append(
        {
            "lead_id": next_lead_id(expo),
            "company": company.strip(),
            "industry": industry.strip(),
            "city": city.strip(),
            "interested_zone": interested_zone,
            "desired_stalls": int(desired_stalls),
            "status": status,
            "budget_inr": int(budget_inr),
            "contact_person": contact_person.strip(),
            "phone": phone.strip(),
            "email": email.strip(),
            "owner": owner.strip(),
            "next_action": next_action.strip(),
            "created_at": now_timestamp(),
            "updated_at": now_timestamp(),
        }
    )


def save_expo_profile(
    expo: dict,
    *,
    expo_name: str,
    host_city: str,
    venue_name: str,
    event_dates: str,
    organizer_name: str,
    status: str,
    contact_email: str,
    contact_phone: str,
    total_area_sqft: int,
    stall_area_sqft: int,
    total_stalls: int,
    base_stall_price_inr: int,
    operating_cost_inr: int,
    organizer_margin_goal_inr: int,
    diamond_multiplier: float,
    prime_multiplier: float,
    standard_multiplier: float,
    target_industries: str,
    services: str,
    notes: str,
    actor_name: str,
) -> None:
    expo.update(
        {
            "expo_name": expo_name.strip(),
            "host_city": host_city.strip(),
            "venue_name": venue_name.strip(),
            "event_dates": event_dates.strip(),
            "organizer_name": organizer_name.strip(),
            "status": status,
            "contact_email": contact_email.strip(),
            "contact_phone": contact_phone.strip(),
            "total_area_sqft": int(total_area_sqft),
            "stall_area_sqft": int(stall_area_sqft),
            "total_stalls": int(total_stalls),
            "base_stall_price_inr": int(base_stall_price_inr),
            "operating_cost_inr": int(operating_cost_inr),
            "organizer_margin_goal_inr": int(organizer_margin_goal_inr),
            "zone_multipliers": {
                "Diamond": float(diamond_multiplier),
                "Prime": float(prime_multiplier),
                "Standard": float(standard_multiplier),
            },
            "target_industries": parse_multi_value(target_industries),
            "services": parse_multi_value(services),
            "notes": notes.strip(),
            "updated_at": now_timestamp(),
            "updated_by": actor_name,
        }
    )
    expo["stalls"] = generate_stalls(expo, expo.get("stalls", []))


def create_expo(
    app_data: dict,
    *,
    expo_name: str,
    host_city: str,
    venue_name: str,
    event_dates: str,
    organizer_name: str,
    total_area_sqft: int,
    stall_area_sqft: int,
    total_stalls: int,
    base_stall_price_inr: int,
    operating_cost_inr: int,
    organizer_margin_goal_inr: int,
    diamond_multiplier: float,
    prime_multiplier: float,
    standard_multiplier: float,
    target_industries: str,
    services: str,
    notes: str,
    actor_name: str,
) -> dict:
    expo = {
        "expo_id": next_expo_id(app_data),
        "expo_name": expo_name.strip(),
        "host_city": host_city.strip(),
        "venue_name": venue_name.strip(),
        "event_dates": event_dates.strip(),
        "organizer_name": organizer_name.strip(),
        "status": "Selling",
        "contact_email": "",
        "contact_phone": "",
        "total_area_sqft": int(total_area_sqft),
        "stall_area_sqft": int(stall_area_sqft),
        "total_stalls": int(total_stalls),
        "stalls_per_row": DEFAULT_STALLS_PER_ROW,
        "base_stall_price_inr": int(base_stall_price_inr),
        "operating_cost_inr": int(operating_cost_inr),
        "organizer_margin_goal_inr": int(organizer_margin_goal_inr),
        "zone_multipliers": {
            "Diamond": float(diamond_multiplier),
            "Prime": float(prime_multiplier),
            "Standard": float(standard_multiplier),
        },
        "target_industries": parse_multi_value(target_industries),
        "services": parse_multi_value(services),
        "notes": notes.strip(),
        "created_at": now_timestamp(),
        "updated_at": now_timestamp(),
        "created_by": actor_name,
        "stalls": [],
        "leads": [],
    }
    expo["stalls"] = generate_stalls(expo)
    app_data["expos"].append(expo)
    return expo


def create_user(app_data: dict, username: str, full_name: str, password: str, role: str) -> None:
    if get_user(app_data, username):
        raise ValueError("That username already exists.")
    app_data["users"].append(make_user_record(username, full_name, password, role=role))


def update_user_password(user: dict, new_password: str) -> None:
    salt, password_hash = hash_password(new_password)
    user["password_salt"] = salt
    user["password_hash"] = password_hash
    user["updated_at"] = now_timestamp()


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
            padding-top: 1.4rem;
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
            font-size: clamp(2rem, 3vw, 3.15rem);
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
            font-size: 1.55rem;
            color: #ffd88a;
            margin: 0.35rem 0;
        }
        .metric-card, .panel-shell, .soft-card {
            border-radius: 18px;
            background: rgba(255, 249, 240, 0.95);
            border: 1px solid rgba(31, 35, 40, 0.08);
            box-shadow: 0 10px 30px rgba(31, 35, 40, 0.06);
        }
        .metric-card {
            padding: 1rem 1.05rem;
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
        .panel-shell, .soft-card {
            padding: 1.1rem;
        }
        .soft-card h4 {
            margin: 0 0 0.55rem;
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
        .legend-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-bottom: 0.35rem;
        }
        .legend-chip {
            display: inline-block;
            padding: 0.3rem 0.6rem;
            border-radius: 999px;
            font-size: 0.8rem;
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
        .login-shell {
            padding: 1.6rem;
            border-radius: 24px;
            background: linear-gradient(135deg, #20252d 0%, #3b414b 100%);
            color: #fff5e8;
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 20px 45px rgba(31, 35, 40, 0.15);
        }
        .login-shell h1 {
            margin: 0 0 0.65rem;
            font-size: clamp(2rem, 4vw, 3.1rem);
        }
        .login-shell p {
            color: rgba(255, 245, 232, 0.86);
        }
        .mini-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.8rem;
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
            .mini-grid {
                grid-template-columns: 1fr;
            }
        }
        @media (max-width: 640px) {
            .main .block-container {
                padding-top: 1rem;
                padding-left: 0.9rem;
                padding-right: 0.9rem;
            }
            .hero-panel h1,
            .login-shell h1 {
                font-size: 1.9rem;
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
            .panel-shell, .soft-card, .login-shell {
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


def make_price_book(expo: dict, base_price: int, diamond_uplift: float, prime_uplift: float) -> pd.DataFrame:
    row_count = max(1, math.ceil(expo["total_stalls"] / expo.get("stalls_per_row", DEFAULT_STALLS_PER_ROW)))
    counts = {"Diamond": 0, "Prime": 0, "Standard": 0}
    for row_index in range(row_count):
        zone = zone_from_row_index(row_index, row_count)
        row_start = row_index * expo.get("stalls_per_row", DEFAULT_STALLS_PER_ROW)
        remaining = max(0, expo["total_stalls"] - row_start)
        counts[zone] += min(expo.get("stalls_per_row", DEFAULT_STALLS_PER_ROW), remaining)

    prices = [
        {"zone": "Diamond", "stall_price_inr": int(round(base_price * diamond_uplift, -3))},
        {"zone": "Prime", "stall_price_inr": int(round(base_price * prime_uplift, -3))},
        {"zone": "Standard", "stall_price_inr": int(round(base_price, -3))},
    ]
    price_book = pd.DataFrame(prices)
    price_book["zone_count"] = price_book["zone"].map(counts)
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


def render_login_page(app_data: dict) -> None:
    default_creds = app_data["meta"]["default_credentials"]
    left_col, right_col = st.columns([1.15, 0.85], gap="large")
    with left_col:
        st.markdown(
            """
            <div class="login-shell">
                <p class="eyebrow">Expo Operating System</p>
                <h1>Run offline expo inventory with real controls.</h1>
                <p>Manage logins, admin approvals, expo creation, stall inventory, live pipeline, pricing, and bookings from one Streamlit workspace.</p>
                <div class="mini-grid">
                    <div class="soft-card">
                        <h4>Admin controls</h4>
                        <p>Create users, reset passwords, build new expo spaces, and adjust layouts and pricing.</p>
                    </div>
                    <div class="soft-card">
                        <h4>Working inventory</h4>
                        <p>Edit stall details, reserve or book spaces, and manage more than one expo from the same app.</p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right_col:
        st.subheader("Login")
        st.info(
            f"Default admin for first run: username `{default_creds['username']}` and password `{default_creds['password']}`. Change it after login."
        )
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)

        if submitted:
            user = authenticate_user(app_data, username, password)
            if user:
                st.session_state.auth_username = user["username"]
                st.rerun()
            st.error("Invalid username or password.")


def render_sidebar(
    app_data: dict,
    current_user: dict,
    expo: dict,
    stalls_df: pd.DataFrame,
) -> tuple[list[str], list[str], str]:
    st.sidebar.header("Control Tower")
    st.sidebar.caption(f"{current_user['full_name']} | {current_user['role'].title()}")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.pop("auth_username", None)
        st.rerun()

    with st.sidebar.expander("Account", expanded=False):
        st.write(f"Username: `{current_user['username']}`")
        with st.form("change_password_form", clear_on_submit=True):
            current_password = st.text_input("Current password", type="password")
            new_password = st.text_input("New password", type="password")
            confirm_password = st.text_input("Confirm new password", type="password")
            change_password = st.form_submit_button("Change password", use_container_width=True)

        if change_password:
            if new_password != confirm_password:
                st.error("New passwords do not match.")
            elif len(new_password) < 8:
                st.error("Use at least 8 characters.")
            elif not verify_password(
                current_password,
                current_user["password_salt"],
                current_user["password_hash"],
            ):
                st.error("Current password is incorrect.")
            else:
                update_user_password(current_user, new_password)
                write_app_data(app_data)
                st.success("Password updated.")
                st.rerun()

    expo_options = [item["expo_id"] for item in app_data["expos"]]
    selected_expo_id = st.sidebar.selectbox(
        "Active expo",
        options=expo_options,
        index=expo_options.index(expo["expo_id"]),
        format_func=lambda expo_id: f"{get_expo(app_data, expo_id)['expo_name']} | {get_expo(app_data, expo_id)['host_city']}",
        key="active_expo_select",
    )
    if selected_expo_id != expo["expo_id"]:
        st.session_state.active_expo_override = selected_expo_id
        st.rerun()

    status_filter = st.sidebar.multiselect("Stall status", options=STATUS_ORDER, default=STATUS_ORDER)
    zone_filter = st.sidebar.multiselect(
        "Zone",
        options=["Diamond", "Prime", "Standard"],
        default=["Diamond", "Prime", "Standard"],
    )

    focus_key = f"focus_stall_{expo['expo_id']}"
    stall_options = stalls_df["stall_id"].tolist()
    if focus_key not in st.session_state or st.session_state[focus_key] not in stall_options:
        st.session_state[focus_key] = stall_options[0]
    selected_stall = st.sidebar.selectbox("Focus stall", options=stall_options, key=focus_key)

    with st.sidebar.form(f"booking_form_{expo['expo_id']}", clear_on_submit=True):
        st.subheader("Reserve or close a stall")
        stall_to_update = st.selectbox("Stall", options=stall_options, index=0)
        booking_stage = st.selectbox("Booking stage", options=["Reserved", "Booked"])
        company = st.text_input("Company")
        contact_person = st.text_input("Contact person")
        city = st.text_input("City")
        industry = st.text_input("Industry")
        phone = st.text_input("Phone")
        email = st.text_input("Email")
        note = st.text_area("Next step or call note")
        save_booking = st.form_submit_button("Save booking", use_container_width=True)

    if save_booking:
        if not company.strip():
            st.sidebar.error("Company is required for reserved or booked stalls.")
        else:
            stall = next(item for item in expo["stalls"] if item["stall_id"] == stall_to_update)
            update_stall(
                expo,
                stall_id=stall_to_update,
                status=booking_stage,
                company=company,
                city=city,
                industry=industry,
                contact_person=contact_person,
                phone=phone,
                email=email,
                remarks=note,
                price_inr=int(stall["price_inr"]),
                actor_name=current_user["full_name"],
            )
            expo["updated_at"] = now_timestamp()
            write_app_data(app_data)
            st.sidebar.success(f"{stall_to_update} updated.")
            st.rerun()

    return status_filter, zone_filter, selected_stall


def render_hero(expo: dict, metrics: dict) -> None:
    target_industries = ", ".join(expo["target_industries"][:3]) if expo["target_industries"] else "Custom portfolio"
    st.markdown(
        f"""
        <div class="hero-panel">
            <div class="hero-copy">
                <p class="eyebrow">Expo Space Selling Desk</p>
                <h1>{expo['expo_name']}</h1>
                <p>Convert one large offline exhibition allocation into a tightly managed online stall-selling operation.</p>
                <p>{expo['host_city']} | {expo['venue_name']} | {expo['event_dates']}</p>
                <p>{expo['total_area_sqft']:,} sq ft total area | {expo['total_stalls']} stalls | {metrics['occupancy']:.0f}% occupancy</p>
            </div>
            <div class="hero-stat">
                <span>Target industries</span>
                <strong>{target_industries}</strong>
                <p>Status: {expo['status']}</p>
                <p>Organizer: {expo['organizer_name']}</p>
                <p>Contact: {expo['contact_phone'] or 'Add phone'} | {expo['contact_email'] or 'Add email'}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_cards(metrics: dict) -> None:
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


def render_sales_command(stalls_df: pd.DataFrame, filtered_stalls: pd.DataFrame) -> None:
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
    if booked_categories.empty:
        st.info("No booked stalls yet.")
    else:
        st.bar_chart(booked_categories)


def render_expo_map(app_data: dict, expo: dict, stalls_df: pd.DataFrame, selected_stall: str, current_user: dict) -> None:
    expo_left, expo_right = st.columns([1.95, 1], gap="large")
    with expo_left:
        st.subheader(f"{expo['total_stalls']}-stall expo layout")
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
                <p><strong>Status:</strong> {stall_details['status']}</p>
                <p><strong>Zone:</strong> {stall_details['zone']}</p>
                <p><strong>Client:</strong> {stall_details['client']}</p>
                <p><strong>Industry:</strong> {stall_details['category']}</p>
                <p><strong>City:</strong> {stall_details['city']}</p>
                <p><strong>Contact:</strong> {stall_details['contact_person'] or 'Not added'}</p>
                <p><strong>Phone:</strong> {stall_details['phone'] or 'Not added'}</p>
                <p><strong>Email:</strong> {stall_details['email'] or 'Not added'}</p>
                <p><strong>Rate:</strong> {format_inr(stall_details['price_inr'])}</p>
                <p><strong>Footfall score:</strong> {stall_details['footfall_score']}/100</p>
                <p><strong>Last updated:</strong> {stall_details['last_updated_at']}</p>
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

        with st.expander("Adjust selected stall", expanded=current_user["role"] == "admin"):
            with st.form(f"stall_adjust_form_{expo['expo_id']}_{selected_stall}"):
                new_status = st.selectbox(
                    "Status",
                    options=["Available", "Reserved", "Booked"],
                    index=["Available", "Reserved", "Booked"].index(stall_details["status"]),
                )
                adjusted_price = st.number_input(
                    "Price",
                    min_value=0,
                    max_value=5000000,
                    value=int(stall_details["price_inr"]),
                    step=5000,
                )
                client = st.text_input("Company", value=stall_details["client"] if stall_details["status"] != "Available" else "")
                industry = st.text_input("Industry", value="" if stall_details["category"] == "Open" else stall_details["category"])
                city = st.text_input("City", value="" if stall_details["city"] == "Pan India" else stall_details["city"])
                contact_person = st.text_input("Contact person", value=stall_details["contact_person"])
                phone = st.text_input("Phone", value=stall_details["phone"])
                email = st.text_input("Email", value=stall_details["email"])
                remarks = st.text_area("Remarks", value=stall_details["remarks"])
                save_stall = st.form_submit_button("Save stall changes", use_container_width=True)

            if save_stall:
                if new_status != "Available" and not client.strip():
                    st.error("Company is required unless the stall is marked as Available.")
                else:
                    update_stall(
                        expo,
                        stall_id=selected_stall,
                        status=new_status,
                        company=client,
                        city=city,
                        industry=industry,
                        contact_person=contact_person,
                        phone=phone,
                        email=email,
                        remarks=remarks,
                        price_inr=int(adjusted_price),
                        actor_name=current_user["full_name"],
                    )
                    expo["updated_at"] = now_timestamp()
                    write_app_data(app_data)
                    st.success("Stall updated.")
                    st.rerun()


def render_lead_pipeline(app_data: dict, expo: dict, leads_df: pd.DataFrame, current_user: dict) -> None:
    lead_metrics = st.columns(3)
    live_opportunities = int(leads_df["status"].isin(["Negotiation", "Qualified", "Proposal Sent", "Lead In"]).sum()) if not leads_df.empty else 0
    pipeline_sqft = int(leads_df["desired_stalls"].sum() * expo["stall_area_sqft"]) if not leads_df.empty else 0
    average_budget = int(leads_df["budget_inr"].mean()) if not leads_df.empty else 0
    lead_metrics[0].metric("Open opportunities", live_opportunities)
    lead_metrics[1].metric("Requested inventory", f"{pipeline_sqft:,} sq ft")
    lead_metrics[2].metric("Average budget", format_inr(average_budget))

    with st.expander("Add lead", expanded=False):
        with st.form(f"lead_form_{expo['expo_id']}", clear_on_submit=True):
            col1, col2 = st.columns(2)
            company = col1.text_input("Company")
            industry = col2.text_input("Industry")
            city = col1.text_input("City")
            interested_zone = col2.selectbox("Interested zone", options=["Diamond", "Prime", "Standard"])
            desired_stalls = col1.number_input("Desired stalls", min_value=1, max_value=100, value=1)
            status = col2.selectbox(
                "Lead status",
                options=["Lead In", "Qualified", "Proposal Sent", "Negotiation", "Won"],
            )
            budget_inr = col1.number_input("Budget", min_value=0, max_value=100000000, value=150000, step=10000)
            contact_person = col2.text_input("Contact person")
            phone = col1.text_input("Phone")
            email = col2.text_input("Email")
            next_action = st.text_area("Next action")
            save_lead = st.form_submit_button("Add lead", use_container_width=True)

        if save_lead:
            if not company.strip():
                st.error("Company is required.")
            else:
                add_manual_lead(
                    expo,
                    company=company,
                    industry=industry,
                    city=city,
                    interested_zone=interested_zone,
                    desired_stalls=int(desired_stalls),
                    status=status,
                    budget_inr=int(budget_inr),
                    contact_person=contact_person,
                    phone=phone,
                    email=email,
                    owner=current_user["full_name"],
                    next_action=next_action,
                )
                expo["updated_at"] = now_timestamp()
                write_app_data(app_data)
                st.success("Lead added.")
                st.rerun()

    st.subheader("Lead desk")
    if leads_df.empty:
        st.info("No leads have been added to this expo yet.")
    else:
        leads_view = leads_df.sort_values(by="budget_inr", ascending=False).copy()
        leads_view["budget_inr"] = leads_view["budget_inr"].map(format_inr)
        st.dataframe(leads_view[LEAD_COLUMNS], use_container_width=True, hide_index=True)

        zone_demand = leads_df.groupby("interested_zone")["desired_stalls"].sum().reindex(
            ["Diamond", "Prime", "Standard"], fill_value=0
        )
        st.subheader("Demand by preferred zone")
        st.bar_chart(zone_demand)


def render_revenue_engine(expo: dict) -> None:
    st.subheader("Pricing and margin simulator")
    simulator_left, simulator_right = st.columns([1, 1.1])
    with simulator_left:
        base_price = st.number_input(
            "Standard zone price per stall",
            min_value=50000,
            max_value=400000,
            value=int(expo["base_stall_price_inr"]),
            step=5000,
        )
        diamond_uplift = st.slider(
            "Diamond zone multiplier",
            min_value=1.05,
            max_value=1.80,
            value=float(expo["zone_multipliers"]["Diamond"]),
            step=0.05,
        )
        prime_uplift = st.slider(
            "Prime zone multiplier",
            min_value=1.00,
            max_value=1.50,
            value=float(expo["zone_multipliers"]["Prime"]),
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
            value=int(expo["operating_cost_inr"]),
            step=100000,
        )

    with simulator_right:
        price_book = make_price_book(expo, base_price, diamond_uplift, prime_uplift)
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
    for column_name in [
        "ticket_revenue_inr",
        "add_on_revenue_inr",
        "gross_revenue_inr",
        "projected_margin_inr",
    ]:
        scenario_view[column_name] = scenario_view[column_name].map(format_inr)
    st.markdown("#### Revenue scenarios")
    st.dataframe(scenario_view, use_container_width=True, hide_index=True)
    st.line_chart(scenarios.set_index("scenario")["gross_revenue_inr"])


def render_expo_setup(app_data: dict, expo: dict, current_user: dict) -> None:
    st.subheader("Expo master controls")
    left_col, right_col = st.columns([1.15, 0.85], gap="large")
    with left_col:
        with st.form(f"expo_setup_form_{expo['expo_id']}"):
            col1, col2 = st.columns(2)
            expo_name = col1.text_input("Expo name", value=expo["expo_name"])
            host_city = col2.text_input("Host city", value=expo["host_city"])
            venue_name = col1.text_input("Venue", value=expo["venue_name"])
            event_dates = col2.text_input("Event dates", value=expo["event_dates"])
            organizer_name = col1.text_input("Organizer", value=expo["organizer_name"])
            status = col2.selectbox(
                "Expo status",
                options=["Planning", "Selling", "Sold Out", "Closed"],
                index=["Planning", "Selling", "Sold Out", "Closed"].index(expo["status"]),
            )
            contact_email = col1.text_input("Contact email", value=expo["contact_email"])
            contact_phone = col2.text_input("Contact phone", value=expo["contact_phone"])
            total_area_sqft = col1.number_input("Total area (sq ft)", min_value=100, max_value=500000, value=int(expo["total_area_sqft"]), step=100)
            stall_area_sqft = col2.number_input("Stall area (sq ft)", min_value=25, max_value=5000, value=int(expo["stall_area_sqft"]), step=25)
            total_stalls = col1.number_input("Total stalls", min_value=1, max_value=5000, value=int(expo["total_stalls"]), step=1)
            base_stall_price_inr = col2.number_input("Base stall price", min_value=10000, max_value=5000000, value=int(expo["base_stall_price_inr"]), step=5000)
            operating_cost_inr = col1.number_input("Operating cost", min_value=0, max_value=50000000, value=int(expo["operating_cost_inr"]), step=100000)
            margin_goal_inr = col2.number_input("Margin goal", min_value=0, max_value=50000000, value=int(expo["organizer_margin_goal_inr"]), step=100000)
            diamond_multiplier = col1.number_input("Diamond multiplier", min_value=1.0, max_value=3.0, value=float(expo["zone_multipliers"]["Diamond"]), step=0.05)
            prime_multiplier = col2.number_input("Prime multiplier", min_value=1.0, max_value=3.0, value=float(expo["zone_multipliers"]["Prime"]), step=0.05)
            standard_multiplier = col1.number_input("Standard multiplier", min_value=0.5, max_value=2.0, value=float(expo["zone_multipliers"]["Standard"]), step=0.05)
            target_industries = st.text_area("Target industries", value=", ".join(expo["target_industries"]))
            services = st.text_area("Services / add-ons", value=", ".join(expo["services"]))
            notes = st.text_area("Internal notes", value=expo["notes"])
            save_expo = st.form_submit_button("Save expo adjustments", use_container_width=True)

        if save_expo:
            try:
                save_expo_profile(
                    expo,
                    expo_name=expo_name,
                    host_city=host_city,
                    venue_name=venue_name,
                    event_dates=event_dates,
                    organizer_name=organizer_name,
                    status=status,
                    contact_email=contact_email,
                    contact_phone=contact_phone,
                    total_area_sqft=int(total_area_sqft),
                    stall_area_sqft=int(stall_area_sqft),
                    total_stalls=int(total_stalls),
                    base_stall_price_inr=int(base_stall_price_inr),
                    operating_cost_inr=int(operating_cost_inr),
                    organizer_margin_goal_inr=int(margin_goal_inr),
                    diamond_multiplier=float(diamond_multiplier),
                    prime_multiplier=float(prime_multiplier),
                    standard_multiplier=float(standard_multiplier),
                    target_industries=target_industries,
                    services=services,
                    notes=notes,
                    actor_name=current_user["full_name"],
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                write_app_data(app_data)
                st.success("Expo settings updated.")
                st.rerun()

    with right_col:
        st.markdown(
            f"""
            <div class="soft-card">
                <h4>Selected expo summary</h4>
                <p><strong>ID:</strong> {expo['expo_id']}</p>
                <p><strong>Spaces:</strong> {expo['total_stalls']} stalls x {expo['stall_area_sqft']} sq ft</p>
                <p><strong>Services:</strong> {", ".join(expo['services']) or 'None added'}</p>
                <p><strong>Updated:</strong> {expo.get('updated_at', expo.get('created_at', ''))}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("create_expo_form", clear_on_submit=True):
            st.markdown("#### Create new expo space")
            new_expo_name = st.text_input("Expo name")
            new_host_city = st.text_input("Host city")
            new_venue_name = st.text_input("Venue")
            new_event_dates = st.text_input("Event dates")
            new_organizer = st.text_input("Organizer")
            new_total_area = st.number_input("Total area", min_value=100, max_value=500000, value=3000, step=100)
            new_stall_area = st.number_input("Stall area", min_value=25, max_value=5000, value=100, step=25)
            new_total_stalls = st.number_input("Total stalls", min_value=1, max_value=5000, value=30, step=1)
            new_base_price = st.number_input("Base stall price", min_value=10000, max_value=5000000, value=90000, step=5000)
            new_operating_cost = st.number_input("Operating cost", min_value=0, max_value=50000000, value=1800000, step=100000)
            new_margin_goal = st.number_input("Margin goal", min_value=0, max_value=50000000, value=900000, step=100000)
            new_target_industries = st.text_area("Target industries", value="Retail, FMCG, D2C")
            new_services = st.text_area("Services", value="Shell scheme, Power connection")
            new_notes = st.text_area("Notes")
            create_expo_button = st.form_submit_button("Create expo", use_container_width=True)

        if create_expo_button:
            if not new_expo_name.strip():
                st.error("Expo name is required.")
            else:
                new_expo = create_expo(
                    app_data,
                    expo_name=new_expo_name,
                    host_city=new_host_city,
                    venue_name=new_venue_name,
                    event_dates=new_event_dates,
                    organizer_name=new_organizer,
                    total_area_sqft=int(new_total_area),
                    stall_area_sqft=int(new_stall_area),
                    total_stalls=int(new_total_stalls),
                    base_stall_price_inr=int(new_base_price),
                    operating_cost_inr=int(new_operating_cost),
                    organizer_margin_goal_inr=int(new_margin_goal),
                    diamond_multiplier=1.35,
                    prime_multiplier=1.15,
                    standard_multiplier=1.0,
                    target_industries=new_target_industries,
                    services=new_services,
                    notes=new_notes,
                    actor_name=current_user["full_name"],
                )
                write_app_data(app_data)
                st.session_state.active_expo_override = new_expo["expo_id"]
                st.success("New expo created.")
                st.rerun()


def render_admin_control(app_data: dict) -> None:
    st.subheader("Admin controls")
    left_col, right_col = st.columns([1, 1], gap="large")
    with left_col:
        with st.form("create_user_form", clear_on_submit=True):
            st.markdown("#### Create username and password")
            username = st.text_input("Username")
            full_name = st.text_input("Full name")
            role = st.selectbox("Role", options=["sales", "admin"])
            password = st.text_input("Password", type="password")
            create_user_button = st.form_submit_button("Create user", use_container_width=True)

        if create_user_button:
            if not username.strip() or not password:
                st.error("Username and password are required.")
            elif len(password) < 8:
                st.error("Password should be at least 8 characters.")
            else:
                try:
                    create_user(app_data, username, full_name, password, role)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    write_app_data(app_data)
                    st.success("User created.")
                    st.rerun()

        st.markdown("#### Users")
        users_view = pd.DataFrame(
            [
                {
                    "username": user["username"],
                    "full_name": user["full_name"],
                    "role": user["role"],
                    "active": user["active"],
                    "updated_at": user.get("updated_at", ""),
                }
                for user in app_data["users"]
            ]
        )
        st.dataframe(users_view, use_container_width=True, hide_index=True)

    with right_col:
        with st.form("user_admin_form", clear_on_submit=True):
            st.markdown("#### User controls")
            user_options = [user["username"] for user in app_data["users"]]
            selected_username = st.selectbox("User", options=user_options)
            selected_user = get_user(app_data, selected_username)
            new_role = st.selectbox(
                "Role",
                options=["sales", "admin"],
                index=["sales", "admin"].index(selected_user["role"]),
            )
            active = st.checkbox("Active", value=selected_user["active"])
            reset_password = st.text_input("Reset password", type="password")
            save_user_admin = st.form_submit_button("Save user controls", use_container_width=True)

        if save_user_admin:
            selected_user["role"] = new_role
            selected_user["active"] = active
            selected_user["updated_at"] = now_timestamp()
            if reset_password:
                if len(reset_password) < 8:
                    st.error("Reset password should be at least 8 characters.")
                else:
                    update_user_password(selected_user, reset_password)
                    write_app_data(app_data)
                    st.success("User controls updated.")
                    st.rerun()
            else:
                write_app_data(app_data)
                st.success("User controls updated.")
                st.rerun()

        st.markdown("#### System summary")
        st.markdown(
            f"""
            <div class="soft-card">
                <p><strong>Total users:</strong> {len(app_data['users'])}</p>
                <p><strong>Total expos:</strong> {len(app_data['expos'])}</p>
                <p><strong>Active users:</strong> {sum(1 for user in app_data['users'] if user['active'])}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main() -> None:
    st.set_page_config(
        page_title="Expo Space Marketplace",
        page_icon="E",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_styles()
    app_data = load_app_data()

    auth_username = st.session_state.get("auth_username")
    current_user = get_user(app_data, auth_username)
    if auth_username and (not current_user or not current_user.get("active", True)):
        st.session_state.pop("auth_username", None)
        current_user = None

    if not current_user:
        render_login_page(app_data)
        return

    expo_ids = [expo["expo_id"] for expo in app_data["expos"]]
    active_override = st.session_state.pop("active_expo_override", None)
    if active_override and active_override in expo_ids:
        active_expo_id = active_override
    else:
        active_expo_id = st.session_state.get("active_expo_select", expo_ids[0])
        if active_expo_id not in expo_ids:
            active_expo_id = expo_ids[0]

    expo = get_expo(app_data, active_expo_id)
    stalls_df = stalls_df_from_expo(expo)
    leads_df = leads_df_from_expo(expo)
    metrics = calculate_metrics(stalls_df)

    status_filter, zone_filter, selected_stall = render_sidebar(app_data, current_user, expo, stalls_df)
    filtered_stalls = stalls_df[
        stalls_df["status"].isin(status_filter) & stalls_df["zone"].isin(zone_filter)
    ].copy()

    render_hero(expo, metrics)
    render_metric_cards(metrics)

    tab_labels = ["Sales Command", "Expo Map", "Lead Pipeline", "Revenue Engine"]
    if current_user["role"] == "admin":
        tab_labels.extend(["Expo Setup", "Admin Control"])
    tabs = st.tabs(tab_labels)

    with tabs[0]:
        render_sales_command(stalls_df, filtered_stalls)

    with tabs[1]:
        render_expo_map(app_data, expo, stalls_df, selected_stall, current_user)

    with tabs[2]:
        render_lead_pipeline(app_data, expo, leads_df, current_user)

    with tabs[3]:
        render_revenue_engine(expo)

    if current_user["role"] == "admin":
        with tabs[4]:
            render_expo_setup(app_data, expo, current_user)
        with tabs[5]:
            render_admin_control(app_data)


if __name__ == "__main__":
    main()
