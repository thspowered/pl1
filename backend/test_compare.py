#!/usr/bin/env python3
import os
import sys

# Pridanie rootu projektu do Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pl1.backend.model import Model, Link, LinkType, Object, ClassificationTree, is_valid_example, formula_to_model
from pl1.backend.pl1_parser import parse_pl1_formula, Formula, Predicate, PredicateType

def init_classification_tree():
    """Inicializuje klasifikačný strom so základnými triedami."""
    tree = ClassificationTree()
    
    # Základné triedy pre BMW príklady
    tree.add_relationship("Vehicle", None)  # Koreňová trieda
    
    # Triedy BMW
    tree.add_relationship("BMW", "Vehicle")
    tree.add_relationship("Series3", "BMW")
    tree.add_relationship("Series5", "BMW")
    tree.add_relationship("Series7", "BMW")
    tree.add_relationship("X5", "BMW")
    tree.add_relationship("X7", "BMW")
    
    # Komponenty
    tree.add_relationship("Component", None)
    
    # Motor a jeho podtriedy
    tree.add_relationship("Engine", "Component")
    tree.add_relationship("PetrolEngine", "Engine")
    tree.add_relationship("DieselEngine", "Engine")
    tree.add_relationship("HybridEngine", "Engine")
    
    # Prevodovka a jej podtriedy
    tree.add_relationship("Transmission", "Component")
    tree.add_relationship("AutomaticTransmission", "Transmission")
    tree.add_relationship("ManualTransmission", "Transmission")
    
    # Pohon a jeho podtriedy
    tree.add_relationship("DriveSystem", "Component")
    tree.add_relationship("RWD", "DriveSystem")
    tree.add_relationship("AWD", "DriveSystem")
    tree.add_relationship("XDrive", "AWD")  # XDrive je typ AWD
    
    return tree

def create_test_model():
    """Vytvorí testovací model pre BMW auta s pravidlami."""
    model = Model()
    
    # Pridanie základných BMW objektov
    model.objects.append(Object("BMW", "BMW"))
    model.objects.append(Object("Series3", "Series3"))
    model.objects.append(Object("Series5", "Series5")) 
    model.objects.append(Object("Series7", "Series7"))
    model.objects.append(Object("X5", "X5"))
    model.objects.append(Object("X7", "X7"))
    
    # Pridanie komponentov
    model.objects.append(Object("Engine", "Engine"))
    model.objects.append(Object("PetrolEngine", "PetrolEngine"))
    model.objects.append(Object("DieselEngine", "DieselEngine"))
    model.objects.append(Object("HybridEngine", "HybridEngine"))
    model.objects.append(Object("Transmission", "Transmission"))
    model.objects.append(Object("AutomaticTransmission", "AutomaticTransmission"))
    model.objects.append(Object("ManualTransmission", "ManualTransmission"))
    model.objects.append(Object("DriveSystem", "DriveSystem"))
    model.objects.append(Object("RWD", "RWD"))
    model.objects.append(Object("AWD", "AWD"))
    model.objects.append(Object("XDrive", "XDrive"))
    
    # Vytvorenie základných pravidiel pre všetky BMW modely
    for bmw_model in ["BMW", "Series3", "Series5", "Series7", "X5", "X7"]:
        # Všetky BMW modely musia mať motor
        model.links.append(Link(bmw_model, "Engine", LinkType.MUST))
        # Všetky BMW modely musia mať prevodovku
        model.links.append(Link(bmw_model, "Transmission", LinkType.MUST))
        # Všetky BMW modely musia mať pohon
        model.links.append(Link(bmw_model, "DriveSystem", LinkType.MUST))
    
    # X modely musia mať XDrive
    model.links.append(Link("X5", "XDrive", LinkType.MUST))
    model.links.append(Link("X7", "XDrive", LinkType.MUST))
    
    # Series7 musí mať AWD
    model.links.append(Link("Series7", "AWD", LinkType.MUST))
    
    # Series3 a Series5 majú RWD
    model.links.append(Link("Series3", "RWD", LinkType.MUST))
    model.links.append(Link("Series5", "RWD", LinkType.MUST))
    
    # X7 musí mať automatickú prevodovku
    model.links.append(Link("X7", "AutomaticTransmission", LinkType.MUST))
    
    return model

def test_example(formula, model, classification_tree, expected_result=True, description=""):
    """Test jedného príkladu."""
    # Odstránime medzery a nové riadky na začiatku a konci
    formula = formula.strip()
    
    # Vyčistíme štruktúru vzorca - odstránime nadbytočné medzery a znaky nových riadkov
    lines = [line.strip() for line in formula.split('\n') if line.strip()]
    # Odstránime riadky so začínajúce #
    filtered_lines = [line for line in lines if not line.startswith('#')]
    
    # Upravíme formát, odstránime ∧ na koncoch riadkov
    cleaned_lines = []
    for line in filtered_lines:
        if line.endswith('∧'):
            line = line[:-1].strip()
        cleaned_lines.append(line)
    
    # Spojíme riadky s ∧
    clean_formula = ' ∧ '.join(cleaned_lines)
    
    print(f"Čistý vzorec: {clean_formula}")
    
    try:
        parsed_formula = parse_pl1_formula(clean_formula)
        example_model = formula_to_model(parsed_formula)
        
        print(f"\nTEST DEBUG - {description}")
        print("Objekty v príklade:")
        for obj in example_model.objects:
            print(f"  - {obj.name}: {obj.class_name}")
        
        print("Spojenia v príklade:")
        for link in example_model.links:
            print(f"  - {link.source} -> {link.target} (typ: {link.link_type.name})")
        
        print("\nPravidlá v testovacom modeli:")
        bmw_models = ["BMW", "Series3", "Series5", "Series7", "X5", "X7"]
        for link in model.links:
            if link.link_type == LinkType.MUST and link.source in bmw_models:
                print(f"  - {link.source} MUST connect to {link.target}")
        
        is_valid, differences = is_valid_example(model, example_model, classification_tree)
        
        print(f"\nTest: {description}")
        print(f"Očakávaný výsledok: {expected_result}, Aktuálny výsledok: {is_valid}")
        
        if is_valid == expected_result:
            print("✅ TEST ÚSPEŠNÝ")
        else:
            print("❌ TEST ZLYHAL")
        
        if differences:
            print("Dôvody neplatnosti:")
            for diff in differences:
                print(f"  - {diff}")
        
        return is_valid == expected_result
    
    except Exception as e:
        print(f"CHYBA pri spracovaní príkladu: {e}")
        return False

def run_tests():
    """Spustí všetky testy porovnávania príkladov."""
    # Inicializácia klasifikačného stromu a modelu
    classification_tree = init_classification_tree()
    test_model = create_test_model()
    
    print("=== TESTOVANIE ALGORITMU POROVNÁVANIA PRÍKLADOV ===")
    
    # Test 1: X5 s benzínovým motorom a manuálnou prevodovkou (platný príklad)
    test1 = """
    Ι(c₁, X5) ∧ 
    Π(c₁, e₁) ∧ Ι(e₁, PetrolEngine) ∧ 
    Π(c₁, t₁) ∧ Ι(t₁, ManualTransmission) ∧ 
    Π(c₁, d₁) ∧ Ι(d₁, XDrive) ∧ 
    Π(e₁, t₁) ∧ 
    Α(c₁, color, blue) ∧ 
    Α(e₁, power, 250) ∧ 
    Α(e₁, cylinders, 6)
    """
    test_example(test1, test_model, classification_tree, True, "X5 s benzínovým motorom a manuálnou prevodovkou")
    
    # Test 2: X5 bez motora (neplatný príklad)
    test2 = """
    Ι(c₂, X5) ∧ 
    Π(c₂, t₂) ∧ Ι(t₂, ManualTransmission) ∧ 
    Π(c₂, d₂) ∧ Ι(d₂, XDrive) ∧ 
    Α(c₂, color, green)
    """
    test_example(test2, test_model, classification_tree, False, "X5 bez motora")
    
    # Test 3: X5 s RWD namiesto XDrive (neplatný príklad)
    test3 = """
    Ι(c₃, X5) ∧ 
    Π(c₃, e₃) ∧ Ι(e₃, PetrolEngine) ∧ 
    Π(c₃, t₃) ∧ Ι(t₃, ManualTransmission) ∧ 
    Π(c₃, d₃) ∧ Ι(d₃, RWD) ∧ 
    Π(e₃, t₃) ∧ 
    Α(c₃, color, silver) ∧ 
    Α(e₃, power, 245) ∧ 
    Α(e₃, cylinders, 6)
    """
    test_example(test3, test_model, classification_tree, False, "X5 s RWD namiesto XDrive")
    
    # Test 4: X7 s manuálnou prevodovkou (neplatný príklad)
    test4 = """
    Ι(c₄, X7) ∧ 
    Π(c₄, e₄) ∧ Ι(e₄, DieselEngine) ∧ 
    Π(c₄, t₄) ∧ Ι(t₄, ManualTransmission) ∧ 
    Π(c₄, d₄) ∧ Ι(d₄, XDrive) ∧ 
    Π(e₄, t₄) ∧ 
    Α(c₄, color, blue) ∧ 
    Α(e₄, power, 300) ∧ 
    Α(e₄, cylinders, 6)
    """
    test_example(test4, test_model, classification_tree, False, "X7 s manuálnou prevodovkou")
    
    # Test 5: Series7 s AWD (platný príklad)
    test5 = """
    Ι(c₅, Series7) ∧ 
    Π(c₅, e₅) ∧ Ι(e₅, PetrolEngine) ∧ 
    Π(c₅, t₅) ∧ Ι(t₅, AutomaticTransmission) ∧ 
    Π(c₅, d₅) ∧ Ι(d₅, AWD) ∧ 
    Π(e₅, t₅) ∧ 
    Α(c₅, color, black) ∧ 
    Α(e₅, power, 400) ∧ 
    Α(e₅, cylinders, 8)
    """
    test_example(test5, test_model, classification_tree, True, "Series7 s AWD")
    
    # Test 6: Series7 s RWD (neplatný príklad)
    test6 = """
    Ι(c₆, Series7) ∧ 
    Π(c₆, e₆) ∧ Ι(e₆, PetrolEngine) ∧ 
    Π(c₆, t₆) ∧ Ι(t₆, AutomaticTransmission) ∧ 
    Π(c₆, d₆) ∧ Ι(d₆, RWD) ∧ 
    Π(e₆, t₆) ∧ 
    Α(c₆, color, black) ∧ 
    Α(e₆, power, 350) ∧ 
    Α(e₆, cylinders, 6)
    """
    test_example(test6, test_model, classification_tree, False, "Series7 s RWD namiesto AWD")
    
    # Test 7: Motor neprepojený s prevodovkou (neplatný príklad)
    test7 = """
    Ι(c₇, X5) ∧ 
    Π(c₇, e₇) ∧ Ι(e₇, PetrolEngine) ∧ 
    Π(c₇, t₇) ∧ Ι(t₇, ManualTransmission) ∧ 
    Π(c₇, d₇) ∧ Ι(d₇, XDrive) ∧ 
    Α(c₇, color, blue) ∧ 
    Α(e₇, power, 250) ∧ 
    Α(e₇, cylinders, 6)
    """
    test_example(test7, test_model, classification_tree, False, "X5 - motor neprepojený s prevodovkou")
    
    # Test 8: Series5 s RWD (platný príklad)
    test8 = """
    Ι(c₈, Series5) ∧ 
    Π(c₈, e₈) ∧ Ι(e₈, PetrolEngine) ∧ 
    Π(c₈, t₈) ∧ Ι(t₈, AutomaticTransmission) ∧ 
    Π(c₈, d₈) ∧ Ι(d₈, RWD) ∧ 
    Π(e₈, t₈) ∧ 
    Α(c₈, color, red) ∧ 
    Α(e₈, power, 230) ∧ 
    Α(e₈, cylinders, 4)
    """
    test_example(test8, test_model, classification_tree, True, "Series5 s RWD")

if __name__ == "__main__":
    run_tests() 