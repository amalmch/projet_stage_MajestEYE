# 📊 SONEDE Dashboard Setup — Walkthrough & Implementation Summary

We have built a complete, production-ready setup for your **SONEDE Administration Dashboard** using **Metabase** connected natively to your `sonede_smart_platform` MongoDB collection.

---

## 📁 Key Components Built

| Component | Path | Description |
|---|---|---|
| **Docker Infrastructure** | [`docker-compose.metabase.yml`](file:///c:/PROJET_STAGE_AMAL/docker-compose.metabase.yml) | Runs Metabase + PostgreSQL application DB locally on port 3000 |
| **Setup Guide** | [`metabase/README.md`](file:///c:/PROJET_STAGE_AMAL/metabase/README.md) | Complete step-by-step instructions for launching and configuring the dashboard |
| **Tunisia Map Widget** | [`metabase/custom_viz/tunisia_map.html`](file:///c:/PROJET_STAGE_AMAL/metabase/custom_viz/tunisia_map.html) | Interactive Leaflet.js map with color-coded criticality levels (🔴 Rouge, 🟠 Élevé, 🟡 Modéré, 🟢 Faible) |
| **Radar Chart Widget** | [`metabase/custom_viz/radar_chart.html`](file:///c:/PROJET_STAGE_AMAL/metabase/custom_viz/radar_chart.html) | Chart.js radar showing monthly evolution of complaint types |
| **Treemap Widget** | [`metabase/custom_viz/treemap_chart.html`](file:///c:/PROJET_STAGE_AMAL/metabase/custom_viz/treemap_chart.html) | D3.js treemap breaking down: **Gouvernorat → Catégorie → Urgence** |

---

## 🗃️ MongoDB Aggregation Queries Provided

All query files are ready in [`metabase/queries/`](file:///c:/PROJET_STAGE_AMAL/metabase/queries/):

1. [`kpi_counters.json`](file:///c:/PROJET_STAGE_AMAL/metabase/queries/kpi_counters.json): Total complaints, % critical, impacted regions, avg resolution days, resolution rate %.
2. [`bar_chart.json`](file:///c:/PROJET_STAGE_AMAL/metabase/queries/bar_chart.json): Complaints by type grouped by governorate.
3. [`radar_data.json`](file:///c:/PROJET_STAGE_AMAL/metabase/queries/radar_data.json): Monthly complaint distribution by category.
4. [`treemap_data.json`](file:///c:/PROJET_STAGE_AMAL/metabase/queries/treemap_data.json): Region → Problem → Severity hierarchy.
5. [`map_data.json`](file:///c:/PROJET_STAGE_AMAL/metabase/queries/map_data.json): Geographic risk aggregation with lat/lng and risk level.
6. [`detail_table.json`](file:///c:/PROJET_STAGE_AMAL/metabase/queries/detail_table.json): Full detailed complaint table.
7. [`seasonal_analysis.json`](file:///c:/PROJET_STAGE_AMAL/metabase/queries/seasonal_analysis.json): Seasonal breakdown (e.g. water cuts in Summer vs leaks in Winter).

---

## 🚀 How to Run locally right now

1. Open PowerShell / Terminal in `c:\PROJET_STAGE_AMAL` and run:
   ```bash
   docker compose -f docker-compose.metabase.yml up -d
   ```
2. Navigate to **`http://localhost:3000`** in your browser.
3. Add your MongoDB connection (`host.docker.internal:27017` / database: `sonede_smart_platform`).
4. Follow [`metabase/README.md`](file:///c:/PROJET_STAGE_AMAL/metabase/README.md) to add the queries and arrange your administration dashboard!
