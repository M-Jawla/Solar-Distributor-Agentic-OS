import os
import sys
from agent_core import SolarOrchestrator

# Reconfigure stdout to use UTF-8 on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding='utf-8')

def print_separator(title: str):
    print("\n" + "="*60)
    print(f" {title.upper()} ")
    print("="*60)

def main():
    print("Starting Solar Multi-Agent Sizing & Sourcing System Test Suite...")
    
    # Initialize the orchestrator
    orchestrator = SolarOrchestrator()
    
    # --- TEST CASE 1: Standard Customer Ingestion (Happy Path) ---
    print_separator("Test Case 1: Standard Ingestion (Happy Path)")
    happy_path_email = (
        "Dear Solar Distributor, "
        "I am looking to install a solar setup at my house in Austin, Texas. "
        "My roof is roughly 600 sq ft. I pay $0.18/kWh to the utility and use about "
        "12,000 kWh annually. I want a 6.0 kW system capacity. My budget is $20,000."
    )
    print(f"Customer Input Email:\n\"{happy_path_email}\"\n")
    response_1 = orchestrator.receive_query(happy_path_email)
    print("Extracted Ingestion State (Triage):", orchestrator.context.triage_data)
    print("Orchestrator Response:")
    print(response_1)
    
    # Print the internal memory bank state to show routing and data variables
    orchestrator.context.print_state()
    
    # --- TEST CASE 2: Multi-Turn Modification Request ---
    print_separator("Test Case 2: Multi-Turn Sizing Modification")
    modification_message = (
        "Actually, my neighbor said I should get an 8.0 kW system instead. "
        "Can we update the capacity to 8.0 kW and recalculate the ROI and Bill of Materials?"
    )
    print(f"Customer Message:\n\"{modification_message}\"\n")
    response_2 = orchestrator.receive_query(modification_message)
    print("Orchestrator Response:")
    print(response_2)
    
    # Print updated memory bank state
    orchestrator.context.print_state()
    
    # --- TEST CASE 3: Physical Anomaly Sizing Guardrail (Negative Roof Space) ---
    print_separator("Test Case 3: Guardrail Check - Negative Sizing Footprint")
    negative_space_email = (
        "Hello, I need a standard 5.0 kW solar capacity system, but my roof area is -400 sq ft. "
        "Please send a quote."
    )
    print(f"Customer Input Email:\n\"{negative_space_email}\"\n")
    # Reset orchestrator for fresh session
    orchestrator_guard1 = SolarOrchestrator()
    response_3 = orchestrator_guard1.receive_query(negative_space_email)
    print("Orchestrator Response:")
    print(response_3)
    
    # --- TEST CASE 4: Sizing Footprint Constraint (Roof space too small for size) ---
    print_separator("Test Case 4: Guardrail Check - Sizing Footprint Shortfall")
    too_small_roof_email = (
        "Hi, I want a large 15.0 kW solar capacity system. My roof space is only 300 sq ft. "
        "I pay $0.22/kWh and use 20,000 kWh annually. Can you build this?"
    )
    print(f"Customer Input Email:\n\"{too_small_roof_email}\"\n")
    orchestrator_guard2 = SolarOrchestrator()
    response_4 = orchestrator_guard2.receive_query(too_small_roof_email)
    print("Orchestrator Response:")
    print(response_4)
    
    # --- TEST CASE 5: Warehouse Sourcing Limit Exceeded (Commercial Size Request) ---
    print_separator("Test Case 5: Guardrail Check - Warehouse Stock Sourcing Limit")
    commercial_email = (
        "Good afternoon. We need a commercial 70.0 kW system for our warehouse in San Jose. "
        "We have plenty of space (10,000 sq ft) and a budget of $150,000. Send over the invoice."
    )
    print(f"Customer Input Email:\n\"{commercial_email}\"\n")
    orchestrator_guard3 = SolarOrchestrator()
    response_5 = orchestrator_guard3.receive_query(commercial_email)
    print("Orchestrator Response:")
    print(response_5)

if __name__ == "__main__":
    main()
