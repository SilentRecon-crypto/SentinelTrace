\# SentinelTrace



\*\*Predictive Cybercrime Network Intelligence for Proactive Intervention\*\*



SentinelTrace is a cybercrime investigation prototype that helps analysts prioritize suspicious intermediary accounts, explore transaction networks, and manage investigation workflows.



Developed as an SIH 2026 project.



\## Key Features



\- \*\*Model A — Mule-Chain Identification:\*\* Ranks candidate accounts using machine-learning and transaction-network features.

\- \*\*Network Intelligence:\*\* Visualizes transaction relationships to support investigation.

\- \*\*Risk Prioritization:\*\* Provides risk scores, bands, and intervention-window information.

\- \*\*Alert Generation:\*\* Allows analysts to generate alerts from the backend workflow.

\- \*\*Case Management:\*\* Supports investigator notes, evidence references, resolution, and a consolidated dossier.

\- \*\*Analyst Interface:\*\* React-based frontend connected to a FastAPI backend.



\## Architecture



\- Frontend: React, TypeScript, Vite, Tailwind CSS

\- Backend: FastAPI, Python

\- Database: PostgreSQL

\- Graph Analysis: NetworkX

\- Machine Learning: scikit-learn



\## Project Structure



\- `sentinltrace-frontend/` — Analyst interface

\- `sentineltrace-backend/` — API, data models, graph services, and ML integration



\## Current Scope and Limitations



SentinelTrace is a prototype validated using controlled synthetic transaction networks. Its results should not be interpreted as proof of real-world criminal activity.



Model A focuses on ranking potential mule-chain candidates. These candidates are investigative leads, not confirmed criminal chains.



\*\*Model B — Cash-Out Location Prediction — is deferred.\*\* The current prototype does not claim real ATM prediction or validation using real NCRP or banking cash-out location data.



Production use would require authorized real-world data, independent validation, appropriate security controls, and operational evaluation.



\## Setup



See `sentinltrace-frontend/` and `sentineltrace-backend/` for their respective setup instructions and dependency files.



Do not commit `.env` files, credentials, private keys, local virtual environments, or `node\_modules`.



\## Responsible Use



This project is intended for research, demonstration, and investigator decision support. Model outputs require human review and should not be treated as conclusive allegations.



\## Team



Developed by the SentinelTrace team for SIH 2026.


