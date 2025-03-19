#!/usr/bin/env python
"""
Testovací skript pre generalizáciu na úrovni tried vo Winston Learner.
Tento test sa zameriava na vytvorenie generických pravidiel namiesto konkrétnych inštancií.
"""

from backend.model import Model, Object, Link, LinkType, ClassificationTree
from backend.learner import WinstonLearner
from backend.pl1_parser import parse_pl1_formula

def create_classification_tree():
    """Vytvorí hierarchiu tried pre BMW a komponenty."""
    tree = ClassificationTree()
    
    # Základná hierarchia pre BMW
    tree.add_relationship("Vehicle", None)  # Root
    tree.add_relationship("BMW", "Vehicle")
    tree.add_relationship("Series5", "BMW")
    tree.add_relationship("Series7", "BMW")
    tree.add_relationship("X5", "BMW")
    tree.add_relationship("X7", "BMW")
    
    # Komponenty
    tree.add_relationship("Component", None)  # Root
    tree.add_relationship("Engine", "Component")
    tree.add_relationship("DieselEngine", "Engine")
    tree.add_relationship("PetrolEngine", "Engine")
    tree.add_relationship("HybridEngine", "Engine")
    
    tree.add_relationship("Transmission", "Component")
    tree.add_relationship("AutomaticTransmission", "Transmission")
    tree.add_relationship("ManualTransmission", "Transmission")
    
    tree.add_relationship("DriveSystem", "Component")
    tree.add_relationship("RWD", "DriveSystem")
    tree.add_relationship("AWD", "DriveSystem")
    tree.add_relationship("XDrive", "AWD")
    
    print("Klasifikačný strom pre testovanie generalizácie:")
    for child, parent in tree.parent_map.items():
        print(f"  {child} -> {parent or 'ROOT'}")
    
    return tree

def create_model_from_string(formula_text):
    """Vytvorí model z PL1 formuly."""
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

def print_model(model, title="Model"):
    """Vypíše model v ľudsky čitateľnej forme."""
    print(f"\n{title}:")
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

def get_generic_rules(model):
    """Vypíše všetky generické pravidlá (spojenia medzi triedami) z modelu."""
    generic_rules = []
    
    for link in model.links:
        # Ak source alebo target nie je názov objektu, je to generické pravidlo
        if not any(obj.name == link.source for obj in model.objects) or \
           not any(obj.name == link.target for obj in model.objects):
            rule = {
                "source": link.source,
                "target": link.target,
                "type": link.link_type
            }
            generic_rules.append(rule)
    
    return generic_rules

def test_step(learner, current_model, positive, negative, step_name="Test"):
    """Vykoná jeden krok testovania a vráti aktualizovaný model."""
    print(f"\n=== {step_name} ===")
    
    print_model(positive, "Pozitívny príklad")
    print_model(negative, "Negatívny príklad (near-miss)")
    print_model(current_model, "Aktuálny model pred aktualizáciou")
    
    # Aplikuj update_model
    updated_model = learner.update_model(current_model, positive, negative)
    
    print(f"\nAplikovaná heuristika: {learner.last_applied_heuristic}")
    print_model(updated_model, "Aktualizovaný model")
    
    # Skontroluj generické pravidlá
    generic_rules = get_generic_rules(updated_model)
    if generic_rules:
        print("\nGenerické pravidlá:")
        for rule in generic_rules:
            link_type_str = {
                LinkType.REGULAR: "REGULAR",
                LinkType.MUST: "MUST",
                LinkType.MUST_NOT: "MUST_NOT"
            }.get(rule["type"], "UNKNOWN")
            print(f"  {rule['source']} -> {rule['target']} ({link_type_str})")
    else:
        print("\nV modeli nie sú žiadne generické pravidlá!")
    
    return updated_model

def main():
    # Vytvorenie klasifikačného stromu
    tree = create_classification_tree()
    
    # Inicializácia učiaceho algoritmu
    learner = WinstonLearner(tree)
    learner.debug_enabled = True
    
    # Inicializačný príklad - X5 s xDrive pohonom
    initial_model = create_model_from_string("""
        Ι(car1, X5) ∧
        Ι(drive1, XDrive) ∧
        Π(car1, drive1)
    """)
    
    # TEST 1: X5 musí mať XDrive 
    pos1 = create_model_from_string("""
        Ι(car1, X5) ∧
        Ι(drive1, XDrive) ∧
        Π(car1, drive1)
    """)
    
    neg1 = create_model_from_string("""
        Ι(car1, X5) ∧
        Ι(drive1, RWD) ∧
        Π(car1, drive1)
    """)
    
    model = test_step(learner, initial_model, pos1, neg1, "TEST 1: X5 musí mať XDrive")
    
    # TEST 2: X7 musí mať XDrive (mal by generalizovať na BMW X...)
    pos2 = create_model_from_string("""
        Ι(car1, X7) ∧
        Ι(drive1, XDrive) ∧
        Π(car1, drive1)
    """)
    
    neg2 = create_model_from_string("""
        Ι(car1, X7) ∧
        Ι(drive1, RWD) ∧
        Π(car1, drive1)
    """)
    
    model = test_step(learner, model, pos2, neg2, "TEST 2: X7 musí mať XDrive")
    
    # TEST 3: BMW Series7 musí mať automatickú prevodovku
    pos3 = create_model_from_string("""
        Ι(car1, Series7) ∧
        Ι(trans1, AutomaticTransmission) ∧
        Π(car1, trans1)
    """)
    
    neg3 = create_model_from_string("""
        Ι(car1, Series7) ∧
        Ι(trans1, ManualTransmission) ∧
        Π(car1, trans1)
    """)
    
    model = test_step(learner, model, pos3, neg3, "TEST 3: Series7 musí mať automatickú prevodovku")
    
    # Skontrolujeme, či model obsahuje generické pravidlá
    final_generic_rules = get_generic_rules(model)
    
    print("\n=== ZÁVEREČNÉ VYHODNOTENIE ===")
    print(f"Počet generických pravidiel: {len(final_generic_rules)}")
    
    # Čo by sme mali vidieť:
    # 1. X5 -> XDrive MUST (requirement)
    # 2. X7 -> XDrive MUST (requirement)
    # 3. BMW -> XDrive MUST (generalizácia typov X)
    # 4. Series7 -> AutomaticTransmission MUST (requirement)
    
    expected_rules = [
        ("X5", "XDrive", LinkType.MUST),
        ("X7", "XDrive", LinkType.MUST),
        ("Series7", "AutomaticTransmission", LinkType.MUST)
    ]
    
    for source, target, link_type in expected_rules:
        found = False
        for rule in final_generic_rules:
            if rule["source"] == source and rule["target"] == target and rule["type"] == link_type:
                found = True
                break
        
        if found:
            print(f"✅ Pravidlo {source} -> {target} ({link_type.name}) je v modeli.")
        else:
            print(f"❌ Pravidlo {source} -> {target} ({link_type.name}) CHÝBA v modeli!")

    # Skúsime pridať explicitné generické pravidlo a overiť, či sa správne aplikuje drop-link
    print("\n=== TEST EXPLICITNÉHO GENERICKÉHO PRAVIDLA ===")
    
    # Model s explicitným generickým pravidlom
    generic_model = create_model_from_string("""
        Ι(car1, X5) ∧
        Ι(drive1, XDrive) ∧
        Π(car1, drive1) ∧
        Μ(X5, XDrive)  # Explicitné generické pravidlo
    """)
    
    print_model(generic_model, "Model s explicitným generickým pravidlom")
    
    # Dva príklady, kde oba majú X5 s XDrive - pravidlo by malo zostať
    pos_generic = create_model_from_string("""
        Ι(car1, X5) ∧
        Ι(drive1, XDrive) ∧
        Π(car1, drive1)
    """)
    
    neg_generic = create_model_from_string("""
        Ι(car2, X5) ∧
        Ι(drive2, XDrive) ∧
        Π(car2, drive2)
    """)
    
    # Aplikácia drop-link heuristiky
    drop_link_result = learner._apply_drop_link(generic_model, pos_generic, neg_generic)
    
    if learner.last_applied_heuristic == "drop_link":
        print("\n✅ Drop-link heuristika bola aplikovaná.")
    else:
        print("\n❌ Drop-link heuristika NEBOLA aplikovaná!")
    
    print_model(drop_link_result, "Výsledok po drop-link")
    
    # Kontrola, či generické pravidlo zostalo
    generic_rules = get_generic_rules(drop_link_result)
    found_rule = False
    for rule in generic_rules:
        if rule["source"] == "X5" and rule["target"] == "XDrive" and rule["type"] == LinkType.MUST:
            found_rule = True
            break
    
    if found_rule:
        print("✅ Generické pravidlo X5 -> XDrive (MUST) zostalo zachované.")
    else:
        print("❌ Generické pravidlo X5 -> XDrive (MUST) bolo nesprávne odstránené!")

if __name__ == "__main__":
    main() 