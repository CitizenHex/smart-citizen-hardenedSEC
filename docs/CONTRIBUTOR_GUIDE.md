# Contributor Guide

How to set up Smart Citizen for local development.

## Prerequisites

- Python 3.9+ (recommended 3.10+)
- Windows 10/11 (the app uses Windows Registry and is Win32-only)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Osiris-DevWorks/smart-citizen.git
   cd smart-citizen
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python src/main.py
   ```

## Going deeper

For architecture, conventions, and design decisions, see [`CLAUDE.md`](../CLAUDE.md) at the repo root and the per-directory `CLAUDE.md` files it points to.
