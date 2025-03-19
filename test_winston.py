#!/usr/bin/env python
"""
Testovací skript pre Winston Learner - testuje jednotlivé heuristiky na jednoduchom datasete.
"""

from backend.model import Model, Object, Link, LinkType, ClassificationTree
from backend.learner import WinstonLearner
from backend.pl1_parser import parse_pl1_formula

def create_classification_tree():
    """Vytvorí jednoduchý klasifikačný strom pre testovanie."""
    tree = ClassificationTree()
    
    # Základná hierarchia pre testovanie
    tree.add_relationship("Vehicle", None)  # Root
    tree.add_relationship("BMW", "Vehicle")
    tree.add_relationship("Series5", "BMW")
    tree.add_relationship("Series7", "BMW")
    tree.add_relationship("X5", "BMW")
    
    tree.add_relationship("Component", None)  # Root
    tree.add_relationship("Engine", "Component")
    tree.add_relationship("DieselEngine", "Engine")
    tree.add_relationship("PetrolEngine", "Engine")
    
    tree.add_relationship("Transmission", "Component")
    tree.add_relationship("AutomaticTransmission", "Transmission")
    tree.add_relationship("ManualTransmission", "Transmission")
    
    tree.add_relationship("DriveSystem", "Component")
    tree.add_relationship("RWD", "DriveSystem")
    tree.add_relationship("XDrive", "DriveSystem")
    
    # Výpis hierarchie pre debug
    print("Klasifikačný strom:")
    for child, parent in tree.parent_map.items():
        print(f"  {child} -> {parent or 'ROOT'}")
    
    return tree

def create_simple_model(formula_text):
    """Vytvorí jednoduchý model z formuly."""
    formula = parse_pl1_formula(formula_text)
    
    objects = []
    links = []
    object_classes = {}
    
    # Extrahuj triedy objektov z predikátov Ι
    for predicate in formula.predicates:
        if predicate.name == "Ι" and len(predicate.arguments) == 2:
            obj_name = predicate.arguments[0]
            class_name = predicate.arguments[1]
            object_classes[obj_name] = class_name
    
    # Vytvor objekty
    for obj_name, class_name in object_classes.items():
        objects.append(Object(name=obj_name, class_name=class_name))
    
    # Vytvor spojenia z predikátov Π, Μ a Ν
    for predicate in formula.predicates:
        if predicate.name == "Π" and len(predicate.arguments) == 2:
            source = predicate.arguments[0]
            target = predicate.arguments[1]
            links.append(Link(source=source, target=target, link_type=LinkType.REGULAR))
        elif predicate.name == "Μ" and len(predicate.arguments) == 2:
            source = predicate.arguments[0]
            target = predicate.arguments[1]
            links.append(Link(source=source, target=target, link_type=LinkType.MUST))
        elif predicate.name == "Ν" and len(predicate.arguments) == 2:
            source = predicate.arguments[0]
            target = predicate.arguments[1]
            links.append(Link(source=source, target=target, link_type=LinkType.MUST_NOT))
    
    return Model(objects=objects, links=links)

def pretty_print_model(model):
    """Vypíše model v ľudsky čitateľnej forme."""
    print("Model:")
    print(f"  Objekty ({len(model.objects)}):")
    for obj in model.objects:
        print(f"    {obj.name}: {obj.class_name}")
    
    print(f"  Spojenia ({len(model.links)}):")
    for link in model.links:
        link_type_str = {
            LinkType.REGULAR: "REGULAR",
            LinkType.MUST: "MUST",
            LinkType.MUST_NOT: "MUST_NOT"
        }.get(link.link_type, "UNKNOWN")
        print(f"    {link.source} -> {link.target} ({link_type_str})")

def test_heuristic(heuristic_name, learner, model, good, near_miss):
    """Testuje konkrétnu heuristiku a vracia výsledok."""
    print(f"\nTestujem heuristiku {heuristic_name}:")
    
    # Získanie metódy podľa názvu
    heuristic_method = getattr(learner, f"_apply_{heuristic_name}")
    
    # Aplikácia heuristiky
    result_model = heuristic_method(model.copy(), good, near_miss)
    
    # Kontrola, či bola heuristika aplikovaná
    if learner.last_applied_heuristic == heuristic_name:
        print(f"  HEURISTIKA APLIKOVANÁ")
        learner.last_applied_heuristic = None
        return True, result_model
    else:
        print(f"  Heuristika nebola aplikovaná")
        return False, model

def main():
    # 1. Vytvorenie klasifikačného stromu
    tree = create_classification_tree()
    
    # 2. Inicializácia učiaceho algoritmu
    learner = WinstonLearner(tree)
    learner.debug_enabled = True

    # 3. Testovanie s jednoduchým datasetom
    print("\n=== TEST 1: Require-link ===")
    
    # Pozitívny príklad: BMW Series5 s motorom, ktorý je diesel
    good_example = create_simple_model("""
        Ι(c₁, Series5) ∧ 
        Ι(e₁, DieselEngine) ∧
        Π(c₁, e₁)
    """)
    
    # Near-miss príklad: BMW Series5 bez motora
    near_miss = create_simple_model("""
        Ι(c₁, Series5)
    """)
    
    # Aktuálny model
    current_model = create_simple_model("Ι(c₁, Series5)")
    
    print("--- Pozitívny príklad:")
    pretty_print_model(good_example)
    
    print("\n--- Near-miss príklad:")
    pretty_print_model(near_miss)
    
    print("\n--- Aktuálny model pred aplikáciou heuristík:")
    pretty_print_model(current_model)
    
    # Testovanie require-link
    applied, result = test_heuristic("require_link", learner, current_model, good_example, near_miss)
    if applied:
        print("\n--- Výsledný model po require-link:")
        pretty_print_model(result)
        current_model = result
    
    # 4. Test climb-tree s triedami
    print("\n=== TEST 2: Climb-tree ===")
    
    # Pozitívny príklad: X5
    good_example2 = create_simple_model("""
        Ι(c₁, X5) ∧ 
        Ι(e₁, DieselEngine) ∧
        Π(c₁, e₁)
    """)
    
    # Near-miss príklad: Series7
    near_miss2 = create_simple_model("""
        Ι(c₁, Series7) ∧
        Ι(e₁, DieselEngine) ∧ 
        Π(c₁, e₁)
    """)
    
    print("--- Pozitívny príklad (X5):")
    pretty_print_model(good_example2)
    
    print("\n--- Near-miss príklad (Series7):")
    pretty_print_model(near_miss2)
    
    # Testovanie climb-tree
    applied, result = test_heuristic("climb_tree", learner, current_model, good_example2, near_miss2)
    if applied:
        print("\n--- Výsledný model po climb-tree:")
        pretty_print_model(result)
        current_model = result
    
    # 5. Test drop-link
    print("\n=== TEST 3: Drop-link ===")
    
    # Pridajme spojenie, ktoré je v oboch príkladoch a malo by byť odstránené
    drop_test_model = current_model.copy()
    drop_test_model.add_link(Link("c₁", "e₁", LinkType.MUST))
    
    print("--- Aktuálny model s MUST spojením:")
    pretty_print_model(drop_test_model)
    
    # Oba príklady majú rovnaké spojenie c₁->e₁
    applied, result = test_heuristic("drop_link", learner, drop_test_model, good_example2, near_miss2)
    if applied:
        print("\n--- Výsledný model po drop-link:")
        pretty_print_model(result)
        current_model = result
    
    # 6. Test forbid-link
    print("\n=== TEST 4: Forbid-link ===")
    
    # Pozitívny príklad: X5 s dieselovým motorom
    good_example3 = create_simple_model("""
        Ι(c₁, X5) ∧ 
        Ι(e₁, DieselEngine) ∧
        Π(c₁, e₁)
    """)
    
    # Near-miss príklad: X5 s benzínovým motorom
    near_miss3 = create_simple_model("""
        Ι(c₁, X5) ∧
        Ι(e₁, PetrolEngine) ∧ 
        Π(c₁, e₁) ∧
        Π(c₁, t₁) ∧  # Extra spojenie, ktoré nie je v pozitívnom príklade
        Ι(t₁, ManualTransmission)
    """)
    
    print("--- Pozitívny príklad (X5 diesel):")
    pretty_print_model(good_example3)
    
    print("\n--- Near-miss príklad (X5 petrol + manuál):")
    pretty_print_model(near_miss3)
    
    forbid_test_model = current_model.copy()
    
    # Testovanie forbid-link
    applied, result = test_heuristic("forbid_link", learner, forbid_test_model, good_example3, near_miss3)
    if applied:
        print("\n--- Výsledný model po forbid-link:")
        pretty_print_model(result)
    
    # 7. Test celého update_model
    print("\n=== TEST 5: Kompletný update_model ===")
    
    # Použijeme rovnaké príklady ako pre forbid-link
    print("--- Pozitívny príklad:")
    pretty_print_model(good_example3)
    
    print("\n--- Near-miss príklad:")
    pretty_print_model(near_miss3)
    
    print("\n--- Aktuálny model pred update_model:")
    pretty_print_model(current_model)
    
    updated = learner.update_model(current_model, good_example3, near_miss3)
    
    print(f"\n--- Výsledný model po update_model (aplikovaná heuristika: {learner.last_applied_heuristic}):")
    pretty_print_model(updated)
    
    print("\n=== HEURISTIKA NA ÚROVNI TRIED ===")
    # Vytvorenie všeobecného pravidla: Series5 musí mať dieselový motor
    class_model = create_simple_model("""
        Ι(c₁, Series5) ∧ 
        Ι(e₁, DieselEngine) ∧
        Μ(Series5, DieselEngine)
    """)
    
    # Pozitívny príklad: Series5 s dieselovým motorom
    class_good = create_simple_model("""
        Ι(c₁, Series5) ∧ 
        Ι(e₁, DieselEngine) ∧
        Π(c₁, e₁)
    """)
    
    # Near-miss príklad: Series5 s benzínovým motorom
    class_near_miss = create_simple_model("""
        Ι(c₁, Series5) ∧
        Ι(e₁, PetrolEngine) ∧ 
        Π(c₁, e₁)
    """)
    
    print("\n--- Model s pravidlom na úrovni triedy:")
    pretty_print_model(class_model)
    
    print("\n--- Update modelu s pravidlom na úrovni triedy:")
    updated_class = learner.update_model(class_model, class_good, class_near_miss)
    print(f"Aplikovaná heuristika: {learner.last_applied_heuristic}")
    pretty_print_model(updated_class)

if __name__ == "__main__":
    main() 