from typing import List, Dict, Set, Tuple, Optional, Any
from model import Model, Link, LinkType, Object, ClassificationTree

def build_classification_tree_from_examples(examples: List[Model]) -> ClassificationTree:
    """
    Vytvorí klasifikačný strom na základe príkladov.
    
    Args:
        examples: Zoznam modelov predstavujúcich príklady
        
    Returns:
        Klasifikačný strom reprezentujúci hierarchiu tried
    """
    tree = ClassificationTree()
    
    # 1. Získame všetky triedy z príkladov
    all_classes = set()
    for example in examples:
        for obj in example.objects:
            all_classes.add(obj.class_name)
    
    # 2. Identifikujeme vzťahy tried na základe MUST_BE_A spojení
    relationships = {}
    
    for example in examples:
        for link in example.links:
            if link.link_type == LinkType.MUST_BE_A:
                # Nájdeme objekt a jeho triedu
                obj = next((o for o in example.objects if o.name == link.source), None)
                if obj and link.target in all_classes:
                    # Zaznamenáme vzťah trieda -> nadtrieda
                    relationships[obj.class_name] = link.target
    
    # 3. Pridáme vzťahy do klasifikačného stromu
    for child, parent in relationships.items():
        tree.add_relationship(child, parent)
    
    # 4. Identifikujeme koreňové triedy, ktoré nemajú rodiča
    for cls in all_classes:
        if cls not in relationships:
            # Pridáme koreňovú triedu
            tree.add_relationship(cls, None)
    
    return tree

def identify_main_objects_from_examples(examples: List[Model]) -> Dict[str, int]:
    """
    Identifikuje hlavné typy objektov z príkladov na základe počtu výskytov.
    
    Args:
        examples: Zoznam modelov predstavujúcich príklady
        
    Returns:
        Slovník mapujúci názvy tried na počet ich výskytov
    """
    class_count = {}
    
    for example in examples:
        # Počítame výskyty každej triedy
        for obj in example.objects:
            class_name = obj.class_name
            if class_name not in class_count:
                class_count[class_name] = 0
            class_count[class_name] += 1
    
    return class_count

def identify_component_relations(examples: List[Model]) -> Dict[str, Set[str]]:
    """
    Identifikuje vzťahy medzi hlavnými objektami a ich komponentami.
    
    Args:
        examples: Zoznam modelov predstavujúcich príklady
        
    Returns:
        Slovník mapujúci triedy hlavných objektov na množiny tried komponentov
    """
    component_relations = {}
    
    for example in examples:
        # Namiesto volania metódy identify_main_objects, ktorá neexistuje,
        # použijeme všetky objekty ako potenciálne hlavné objekty
        for obj in example.objects:
            if obj.class_name not in component_relations:
                component_relations[obj.class_name] = set()
            
            # Identifikujeme komponenty pripojené k objektu
            for link in example.links:
                if link.source == obj.name:
                    target_obj = next((o for o in example.objects if o.name == link.target), None)
                    if target_obj:
                        component_relations[obj.class_name].add(target_obj.class_name)
    
    return component_relations

def is_example_valid(model: Model, example: Model, classification_tree: ClassificationTree) -> Tuple[bool, List[str]]:
    """
    Kontroluje, či príklad spĺňa všetky pravidlá modelu.
    
    Args:
        model: Model obsahujúci pravidlá
        example: Príklad, ktorý sa má overiť
        classification_tree: Klasifikačný strom pre určenie vzťahov medzi triedami
        
    Returns:
        Dvojica (is_valid, reasons), kde is_valid je True, ak príklad spĺňa všetky
        pravidlá, a reasons je zoznam dôvodov, prečo príklad nie je platný (prázdny
        ak je príklad platný)
    """
    is_valid = True
    reasons = []
    
    # 1. Kontrola MUST vzťahov
    for link in model.links:
        if link.link_type == LinkType.MUST:
            source_class = link.source
            target_class = link.target
            
            # Nájdeme objekty v príklade s rovnakou triedou ako source_class
            source_objects = [obj for obj in example.objects if obj.class_name == source_class]
            
            # Pre každý taký objekt kontrolujeme, či má spojenie na komponent typu target_class
            for source_obj in source_objects:
                has_required_component = False
                
                for example_link in example.links:
                    if example_link.source == source_obj.name:
                        # Nájdeme cieľový objekt
                        target_obj = next((obj for obj in example.objects if obj.name == example_link.target), None)
                        # Kontrolujeme, či je trieda cieľového objektu target_class alebo jej podtrieda
                        if target_obj and (target_obj.class_name == target_class or 
                                          classification_tree.is_subclass(target_obj.class_name, target_class)):
                            has_required_component = True
                            break
                
                if not has_required_component:
                    is_valid = False
                    reasons.append(f"Objekt {source_obj.name} triedy {source_class} nemá požadovanú komponentu triedy {target_class}")
    
    # 2. Kontrola MUST_NOT vzťahov
    for link in model.links:
        if link.link_type == LinkType.MUST_NOT:
            source_class = link.source
            target_class = link.target
            
            # Nájdeme objekty v príklade s rovnakou triedou ako source_class
            source_objects = [obj for obj in example.objects if obj.class_name == source_class]
            
            # Pre každý taký objekt kontrolujeme, či nemá spojenie na komponent typu target_class
            for source_obj in source_objects:
                for example_link in example.links:
                    if example_link.source == source_obj.name:
                        # Nájdeme cieľový objekt
                        target_obj = next((obj for obj in example.objects if obj.name == example_link.target), None)
                        # Kontrolujeme, či je trieda cieľového objektu target_class alebo jej podtrieda
                        if target_obj and (target_obj.class_name == target_class or 
                                          classification_tree.is_subclass(target_obj.class_name, target_class)):
                            is_valid = False
                            reasons.append(f"Objekt {source_obj.name} triedy {source_class} má zakázanú komponentu triedy {target_class}")
    
    # 3. Kontrola atribútov
    for model_obj in model.objects:
        if not model_obj.attributes:
            continue
        
        # Nájdeme zodpovedajúce objekty v príklade
        for example_obj in example.objects:
            if example_obj.class_name == model_obj.class_name:
                # Kontrola atribútov
                for attr_name, model_value in model_obj.attributes.items():
                    if example_obj.attributes and attr_name in example_obj.attributes:
                        example_value = example_obj.attributes[attr_name]
                        
                        # Kontrola intervalu
                        if isinstance(model_value, tuple) and len(model_value) == 2:
                            min_val, max_val = model_value
                            if isinstance(example_value, (int, float)) and (example_value < min_val or example_value > max_val):
                                is_valid = False
                                reasons.append(f"Hodnota atribútu {attr_name} objektu {example_obj.name} ({example_value}) nie je v povolenom intervale [{min_val}, {max_val}]")
                        
                        # Kontrola množiny hodnôt
                        elif isinstance(model_value, set):
                            if example_value not in model_value:
                                is_valid = False
                                reasons.append(f"Hodnota atribútu {attr_name} objektu {example_obj.name} ({example_value}) nie je v povolenej množine {model_value}")
    
    return is_valid, reasons

def identify_concept_from_examples(positive_examples: List[Model], negative_examples: List[Model]) -> Model:
    """
    Identifikuje koncept na základe pozitívnych a negatívnych príkladov.
    
    Táto funkcia používa algoritmus inkrementálneho konceptuálneho učenia
    pre vytvorenie modelu, ktorý vyhovuje všetkým pozitívnym príkladom
    a nevyhovuje žiadnemu negatívnemu príkladu.
    
    Args:
        positive_examples: Zoznam pozitívnych príkladov
        negative_examples: Zoznam negatívnych príkladov
        
    Returns:
        Model reprezentujúci naučený koncept
    """
    from learner import WinstonLearner
    
    # 1. Vytvoríme klasifikačný strom z príkladov
    classification_tree = build_classification_tree_from_examples(positive_examples + negative_examples)
    
    # 2. Vytvoríme učiaci algoritmus
    learner = WinstonLearner(classification_tree)
    
    # 3. Inicializujeme model z prvého pozitívneho príkladu
    if not positive_examples:
        return Model()
    
    model = positive_examples[0].copy()
    print(f"Inicializovaný model z prvého pozitívneho príkladu")
    
    # 4. Pripravíme si páry pozitívnych a near-miss príkladov
    learning_pairs = []
    
    # Najprv skúsime nájsť near-miss páry (pozitívny príklad + blízky negatívny príklad)
    for positive in positive_examples[1:]:
        # Hľadáme najvhodnejší near-miss pre tento pozitívny príklad
        best_near_miss = None
        closest_difference = float('inf')
        
        for negative in negative_examples:
            # Kontrola, či je negatívny príklad blízky (počet rozdielov)
            if is_single_difference(positive, negative):
                # Je to near-miss s jedinou odlišnosťou
                learning_pairs.append((positive, negative))
                best_near_miss = negative
                break
            else:
                # Počítame rozdiel medzi príkladmi (nájdeme najmenší rozdiel)
                difference_count = count_differences(positive, negative)
                if difference_count < closest_difference:
                    closest_difference = difference_count
                    best_near_miss = negative
        
        # Ak sme nenašli near-miss s jedinou odlišnosťou, ale máme najlepšieho kandidáta
        if best_near_miss and not any(p[0] == positive for p in learning_pairs):
            learning_pairs.append((positive, best_near_miss))
    
    # Pre pozitívne príklady, ktoré nemajú near-miss
    for positive in positive_examples[1:]:
        if not any(p[0] == positive for p in learning_pairs):
            learning_pairs.append((positive, None))
    
    # 5. Postupne aplikujeme páry príkladov na model
    for i, (positive, near_miss) in enumerate(learning_pairs):
        print(f"Aplikujem pár {i+1}/{len(learning_pairs)}: pozitívny príklad + {'near-miss' if near_miss else 'bez near-miss'}")
        
        # Aktualizujeme model
        model = learner.update_model(model, positive, near_miss)
    
    # 6. Ak sme nespracovali všetky pozitívne príklady, pridáme aj tie zostávajúce
    unprocessed_positives = [p for p in positive_examples[1:] if not any(pair[0] == p for pair in learning_pairs)]
    for positive in unprocessed_positives:
        print(f"Spracovávam dodatočný pozitívny príklad bez near-miss")
        model = learner.update_model(model, positive)
    
    print(f"Dokončené učenie konceptu z {len(positive_examples)} pozitívnych a {len(negative_examples)} negatívnych príkladov")
    return model

def count_differences(model_a: Model, model_b: Model) -> int:
    """
    Počíta počet rozdielov medzi dvoma modelmi.
    
    Args:
        model_a: Prvý model
        model_b: Druhý model
        
    Returns:
        Počet rozdielov medzi modelmi
    """
    differences = 0
    
    # 1. Porovnáme objekty
    objects_a = {obj.name: obj for obj in model_a.objects}
    objects_b = {obj.name: obj for obj in model_b.objects}
    
    # Chýbajúce alebo dodatočné objekty
    only_in_a = set(objects_a.keys()) - set(objects_b.keys())
    only_in_b = set(objects_b.keys()) - set(objects_a.keys())
    
    differences += len(only_in_a) + len(only_in_b)
    
    # Rozdielne triedy objektov
    for name in set(objects_a.keys()) & set(objects_b.keys()):
        if objects_a[name].class_name != objects_b[name].class_name:
            differences += 1
    
    # 2. Porovnáme spojenia
    links_a = {(link.source, link.target, link.link_type) for link in model_a.links}
    links_b = {(link.source, link.target, link.link_type) for link in model_b.links}
    
    differences += len(links_a.symmetric_difference(links_b))
    
    # 3. Porovnáme atribúty
    for name in set(objects_a.keys()) & set(objects_b.keys()):
        obj_a = objects_a[name]
        obj_b = objects_b[name]
        
        # Ak oba objekty majú atribúty
        if obj_a.attributes and obj_b.attributes:
            # Rozdielne kľúče atribútov
            attrs_a = set(obj_a.attributes.keys())
            attrs_b = set(obj_b.attributes.keys())
            
            differences += len(attrs_a.symmetric_difference(attrs_b))
            
            # Rozdielne hodnoty atribútov
            for attr in attrs_a & attrs_b:
                if obj_a.attributes[attr] != obj_b.attributes[attr]:
                    differences += 1
        # Ak len jeden objekt má atribúty
        elif bool(obj_a.attributes) != bool(obj_b.attributes):
            # Počítame každý chýbajúci atribút ako rozdiel
            if obj_a.attributes:
                differences += len(obj_a.attributes)
            else:
                differences += len(obj_b.attributes)
    
    return differences

def is_single_difference(model_a: Model, model_b: Model) -> bool:
    """
    Kontroluje, či dva modely majú iba jedinú odlišnosť.
    
    Args:
        model_a: Prvý model
        model_b: Druhý model
        
    Returns:
        True, ak modely majú iba jedinú odlišnosť, inak False
    """
    differences = 0
    
    # 1. Porovnáme objekty
    if len(model_a.objects) != len(model_b.objects):
        # Rôzny počet objektov - viac ako jedna odlišnosť
        return False
    
    # 2. Porovnáme triedy objektov
    objects_a = {obj.name: obj for obj in model_a.objects}
    objects_b = {obj.name: obj for obj in model_b.objects}
    
    for name, obj_a in objects_a.items():
        if name not in objects_b:
            # Chýbajúci objekt - jedna odlišnosť
            differences += 1
            if differences > 1:
                return False
        elif obj_a.class_name != objects_b[name].class_name:
            # Rôzna trieda objektu - jedna odlišnosť
            differences += 1
            if differences > 1:
                return False
    
    # 3. Porovnáme spojenia
    links_a = {(link.source, link.target, link.link_type) for link in model_a.links}
    links_b = {(link.source, link.target, link.link_type) for link in model_b.links}
    
    link_diff = len(links_a.symmetric_difference(links_b))
    differences += link_diff
    if differences > 1:
        return False
    
    # 4. Porovnáme atribúty
    for name, obj_a in objects_a.items():
        if name in objects_b:
            obj_b = objects_b[name]
            
            # Ak oba objekty majú atribúty
            if obj_a.attributes and obj_b.attributes:
                # Nájdeme rozdielne atribúty
                attrs_a = set(obj_a.attributes.keys())
                attrs_b = set(obj_b.attributes.keys())
                
                # Rozdielne kľúče
                attr_keys_diff = len(attrs_a.symmetric_difference(attrs_b))
                differences += attr_keys_diff
                if differences > 1:
                    return False
                
                # Rovnaké kľúče, ale rozdielne hodnoty
                for attr in attrs_a.intersection(attrs_b):
                    if obj_a.attributes[attr] != obj_b.attributes[attr]:
                        differences += 1
                        if differences > 1:
                            return False
            # Iba jeden objekt má atribúty
            elif bool(obj_a.attributes) != bool(obj_b.attributes):
                differences += 1
                if differences > 1:
                    return False
    
    return differences == 1 