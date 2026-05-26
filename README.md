 Orakle Backend

**Orakle** is an AI‑powered blockchain intelligence platform that transforms raw on‑chain data into human‑readable security insights. This repository contains the **Django REST API** – the deterministic analysis engine and Gemma 4 AI integration layer.

> 🧠 **Primary AI Model:** Google Gemma 4 (with fallback to Gemini 1.5 Flash for stability)

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-5.2-green)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Variables](#environment-variables)
- [API Endpoints](#api-endpoints)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

Blockchain data is dense and unreadable. Orakle solves this by combining **deterministic security analysis** with **Google Gemma 4** to produce plain‑English summaries, threat assessments, and actionable recommendations.

**This backend handles:**
- Fetching on‑chain data (Ethereum via Etherscan, Solana via RPC)
- Computing risk scores and detecting suspicious signals
- Scanning smart contracts for dangerous functions (`mint`, `blacklist`, `delegatecall`, etc.)
- Translating raw transaction hashes into human‑readable descriptions
- Generating AI explanations using Gemma 4 (with fallback models)

The frontend repository is available [here](https://github.com/uduakgabriel-netizen/Orakle-frontend).

---

## Architecture

```

Raw Blockchain Data
↓
Deterministic Intelligence Layer (this backend)
↓
Structured Metrics & Signals
↓
Gemma 4 AI Reasoning
↓
Human-Readable Intelligence → Frontend / PDF Reports

```

**Key principle:** AI never calculates risk scores directly. It only explains and recommends based on deterministic outputs.

---

## Features

| Feature | Description |
|---------|-------------|
| **Wallet Intelligence** | Analyze any Ethereum or Solana wallet – risk score, signals, metrics |
| **Contract Audit** | Detect dangerous functions, ownership risks, delegatecall patterns |
| **Transaction Translation** | Convert raw transaction hash into plain English |
| **Gemma 4 Integration** | Structured JSON output: summary, threat assessment, key findings, recommendations, confidence score |
| **Model Fallback Chain** | Primary: `gemma-4-26b-a4b-it` → Fallback: `gemini-1.5-flash` → `gemini-1.5-pro` |
| **PDF Report Generation** | Download professional security reports |
| **Multi‑chain** | Ethereum (Etherscan V2) & Solana (Helius / public RPC) |
| **Supabase PostgreSQL** | Persistent storage for all analyses |

---

## Tech Stack

- **Framework:** Django 5.2 + Django REST Framework
- **Database:** PostgreSQL (Supabase recommended)
- **AI Provider:** Google Gemini API (Gemma 4 & Gemini models)
- **Blockchain APIs:** Etherscan V2, Solana RPC, Alchemy (optional)
- **PDF Generation:** fpdf2
- **Deployment:** Render (Gunicorn + Whitenoise)
- **Language:** Python 3.11+

---

## Getting Started

### Prerequisites

- Python 3.11 or higher
- PostgreSQL database (or Supabase account)
- API keys:
  - [Google Gemini API key](https://aistudio.google.com/) (for Gemma 4)
  - [Etherscan API key](https://etherscan.io/register)
  - [Alchemy RPC URL](https://www.alchemy.com/) (optional, for ETH_RPC_URL)

### Installation

```bash
# Clone the repository
git clone https://github.com/uduakgabriel-netizen/Orakle-backend.git
cd Orakle-backend/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your actual keys (see below)

# Run migrations
python manage.py migrate

# Start the development server
python manage.py runserver
```

The API will be available at http://localhost:8000/api/.

Environment Variables

Create a .env file in the backend/ folder with the following:

```env
DEBUG=True   # Set to False in production
SECRET_KEY=your-django-secret-key

DATABASE_URL=postgresql://user:password@host:port/database

GEMINI_API_KEY=your-google-gemini-api-key
ETHERSCAN_API_KEY=your-etherscan-api-key
ETH_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/your-key

# Optional for Solana
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com

# CORS (for frontend)
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://your-frontend.com
```

Note: A .env.example file is included in the repo – rename and fill in your values.

---

API Endpoints

All endpoints return a standard JSON structure:

```json
{
  "success": true,
  "data": { ... },
  "message": "..."
}
```

Method Endpoint Description
POST /api/analyze-wallet Analyze Ethereum wallet
POST /api/analyze-contract Audit smart contract
POST /api/translate-transaction Translate transaction hash
POST /api/solana/analyze-wallet Analyze Solana wallet
POST /api/ai/analyze-wallet Get Gemma 4 explanation for a wallet analysis (requires id)
POST /api/ai/analyze-contract Get AI summary for a contract audit
POST /api/ai/analyze-transaction Get AI summary for a transaction
POST /api/generate-report Generate PDF report (type: wallet/contract/transaction, id)
GET /api/dashboard-metrics Get platform usage statistics
GET /api/all-history List all past analyses

Example request (wallet analysis):

```bash
curl -X POST http://localhost:8000/api/analyze-wallet \
  -H "Content-Type: application/json" \
  -d '{"wallet_address": "0xab5801a7D398351b8bE11C439e05C5B3259aeC9B"}'
```

Example AI response:

```json
{
  "success": true,
  "data": {
    "summary": "The wallet exhibits high‑frequency, zero‑value transactions...",
    "threat_assessment": "Low",
    "key_findings": ["Finding 1", "Finding 2"],
    "recommendations": ["Recommendation 1", "Recommendation 2"],
    "confidence_score": 94
  }
}
```

Full API documentation is available at /api/ when the server is running (Django REST framework browsable API).


Deployment

Deploy to Render

1. Push the repository to GitHub.
2. Create a new Web Service on Render.
3. Connect your repository.
4. Set:
   · Build Command: pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
   · Start Command: gunicorn config.wsgi:application
5. Add all environment variables from your .env file.
6. Click Deploy.

A Procfile and runtime.txt are included in the repository for Render compatibility.

Environment Variables on Render

```env
DEBUG=False
SECRET_KEY=(generate a long random string)
DATABASE_URL=postgresql://...
GEMINI_API_KEY=...
ETHERSCAN_API_KEY=...
ETH_RPC_URL=...
ALLOWED_HOSTS=your-app.onrender.com
CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app
```



Project Structure

```
backend/
├── ai/                 # Gemma 4 integration & prompt engineering
├── wallets/            # Wallet analysis (Ethereum & Solana)
├── contracts/          # Smart contract auditing
├── transactions/       # Transaction translation
├── reports/            # PDF report generation
├── core/               # Shared utilities, Etherscan client, responses
├── config/             # Django settings, URLs, WSGI
├── media/              # Generated PDF reports (gitignored)
├── requirements.txt
├── .env.example
├── manage.py
└── Procfile
```

Testing

Run the built‑in Django test suite:

```bash
python manage.py test
```

For manual testing, use the provided curl commands or the browsable API at /api/.



Contributing

Contributions are welcome! Please open an issue or pull request for any improvements.

1. Fork the repository
2. Create a feature branch (git checkout -b feature/amazing-feature)
3. Commit your changes (git commit -m 'Add amazing feature')
4. Push to the branch (git push origin feature/amazing-feature)
5. Open a Pull Request



License

Distributed under the MIT License. See LICENSE for more information.



Acknowledgments

· Google Gemma 4 – open‑weight AI model
· Etherscan – blockchain data
· Solana – blockchain data
· Render – deployment platform

---

Built for the Gemma 4 Challenge 2026
