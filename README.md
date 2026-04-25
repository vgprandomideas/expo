# Expo Space Marketplace

Streamlit sales cockpit for operators who buy bulk exhibition area and resell it as smaller branded stalls.

This demo is built around a simple operating model:

- You secure `5,000 sq ft` of expo inventory.
- That inventory is split into `50 stalls x 100 sq ft`.
- Each stall can be sold as `Available`, `Reserved`, or `Booked`.
- The app tracks occupancy, revenue, pipeline, and lead follow-up in one place.

## What the app includes

- Executive dashboard for occupancy, confirmed sales, and hot pipeline.
- Visual expo map with `50` stalls and color-coded availability.
- Lead pipeline with example companies from across India.
- Revenue engine for testing price, upsell, and margin scenarios.
- Booking form in the sidebar to reserve or close stalls during a client call.

## Project structure

```text
expo-space-marketplace/
|-- .streamlit/config.toml
|-- app.py
|-- data/
|   |-- expo_profile.json
|   `-- leads.csv
|-- requirements.txt
`-- README.md
```

## Run locally

1. Create and activate a Python virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
streamlit run app.py
```

## Run in this workspace

This workspace uses a project-local `.packages` folder with the bundled Python runtime. To launch the app here, run:

```powershell
.\run_streamlit.ps1
```

## Next upgrades

- Persist leads and bookings to SQLite or PostgreSQL.
- Add customer login for stall reservations.
- Add invoice generation and payment tracking.
- Connect WhatsApp, email, or CRM follow-ups.
