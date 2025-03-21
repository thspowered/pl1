from backend.model import Model, ClassificationTree, Object, Link, LinkType
from backend.app import formula_to_model
from backend.learner import WinstonLearner
from backend.pl1_parser import parse_pl1_formula, parse_pl1_dataset
import re

def initialize_tree():
    tree = ClassificationTree()
    
    # Základní třídy
    tree.add_relationship("BMW", None)
    tree.add_relationship("Engine", None)
    tree.add_relationship("Transmission", None)
    tree.add_relationship("DriveSystem", None)
    tree.add_relationship("Component", None)
    
    # Typy BMW
    tree.add_relationship("X5", "BMW")
    tree.add_relationship("X7", "BMW")
    tree.add_relationship("Series5", "BMW")
    tree.add_relationship("Series7", "BMW")
    
    # Typy motorů
    tree.add_relationship("DieselEngine", "Engine")
    tree.add_relationship("PetrolEngine", "Engine")
    tree.add_relationship("HybridEngine", "Engine")
    
    # Engine je komponenta
    tree.add_relationship("Engine", "Component")
    
    # Typy převodovek
    tree.add_relationship("AutomaticTransmission", "Transmission")
    tree.add_relationship("ManualTransmission", "Transmission")
    
    # Transmission je komponenta
    tree.add_relationship("Transmission", "Component")
    
    # Typy pohonu
    tree.add_relationship("XDrive", "DriveSystem")
    tree.add_relationship("RWD", "DriveSystem")
    tree.add_relationship("AWD", "DriveSystem")
    
    # DriveSystem je komponenta
    tree.add_relationship("DriveSystem", "Component")
    
    return tree

def test_dataset():
    """Hlavní funkce pro testování datasetu."""
    tree = initialize_tree()
    
    print("=== KLASIFIKAČNÍ STROM ===")
    print("BMW")
    print("  |- X5")
    print("  |- X7")
    print("  |- Series5")
    print("  |- Series7")
    print("Engine")
    print("  |- DieselEngine")
    print("  |- PetrolEngine")
    print("  |- HybridEngine")
    print("Transmission")
    print("  |- AutomaticTransmission")
    print("  |- ManualTransmission")
    print("DriveSystem")
    print("  |- XDrive")
    print("  |- RWD")
    print("  |- AWD")
    print("Component")
    print("  |- Engine")
    print("  |- Transmission")
    print("  |- DriveSystem")
    
    try:
        # Načtení datasetu
        with open("data/optimized_dataset.pl1", 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Rozdělit dataset na příklady
        examples = []
        is_positive = True
        current_formula = ""
        example_count = 1
        
        for line in content.split('\n'):
            line = line.strip()
            
            if "# Pozitívny príklad:" in line:
                # Uložit předchozí příklad, pokud existuje
                if current_formula:
                    print(f"\n=== Parsování příkladu {example_count} (pozitivní: {is_positive}) ===")
                    print(f"Raw formula text: {current_formula}")
                    
                    # Kontrola přítomnosti a správného formátu unicode znaků
                    print(f"Přítomnost unicode znaků:")
                    print(f"  'Ι' (is-a): {current_formula.count('Ι')}")
                    print(f"  'Π' (has-part): {current_formula.count('Π')}")
                    print(f"  'Α' (attribute): {current_formula.count('Α')}")
                    print(f"  'Ν' (must-not): {current_formula.count('Ν')}")
                    
                    # Zkontrolujeme kódování Unicode znaků
                    special_chars = {
                        'Ι': '\\u0399',  # GREEK CAPITAL LETTER IOTA
                        'Π': '\\u03A0',  # GREEK CAPITAL LETTER PI
                        'Α': '\\u0391',  # GREEK CAPITAL LETTER ALPHA
                        'Ν': '\\u039D'   # GREEK CAPITAL LETTER NU
                    }
                    for char, unicode_code in special_chars.items():
                        print(f"  {char} encoded as {ord(char)} - expected {int(unicode_code[2:], 16)}")
                    
                    formula = parse_pl1_formula(current_formula)
                    print(f"Parsed predicates: {len(formula.predicates)}")
                    for pred in formula.predicates:
                        print(f"  - {pred.name}({', '.join(pred.arguments)})")
                    
                    model = formula_to_model(formula)
                    print(f"Model: {len(model.objects)} objects, {len(model.links)} links")
                    if model.objects:
                        print(f"  Objects: {', '.join([f'{obj.name}({obj.class_name})' for obj in model.objects])}")
                    if model.links:
                        print(f"  Links: {', '.join([f'{link.source}->{link.target}({link.link_type.value})' for link in model.links])}")
                    
                    examples.append((model, is_positive))
                    current_formula = ""
                    example_count += 1
                
                is_positive = True
            elif "# Negatívny príklad:" in line:
                # Uložit předchozí příklad, pokud existuje
                if current_formula:
                    print(f"\n=== Parsování příkladu {example_count} (pozitivní: {is_positive}) ===")
                    print(f"Raw formula text: {current_formula}")
                    
                    # Kontrola přítomnosti a správného formátu unicode znaků
                    print(f"Přítomnost unicode znaků:")
                    print(f"  'Ι' (is-a): {current_formula.count('Ι')}")
                    print(f"  'Π' (has-part): {current_formula.count('Π')}")
                    print(f"  'Α' (attribute): {current_formula.count('Α')}")
                    print(f"  'Ν' (must-not): {current_formula.count('Ν')}")
                    
                    # Zkontrolujeme kódování Unicode znaků
                    special_chars = {
                        'Ι': '\\u0399',  # GREEK CAPITAL LETTER IOTA
                        'Π': '\\u03A0',  # GREEK CAPITAL LETTER PI
                        'Α': '\\u0391',  # GREEK CAPITAL LETTER ALPHA
                        'Ν': '\\u039D'   # GREEK CAPITAL LETTER NU
                    }
                    for char, unicode_code in special_chars.items():
                        print(f"  {char} encoded as {ord(char)} - expected {int(unicode_code[2:], 16)}")
                    
                    formula = parse_pl1_formula(current_formula)
                    print(f"Parsed predicates: {len(formula.predicates)}")
                    for pred in formula.predicates:
                        print(f"  - {pred.name}({', '.join(pred.arguments)})")
                    
                    model = formula_to_model(formula)
                    print(f"Model: {len(model.objects)} objects, {len(model.links)} links")
                    if model.objects:
                        print(f"  Objects: {', '.join([f'{obj.name}({obj.class_name})' for obj in model.objects])}")
                    if model.links:
                        print(f"  Links: {', '.join([f'{link.source}->{link.target}({link.link_type.value})' for link in model.links])}")
                    
                    examples.append((model, is_positive))
                    current_formula = ""
                    example_count += 1
                
                is_positive = False
            elif not line.startswith('#') and line:
                # Přidat řádek do aktuální formule
                current_formula += line + " "
        
        # Přidat poslední příklad
        if current_formula:
            print(f"\n=== Parsování příkladu {example_count} (pozitivní: {is_positive}) ===")
            print(f"Raw formula text: {current_formula}")
            
            # Kontrola přítomnosti a správného formátu unicode znaků
            print(f"Přítomnost unicode znaků:")
            print(f"  'Ι' (is-a): {current_formula.count('Ι')}")
            print(f"  'Π' (has-part): {current_formula.count('Π')}")
            print(f"  'Α' (attribute): {current_formula.count('Α')}")
            print(f"  'Ν' (must-not): {current_formula.count('Ν')}")
            
            # Zkontrolujeme kódování Unicode znaků
            special_chars = {
                'Ι': '\\u0399',  # GREEK CAPITAL LETTER IOTA
                'Π': '\\u03A0',  # GREEK CAPITAL LETTER PI
                'Α': '\\u0391',  # GREEK CAPITAL LETTER ALPHA
                'Ν': '\\u039D'   # GREEK CAPITAL LETTER NU
            }
            for char, unicode_code in special_chars.items():
                print(f"  {char} encoded as {ord(char)} - expected {int(unicode_code[2:], 16)}")
            
            formula = parse_pl1_formula(current_formula)
            print(f"Parsed predicates: {len(formula.predicates)}")
            for pred in formula.predicates:
                print(f"  - {pred.name}({', '.join(pred.arguments)})")
            
            model = formula_to_model(formula)
            print(f"Model: {len(model.objects)} objects, {len(model.links)} links")
            if model.objects:
                print(f"  Objects: {', '.join([f'{obj.name}({obj.class_name})' for obj in model.objects])}")
            if model.links:
                print(f"  Links: {', '.join([f'{link.source}->{link.target}({link.link_type.value})' for link in model.links])}")
            
            examples.append((model, is_positive))
            
        print(f"\nNačteno {len(examples)} příkladů z datasetu.")
        
        # Rozdělíme příklady na páry (pozitivní + negativní)
        example_pairs = []
        for i in range(0, len(examples), 2):
            if i + 1 < len(examples):
                # Ověříme, že první je pozitivní a druhý negativní
                if examples[i][1] and not examples[i+1][1]:
                    example_pairs.append((examples[i][0], examples[i+1][0]))
                else:
                    print(f"VAROVÁNÍ: Pár příkladů {i//2 + 1} nemá správné pořadí (pozitivní, negativní)")
            else:
                print(f"VAROVÁNÍ: Poslední příklad nemá svůj protějšek")
                
        # Inicializovat učící algoritmus
        learner = WinstonLearner(tree)
        learner.debug_enabled = True
        
        # Začít s prázdným modelem
        print("\n=== ZAHÁJENÍ UČENÍ ===")
        model = Model(objects=[], links=[])
        
        # Postupně učit model na párech příkladů
        for i, (positive, near_miss) in enumerate(example_pairs):
            print(f"\n=== UČENÍ PÁRU {i+1} ===")
            print(f"Pozitivní příklad: {[obj.name for obj in positive.objects]}")
            print(f"Near-miss příklad: {[obj.name for obj in near_miss.objects]}")
            
            print("\nModel před aktualizací:")
            model_dict = model.to_dict()
            if model_dict["objects"]:
                print(f"  Objekty: {[obj['name'] for obj in model_dict['objects']]}")
            else:
                print("  Objekty: []")
                
            if model_dict["links"]:
                print(f"  Spojení: {[(link['source'], link['target'], link['link_type']) for link in model_dict['links']]}")
            else:
                print("  Spojení: []")
                
            # Aktualizovat model
            model = learner.update_model(model, positive, near_miss)
            
            print("\nModel po aktualizaci:")
            model_dict = model.to_dict()
            if model_dict["objects"]:
                print(f"  Objekty: {[obj['name'] for obj in model_dict['objects']]}")
            else:
                print("  Objekty: []")
                
            if model_dict["links"]:
                print(f"  Spojení: {[(link['source'], link['target'], link['link_type']) for link in model_dict['links']]}")
            else:
                print("  Spojení: []")
                
            print(f"Aplikované heuristiky: {learner.applied_heuristics}")
            
            # Zobrazit hypotézu po tomto kroku
            print("\nHypotéza po tomto kroku:")
            hypothesis = model.to_formula()
            print(hypothesis)
        
        print("\n=== VÝSLEDNÝ MODEL ===")
        model_dict = model.to_dict()
        print("Objekty:")
        for obj in model_dict["objects"]:
            print(f"  - {obj['name']} (class: {obj['class_name']})")
            
        print("\nSpojení:")
        for link in model_dict["links"]:
            print(f"  - {link['source']} -> {link['target']} (type: {link['link_type']})")
        
        print("\n=== VÝSLEDNÁ HYPOTÉZA ===")
        hypothesis = model.to_formula()
        print(hypothesis)
        
    except Exception as e:
        import traceback
        print(f"Chyba při zpracování datasetu: {str(e)}")
        print(traceback.format_exc())

if __name__ == "__main__":
    test_dataset()