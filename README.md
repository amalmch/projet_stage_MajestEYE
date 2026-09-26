# 💧 SONEDE Smart — AI-Powered Citizen Water Incident & Complaint Management Platform

[![Flutter](https://img.shields.io/badge/Flutter-02569B?style=for-the-badge&logo=flutter&logoColor=white)](https://flutter.dev/)
[![Spring Boot](https://img.shields.io/badge/Spring_Boot-6DB33F?style=for-the-badge&logo=spring-boot&logoColor=white)](https://spring.io/projects/spring-boot)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-4EA94B?style=for-the-badge&logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Metabase](https://img.shields.io/badge/Metabase-509EE3?style=for-the-badge&logo=metabase&logoColor=white)](https://www.metabase.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

> **Academic & Professional Context:**
> Project developed by **Amal Mechergui** ([ENSTAB](http://www.enstab.rnu.tn/) — Université de Carthage) during an engineering internship at **MajestEYE**, under the supervision of **M. Saad Eddine Khemiri**.

---

## 📌 Executive Summary

**SONEDE Smart** is an end-to-end intelligent platform engineered to modernize citizen incident reporting and optimize operational interventions for the Tunisian National Water Distribution Utility (**SONEDE**). 

By uniting **Conversational AI**, **Computer Vision**, and **Real-Time Geospatial Business Intelligence**, the solution bridges the communication gap between citizens and field technicians, drastically cutting down the Mean Time to Repair (**MTTR**) for water leaks, pipe bursts, and service interruptions.

---

## 🌟 Key Features

### 1. 📱 Citizen Mobile Application (Flutter)
- **Multimodal Conversational Chatbot:** Seamlessly guides citizens through reporting incidents in Tunisian Derja, Arabic, and French.
- **Interactive Voice Assistant (STT & TTS):** Hands-free voice reporting with localized dialect recognition and instant synthesized spoken responses.
- **Geolocated Live Tracking:** Real-time GPS tagging of leak sites with stage-by-stage status tracking (*Submitted ➔ Under Review ➔ Assigned ➔ Resolved*).
- **Incident Photo Upload:** Instant capture and attachment of water leak imagery for automated AI verification.

### 2. 🧠 AI & Deep Learning Engine (Python)
- **Semantic Classification & RAG:** NLP intent classification and Retrieval-Augmented Generation to answer citizen inquiries and route reports accurately.
- **Predictive Urgency Scoring (Random Forest):** Automatically calculates incident severity and priority based on problem type, impact area, and citizen reports.
- **Visual Leak Qualification (Vision Transformers - ViT / CLIP):** Assesses user-submitted photos to automatically validate water damage and filter false reports.

### 3. ⚙️ Enterprise Management Backend (Spring Boot & MongoDB)
- **Role-Based Access Control (RBAC):** Differentiated access and portals for Citizens, Field Technicians, and Administration.
- **Secure Authentication:** Stateless JSON Web Token (**JWT**) token generation and validation.
- **Microservice APIs:** Scalable REST endpoints coordinating Flutter, AI inference services, and persistent MongoDB collections.

### 4. 📈 Business Intelligence & Operational Dashboards (Metabase & Leaflet.js)
- **Interactive Tunisia Map:** Color-coded criticality heatmaps showing real-time regional incident density across all 24 governorates.
- **Analytical Visualizations:** Radar charts for monthly category trends, Treemaps for multi-level risk breakdowns, and dynamic KPI counters.
- **Field Technician Workflow:** Dynamic task assignment, intervention logging, and status transitions for field workers.

---

## 🏗️ System Architecture

```
                     ┌─────────────────────────────────────────┐
                     │          Citizen Mobile Client          │
                     │          (Flutter / Dart UI)            │
                     └────────────────────┬────────────────────┘
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
     ┌────────────────────────┐                     ┌────────────────────────┐
     │   Spring Boot Backend  │                     │    Python AI Engine    │
     │  (Security / JWT / DB) │                     │ (NLP / ViT / STT / RF) │
     └────────────┬───────────┘                     └────────────┬───────────┘
                  │                                               │
                  ├───────────────────────┬───────────────────────┘
                  ▼                       ▼
     ┌────────────────────────┐     ┌────────────────────────┐
     │    MongoDB Database    │     │ Metabase & Tech Portal │
     │  (sonede_smart_plat.)  │     │   (BI & Intervention)  │
     └────────────────────────┘     └────────────────────────┘
```

---

## 💻 Tech Stack

- **Mobile Frontend:** Flutter, Dart, Provider / Bloc, Geolocator, Audio Streamers.
- **AI & Data Science:** Python 3.12, Scikit-Learn (Random Forest), PyTorch, Hugging Face Transformers (ViT, CLIP), Vosk ASR, Flask / FastAPI.
- **Backend & Security:** Java 17, Spring Boot 3, Spring Security, JWT (JSON Web Tokens), Maven.
- **Database & Storage:** MongoDB, PostgreSQL (Metabase application DB).
- **Business Intelligence & Devops:** Metabase, Docker, Docker Compose, Leaflet.js, Chart.js, D3.js.

---

## 🚀 Getting Started

### Prerequisites
- [Docker & Docker Compose](https://www.docker.com/)
- [Java 17+](https://adoptium.net/) & Maven
- [Python 3.10+](https://www.python.org/)
- [Flutter SDK](https://flutter.dev/docs/get-started/install)

---

### 1. Launch Analytics & Metabase
Start Metabase and the local reporting infrastructure:
```bash
docker compose -f docker-compose.metabase.yml up -d
```
Access the Metabase console at `http://localhost:3000`.

---

### 2. Run the AI Microservice (`sonede_ai`)
```bash
cd sonede_ai
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

pip install -r requirements.txt
python app.py
```
*The AI engine runs by default on `http://localhost:5000`.*

---

### 3. Run the Spring Boot Backend (`demo`)
```bash
cd demo
# Windows:
.\mvnw.cmd spring-boot:run
# Linux/macOS:
# ./mvnw spring-boot:run
```
*Backend API initializes at `http://localhost:8080`.*

---

### 4. Run the Citizen Mobile App (`Mobile_app`)
```bash
cd Mobile_app/flutter_application_1
flutter pub get
flutter run
```

---

## 🤝 Acknowledgments

Special thanks to:
- **M. Saad Eddine Khemiri** — Professional Internship Supervisor at **MajestEYE**, for his valuable mentorship, technical guidance, and consistent support.
- **MajestEYE** — For providing a stimulating, innovative environment.
- **École Nationale des Sciences et Technologies Avancées à Borj Cédria (ENSTAB)** — Université de Carthage.

---

