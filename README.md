SentinelTrace

Predictive Cybercrime Network Intelligence for Proactive Investigation

SentinelTrace is a cybersecurity investigation prototype developed for Smart India Hackathon (SIH) 2026. It helps analysts explore suspicious transaction networks, prioritize potential intermediary accounts, and organize investigation workflows.

The project combines machine learning, graph-based transaction analysis, and an analyst-facing web interface to support investigation and decision-making.

«Project status: Research and demonstration prototype. Model A focuses on mule-chain candidate identification. Model B, intended for cash-out location prediction, is deferred.»

Overview

Investigating cybercrime-related financial activity can require analysts to examine complex transaction relationships and prioritize large numbers of potential leads. SentinelTrace aims to make this process more structured by combining account-level features, transaction-network analysis, risk prioritization, and investigation tools.

Key capabilities

- Mule-chain identification (Model A): Ranks candidate accounts using machine-learning and transaction-network features.
- Transaction-network exploration: Helps analysts inspect relationships between accounts and investigate suspicious network structures.
- Risk prioritization: Supports the review of potentially relevant accounts and complaints.
- Investigation workflows: Provides prototype capabilities for alerts, case management, and analyst review.
- Analyst dashboard: Brings investigation-related information together in a web-based interface.

These capabilities are intended to support human investigation, not replace it.

Architecture

Component| Technology
Frontend| React, TypeScript, Vite, Tailwind CSS
Backend API| Python, FastAPI
Database| PostgreSQL
Network analysis| NetworkX
Machine learning| scikit-learn

High-level workflow

1. Transaction and complaint data are made available to the backend.
2. Account and transaction relationships are analyzed using network-derived and account-level features.
3. Model A ranks candidate accounts for further investigation.
4. The API exposes investigation information to the frontend.
5. Analysts review the available evidence and decide what to investigate next.

Project structure

Sentinel-Trace/
├── sentineltrace-backend/
│   ├── app/
│   ├── artifacts/
│   ├── data/
│   ├── research_model_a/
│   ├── scripts/
│   ├── tests/
│   ├── requirements.txt
│   └── README.md
├── sentinltrace-frontend/
│   ├── public/
│   ├── src/
│   ├── package.json
│   ├── package-lock.json
│   └── README.md
├── .gitignore
└── README.md

Getting started

Prerequisites

- Python and pip
- Node.js and npm
- PostgreSQL
- Git

Setup

Clone the repository:

git clone https://github.com/SilentRecon-crypto/SentinelTrace.git
cd SentinelTrace

Follow the backend-specific instructions in ""sentineltrace-backend/README.md"" (sentineltrace-backend/README.md) and the frontend-specific instructions in ""sentinltrace-frontend/README.md"" (sentinltrace-frontend/README.md).

Use the provided environment example files to configure local settings. Keep actual credentials and local environment files private.

The backend and frontend must be configured and running for the integrated application to work. Consult the component READMEs for their specific commands and configuration requirements.

Model scope and data limitations

Model A — Mule-chain identification

Model A is the primary implemented machine-learning component. It ranks candidate accounts using account-level and transaction-network features to help prioritize investigative leads.

A high score is a prioritization signal, not proof of criminal activity or confirmation that an account is a money mule.

Model B — Cash-out location prediction

Model B is deferred. This repository should not be interpreted as demonstrating validated predictions of exact ATM locations or other real-world cash-out destinations.

Data and validation

The prototype uses controlled synthetic transaction data for development and experimentation. Synthetic evaluation results do not establish performance on real cybercrime complaints or real banking transactions.

Production-oriented evaluation would require appropriately authorized real-world data, independent validation, privacy safeguards, security controls, and operational testing.

Responsible use

SentinelTrace is intended for research, demonstration, and analyst decision support.

- Review model outputs alongside supporting evidence.
- Do not treat risk scores as conclusive allegations.
- Do not use prototype predictions as the sole basis for enforcement or financial decisions.
- Protect sensitive financial, complaint, and account information.
- Use only data that you are authorized to access and process.

Future development

Potential next steps include validating Model A with authorized real-world data, strengthening automated testing and deployment, and evaluating whether Model B can be developed and validated using suitable cash-out location data.

These are future directions, not claims about currently completed functionality.

Project

SentinelTrace — SIH 2026

Repository: "SilentRecon-crypto/SentinelTrace" (https://github.com/SilentRecon-crypto/SentinelTrace)