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

##2. Installation & Setup

1. **Verify Python Installation:**
   Ensure Python 3.10 or later is installed.

2. **Clone / Download Code:**
   Ensure you have the following files in your workspace directory:
   - `solar_tools.py` (Deterministic math models)
   - `agent_core.py` (Agent routing & memory code)
   - `main.py` (Test execution script)

3. **Install Dependencies:**
   Install required Python packages:
   ```bash
   pip install google-genai pydantic
   ```

4. **Set Up Gemini API Key (Optional but Recommended):**
   The agents run out of the box using a local regex parameter extractor and fallback markdown generators if no API key is present. To enable live AI extraction and proposal generation via Gemini 2.5 Flash, export your API key:
   * **Windows (Command Prompt):**
     ```cmd
     set GEMINI_API_KEY=your_api_key_here
     ```
   * **Windows (PowerShell):**
     ```powershell
     $env:GEMINI_API_KEY="your_api_key_here"
     ```
   * **Linux/macOS:**
     ```bash
     export GEMINI_API_KEY="your_api_key_here"
     ```

---

## 3. Running the System

Execute the test suite to run the pre-configured scenarios:
```bash
python main.py
```

This runs the system through 5 test payloads representing:
1. **Happy Path:** standard ingestion ( Austin, TX setup).
2. **Multi-Turn Sizing Edit:** customer updates target size from 6kW to 8kW midway.
3. **Negative Area Guardrail:** catches anomalous negative roof space input.
4. **Footprint Shortfall Guardrail:** catches a 15kW capacity request forced onto a tiny 300 sq. ft. roof.
5. **Supply Chain Guardrail:** blocks commercial-scale requests (>60kW) that exceed the standard 150-panel warehouse allocation.

---

## 5. Test Payloads

To test the system interactively or feed in custom payloads, pass customer messages to `orchestrator.receive_query(message)`.

### Payload 1: Happy Path Ingestion
```text
Dear Solar Distributor, I am looking to install a solar setup at my house in Austin, Texas. My roof is roughly 600 sq ft. I pay $0.18/kWh to the utility and use about 12,000 kWh annually. I want a 6.0 kW system capacity. My budget is $20,000.
```

### Payload 2: Multi-Turn Sizing Update
```text
Actually, my neighbor said I should get an 8.0 kW system instead. Can we update the capacity to 8.0 kW and recalculate the ROI and Bill of Materials?
```

### Payload 3: Physical Anomaly (Negative Sizing)
```text
Hello, I need a standard 5.0 kW solar capacity system, but my roof area is -400 sq ft. Please send a quote.
```

### Payload 4: Footprint Shortfall
```text
Hi, I want a large 15.0 kW solar capacity system. My roof space is only 300 sq ft. I pay $0.22/kWh and use 20,000 kWh annually. Can you build this?
```

### Payload 5: Sourcing Limit Exceeded
```text
Good afternoon. We need a commercial 70.0 kW system for our warehouse in San Jose. We have plenty of space (10,000 sq ft) and a budget of $150,000. Send over the invoice.
```
