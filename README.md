# Expo Space Marketplace

Streamlit operating system for expo operators who buy bulk exhibition area and resell it as smaller branded stalls.

This demo is built around a simple operating model:

- You secure `5,000 sq ft` of expo inventory.
- That inventory is split into `50 stalls x 100 sq ft`.
- Each stall can be sold as `Available`, `Reserved`, or `Booked`.
- The app tracks occupancy, revenue, pipeline, and lead follow-up in one place.

## What the app includes

- Login screen with username and password authentication.
- Admin controls for creating users, resetting passwords, and role management.
- Multi-expo setup so you can create and manage more than one expo space.
- Expo master controls for adjusting total stalls, stall size, pricing, services, and venue details.
- Visual expo map with editable stall details, pricing, contact fields, and booking status.
- Lead pipeline with manual lead creation and automatic lead updates from stall bookings.
- Revenue engine for testing price, upsell, and margin scenarios.

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

## First login

On first run the app seeds a default admin account:

- Username: `admin`
- Password: `ExpoAdmin@123`

Change the password from the sidebar after signing in.

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
