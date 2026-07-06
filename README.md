# Solar Multi-Agent Sizing & Sourcing System

An enterprise-grade, multi-agent AI system designed for solar distributors. The system automates raw query ingestion, technical sizing verification, supply-chain routing, and 25-year financial compounding ROI projections. It includes stateful memory tracking to support multi-turn design modifications and real-time execution guardrails to flag physical and supply constraints.

---

## 1. Architecture Overview

The system consists of a central **SolarOrchestrator** acting as a stateful router coordinating three specialized agents:
1. **TriageAgent:** Ingests raw customer emails or chat transcripts and extracts structured project parameters.
2. **TechnicalAgent:** Calculates required physical roof footprint and validates layout capacity constraints.
3. **FinancialLogisticsAgent:** Cross-references required quantities with warehouse stock, generates a Bill of Materials (BOM), and compiles a compounding 25-year return on investment timeline.

Memory tracking is managed via an `InMemoryContextBank` that stores all variables, history, and warning flags to allow seamless multi-turn design updates.

---

## 2. Interactive Presentation Dashboard (`presentation_dashboard.html`)

The repository includes a responsive companion HTML/JS dashboard (`presentation_dashboard.html`) designed for full frontend visualization. It functions locally entirely inside any standard web browser without requiring a backend runtime server.

### Features:
* **Presentation Deck:** An integrated slide deck outlining business friction points, multi-agent router topologies, tool math formulas, and pre-flight guardrail thresholds.
* **Live Interactive Pipeline Simulator:** Simulates agent processing transitions (`TriageAgent` ➔ `TechnicalAgent` ➔ `FinancialLogisticsAgent`) across pre-configured user study cases.
* **Dynamic Visual Sizing & Charts:** Renders physical panel layouts over roof areas, populates a warehouse stock ledger, and compiles canvas-driven 25-year cumulative ROI curve graphics.
* **Active Execution Guardrails:** Emulates active pipeline halting and outputs a high-visibility, localized `SYSTEM GUARDRAIL ALERT` layout if anomalous data (e.g., negative area metrics or out-of-stock thresholds) is passed into the system.

---

## 3. Installation & Setup

1. **Verify Python Installation:**
   Ensure Python 3.10 or later is installed.

2. **Download Code Repository Assets:**
   Ensure you have the following core files in your workspace directory:
   - `solar_tools.py` (Deterministic math models)
   - `agent_core.py` (Agent routing & memory code)
   - `main.py` (Test execution script)
   - `presentation_dashboard.html` (Interactive Presentation UI)

3. **Install Dependencies:**
   Install required Python packages:
   ```bash
   pip install google-genai pydantic
Set Up Gemini API Key (Optional but Recommended):
The agents run out of the box using a local regex parameter extractor and fallback markdown generators if no API key is present. To enable live AI extraction and proposal generation via Gemini 2.5 Flash, export your API key:

Windows (Command Prompt):

DOS
set GEMINI_API_KEY=your_api_key_here
Windows (PowerShell):

PowerShell
$env:GEMINI_API_KEY="your_api_key_here"
Linux/macOS:

Bash
export GEMINI_API_KEY="your_api_key_here"

Running the System
Running the Python Backend Test Suite:
Execute the test suite locally to process sample customer inquiries and validation limits:

Bash
python main.py
This runs the system through 5 distinct test payloads representing standard ingestion, multi-turn modifications, negative areas, roof constraints, and supply limits.

Running the Frontend UI:
Right-click on presentation_dashboard.html and choose Open With ➔ select your preferred web browser (Chrome, Edge, Safari, or Firefox). You can view the full slide deck and test scenarios immediately without launching a terminal execution window.

4. Test Scenarios Covered
To test the system interactively or evaluate performance, the suite leverages these sample customer data flows:

Happy Path Ingestion: A standard message details an Austin, TX installation request with valid footprint and pricing requirements.

Multi-Turn Sizing Edit: A follow-up request dynamically updates target system capacity from 6kW to 8kW midway, updating the context bank and recalculating billing metrics.

Negative Area Guardrail: Intercepts a physical input anomaly where the user reports a negative roof space value (-400 sq ft).

Footprint Shortfall Guardrail: Halts execution when a massive 15.0 kW system footprint physically cannot fit inside a tiny 300 sq ft roof limitation.

Supply Chain Guardrail: Blocks commercial-scale installations (>60kW) that break past standard warehouse inventory limits.

***
