import os
import re
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import solar_tools

# Try to import Google Gen AI SDK
# Fallback gracefully if not installed to prevent imports from blocking run
try:
    from google import genai
    from google.genai import types
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

class SolarTriageSchema(BaseModel):
    system_size_kw: Optional[float] = Field(None, description="Target solar panel capacity in kW. Residential average is 5 to 10 kW.")
    budget_usd: Optional[float] = Field(None, description="Customer budget in USD.")
    location: Optional[str] = Field(None, description="City/State or zip code.")
    utility_rate_kwh: Optional[float] = Field(None, description="Current utility rate per kWh in USD (e.g., 0.28).")
    annual_usage_kwh: Optional[float] = Field(None, description="Annual electricity usage in kWh (e.g., 12000).")
    roof_space_sqft: Optional[float] = Field(None, description="Available roof space in square feet.")
    notes: Optional[str] = Field(None, description="Any specific customer requests, preferences, or notes.")

class InMemoryContextBank:
    """
    Stateful memory manager storing context variables, history, agent outputs,
    and validation flags across multiple conversation turns.
    """
    def __init__(self):
        self.session_id: str = "session_001"
        self.raw_query: str = ""
        self.triage_data: Dict[str, Any] = {}
        self.technical_data: Dict[str, Any] = {}
        self.financial_logistics_data: Dict[str, Any] = {}
        self.history: List[Dict[str, str]] = []
        self.validation_errors: List[str] = []
        self.status: str = "INIT"  # INIT, TRIAGED, TECH_OK, ERROR, COMPLETE

    def add_to_history(self, role: str, content: str):
        self.history.append({"role": role, "content": content})

    def update_triage(self, data: Dict[str, Any]):
        # Update existing parameters, supporting partial overrides in multi-turn
        for k, v in data.items():
            if v is not None:
                self.triage_data[k] = v

    def clear_errors(self):
        self.validation_errors = []

    def add_error(self, err: str):
        if err not in self.validation_errors:
            self.validation_errors.append(err)

    def print_state(self):
        print("\n--- [MEM BANK STATE] ---")
        print(f"Status: {self.status}")
        print(f"Triage Data: {json.dumps(self.triage_data, indent=2)}")
        print(f"Technical Data: {json.dumps(self.technical_data, indent=2)}")
        print(f"Logistics & Financials: {self.financial_logistics_data.get('total_retail_quote_usd', 'N/A')} USD Retail Quote")
        print(f"Validation Errors: {self.validation_errors}")
        print("------------------------\n")

class TriageAgent:
    """
    Agent 1: Parses raw customer emails/messages, extracts key variables, and updates memory bank.
    """
    def __init__(self, client: Optional[Any] = None):
        self.client = client

    def process(self, query: str, context: InMemoryContextBank) -> Dict[str, Any]:
        print("[TriageAgent] Parsing query and extracting parameters...")
        extracted = {}
        
        # Check if we should call the Gemini API
        if SDK_AVAILABLE and self.client and os.environ.get("GEMINI_API_KEY"):
            try:
                prompt = (
                    f"Analyze this raw solar query and extract the following parameters: "
                    f"system_size_kw, budget_usd, location, utility_rate_kwh, annual_usage_kwh, "
                    f"roof_space_sqft, notes.\n\nQuery: {query}"
                )
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=SolarTriageSchema,
                        system_instruction="You are an expert sales ingestion agent for a solar panel distributor. Extract parameters into JSON."
                    )
                )
                extracted = json.loads(response.text)
            except Exception as e:
                print(f"[TriageAgent] API call failed: {e}. Falling back to regex parser.")
                extracted = self._regex_fallback(query)
        else:
            extracted = self._regex_fallback(query)

        # Merge extracted values into context bank
        context.update_triage(extracted)
        context.status = "TRIAGED"
        return extracted

    def _regex_fallback(self, query: str) -> Dict[str, Any]:
        """Deterministic regex fallback for local environment testing."""
        # Simple extraction heuristics based on standard test cases
        data = {
            "system_size_kw": None,
            "budget_usd": None,
            "location": "Unknown",
            "utility_rate_kwh": None,
            "annual_usage_kwh": None,
            "roof_space_sqft": None,
            "notes": ""
        }
        
        # Extract location
        loc_match = re.search(r"in\s+([A-Za-z\s]{3,15})(?=\.|,|\bin\b|\s+with|\s+and|\s+my)", query, re.IGNORECASE)
        if loc_match:
            data["location"] = loc_match.group(1).strip()
            
        # Sizing / kW extraction (ensure we do not match kWh)
        kw_match = re.search(r"(-?\d+(\.\d+)?)\s*k[wW](?![hH])", query)
        if kw_match:
            data["system_size_kw"] = float(kw_match.group(1))
            
        # Extract utility rate first
        rate_match = re.search(r"(?:pay|rate|price|utility)?\s*\$\s*(0\.\d+)\s*/\s*k[wW]h", query, re.IGNORECASE)
        if not rate_match:
            rate_match = re.search(r"(0\.\d+)\s*(?:per|\/)\s*k[wW]h", query, re.IGNORECASE)
        if rate_match:
            data["utility_rate_kwh"] = float(rate_match.group(1))
            
        # Extract budget by looking for dollar signs that are NOT utility rates
        all_dollar_matches = re.finditer(r"\$\s*(-?\d{1,3}(?:,\d{3})*(?:\.\d+)?)", query)
        for match in all_dollar_matches:
            val = float(match.group(1).replace(",", ""))
            if val <= 5.0:
                if data["utility_rate_kwh"] is None:
                    data["utility_rate_kwh"] = val
            else:
                data["budget_usd"] = val
            
        # Annual Usage
        usage_match = re.search(r"(\d{1,3}(,\d{3})*)\s*k[wW]h\s*(?:per\s*year|annually|a\s*year|annual|used)", query, re.IGNORECASE)
        if usage_match:
            data["annual_usage_kwh"] = float(usage_match.group(1).replace(",", ""))
            
        # Roof space (allow negative values to trigger guardrails)
        roof_match = re.search(r"(-?\d{1,5}(,\d{3})*)\s*(?:sq\s*ft|square\s*feet|sq\.?\s*ft\.?)", query, re.IGNORECASE)
        if roof_match:
            data["roof_space_sqft"] = float(roof_match.group(1).replace(",", ""))
            
        # Save whole query in notes for context
        data["notes"] = f"Raw source: {query[:80]}..."
        return data

class TechnicalAgent:
    """
    Agent 2: Sizing validator. Checks physical constraints (roof area) using mathematical tools
    and alerts the Orchestrator of anomalies.
    """
    def __init__(self, client: Optional[Any] = None):
        self.client = client

    def process(self, context: InMemoryContextBank) -> Dict[str, Any]:
        print("[TechnicalAgent] Sizing and constraints vetting...")
        
        triage = context.triage_data
        target_kw = triage.get("system_size_kw")
        roof_space = triage.get("roof_space_sqft")
        
        # Estimate kW from budget if not provided ($3,000 / kW average customer retail price)
        if target_kw is None:
            budget = triage.get("budget_usd")
            if budget:
                # Estimate capacity based on retail cost factor
                estimated_kw = round(budget / 3000.0, 1)
                print(f"[TechnicalAgent] Target kW missing. Estimating {estimated_kw} kW from budget of ${budget}")
                triage["system_size_kw"] = estimated_kw
                target_kw = estimated_kw
            else:
                # Fallback default
                triage["system_size_kw"] = 5.0
                target_kw = 5.0

        # Calculate physical footprint using tool
        footprint_res = solar_tools.calculate_required_footprint(target_kw)
        required_sqft = footprint_res["required_footprint_sqft"]
        panels_needed = footprint_res["panels_needed"]
        
        # Check roof limits
        valid = True
        notes = "Physical footprint fits available roof space."
        
        if roof_space is not None:
            if required_sqft > roof_space:
                valid = False
                notes = f"Sizing constraint violation: Required footprint ({required_sqft} sq ft) exceeds available roof space ({roof_space} sq ft)."
                context.add_error("ROOF_SPACE_EXCEEDED")
        else:
            notes = "Roof space not specified by customer. Assumed standard layout spacing."
            
        tech_data = {
            "required_footprint_sqft": required_sqft,
            "panels_needed": panels_needed,
            "panel_wattage_w": footprint_res["panel_wattage_w"],
            "constraints_valid": valid,
            "technical_notes": notes
        }
        
        context.technical_data = tech_data
        
        # Ask Gemini to draft a brief layout assessment if API available
        if SDK_AVAILABLE and self.client and os.environ.get("GEMINI_API_KEY"):
            try:
                prompt = (
                    f"Write a summary of this technical layout. "
                    f"Target capacity: {target_kw} kW. Panels: {panels_needed}. "
                    f"Required space: {required_sqft} sq ft. Roof Space: {roof_space} sq ft. "
                    f"Valid: {valid}. Notes: {notes}."
                )
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction="You are a professional solar engineer. Provide a concise 2-3 sentence assessment of the physical layout configuration."
                    )
                )
                tech_data["narrative"] = response.text.strip()
            except Exception as e:
                tech_data["narrative"] = f"Layout validation complete. {notes}"
        else:
            tech_data["narrative"] = f"Layout validation complete. {notes}"
            
        if valid and not context.validation_errors:
            context.status = "TECH_OK"
            
        return tech_data

class FinancialLogisticsAgent:
    """
    Agent 3: Financial & Sourcing manager. Runs 25-yr lifecycle compounding ROI
    and retrieves BOM, compiling the final retail sales quotation.
    """
    def __init__(self, client: Optional[Any] = None):
        self.client = client

    def process(self, context: InMemoryContextBank) -> Dict[str, Any]:
        print("[FinancialLogisticsAgent] Sourcing components and building compounding model...")
        
        triage = context.triage_data
        tech = context.technical_data
        
        target_kw = triage.get("system_size_kw", 5.0)
        utility_rate = triage.get("utility_rate_kwh")
        annual_usage = triage.get("annual_usage_kwh")
        
        # Sourcing BOM using tool
        bom_res = solar_tools.check_inventory_and_bom(target_kw)
        
        # Sizing Defaults if missing
        if utility_rate is None:
            utility_rate = 0.23  # California baseline average
            triage["utility_rate_kwh"] = utility_rate
        if annual_usage is None:
            # 10,000 kWh standard annual household use
            annual_usage = 10000.0
            triage["annual_usage_kwh"] = annual_usage
            
        # Investment calculation (distributor retail quote)
        initial_investment = bom_res["total_retail_quote_usd"]
        
        # compounding ROI calculation
        roi_res = solar_tools.calculate_roi(
            kw_capacity=target_kw,
            initial_investment=initial_investment,
            utility_rate=utility_rate,
            annual_usage_kwh=annual_usage
        )
        
        # Sourcing shortage flags
        if bom_res["shortage_detected"]:
            context.add_error("WAREHOUSE_SHORTAGE")
            
        fin_log = {
            "bom_details": bom_res,
            "roi_details": roi_res,
            "quote_summary_usd": initial_investment,
            "payback_period_years": roi_res["payback_period_years"],
            "net_25yr_savings_usd": roi_res["net_25yr_savings_usd"],
            "roi_percentage": roi_res["roi_percentage"]
        }
        
        context.financial_logistics_data = fin_log
        
        # Call Gemini to build customer-facing presentation
        if SDK_AVAILABLE and self.client and os.environ.get("GEMINI_API_KEY"):
            try:
                prompt = (
                    f"Create a sales quotation email. "
                    f"Target size: {target_kw} kW. Quote: ${initial_investment:,.2f}. "
                    f"BOM: {json.dumps(bom_res['bom'])}. "
                    f"25-Yr Savings: ${roi_res['net_25yr_savings_usd']:,.2f}. "
                    f"Payback period: {roi_res['payback_period_years']} years. "
                    f"Shortages: {bom_res['shortages']}."
                )
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction="You are a professional solar distributor sales executive. Draft a compelling proposal detailing pricing, BOM, and long-term utility offsets. Mention stock details."
                    )
                )
                fin_log["proposal_narrative"] = response.text.strip()
            except Exception as e:
                fin_log["proposal_narrative"] = self._generate_markdown_narrative(bom_res, roi_res)
        else:
            fin_log["proposal_narrative"] = self._generate_markdown_narrative(bom_res, roi_res)
            
        if not context.validation_errors:
            context.status = "COMPLETE"
            
        return fin_log

    def _generate_markdown_narrative(self, bom: dict, roi: dict) -> str:
        """Deterministic fallback proposal generator."""
        shortage_text = ""
        if bom["shortage_detected"]:
            shortage_text = (
                f"\n> **ALERT: WAREHOUSE STOCK CONSTRAINT**\n"
                f"> Some items are currently on backorder: {', '.join(bom['shortages'])}.\n"
                f"> Delivery timelines may be delayed by 2-3 weeks.\n"
            )
            
        bom_rows = ""
        for item in bom["bom"]:
            bom_rows += f"| {item['item']} | {item['name']} | {item['required']} | {item['status']} | ${item['total_cost_usd']:,.2f} |\n"
            
        proposal = f"""Dear Customer,

We are pleased to submit our formal solar system proposal based on your criteria.

### Project Sizing Summary
*   **System Capacity:** {bom['target_kw']:.1f} kW DC
*   **Total Estimated Hardware & Sourcing Cost:** ${bom['hardware_cost_usd']:,.2f} USD
*   **Total Retail System Investment:** ${bom['total_retail_quote_usd']:,.2f} USD (Includes installation, permitting, and engineering markup)
{shortage_text}
### Sourced Bill of Materials (BOM)
| Category | Component Description | Qty Required | Stock Status | Sourcing Total |
| :--- | :--- | :--- | :--- | :--- |
{bom_rows}

### Compounding Financial Sizing Model (25-Year Lifecycle)
*   **Current Electricity Rate:** ${roi['timeline'][0]['utility_rate_per_kwh']:.2f}/kWh (Compounding grid cost escalation: 5.0% annually)
*   **Payback (Break-Even) Period:** {roi['payback_period_years']} Years
*   **Total 25-Year Utility Offset Savings:** ${roi['total_25yr_savings_usd']:,.2f} USD
*   **Net Lifetime Return on Investment:** ${roi['net_25yr_savings_usd']:,.2f} USD ({roi['roi_percentage']}% ROI)

This solution offsets your utility bills, locking in a compounding savings curve while utilizing premium components. Let us know if you want to proceed with engineering approval!

Best Regards,
Antigravity Solar Distribution Team
"""
        return proposal

class SolarOrchestrator:
    """
    Central Stateful Orchestrator that uses a Router pattern to pipeline requests
    across TriageAgent, TechnicalAgent, and FinancialLogisticsAgent.
    Includes active Guardrails and supports multi-turn modifications.
    """
    def __init__(self):
        # Initialize Gemini Client if possible
        self.client = None
        if SDK_AVAILABLE and os.environ.get("GEMINI_API_KEY"):
            try:
                self.client = genai.Client()
                print("[Orchestrator] Google Gen AI Client initialized.")
            except Exception as e:
                print(f"[Orchestrator] Error initializing Client: {e}. Fallback to local execution.")
                
        self.context = InMemoryContextBank()
        self.triage_agent = TriageAgent(self.client)
        self.technical_agent = TechnicalAgent(self.client)
        self.fin_agent = FinancialLogisticsAgent(self.client)

    def receive_query(self, user_query: str) -> str:
        """
        Receives a query (or multi-turn update), evaluates state, runs execution guardrails,
        and coordinates execution.
        """
        self.context.raw_query = user_query
        self.context.add_to_history("user", user_query)
        self.context.clear_errors()
        
        # STEP 1: Routing Check.
        # If the query is an update to an existing project, route differently.
        is_modification = False
        if self.context.status in ["TECH_OK", "COMPLETE", "ERROR"]:
            # Evaluate if user is trying to modify parameters
            is_modification = self._detect_modification(user_query)
            
        if is_modification:
            print(f"[Orchestrator] Detected system modification request in query.")
            # Run localized triage to update memory variables
            self.triage_agent.process(user_query, self.context)
        else:
            # Full ingestion pipeline
            print(f"[Orchestrator] Processing raw discovery query.")
            self.context.status = "INIT"
            self.triage_agent.process(user_query, self.context)

        # STEP 2: Execution Filters & Guardrail Checking (Physical Anomalies / Limits)
        self._run_pre_flight_guardrails()
        
        if self.context.validation_errors:
            self.context.status = "ERROR"
            return self._handle_guardrail_alerts()

        # STEP 3: Sizing & Sourcing vetting (Technical Agent)
        self.technical_agent.process(self.context)
        
        # Re-evaluate guardrails post-technical calculations
        self._run_post_tech_guardrails()
        
        if self.context.validation_errors:
            self.context.status = "ERROR"
            return self._handle_guardrail_alerts()

        # STEP 4: Logistics & ROI (Financial & Logistics Agent)
        self.fin_agent.process(self.context)
        
        # Post-financial/logistics inventory check
        if self.context.validation_errors:
            self.context.status = "ERROR"
            return self._handle_guardrail_alerts()

        # Pipeline complete. Deliver finalized output.
        proposal = self.context.financial_logistics_data.get("proposal_narrative", "")
        self.context.add_to_history("assistant", proposal)
        return proposal

    def _detect_modification(self, query: str) -> bool:
        """Check if query is asking to modify target size, budget, or specifications."""
        keywords = ["change", "update", "modify", "instead", "make it", "size to", "reduce", "increase", "capacity"]
        for kw in keywords:
            if kw in query.lower():
                return True
        # Check if numbers matching kW or budget are mentioned
        if re.search(r"\d+\s*k[wW]|\$\d+", query):
            return True
        return False

    def _run_pre_flight_guardrails(self):
        """Active guardrails checking for input errors and safety thresholds."""
        triage = self.context.triage_data
        
        # Sizing boundaries
        kw = triage.get("system_size_kw")
        if kw is not None:
            if kw <= 0:
                self.context.add_error("ANOMALOUS_NEGATIVE_CAPACITY")
            # Warehouse allocation threshold: Premium panels stock is 150 (60kW system max)
            elif kw > 60.0:
                self.context.add_error("CAPACITY_EXCEEDS_WAREHOUSE_LIMIT")

        # Roof limits
        roof = triage.get("roof_space_sqft")
        if roof is not None:
            if roof <= 0:
                self.context.add_error("ANOMALOUS_NEGATIVE_ROOF")
            elif roof > 15000:
                self.context.add_error("ANOMALOUS_EXCESSIVE_ROOF")

        # Budget boundaries
        budget = triage.get("budget_usd")
        if budget is not None and budget <= 0:
            self.context.add_error("ANOMALOUS_NEGATIVE_BUDGET")

    def _run_post_tech_guardrails(self):
        """Post-technical sizing validation check."""
        tech = self.context.technical_data
        if not tech.get("constraints_valid", True):
            self.context.add_error("ROOF_SPACE_EXCEEDED")

    def _handle_guardrail_alerts(self) -> str:
        """Construct clarifying prompts for anomalous states."""
        errors = self.context.validation_errors
        alerts_text = []
        
        for err in errors:
            if err == "ANOMALOUS_NEGATIVE_CAPACITY":
                alerts_text.append("* **Capacity Limit Exception:** A negative capacity capacity (kW) was entered.")
            elif err == "CAPACITY_EXCEEDS_WAREHOUSE_LIMIT":
                alerts_text.append("* **Warehouse Supply Limit Exceeded:** The target system size (>60 kW) requires more than our standard 150-panel warehouse allocation.")
            elif err == "ANOMALOUS_NEGATIVE_ROOF":
                alerts_text.append("* **Physical Space Exception:** The roof space size entered was negative or zero.")
            elif err == "ANOMALOUS_EXCESSIVE_ROOF":
                alerts_text.append("* **Verification Warning:** The roof space entered exceeds 15,000 sq ft, which is anomalous for a standard residential footprint allocation.")
            elif err == "ANOMALOUS_NEGATIVE_BUDGET":
                alerts_text.append("* **Budget Boundary Exception:** The budget entered was negative or zero.")
            elif err == "ROOF_SPACE_EXCEEDED":
                req = self.context.technical_data.get("required_footprint_sqft", 0)
                avail = self.context.triage_data.get("roof_space_sqft", 0)
                alerts_text.append(f"* **Sizing Footprint Shortfall:** The estimated layout requires {req} sq ft, but available roof space is only {avail} sq ft.")
            elif err == "WAREHOUSE_SHORTAGE":
                shortages = self.context.financial_logistics_data.get("bom_details", {}).get("shortages", [])
                alerts_text.append(f"* **Supply Chain Alert:** Sourcing shortages identified for: {', '.join(shortages)}.")

        alerts_joined = "\n".join(alerts_text)
        
        clarification_prompt = f"""### ⚠️ SYSTEM GUARDRAIL ALERT

The Multi-Agent Orchestrator has halted execution due to the following validation exceptions:

{alerts_joined}

**Next Step Required:**
Please clarify or update your input specifications (e.g., adjust the capacity, roof space, or budget) so we can recalculate your proposal correctly.
"""
        return clarification_prompt
