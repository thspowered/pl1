#!/usr/bin/env python3
import os
import sys

# Add root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pl1.backend.pl1_parser import parse_pl1_formula
from pl1.backend.model import formula_to_model

def test_model_rules_with_attributes():
    """
    Test na generovanie pravidiel s atribútmi.
    
    Táto funkcia testuje extrakciu pravidiel pre modely automobilov, 
    ktoré okrem štandardných vzťahov obsahujú aj atribúty ako:
    - power (výkon motora)
    - cylinders (počet valcov)
    - color (farba vozidla)
    - allowed_transmission_types (povolené typy prevodoviek)
    - allowed_engine_types (povolené typy motorov)
    """
    
    # Definujeme zložitú formulu s atribútmi
    formula_str = """
    Ι(e₁, PetrolEngine) ∧
    Ι(d₁, XDrive) ∧
    Ι(t₁, ManualTransmission) ∧
    Ι(c₁, X5) ∧
    Π(c₁, d₁) ∧
    Π(c₁, t₁) ∧
    Π(e₁, t₁) ∧
    Π(c₁, e₁) ∧
    Μ(X5, AWD) ∧
    Μ(BMW, DriveSystem) ∧
    Μ(X5, Transmission) ∧
    Μ(BMW, Component) ∧
    Μ(PetrolEngine, Transmission) ∧
    Μ(Engine, Component) ∧
    Μ(X5, Engine) ∧
    Μ(X5, ManualTransmission) ∧
    Μ(c₁, t₁) ∧
    Μ(PetrolEngine, ManualTransmission) ∧
    Μ(e₁, t₁) ∧
    Μ(X5, PetrolEngine) ∧
    Μ(c₁, e₁) ∧
    Μ(X5, XDrive) ∧
    Μ(c₁, d₁) ∧
    Α(e₁, power, (262.6, 400)) ∧
    Α(e₁, cylinders, (6.06, 8)) ∧
    Α(e₁, allowed_transmission_types, {"AutomaticTransmission", "ManualTransmission"}) ∧
    Α(c₁, color, {"blue", "black"}) ∧
    Α(c₁, allowed_engine_types, {"PetrolEngine", "HybridEngine", "DieselEngine"}) ∧
    Α(c₁, allowed_transmission_types, {"AutomaticTransmission", "ManualTransmission"})
    """
    
    # Vyčistenie formuly (odstránenie whitespace a prázdnych riadkov)
    lines = [line.strip() for line in formula_str.split('\n') if line.strip()]
    cleaned_lines = []
    for line in lines:
        if line.endswith('∧'):
            line = line[:-1].strip()
        cleaned_lines.append(line)
    clean_formula = ' ∧ '.join(cleaned_lines)
    
    print(f"Čistá formula: {clean_formula}")
    
    # Parsovanie formuly
    parsed_formula = parse_pl1_formula(clean_formula)
    
    # Vytvorenie modelu z formuly
    model = formula_to_model(parsed_formula)
    
    # Výpis objektov a ich atribútov
    print("\nObjekty a ich atribúty:")
    for obj in model.objects:
        if obj.attributes:
            print(f"  {obj.name} ({obj.class_name}): {obj.attributes}")
    
    # Výpis spojení v modeli
    print("\nSpojenia v modeli:")
    for link in model.links:
        print(f"  {link.source} -> {link.target} (typ: {link.link_type.name})")
    
    # Extrakcia pravidiel z modelu
    model_rules = model.extract_model_rules()
    
    # Výpis extrahovaných pravidiel
    print("\nExtrahované pravidlá:\n")
    for model_name, rule in model_rules.items():
        print(f"{model_name}:\n{rule}\n")

if __name__ == "__main__":
    test_model_rules_with_attributes() 