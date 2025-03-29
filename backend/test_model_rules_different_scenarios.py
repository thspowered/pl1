#!/usr/bin/env python3
import os
import sys

# Add root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pl1.backend.pl1_parser import parse_pl1_formula
from pl1.backend.model import formula_to_model

def run_test_case(name, formula_str):
    """
    Spustí testovací prípad pre danú formulu.
    
    Args:
        name: Názov testovacieho prípadu
        formula_str: Formula na testovanie
    """
    print(f"\n\n{'=' * 80}")
    print(f"TEST CASE: {name}")
    print(f"{'=' * 80}\n")
    
    # Vyčistenie formuly (odstránenie whitespace a prázdnych riadkov)
    lines = [line.strip() for line in formula_str.split('\n') if line.strip()]
    cleaned_lines = []
    for line in lines:
        if line.endswith('∧'):
            line = line[:-1].strip()
        cleaned_lines.append(line)
    clean_formula = ' ∧ '.join(cleaned_lines)
    
    print(f"Čistá formula: {clean_formula[:100]}..." if len(clean_formula) > 100 else clean_formula)
    
    # Parsovanie formuly
    parsed_formula = parse_pl1_formula(clean_formula)
    
    # Vytvorenie modelu z formuly
    model = formula_to_model(parsed_formula)
    
    # Výpis objektov a ich atribútov
    print("\nObjekty a ich atribúty:")
    for obj in model.objects:
        if obj.attributes:
            print(f"  {obj.name} ({obj.class_name}): {obj.attributes}")
    
    # Extrakcia pravidiel z modelu
    model_rules = model.extract_model_rules()
    
    # Výpis extrahovaných pravidiel
    print("\nExtrahované pravidlá:\n")
    for model_name, rule in model_rules.items():
        if rule and len(rule.strip()) > 0:
            print(f"{model_name}:\n{rule}\n")
        else:
            print(f"{model_name}: Žiadne pravidlo nebolo extrahované\n")
    
    return model_rules

def test_series_model_with_engine_attributes():
    """Test Series3 modelu s atribútmi motora."""
    formula = """
    Ι(e₁, PetrolEngine) ∧
    Ι(d₁, RWD) ∧
    Ι(t₁, AutomaticTransmission) ∧
    Ι(c₁, Series3) ∧
    Π(c₁, d₁) ∧
    Π(c₁, t₁) ∧
    Π(c₁, e₁) ∧
    Μ(Series3, RWD) ∧
    Μ(Series3, Engine) ∧
    Μ(Series3, Transmission) ∧
    Μ(c₁, d₁) ∧
    Μ(c₁, e₁) ∧
    Μ(c₁, t₁) ∧
    Α(e₁, power, (180, 250)) ∧
    Α(e₁, cylinders, 4) ∧
    Α(e₁, fuel_consumption, (6.5, 8.2)) ∧
    Α(c₁, color, {"white", "silver", "black"}) ∧
    Α(c₁, max_speed, 240)
    """
    return run_test_case("Series3 s atribútmi motora", formula)

def test_x5_model_with_complex_attributes():
    """Test X5 modelu s komplexnými atribútmi a viacerými objektmi."""
    formula = """
    Ι(e₁, PetrolEngine) ∧
    Ι(e₂, DieselEngine) ∧
    Ι(d₁, XDrive) ∧
    Ι(t₁, AutomaticTransmission) ∧
    Ι(c₁, X5) ∧
    Π(c₁, d₁) ∧
    Π(c₁, t₁) ∧
    Π(c₁, e₁) ∧
    Μ(X5, XDrive) ∧
    Μ(X5, Engine) ∧
    Μ(X5, Transmission) ∧
    Μ(c₁, d₁) ∧
    Μ(c₁, e₁) ∧
    Μ(c₁, t₁) ∧
    Α(e₁, power, (286, 530)) ∧
    Α(e₁, cylinders, (6, 8)) ∧
    Α(e₂, power, (265, 400)) ∧
    Α(e₂, cylinders, 6) ∧
    Α(e₂, torque, (620, 760)) ∧
    Α(c₁, weight, (2185, 2510)) ∧
    Α(c₁, length, 4922) ∧
    Α(c₁, width, 2004) ∧
    Α(c₁, height, 1745) ∧
    Α(c₁, color, {"alpine_white", "carbon_black", "mineral_white", "phytonic_blue", "arctic_grey"}) ∧
    Α(t₁, gears, 8)
    """
    return run_test_case("X5 s komplexnými atribútmi", formula)

def test_bmw_with_multiple_drive_systems():
    """Test základného BMW modelu s viacerými systémami pohonu."""
    formula = """
    Ι(d₁, RWD) ∧
    Ι(d₂, XDrive) ∧
    Ι(e₁, PetrolEngine) ∧
    Ι(t₁, ManualTransmission) ∧
    Ι(t₂, AutomaticTransmission) ∧
    Ι(c₁, BMW) ∧
    Π(c₁, d₁) ∧
    Π(c₁, e₁) ∧
    Π(c₁, t₁) ∧
    Μ(BMW, DriveSystem) ∧
    Μ(BMW, Engine) ∧
    Μ(BMW, Transmission) ∧
    Μ(c₁, d₁) ∧
    Μ(c₁, e₁) ∧
    Μ(c₁, t₁) ∧
    Α(c₁, year, 2023) ∧
    Α(c₁, electric_range, 0) ∧
    Α(c₁, allowed_drive_systems, {"RWD", "XDrive"})
    """
    return run_test_case("BMW s viacerými systémami pohonu", formula)

def test_series7_with_hybrid_system():
    """Test Series7 s hybridným systémom a výbavou."""
    formula = """
    Ι(e₁, HybridEngine) ∧
    Ι(d₁, AWD) ∧
    Ι(t₁, AutomaticTransmission) ∧
    Ι(c₁, Series7) ∧
    Ι(b₁, Battery) ∧
    Π(c₁, d₁) ∧
    Π(c₁, t₁) ∧
    Π(c₁, e₁) ∧
    Π(e₁, b₁) ∧
    Μ(Series7, AWD) ∧
    Μ(Series7, Engine) ∧
    Μ(Series7, Transmission) ∧
    Μ(HybridEngine, Battery) ∧
    Μ(c₁, d₁) ∧
    Μ(c₁, e₁) ∧
    Μ(c₁, t₁) ∧
    Μ(e₁, b₁) ∧
    Α(e₁, power, (390, 540)) ∧
    Α(e₁, electric_power, (150, 230)) ∧
    Α(b₁, capacity, (12, 18.7)) ∧
    Α(c₁, features, {"autonomous_parking", "night_vision", "laser_light", "massage_seats"}) ∧
    Α(c₁, price, (110000, 180000))
    """
    return run_test_case("Series7 s hybridným systémom", formula)

def test_x7_with_multimedia_system():
    """Test X7 s multimediálnym systémom a jeho atribútmi."""
    formula = """
    Ι(e₁, PetrolEngine) ∧
    Ι(d₁, XDrive) ∧
    Ι(t₁, AutomaticTransmission) ∧
    Ι(c₁, X7) ∧
    Ι(m₁, MultimediaSystem) ∧
    Π(c₁, d₁) ∧
    Π(c₁, t₁) ∧
    Π(c₁, e₁) ∧
    Π(c₁, m₁) ∧
    Μ(X7, XDrive) ∧
    Μ(X7, Engine) ∧
    Μ(X7, Transmission) ∧
    Μ(X7, MultimediaSystem) ∧
    Μ(c₁, d₁) ∧
    Μ(c₁, e₁) ∧
    Μ(c₁, t₁) ∧
    Μ(c₁, m₁) ∧
    Α(e₁, power, (340, 530)) ∧
    Α(e₁, cylinders, 8) ∧
    Α(m₁, screen_size, (12.3, 14.9)) ∧
    Α(m₁, features, {"apple_carplay", "android_auto", "gesture_control", "voice_assistant"}) ∧
    Α(c₁, seats, (6, 7)) ∧
    Α(c₁, cargo_volume, (326, 2120))
    """
    return run_test_case("X7 s multimediálnym systémom", formula)

def run_all_tests():
    """Spustí všetky testovacie prípady."""
    print("\nSpúšťanie testov pre extrakciu pravidiel modelov s atribútmi...\n")
    
    test_series_model_with_engine_attributes()
    test_x5_model_with_complex_attributes()
    test_bmw_with_multiple_drive_systems()
    test_series7_with_hybrid_system()
    test_x7_with_multimedia_system()
    
    print("\nVšetky testy dokončené.")

if __name__ == "__main__":
    run_all_tests()
 