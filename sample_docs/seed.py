#!/usr/bin/env python3
"""
Seed script: creates realistic sample maritime documents for Seabot.

Generates:
1. Main Engine Operating Manual.pdf (15 pages: procedures, torque tables, diagrams, limits)
2. Fire Safety Checklist.pdf (8 pages: safety procedures, pump checklists, emergency actions)
3. Fuel Management Spreadsheet.xlsx (Sheets: Bunker Batches, Tank Soundings, Daily Consumption)
"""
from __future__ import annotations

import os
from pathlib import Path
import fitz  # PyMuPDF
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

SAMPLE_DIR = Path(__file__).parent


def create_engine_manual():
    pdf_path = SAMPLE_DIR / "Main Engine Operating Manual.pdf"
    doc = fitz.open()

    pages_content = [
        # Page 1: Title & General Description
        "MAIN ENGINE OPERATING MANUAL\nType: Marine Two-Stroke Diesel Engine 6S60ME-C8\nVessel: M/V Ocean Vanguard\n\n1. GENERAL ARRANGEMENT & RATINGS\nThe 6S60ME-C8 is an electronically controlled two-stroke marine diesel engine.\nContinuous Service Rating (CSR): 12,400 kW at 105 RPM.\nMaximum Continuous Rating (MCR): 14,280 kW at 108 RPM.\nBore: 600 mm, Stroke: 2,400 mm, Number of cylinders: 6.\nAll operating crew must read this manual prior to watchkeeping duties.",
        
        # Page 2: Safety & Interlocks
        "2. SAFETY INTERLOCKS AND EMERGENCY SHUTDOWN CRITERIA\nThe safety automation system continuously monitors critical engine parameters:\n- Lubricating oil inlet pressure below 1.2 bar triggers automatic emergency stop (shutdown).\n- Thrust bearing temperature above 85°C triggers immediate slowdown alarm.\n- Scavenge air box temperature above 120°C activates fire warning.\n- Jacket cooling water outlet temperature above 98°C triggers engine slowdown.\nWARNING: Never bypass mechanical or electronic safety interlocks without written authorization from the Chief Engineer.",

        # Page 3: Pre-Starting Checklist
        "3. PRE-STARTING INSPECTION PROCEDURE\n1. Ensure turning gear is disengaged and indicator cock valves are open.\n2. Start auxiliary blower and check delivery pressure > 0.05 bar.\n3. Verify main starting air bottle pressure is at least 25 bar (nominal 30 bar).\n4. Start main lubricating oil pump; verify pressure between 3.8 and 4.2 bar at inlet.\n5. Start jacket cooling water preheating; ensure temperature exceeds 60°C prior to turning.\n6. Blow through engine with air while turning gear is disengaged.\n7. Close indicator cocks and report ready to bridge.",

        # Page 4: Torque Values & Tightening Specifications
        "4. TORQUE SPECIFICATIONS & BOLT TIGHTENING TABLE\nAll fasteners must be lubricated with high-temperature anti-seize paste prior to torque application.\n\nComponent                       Nominal Torque    Tightening Pattern\n--------------------------------------------------------------------------------\nCylinder head cover studs       1250 Nm           Criss-cross (30%, 60%, 100%)\nMain bearing tie rods           2400 Nm           Hydraulic jack (450 bar)\nConnecting rod bottom-end bolts 1850 Nm           Hydraulic jack (380 bar)\nExhaust valve spindle nuts       620 Nm           Sequential circular\nFuel injector holding crab nuts  280 Nm           Alternating pairs\nIndicator cock adapter           140 Nm           Direct torque wrench\n\nCAUTION: Use calibrated torque wrenches only. Recalibrate after every 50 hours of workshop use.",

        # Page 5: Exhaust Gas Monitoring
        "5. EXHAUST GAS SYSTEM AND CYLINDER BALANCING\nNormal exhaust gas temperature at CSR: 340°C to 380°C.\nMaximum permissible exhaust gas temperature deviation between cylinders: 35°C.\nIf exhaust temperature of any single cylinder exceeds 430°C:\n1. Check fuel injector condition.\n2. Inspect scavenge air ports for fouling.\n3. Verify exhaust valve actuator timing.\n4. Reduce engine load if temperature continues to climb.",

        # Page 6: Heavy Fuel Oil Service System
        "6. HEAVY FUEL OIL (HFO) SUPPLY AND TREATMENT\nThe heavy fuel oil service pump maintains circulation through the viscometer and heater.\nOperating limits:\n- Normal operating pressure range of HFO service pump: 4.5 bar to 5.5 bar.\n- Fuel temperature at engine inlet: 135°C to 142°C (adjusted to maintain 12 cSt viscosity).\n- Return line back-pressure valve V-104 setting: 2.5 bar.\nCAUTION: When changing over from MGO to HFO, changeover rate must not exceed 2°C per minute to prevent fuel pump plunger seizure.",

        # Page 7: Lubrication Oil Specifications
        "7. LUBRICATING OIL SPECIFICATIONS & QUALITY CONTROL\nSystem oil: SAE 30 or SAE 40 alkaline detergent engine oil (BN 5–8).\nTurbocharger bearings lubrication: SAE 40 synthetic lubricating oil.\nCylinder lubricating oil:\n- Ultra-low sulfur fuel (<0.1% S): Cylinder oil BN 40.\n- VLSFO (0.5% S): Cylinder oil BN 70.\n- High sulfur fuel (>0.5% S): Cylinder oil BN 100.\nCheck lube oil sump level every watch. Water content in oil must remain below 0.2%.",

        # Page 8: Emergency Stop Procedures
        "8. EMERGENCY STOP AND CASUALTY PROCEDURES\nIf main lubricating oil pressure drops below 1.2 bar:\n1. Immediately press the emergency stop push-button on the bridge or ECR console.\n2. The automation will simultaneously reduce engine rpm and stop main fuel supply.\n3. Manually confirm engagement of auxiliary lube oil pump standby unit.\n4. Do not open crankcase doors for at least 20 minutes after stopping to prevent crankcase explosion.\n5. Keep jacket cooling water circulating to prevent thermal shock to liners.",

        # Page 9: Starting Air System & Compressors
        "9. COMPRESSED AIR SYSTEM\nThe vessel is equipped with two main air compressors and one auxiliary emergency compressor.\n- Starting air bottle capacity: 2 x 3.5 m3 bottles.\n- Normal operating bottle pressure: 30 bar.\n- Minimum air bottle pressure required to start the main engine: 25 bar.\n- Drain starting air receivers of accumulated condensate every morning watch (06:00) and evening watch (18:00).",

        # Page 10: Cooling Water Systems
        "10. JACKET COOLING WATER CIRCUIT\nFreshwater cooling is maintained in a closed-loop system.\n- Jacket cooling water inlet temperature must be maintained at 78°C to 85°C.\n- Outlet temperature from individual cylinders must not exceed 92°C under full load.\n- Expansion tank level must be monitored; test nitrite inhibitor concentration weekly (target 1500–2000 ppm NaNO2).",

        # Page 11: Piping & Valve Diagram Notes (P&ID)
        "11. FUEL OIL SYSTEM P&ID SCHEMATIC DESCRIPTION\nDiagram Reference: P&ID-ENG-FO-001\nMain fuel circulation loop:\nFrom HFO Day Tank (T-101) through suction strainer S-101 to Supply Pump P-101A/B.\nDischarge passes through automatic backwash filter F-102 to Mixing Tank T-102.\nCirculation pump P-102 delivers through steam heater H-101 to engine fuel rail.\nReturn line back-pressure is regulated by pneumatic valve V-104 (isolates fuel return line to the day tank).\nPurge valve V-109 must remain closed during normal sea steaming.",

        # Page 12: Maintenance Intervals & Overhauls
        "12. SCHEDULED PLANNED MAINTENANCE INTERVALS\nInterval             Component               Inspection Scope\n--------------------------------------------------------------------------------\nEvery 3,000 hrs      Fuel injection nozzles  Replacement interval for main engine fuel injection nozzles\nEvery 6,000 hrs      Exhaust valve assembly  Dismantle, grind seat, replace seal rings\nEvery 12,000 hrs     Piston overhaul         Pull piston, measure ring grooves, replace rings\nEvery 16,000 hrs     Turbocharger overhaul   Dynamic balancing and bearing renewal\nEvery 32,000 hrs     Main bearings           Inspect bottom halves and check clearances",

        # Page 13: Cylinder Cover Overhaul Guide
        "13. CYLINDER COVER DISASSEMBLY & ASSEMBLY PROCEDURE\n1. Isolate starting air, open indicator cocks, and engage turning gear.\n2. Drain cylinder jacket cooling water.\n3. Disconnect exhaust valve hydraulic pipes and high-pressure fuel oil injection pipes.\n4. Mount hydraulic tightening tool on cylinder cover studs.\n5. Specified tightening sequence for the cylinder cover studs: criss-cross pattern in three stages: 30%, 60%, 100%.\n6. After reassembly, hydrostatically test the water jacket at 7 bar prior to starting.",

        # Page 14: Crankcase Inspection & Bearing Clearances
        "14. CRANKCASE SAFETY & CLEARANCE MEASUREMENTS\nBefore entering crankcase:\n- Verify lock-out / tag-out of turning gear and starting air supply.\n- Ventilate crankcase and carry out gas check for oxygen content (minimum 20.9%).\nNormal clearances:\n- Main bearing clearance: 0.38 mm to 0.45 mm.\n- Crosshead guide clearance: 0.40 mm to 0.50 mm.\n- Crankpin bearing clearance: 0.35 mm to 0.42 mm.",

        # Page 15: Troubleshooting Guide
        "15. FAULT-FINDING & TROUBLESHOOTING MATRIX\nSymptom                       Probable Cause                  Remedy\n--------------------------------------------------------------------------------\nBlack exhaust smoke           Late injection timing or fouled air filter  Clean blower filter / check timing\nHigh scavenge air temp        Cooler fouled or low cooling water flow     Clean cooler water tubes\nEngine fails to turn on air   Starting air valve stuck closed             Overhaul air distributor valve\nHigh lube oil differential    Filter elements clogged                     Initiate manual backwash"
    ]

    for i, content in enumerate(pages_content, start=1):
        page = doc.new_page(width=595, height=842) # A4
        # Add decorative header
        page.draw_rect(fitz.Rect(40, 30, 555, 60), color=(0.1, 0.3, 0.5), fill=(0.1, 0.3, 0.5))
        page.insert_text((50, 50), f"M/V OCEAN VANGUARD — MAIN ENGINE TECHNICAL MANUAL — PAGE {i}", color=(1, 1, 1), fontsize=10)
        # Content body
        page.insert_textbox(fitz.Rect(50, 80, 545, 780), content, fontsize=11, fontname="helv", lineheight=1.4)
        # Footer
        page.insert_text((50, 810), "CONFIDENTIAL — STRICTLY FOR VESSEL CREW USE ONLY — SEABOT OFFLINE RAG CORPUS", fontsize=8, color=(0.5, 0.5, 0.5))

    doc.save(str(pdf_path))
    doc.close()
    print(f"Created: {pdf_path}")


def create_fire_checklist():
    pdf_path = SAMPLE_DIR / "Fire Safety Checklist.pdf"
    doc = fitz.open()

    pages_content = [
        # Page 1: SOLAS General Safety
        "SOLAS FIRE SAFETY & EMERGENCY EQUIPMENT CHECKLIST\nShip Name: M/V Ocean Vanguard | IMO: 9845123\n\n1. GENERAL FIRE SAFETY POLICY\nIn compliance with SOLAS Chapter II-2, all firefighting equipment must remain in continuous operational readiness.\nResponsibility: Safety Officer (Chief Mate) conducts weekly and monthly inspections under supervision of Master.\nReport any defect or unserviceable appliance immediately in the ship's safety logbook.",

        # Page 2: Emergency Fire Pump
        "2. EMERGENCY FIRE PUMP INSPECTION PROCEDURE\nThe emergency fire pump is situated outside the machinery space in the steering gear compartment.\nThree weekly checks required for the emergency fire pump:\n1. Battery voltage inspection (ensure minimum 24.5 VDC on starter battery banks).\n2. Fuel level check on dedicated emergency diesel engine fuel tank (minimum 85% full).\n3. Primer test and suction valve verification with sea water discharge overboard.\nOperational test: Pump must achieve working pressure of at least 6.5 bar with two fire hoses flowing simultaneously.",

        # Page 3: Quick Closing Valves
        "3. FUEL OIL QUICK-CLOSING VALVES & VENTILATION DAMPERS\nAll remote fuel quick-closing valves (pneumatically or wire operated) must be tested on a monthly basis.\nHow often must the engine room quick-closing valves be tested: monthly testing schedule with remote release from fire control station.\nInspection items:\n- Test pneumatic operating cylinder air pressure (minimum 7 bar in control air receiver).\n- Ensure no mechanical obstruction prevents valve spindle drop.\n- Reset all valves immediately after completion of drill.",

        # Page 4: Fire Hoses & Hydrants
        "4. FIRE HOSES, NOZZLES AND INTERNATIONAL SHORE CONNECTION\n- All fire hose boxes must contain one 15m canvas hose, spanners, and dual-purpose jet/spray nozzle.\n- Required test pressure for fire hoses during annual survey: 10 bar hydrostatic pressure test.\n- International Shore Connection must be stowed at main deck entrance with 4 coupling bolts and washers.\n- Inspect hydrant isolation valves for smooth operation and grease threads every quarter.",

        # Page 5: Emergency Diesel Generator
        "5. EMERGENCY DIESEL GENERATOR (EDG) SAFETY CRITERIA\nThe emergency diesel generator provides emergency power for navigation, emergency lighting, and firefighting.\n- Minimum capacity of the emergency diesel generator fuel day tank: 18 hours of continuous operation at full electrical load.\n- Automatic start-up time test: Generator must take over emergency switchboard load within 45 seconds of main blackout.\n- Test starting both with electric starter motor and secondary spring/hydraulic starter weekly.",

        # Page 6: Fixed CO2 Smothering System
        "6. FIXED CO2 FIRE EXTINGUISHING SYSTEM (ENGINE ROOM)\nSteps that must be taken prior to entering the CO2 bottle room:\n1. Ensure continuous ventilation for 15 minutes before personnel entry.\n2. Carry calibrated portable multi-gas detector check (O2 >= 20.9% and CO2 < 0.1%).\n3. Entry must be made by minimum of two crew members with radio contact to bridge.\nEmergency release procedure:\nOnly Master or Chief Engineer is authorized to pull the CO2 discharge cabinet control cables.",

        # Page 7: Scavenge Box Fire Procedure
        "7. SCAVENGE AIR BOX FIRE EMERGENCY PROCEDURE\nIf high temperature alarm or smoke detector triggers in the scavenge manifold:\nWhat action should be taken if scavenger air box fire alarm activates:\n1. Immediately slow down engine rpm to slow ahead.\n2. Stop fuel to affected cylinder using fuel injection pump cut-off.\n3. Open smothering steam or CO2 extinguishing line to scavenge box.\n4. Keep turning gear and auxiliary blowers off until casing temperature drops below 60°C.\nCAUTION: Never open scavenge inspection doors while hot due to risk of explosion.",

        # Page 8: EEBD and Breathing Apparatus
        "8. EMERGENCY ESCAPE BREATHING DEVICES (EEBD) & SCBA UNITS\n- EEBD units provide 15 minutes of breathing air for emergency evacuation only.\n- SCBA (Self-Contained Breathing Apparatus) cylinders must maintain 200 bar or 300 bar working pressure.\n- Low pressure audible alarm must sound when cylinder pressure falls to 55 bar.\n- Inspect face masks for rubber degradation and check harness buckles monthly."
    ]

    for i, content in enumerate(pages_content, start=1):
        page = doc.new_page(width=595, height=842)
        page.draw_rect(fitz.Rect(40, 30, 555, 60), color=(0.6, 0.1, 0.1), fill=(0.6, 0.1, 0.1))
        page.insert_text((50, 50), f"M/V OCEAN VANGUARD — SAFETY MANAGEMENT MANUAL — SECTION {i}", color=(1, 1, 1), fontsize=10)
        page.insert_textbox(fitz.Rect(50, 80, 545, 780), content, fontsize=11, fontname="helv", lineheight=1.4)
        page.insert_text((50, 810), "OFFICIAL SHIP SAFETY RECORD — VERIFIED BY SEABOT OFFLINE SYSTEM", fontsize=8, color=(0.5, 0.5, 0.5))

    doc.save(str(pdf_path))
    doc.close()
    print(f"Created: {pdf_path}")


def create_fuel_spreadsheet():
    xlsx_path = SAMPLE_DIR / "Fuel Management Spreadsheet.xlsx"
    wb = openpyxl.Workbook()

    # Sheet 1: Tank Capacities & Soundings
    ws1 = wb.active
    ws1.title = "Tank Capacities"

    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")

    headers1 = ["Tank Name", "Location", "Fuel Type", "Nominal Capacity (m3)", "Current Sounding (m)", "Current Volume (m3)", "Density at 15C (kg/m3)"]
    ws1.append(headers1)
    for col in range(1, len(headers1) + 1):
        cell = ws1.cell(row=1, column=col)
        cell.font = header_font
        cell.fill = header_fill

    tank_data = [
        ["HFO Tank 1 Port", "Frames 32-48 Port", "VLSFO", 420.5, 6.82, 385.2, 984.2],
        ["HFO Tank 1 Starboard", "Frames 32-48 Stbd", "VLSFO", 420.5, 6.45, 362.8, 984.2],
        ["HFO Tank 2 Port", "Frames 48-64 Port", "VLSFO", 510.0, 7.10, 470.5, 985.1],
        ["HFO Tank 2 Starboard", "Frames 48-64 Stbd", "VLSFO", 510.0, 7.05, 468.0, 985.1],
        ["MGO Day Tank", "Engine Room Casing", "LSMGO", 35.0, 2.80, 28.5, 858.4],
        ["MGO Tank 3 Starboard", "Frames 64-75 Stbd", "LSMGO", 145.0, 4.20, 122.4, 858.4],
        ["HFO Settling Tank", "Frames 45-50 Center", "VLSFO", 42.0, 3.40, 38.0, 984.5],
        ["HFO Service Tank", "Frames 50-55 Center", "VLSFO", 38.0, 3.10, 34.2, 984.5],
    ]
    for row in tank_data:
        ws1.append(row)

    # Sheet 2: Bunker Batches
    ws2 = wb.create_sheet(title="Bunker Batches")
    headers2 = ["Batch ID", "Bunker Port", "Date Delivered", "Fuel Grade", "Sulfur Content (%)", "Viscosity at 50C (cSt)", "Quantity (MT)"]
    ws2.append(headers2)
    for col in range(1, len(headers2) + 1):
        cell = ws2.cell(row=1, column=col)
        cell.font = header_font
        cell.fill = header_fill

    bunker_data = [
        ["B-2026-01", "Rotterdam", "2026-01-14", "VLSFO 0.5%", 0.46, 310.5, 850.0],
        ["B-2026-02", "Singapore", "2026-02-28", "VLSFO 0.5%", 0.49, 325.0, 1100.0],
        ["B-2026-03", "Fujairah", "2026-03-22", "LSMGO 0.1%", 0.08, 3.8, 220.0],
        ["B-2026-04", "Gibraltar", "2026-04-18", "VLSFO 0.5%", 0.48, 318.2, 750.0],
        ["B-2026-05", "Panama", "2026-05-30", "LSMGO 0.1%", 0.09, 3.6, 180.0],
    ]
    for row in bunker_data:
        ws2.append(row)

    # Sheet 3: Daily Consumption
    ws3 = wb.create_sheet(title="Daily Consumption")
    headers3 = ["Operating Mode", "Engine Speed (RPM)", "Main Engine (MT/day)", "Auxiliary Engines (MT/day)", "Auxiliary Boiler (MT/day)", "Total Fuel (MT/day)"]
    ws3.append(headers3)
    for col in range(1, len(headers3) + 1):
        cell = ws3.cell(row=1, column=col)
        cell.font = header_font
        cell.fill = header_fill

    consumption_data = [
        ["Port / Idle", 0, 0.0, 2.8, 1.2, 4.0],
        ["Maneuvering", 45, 8.5, 3.5, 1.5, 13.5],
        ["Eco Steaming", 85, 24.2, 3.2, 1.8, 29.2],
        ["Full Sea Speed", 102, 36.8, 3.6, 2.1, 42.5],
        ["Maximum Rating", 108, 44.5, 4.0, 2.4, 50.9],
    ]
    for row in consumption_data:
        ws3.append(row)

    wb.save(str(xlsx_path))
    print(f"Created: {xlsx_path}")


if __name__ == "__main__":
    create_engine_manual()
    create_fire_checklist()
    create_fuel_spreadsheet()
    print("Seed documents created successfully!")
