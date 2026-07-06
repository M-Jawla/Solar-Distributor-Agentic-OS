import math

# Warehouse Inventory database mock
INVENTORY_DB = {
    "panels": {"name": "Premium 400W Monocrystalline Panel", "stock": 150, "unit_cost": 250.00},
    "inverters": {"name": "Smart Microinverter 400W", "stock": 100, "unit_cost": 150.00},
    "racking": {"name": "Universal Racking Mount Kit (per panel)", "stock": 200, "unit_cost": 50.00},
    "bos": {"name": "Balance of System (Wiring, Combiner, Breakers)", "stock": 50, "unit_cost": 400.00}
}

def calculate_required_footprint(target_kw: float, panel_efficiency: float = 0.20) -> dict:
    """
    Calculate the required physical footprint (sq. ft.) based on target kW capacity.
    Standard panel specs: 400W (0.4 kW) power output, dimensions ~5.4 ft x 3.2 ft = ~17.28 sq. ft.
    We round standard panel size to 17.5 sq. ft. to account for spacing.
    """
    if target_kw <= 0:
        raise ValueError("Target capacity must be greater than 0 kW.")
        
    panel_wattage_kw = 0.40  # 400W
    panel_area_sqft = 17.5   # 5.4 ft x 3.2 ft + tolerance
    
    # Calculate number of panels needed
    panels_needed = math.ceil(target_kw / panel_wattage_kw)
    total_footprint_sqft = panels_needed * panel_area_sqft
    
    return {
        "target_kw": target_kw,
        "panels_needed": panels_needed,
        "panel_wattage_w": 400,
        "panel_area_sqft": panel_area_sqft,
        "required_footprint_sqft": total_footprint_sqft,
        "efficiency_used": panel_efficiency
    }

def calculate_roi(
    kw_capacity: float, 
    initial_investment: float, 
    utility_rate: float, 
    annual_usage_kwh: float, 
    escalation_rate: float = 0.05, 
    degradation_rate: float = 0.005
) -> dict:
    """
    Calculate 25-year lifecycle savings and payback period.
    Assumes standard insolation: 1 kW of solar capacity generates 1,500 kWh of energy per year.
    Escalates grid energy costs annually (escalation_rate).
    Degrades solar production efficiency annually (degradation_rate).
    """
    if kw_capacity <= 0 or initial_investment <= 0 or utility_rate <= 0 or annual_usage_kwh <= 0:
        raise ValueError("All input parameters must be positive non-zero values.")
        
    annual_generation_base = kw_capacity * 1500.0
    timeline = []
    cumulative_savings = 0.0
    payback_year = None
    
    for year in range(1, 26):
        # Degrade solar generation
        generation_this_year = annual_generation_base * ((1.0 - degradation_rate) ** (year - 1))
        # Escalate grid rates
        rate_this_year = utility_rate * ((1.0 + escalation_rate) ** (year - 1))
        
        # Calculate utility cost offsets
        # If solar generation exceeds usage, the offset is capped at usage. 
        # Excess is exported to grid at 50% export credit.
        offset_kwh = min(generation_this_year, annual_usage_kwh)
        export_kwh = max(0.0, generation_this_year - annual_usage_kwh)
        
        savings_from_offset = offset_kwh * rate_this_year
        savings_from_export = export_kwh * (rate_this_year * 0.5)
        annual_savings = savings_from_offset + savings_from_export
        
        cumulative_savings += annual_savings
        net_position = cumulative_savings - initial_investment
        
        # Track when we break even
        if net_position >= 0 and payback_year is None:
            # Linear interpolation for fractional payback year
            prev_cumulative = cumulative_savings - annual_savings
            needed = initial_investment - prev_cumulative
            fraction = needed / annual_savings if annual_savings > 0 else 0.0
            payback_year = round((year - 1) + fraction, 2)
            
        timeline.append({
            "year": year,
            "solar_gen_kwh": round(generation_this_year, 1),
            "utility_rate_per_kwh": round(rate_this_year, 4),
            "annual_savings_usd": round(annual_savings, 2),
            "cumulative_savings_usd": round(cumulative_savings, 2),
            "net_position_usd": round(net_position, 2)
        })
        
    net_25yr_savings = cumulative_savings - initial_investment
    net_roi_percent = (cumulative_savings / initial_investment) * 100.0 if initial_investment > 0 else 0.0
    
    return {
        "initial_investment_usd": initial_investment,
        "annual_usage_kwh": annual_usage_kwh,
        "base_annual_generation_kwh": annual_generation_base,
        "escalation_rate": escalation_rate,
        "degradation_rate": degradation_rate,
        "payback_period_years": payback_year if payback_year is not None else "Never (>25 yrs)",
        "total_25yr_savings_usd": round(cumulative_savings, 2),
        "net_25yr_savings_usd": round(net_25yr_savings, 2),
        "roi_percentage": round(net_roi_percent, 2),
        "timeline": timeline
    }

def check_inventory_and_bom(target_kw: float) -> dict:
    """
    Cross-reference required quantities with warehouse stocks.
    Generates a formal Bill of Materials (BOM) and flags shortages.
    Calculates retail pricing using a standard pricing model:
    Hardware Cost + Labor ($1200 base + $150 per panel) + Permits ($800) plus 30% distributor margin.
    """
    if target_kw <= 0:
        raise ValueError("Target capacity must be greater than 0 kW.")
        
    panels_needed = math.ceil(target_kw / 0.4)
    inverters_needed = panels_needed
    racking_needed = panels_needed
    bos_needed = 1
    
    bom = []
    shortage_detected = False
    shortages = []
    
    # Check Panels
    panels_stock = INVENTORY_DB["panels"]["stock"]
    panels_cost = panels_needed * INVENTORY_DB["panels"]["unit_cost"]
    panels_status = "Available"
    if panels_needed > panels_stock:
        panels_status = f"Shortage (Needs {panels_needed}, Only {panels_stock} in stock)"
        shortage_detected = True
        shortages.append(f"Solar Panels (Short by {panels_needed - panels_stock})")
    bom.append({
        "item": "Panels",
        "name": INVENTORY_DB["panels"]["name"],
        "required": panels_needed,
        "in_stock": panels_stock,
        "unit_cost_usd": INVENTORY_DB["panels"]["unit_cost"],
        "total_cost_usd": panels_cost,
        "status": panels_status
    })
    
    # Check Inverters
    inverters_stock = INVENTORY_DB["inverters"]["stock"]
    inverters_cost = inverters_needed * INVENTORY_DB["inverters"]["unit_cost"]
    inverters_status = "Available"
    if inverters_needed > inverters_stock:
        inverters_status = f"Shortage (Needs {inverters_needed}, Only {inverters_stock} in stock)"
        shortage_detected = True
        shortages.append(f"Inverters (Short by {inverters_needed - inverters_stock})")
    bom.append({
        "item": "Inverters",
        "name": INVENTORY_DB["inverters"]["name"],
        "required": inverters_needed,
        "in_stock": inverters_stock,
        "unit_cost_usd": INVENTORY_DB["inverters"]["unit_cost"],
        "total_cost_usd": inverters_cost,
        "status": inverters_status
    })
    
    # Check Racking
    racking_stock = INVENTORY_DB["racking"]["stock"]
    racking_cost = racking_needed * INVENTORY_DB["racking"]["unit_cost"]
    racking_status = "Available"
    if racking_needed > racking_stock:
        racking_status = f"Shortage (Needs {racking_needed}, Only {racking_stock} in stock)"
        shortage_detected = True
        shortages.append(f"Racking kits (Short by {racking_needed - racking_stock})")
    bom.append({
        "item": "Racking",
        "name": INVENTORY_DB["racking"]["name"],
        "required": racking_needed,
        "in_stock": racking_stock,
        "unit_cost_usd": INVENTORY_DB["racking"]["unit_cost"],
        "total_cost_usd": racking_cost,
        "status": racking_status
    })
    
    # Check Balance of System (BOS)
    bos_stock = INVENTORY_DB["bos"]["stock"]
    bos_cost = bos_needed * INVENTORY_DB["bos"]["unit_cost"]
    bos_status = "Available"
    if bos_needed > bos_stock:
        bos_status = f"Shortage (Needs {bos_needed}, Only {bos_stock} in stock)"
        shortage_detected = True
        shortages.append(f"BOS kits (Short by {bos_needed - bos_stock})")
    bom.append({
        "item": "BOS",
        "name": INVENTORY_DB["bos"]["name"],
        "required": bos_needed,
        "in_stock": bos_stock,
        "unit_cost_usd": INVENTORY_DB["bos"]["unit_cost"],
        "total_cost_usd": bos_cost,
        "status": bos_status
    })
    
    hardware_cost = panels_cost + inverters_cost + racking_cost + bos_cost
    
    # Calculate installation labor and permit pricing
    labor_cost = 1200.00 + (150.00 * panels_needed)
    permit_fees = 800.00
    subtotal = hardware_cost + labor_cost + permit_fees
    
    # 30% margin added
    distributor_markup = subtotal * 0.30
    total_retail_quote = subtotal + distributor_markup
    
    return {
        "target_kw": target_kw,
        "bom": bom,
        "hardware_cost_usd": round(hardware_cost, 2),
        "labor_cost_usd": round(labor_cost, 2),
        "permits_and_engineering_usd": round(permit_fees, 2),
        "subtotal_cost_usd": round(subtotal, 2),
        "markup_usd": round(distributor_markup, 2),
        "total_retail_quote_usd": round(total_retail_quote, 2),
        "shortage_detected": shortage_detected,
        "shortages": shortages
    }
