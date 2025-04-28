from backend.model import Model, Link, LinkType, ClassificationTree, Object
from typing import List, Dict, Set, Tuple, Optional, Any
import traceback
from datetime import datetime
import time
import copy

class WinstonLearner:
    """
    Implementácia Winstonovho algoritmu inkrementálneho konceptuálneho učenia.
    
    Táto implementácia dodržiava originálny Winstonov prístup:
    - Pracuje striktne inkrementálne - vždy jeden príklad v jednom kroku
    - Vždy pracuje s aktuálnym modelom a nikdy nezačína odznova
    - Po každom príklade okamžite aktualizuje model/hypotézu
    """
    
    def __init__(self, classification_tree: ClassificationTree):
        """
        Inicializácia Winstonovho učiaceho algoritmu.
        
        Args:
            classification_tree: Klasifikačný strom pre hierarchiu pojmov
        """
        self.classification_tree = classification_tree
        # Špeciálny atribút pre sledovanie histórie aplikácie heuristík
        self.applied_heuristics = []
        self.debug_enabled = True  # Zapnem debugovanie
        # Udržování historie modelů pro BackUp Rule
        self.model_history = []
        self.max_history_size = 5  # Maximální počet uložených historických modelů
    
    def _debug_log(self, message):
        """Debugovacie logovanie pre sledovanie priebehu algoritmu."""
        # Vždy vypisujeme logovanie, bez ohľadu na debug_enabled
        print(f"[WinstonLearner] {message}")

    def update_model(self, model: Model, example: Model, example_type: str = None) -> Model:
        """
        Aktualizuje model podľa striktne Winstonovho algoritmu.
        
        Podľa typu príkladu aplikuje rôzne procedúry:
        - "first_positive": Inicializácia modelu prvým pozitívnym príkladom
        - "positive": GENERALIZE heuristiky (climb_tree, close_interval, enlarge_set, drop_link)
        - "negative": SPECIALIZE heuristiky (require_link, forbid_link)
        
        Args:
            model: Aktuálny model (hypotéza)
            example: Príklad na spracovanie
            example_type: Typ príkladu ("first_positive", "positive", "negative")
            
        Returns:
            Aktualizovaný model
        """
        updated_model = model.copy()
        self.applied_heuristics = []
        
        # 1. Inicializácia prázdneho modelu prvým pozitívnym príkladom
        if example_type == "first_positive":
            self._debug_log("Prázdny model, inicializujem s prvým pozitívnym príkladom")
            updated_model = self._add_missing_objects(updated_model, example)
        
        # 2. GENERALIZE - spracovanie pozitívneho príkladu
        elif example_type == "positive":
            self._debug_log("GENERALIZE: Spracovávam pozitívny príklad")
            
            # Najprv kontrola konzistentnosti
            updated_model = self._check_consistency(updated_model, example)
            
            # Aplikovanie GENERALIZE heuristík v poradí podľa Winstona
            # a) Climb-tree: generalizácia v hierarchii
            self._debug_log("GENERALIZE: Skúšam climb-tree heuristiku...")
            updated_model = self._apply_climb_tree(updated_model, example)
            
            # b) Close-interval: intervaly pre numerické hodnoty
            self._debug_log("GENERALIZE: Skúšam close-interval heuristiku...")
            updated_model = self._apply_close_interval(updated_model, example)
            
            # c) Enlarge-set: množiny povolených hodnôt
            self._debug_log("GENERALIZE: Skúšam enlarge-set heuristiku...")
            updated_model = self._apply_enlarge_set(updated_model, example)
            
            # d) Drop-link: odstránenie nepotrebných spojení
            self._debug_log("GENERALIZE: Skúšam drop-link heuristiku...")
            updated_model = self._apply_drop_link(updated_model, example)
        
        # 3. SPECIALIZE - spracovanie negatívneho príkladu (near miss)
        elif example_type == "negative":
            self._debug_log("SPECIALIZE: Spracovávam negatívny príklad (near miss)")
            
            # a) Require-link: identifikácia chýbajúcich spojení v near_miss
            self._debug_log("SPECIALIZE: Skúšam require-link heuristiku...")
            updated_model = self._apply_require_link(updated_model, example)
            
            # b) Forbid-link: identifikácia zakázaných spojení
            self._debug_log("SPECIALIZE: Skúšam forbid-link heuristiku...")
            updated_model = self._apply_forbid_link(updated_model, example)
        
        # Výpis aplikovaných heuristík
        if self.applied_heuristics:
            self._debug_log(f"Aplikované heuristiky: {', '.join(self.applied_heuristics)}")
        else:
            self._debug_log("Žiadna heuristika nebola aplikovaná")
            
        # Odstránenie duplicitných spojení pred vrátením modelu
        removed_count = updated_model.remove_duplicate_links()
        if removed_count > 0:
            self._debug_log(f"Odstránených {removed_count} duplicitných spojení")
            
        # Výpis modelu pre diagnostiku
        print("Model objekty a atribúty:")
        for obj in updated_model.objects:
            if obj.attributes:
                print(f"  {obj.name} ({obj.class_name}): {obj.attributes}")
            else:
                print(f"  {obj.name} ({obj.class_name}): bez atribútov")
        
        print("\nModel spojenia:")
        for link in updated_model.links:
            print(f"  {link.source} -> {link.target} ({link.link_type.value})")
            
        print("\nFormula:")
        print(updated_model.to_formula())
            
        return updated_model

    def _add_to_history(self, model: Model):
        """
        Přidá model do historie pro možnost pozdějšího návratu.
        
        Args:
            model: Model k uložení do historie
        """
        # Uložíme hlubokou kopii modelu
        self.model_history.append(copy.deepcopy(model))
        
        # Omezíme velikost historie
        if len(self.model_history) > self.max_history_size:
            self.model_history.pop(0)  # Odstraníme nejstarší model

    def _apply_close_interval(self, model: Model, good: Model) -> Model:
        """
        Implementuje close-interval heuristiku pre určenie povolených rozsahov
        numerických atribútov.
        
        Podľa Winstonovej definície:
        "The close-interval heuristic is used when a number or interval in
        an evolving model corresponds to a number in an example. If the
        model uses a number, the number is replaced by an interval spanning
        the model's number and the example's number. If the model uses an
        interval, the interval is enlarged to reach the example's number."
        
        Args:
            model: Aktuálny model
            good: Pozitívny príklad
            
        Returns:
            Aktualizovaný model s intervalom hodnôt pre numerické atribúty
        """
        updated_model = model.copy()
        heuristic_applied = False
        
        print("\n[CLOSE_INTERVAL] Skúšam aplikovať close-interval heuristiku...")
        
        # Pre každý objekt v modeli
        for model_obj in updated_model.objects:
            class_name = model_obj.class_name
            
            # Nájdeme zodpovedajúce objekty v príklade, ktoré sú:
            # 1. Rovnakej triedy, alebo
            # 2. Podtriedou triedy v modeli, alebo
            # 3. Známou podtriedou generalizovanej triedy v modeli
            matching_example_objects = []
            
            for example_obj in good.objects:
                # Kontrola, či sa názvy objektov zhodujú (preferujeme presné zhody podľa názvu)
                if example_obj.name == model_obj.name:
                    matching_example_objects.append(example_obj)
                    print(f"[CLOSE_INTERVAL] Našiel som objekt s rovnakým názvom: {example_obj.name}")
                    continue
                
                # Ak nenájdeme presne zhodný názov, skúsime nájsť zhodu podľa triedy
                # Kontrola, či je trieda objektu v príklade rovnaká, podtriedou alebo známou podtriedou
                matches_class = (example_obj.class_name == class_name or
                                self.classification_tree.is_subclass(example_obj.class_name, class_name) or
                                (class_name in model.known_subclasses and 
                                 example_obj.class_name in model.known_subclasses[class_name]))
                
                if matches_class:
                    matching_example_objects.append(example_obj)
                    print(f"[CLOSE_INTERVAL] Našiel som objekt so zodpovedajúcou triedou: {example_obj.name} ({example_obj.class_name})")
            
            print(f"[CLOSE_INTERVAL] Našlo sa {len(matching_example_objects)} zodpovedajúcich objektov pre {model_obj.name} ({class_name})")
            
            for example_obj in matching_example_objects:
                if not example_obj.attributes:
                    print(f"[CLOSE_INTERVAL] Objekt {example_obj.name} nemá atribúty, preskakujem")
                    continue
                
                # Inicializácia atribútov pre model_obj, ak ešte neexistujú
                if model_obj.attributes is None:
                    model_obj.attributes = {}
                
                # Spracovanie atribútov z príkladu
                for attr_name, example_value in example_obj.attributes.items():
                    print(f"[CLOSE_INTERVAL] Kontrolujem atribút {attr_name} v objekte {example_obj.name}")
                    
                    # Prípad 1: Atribút nie je v modeli, ale je v príklade
                    if attr_name not in model_obj.attributes:
                        if isinstance(example_value, (int, float)):
                            model_obj.attributes[attr_name] = example_value
                            heuristic_applied = True
                            print(f"[CLOSE_INTERVAL] Pridaný nový atribút {model_obj.name}.{attr_name}: {example_value}")
                            self._debug_log(f"Pridaný nový atribút {model_obj.name}.{attr_name}: {example_value}")
                            continue
                    
                    # Ak atribút existuje v modeli, spracovávame existujúce hodnoty
                    if attr_name in model_obj.attributes:
                        model_value = model_obj.attributes[attr_name]
                        
                        # Prípad 2: Model obsahuje číslo a príklad obsahuje číslo
                        if isinstance(model_value, (int, float)) and isinstance(example_value, (int, float)):
                            # Vytvoríme interval od minimálnej po maximálnu hodnotu
                            new_interval = (min(model_value, example_value), max(model_value, example_value))
                            model_obj.attributes[attr_name] = new_interval
                            heuristic_applied = True
                            print(f"[CLOSE_INTERVAL] Vytvorený interval pre {model_obj.name}.{attr_name}: {new_interval}")
                            self._debug_log(f"Vytvorený interval pre {model_obj.name}.{attr_name}: {new_interval}")
                        
                        # Prípad 3: Model obsahuje interval a príklad obsahuje číslo
                        elif (isinstance(model_value, tuple) and len(model_value) == 2 and 
                              isinstance(example_value, (int, float))):
                            min_val, max_val = model_value
                            
                            # Rozšírime interval, ak je to potrebné
                            if example_value < min_val:
                                new_interval = (example_value, max_val)
                                model_obj.attributes[attr_name] = new_interval
                                heuristic_applied = True
                                print(f"[CLOSE_INTERVAL] Rozšírený interval pre {model_obj.name}.{attr_name} na {new_interval}")
                                self._debug_log(f"Rozšírený interval pre {model_obj.name}.{attr_name} na {new_interval}")
                            elif example_value > max_val:
                                new_interval = (min_val, example_value)
                                model_obj.attributes[attr_name] = new_interval
                                heuristic_applied = True
                                print(f"[CLOSE_INTERVAL] Rozšírený interval pre {model_obj.name}.{attr_name} na {new_interval}")
                                self._debug_log(f"Rozšírený interval pre {model_obj.name}.{attr_name} na {new_interval}")
        
        if heuristic_applied:
            self.applied_heuristics.append("close_interval")
            print("[CLOSE_INTERVAL] Heuristika bola úspešne aplikovaná!")
        else:
            print("[CLOSE_INTERVAL] Heuristika nebola aplikovaná - neboli nájdené vhodné atribúty")
            
        return updated_model

    def _is_class_in_classification_tree(self, class_name: str) -> bool:
        """
        Kontroluje, či je daná trieda súčasťou klasifikačného stromu.
        
        Args:
            class_name: Názov triedy na kontrolu
            
        Returns:
            True ak trieda existuje v klasifikačnom strome, inak False
        """
        # Trieda je v klasifikačnom strome, ak má rodiča alebo má deti
        return class_name in self.classification_tree.parent_map or class_name in self.classification_tree.children_map

    def _apply_enlarge_set(self, model: Model, good: Model) -> Model:
        """
        Implementuje enlarge-set heuristiku pre vytvorenie množín povolených hodnôt.
        
        Podľa Winstonovej definície:
        "The enlarge-set heuristic is used when a model has a constraint on a 
        component that does not match a constraint in an example. The constraint is 
        broadened to include the example's constraint."
        
        V našej implementácii sa enlarge-set neaplikuje na prvky, ktoré sú 
        v klasifikačnom strome - pre tie sa používa climb-tree heuristika.
        
        Args:
            model: Aktuálny model
            good: Pozitívny príklad
            
        Returns:
            Aktualizovaný model s rozšírenými množinami povolených komponentov
        """
        updated_model = model.copy()
        heuristic_applied = False
        
        print("\n[ENLARGE_SET] Skúšam aplikovať enlarge-set heuristiku...")
        print(f"[ENLARGE_SET] Spojenia v modeli: {[(link.source, link.target, link.link_type) for link in updated_model.links]}")
        print(f"[ENLARGE_SET] Spojenia v príklade: {[(link.source, link.target, link.link_type) for link in good.links]}")
        
        # Získame množinu tried komponentov v príklade
        example_component_classes = self._get_component_class_set(good)
        print(f"[ENLARGE_SET] Triedy komponentov v príklade: {example_component_classes}")
        
        # Najprv nájdeme všetky komponenty v modeli
        model_components = {}
        
        # Vytvoríme mapu medzi rodičovskými objektmi a ich komponentmi
        for link in updated_model.links:
            if link.link_type == LinkType.MUST:
                parent = link.source
                component = link.target
                
                if parent not in model_components:
                    model_components[parent] = []
                
                model_components[parent].append(component)
                print(f"[ENLARGE_SET] Našiel som MUST spojenie: {parent} -> {component}")
        
        # Teraz prejdeme cez príklad a kontrolujeme, či existujú iné povolené komponenty
        # Vytvoríme mapu podobnú ako pre model
        example_components = {}
        
        # Vytvoríme zoznam všetkých regulárnych komponentov v príklade
        for link in good.links:
            if link.link_type == LinkType.REGULAR:
                # Ak nemáme príklad s rovnakým menom, hľadáme objekty s rovnakou triedou
                example_source = next((obj for obj in good.objects if obj.name == link.source), None)
                example_target = next((obj for obj in good.objects if obj.name == link.target), None)
                
                if not example_source or not example_target:
                    continue
                
                parent_class = example_source.class_name
                component_class = example_target.class_name
                
                print(f"[ENLARGE_SET] Našiel som link v príklade: {parent_class} -> {component_class}")
                
                if parent_class not in example_components:
                    example_components[parent_class] = []
                
                if component_class not in example_components[parent_class]:
                    example_components[parent_class].append(component_class)
        
        # Teraz porovnáme množiny komponentov a rozšírime model, ak je to potrebné
        for parent_class, components in example_components.items():
            for component_class in components:
                # Ak existuje MUST pravidlo pre komponent v modeli, musíme ho rozšíriť
                if parent_class in model_components:
                    existing_must_components = set(model_components[parent_class])
                    
                    # Kontrolujeme, či nový komponent aj existujúce komponenty sú v klasifikačnom strome
                    component_in_tree = self._is_class_in_classification_tree(component_class)
                    
                    # Ak je komponent v klasifikačnom strome, preskočíme ho - pre tie sa používa climb-tree
                    if component_in_tree:
                        print(f"[ENLARGE_SET] Preskakujem komponent {component_class}, pretože je v klasifikačnom strome - použite climb-tree heuristiku")
                        continue
                
                    # Skontrolujeme, či existuje konflikt medzi komponentami v klasifikačnom strome
                    existing_component_in_tree = False
                    for existing_component in existing_must_components:
                        if self._is_class_in_classification_tree(existing_component):
                            print(f"[ENLARGE_SET] Existujúci komponent {existing_component} je v klasifikačnom strome")
                            existing_component_in_tree = True
                    
                    # Ak existujúci komponent je v klasifikačnom strome, preskočíme 
                    # pridávanie alternatívneho komponentu, keďže by to vytváralo disjunkciu 
                    # namiesto použitia climb-tree
                    if existing_component_in_tree:
                        print(f"[ENLARGE_SET] Preskakujem pridanie alternatívy {component_class}, pretože existujúci komponent je v klasifikačnom strome - použite climb-tree heuristiku")
                        continue
                
                    # Zistíme, či komponent z príkladu je už povolený
                    component_already_allowed = False
                    for existing_component in existing_must_components:
                        # Kontrola, či komponent z príkladu je podtriedou existujúceho MUST komponentu
                        if self.classification_tree.is_subclass(component_class, existing_component):
                            component_already_allowed = True
                            print(f"[ENLARGE_SET] Komponent {component_class} je už povolený ako podtrieda {existing_component}")
                            break
                    
                    # Ak komponent nie je povolený, pridáme ho
                    if not component_already_allowed and component_class not in existing_must_components:
                        print(f"[ENLARGE_SET] Pridávam nové MUST pravidlo: {parent_class} -> {component_class}")
                        
                        # Pridáme nové MUST pravidlo
                        new_link = Link(
                            source=parent_class,
                            target=component_class,
                            link_type=LinkType.MUST
                        )
                        updated_model.add_link(new_link)
                        heuristic_applied = True
                        self._debug_log(f"Pridané nové MUST pravidlo: {parent_class} -> {component_class}")
        
        if heuristic_applied:
            self.applied_heuristics.append("enlarge_set")
            print("[ENLARGE_SET] Heuristika bola úspešne aplikovaná!")
        else:
            print("[ENLARGE_SET] Heuristika nebola aplikovaná - neboli nájdené nové komponenty na pridanie")
            
        return updated_model

    def _is_example_valid(self, model: Model, example: Model) -> bool:
        """
        Kontroluje, zda příklad je platný podle aktuálního modelu.
        
        Args:
            model: Model k otestování
            example: Příklad k ověření
            
        Returns:
            True, pokud příklad splňuje všechna pravidla modelu, jinak False
        """
        # Kontrola, zda příklad má všechny požadované MUST vazby
        for link in model.links:
            if link.link_type == LinkType.MUST:
                # Najdeme všechny objekty ve zdroji třídy
                source_objects = [obj for obj in example.objects if obj.class_name == link.source]
                
                for source_obj in source_objects:
                    # Hledáme, zda existuje spojení tohoto objektu s objektem cílové třídy
                    has_target = False
                    
                    for example_link in example.links:
                        if example_link.source == source_obj.name:
                            target_obj = next((obj for obj in example.objects if obj.name == example_link.target), None)
                            if target_obj:
                                # Kontrola: 
                                # 1. Je objekt priamo danej triedy?
                                # 2. Je objekt podtriedou danej triedy?
                                # 3. Je objekt jednou zo známych podtried generalizovanej triedy?
                                if (target_obj.class_name == link.target or 
                                    self.classification_tree.is_subclass(target_obj.class_name, link.target) or
                                    (link.target in model.known_subclasses and 
                                     target_obj.class_name in model.known_subclasses[link.target])):
                                    has_target = True
                                    break
                    
                    if not has_target:
                        print(f"[VALIDATE] Objekt {source_obj.name} ({source_obj.class_name}) nemá požadovaný komponent {link.target}")
                        return False
        
        # Kontrola, zda příklad neobsahuje zakázané MUST_NOT vazby
        for link in model.links:
            if link.link_type == LinkType.MUST_NOT:
                source_objects = [obj for obj in example.objects if obj.class_name == link.source]
                
                for source_obj in source_objects:
                    for example_link in example.links:
                        if example_link.source == source_obj.name:
                            target_obj = next((obj for obj in example.objects if obj.name == example_link.target), None)
                            if target_obj:
                                # Podobne ako pri MUST, kontrolujeme všetky možnosti
                                if (target_obj.class_name == link.target or 
                                    self.classification_tree.is_subclass(target_obj.class_name, link.target) or
                                    (link.target in model.known_subclasses and 
                                     target_obj.class_name in model.known_subclasses[link.target])):
                                    print(f"[VALIDATE] Objekt {source_obj.name} ({source_obj.class_name}) má zakázaný komponent {target_obj.name} ({target_obj.class_name})")
                                return False
        
        # Kontrola atributů - pro každý objekt v modelu s definovanými atributy
        for model_obj in model.objects:
            if not model_obj.attributes:
                continue
                
            # Najdeme odpovídající objekty ve příkladu
            for example_obj in example.objects:
                # Kontrolujeme:
                # 1. Či je objekt rovnakej triedy
                # 2. Či je objekt podtriedou modelovej triedy
                # 3. Či je objekt jednou zo známych podtried generalizovanej triedy
                matches_class = (example_obj.class_name == model_obj.class_name or
                                self.classification_tree.is_subclass(example_obj.class_name, model_obj.class_name) or
                                (model_obj.class_name in model.known_subclasses and 
                                 example_obj.class_name in model.known_subclasses[model_obj.class_name]))
                
                if matches_class:
                    # Kontrola numerických intervalů
                    for attr_name, model_value in model_obj.attributes.items():
                        if isinstance(model_value, tuple) and len(model_value) == 2:
                            # Je to interval
                            min_val, max_val = model_value
                            
                            # Pokud příklad má tento atribut, zkontrolujeme, zda hodnota je v intervalu
                            if example_obj.attributes and attr_name in example_obj.attributes:
                                example_value = example_obj.attributes[attr_name]
                                if isinstance(example_value, (int, float)) and (example_value < min_val or example_value > max_val):
                                    print(f"[VALIDATE] Atribút {attr_name} objektu {example_obj.name} ({example_obj.class_name}) má hodnotu {example_value}, čo je mimo interval [{min_val}, {max_val}]")
                                    return False
                        
                        # Kontrola množin hodnot
                        elif isinstance(model_value, set):
                            # Je to množina přijatelných hodnot
                            if example_obj.attributes and attr_name in example_obj.attributes:
                                example_value = example_obj.attributes[attr_name]
                                if example_value not in model_value:
                                    print(f"[VALIDATE] Atribút {attr_name} objektu {example_obj.name} ({example_obj.class_name}) má hodnotu {example_value}, čo nie je v množine povolených hodnôt {model_value}")
                                    return False
        
        # Pokud všechny kontroly prošly, příklad je platný
        print("[VALIDATE] Príklad je platný podľa aktuálneho modelu")
        return True

    def _check_consistency(self, model: Model, good: Model) -> Model:
        """
        Kontroluje, zda nový pozitivní příklad není v konfliktu s existujícími pravidly.
        Pokud konflikt najde, buď odstraní pravidlo nebo ho zobecní.
        
        Toto nie je základná Winstonova heuristika, ale je potrebná pre správne fungovanie
        modelu pri konflikte medzi pozitívnym príkladom a existujúcimi pravidlami.
        
        Args:
            model: Aktuální model
            good: Pozitivní příklad
            
        Returns:
            Aktualizovaný model bez konfliktů
        """
        updated_model = model.copy()
        
        # Projít všechna MUST_NOT pravidla v modelu
        conflicting_links = []
        for link in updated_model.links:
            if link.link_type == LinkType.MUST_NOT:
                source_class = link.source
                target_class = link.target
                
                # Kontrola konfliktu s pozitivním příkladem
                for good_obj in good.objects:
                    for good_link in good.links:
                        if good_link.source == good_obj.name:
                            # Najít cílový objekt v pozitivním příkladu
                            good_target_obj = next((obj for obj in good.objects if obj.name == good_link.target), None)
                            if good_target_obj:
                                # Kontrola, zda jsou třídy v hierarchickém vztahu
                                if (self.classification_tree.is_subclass(good_obj.class_name, source_class) and
                                    self.classification_tree.is_subclass(good_target_obj.class_name, target_class)):
                                    self._debug_log(f"Detekován konflikt: {good_obj.name}({good_obj.class_name}) -> {good_target_obj.name}({good_target_obj.class_name}) konfliktuje s pravidlem {source_class} -> {target_class}")
                                    conflicting_links.append(link)
        
        # Odstranit konfliktní pravidla a vytvořit generalizované pravidlo
        for link in conflicting_links:
            # Odstraníme konfliktní pravidlo
            updated_model.links.remove(link)
            self._debug_log(f"Odstraněno konfliktní pravidlo: {link.source} -> {link.target} ({link.link_type.value})")
            
            # Hledáme nadřazenou třídu, která by mohla sloužit pro generalizaci
            target_parent = self.classification_tree.get_parent(link.target)
            if target_parent:
                # Místo MUST_NOT vazby na konkrétní typ vytvoříme MUST vazbu na nadřazenou třídu
                # Například místo "X5 nesmí mít DieselEngine" -> "X5 musí mít Engine"
                generalized_link = Link(
                    source=link.source,
                    target=target_parent,
                    link_type=LinkType.MUST
                )
                
                # Zkontrolujeme, zda pravidlo již neexistuje
                if not any(l.source == generalized_link.source and 
                           l.target == generalized_link.target and 
                           l.link_type == generalized_link.link_type 
                           for l in updated_model.links):
                    updated_model.add_link(generalized_link)
                    self._debug_log(f"Vytvořeno generalizované pravidlo: {generalized_link.source} -> {generalized_link.target} (MUST)")
        
        return updated_model

    def _add_missing_objects(self, model: Model, good: Model) -> Model:
        """
        Přidá nové objekty a spojení z pozitivního příkladu, pokud v modelu chybí.
        Používá se především při prvním příkladu nebo pro detekci nových objektů.
        
        Args:
            model: Aktuální model
            good: Pozitivní příklad
            
        Returns:
            Aktualizovaný model s novými objekty
        """
        updated_model = model.copy()
        
        # Kontrola, zda objekty z příkladu existují v modelu
        for good_obj in good.objects:
            if not any(obj.name == good_obj.name for obj in updated_model.objects):
                # Přidání nového objektu
                updated_model.objects.append(Object(
                    name=good_obj.name,
                    class_name=good_obj.class_name,
                    attributes=good_obj.attributes
                ))
                self.applied_heuristics.append("add_object")
                self._debug_log(f"Přidán nový objekt: {good_obj.name} ({good_obj.class_name})")
        
        # Přidání chybějících spojení
        for good_link in good.links:
            if not any(link.source == good_link.source and link.target == good_link.target 
                      for link in updated_model.links):
                # Přidání nového spojení
                updated_model.add_link(Link(
                    source=good_link.source,
                    target=good_link.target,
                    link_type=good_link.link_type
                ))
                self.applied_heuristics.append("add_link")
                self._debug_log(f"Přidáno nové spojení: {good_link.source} -> {good_link.target}")
            
        return updated_model

    def _apply_require_link(self, model: Model, near_miss: Model):
            """
            Aplikuje require-link heuristiku.
            
            Podľa Winstonovej definície:
            "The require-link heuristic is used when an evolving model has a link 
            in a place where a near miss does not. The model link is converted to 
            a Must form."
            
            Metóda porovnáva aktuálny model (evolving model) s near-miss príkladom
            a konvertuje vhodné spojenia na MUST.
            
            Args:
                model: Aktuálný model
                near_miss: Near-miss príklad
                
            Returns:
                Aktualizovaný model
            """
            updated_model = model.copy()
            
            # Zbierka spojení medzi triedami v near_miss príklade
            near_miss_class_links = set()
            
            # Zbierame všetky prepojenia tried v near_miss
            for near_miss_link in near_miss.links:
                near_miss_source = next((obj for obj in near_miss.objects if obj.name == near_miss_link.source), None)
                near_miss_target = next((obj for obj in near_miss.objects if obj.name == near_miss_link.target), None)
                
                if near_miss_source and near_miss_target:
                    # Pridáme dvojicu (trieda zdroja, trieda cieľa) do množiny spojení
                    near_miss_class_links.add((near_miss_source.class_name, near_miss_target.class_name))
            
            # Prechádzame všetky spojenia v aktuálnom modeli
            for model_link in model.links:
                # Pracujeme len s bežnými spojeniami, MUST a MUST_NOT spojenia neriešime
                if model_link.link_type != LinkType.REGULAR:
                    continue
                    
                # Získame objekty pre spojenie v modeli
                model_source = next((obj for obj in model.objects if obj.name == model_link.source), None)
                model_target = next((obj for obj in model.objects if obj.name == model_link.target), None)
                
                if not model_source or not model_target:
                    continue
                    
                # Skontrolujeme, či takéto spojenie tried existuje v near_miss
                if (model_source.class_name, model_target.class_name) not in near_miss_class_links:
                    # Vytvoríme MUST spojenie na úrovni tried, ak neexistuje
                    must_link = Link(
                        source=model_source.class_name,
                        target=model_target.class_name,
                        link_type=LinkType.MUST
                    )
                    
                    # Skontrolujeme, či takéto spojenie už neexistuje
                    if not any(link.source == must_link.source and 
                            link.target == must_link.target and 
                            link.link_type == must_link.link_type 
                            for link in updated_model.links):
                        # Skontrolujeme prípadný konflikt s MUST_NOT
                        has_conflict = any(link.source == must_link.source and 
                                        link.target == must_link.target and 
                                        link.link_type == LinkType.MUST_NOT 
                                        for link in updated_model.links)
                        
                        if not has_conflict:
                            updated_model.add_link(must_link)
                            self.applied_heuristics.append("require_link")
                            self._debug_log(f"Pridané MUST pravidlo (spojenie existuje v modeli, ale nie v near_miss): {model_source.class_name} -> {model_target.class_name}")
                    
                    # Aktualizujeme aj konkrétne spojenie na MUST, ak ešte nie je
                    if model_link.link_type != LinkType.MUST:
                        model_link.link_type = LinkType.MUST
                        self.applied_heuristics.append("require_link")
                        self._debug_log(f"Konvertované spojenie na MUST: {model_link.source} -> {model_link.target}")
            
            return updated_model

    def _is_rule_consistent(self, updated_model, source_class, target_class, link_type):
        """
        Zkontroluje, zda je pravidlo konzistentní s existujícím modelem.
        
        Args:
            updated_model: Aktuální model
            source_class: Zdrojová třída
            target_class: Cílová třída
            link_type: Typ vazby (MUST_NOT)
            
        Returns:
            True, pokud pravidlo je konzistentní, jinak False
        """
        # Zkontrolujeme, zda toto pravidlo není v konfliktu s jinými pravidly
        
        # 1. Kontrola konfliktu s existujícími MUST pravidly
        if link_type == LinkType.MUST_NOT:
            for link in updated_model.links:
                if link.link_type == LinkType.MUST and link.source == source_class and link.target == target_class:
                    self._debug_log(f"KONFLIKT: {source_class} nemůže mít MUST_NOT pro {target_class}, protože již má MUST")
                    return False
        
        # 2. Kontrola konfliktu s pozitivními příklady v aktuálním modelu
        # Zkontrolujeme, zda v aktuálním modelu existují objekty, které by porušily toto pravidlo
        for obj in updated_model.objects:
            if obj.class_name == source_class:
                # Najdeme všechny vazby z tohoto objektu
                for link in updated_model.links:
                    if link.source == obj.name:
                        # Najdeme cílový objekt
                        target_obj = next((o for o in updated_model.objects if o.name == link.target), None)
                        if target_obj and target_obj.class_name == target_class and link_type == LinkType.MUST_NOT:
                            self._debug_log(f"KONFLIKT: {source_class} nemůže mít MUST_NOT pro {target_class}, protože objekt {obj.name} již má vazbu na {target_obj.name}")
                            return False
        
        return True

    def _find_specific_difference(self, updated_model, car_class, good, near_miss):
        """
        Hledá konkrétnější rozdíl mezi pozitivním a negativním příkladem.
        
        Args:
            updated_model: Aktuální model
            car_class: Třída auta
            good: Pozitivní příklad
            near_miss: Near-miss příklad
            
        Returns:
            Dvojice (source_class, target_class) pro vytvoření MUST_NOT vazby, nebo None
        """
        # Najdeme objekty daného modelu auta v pozitivním a negativním příkladu
        good_cars = [obj for obj in good.objects if obj.class_name == car_class]
        near_miss_cars = [obj for obj in near_miss.objects if obj.class_name == car_class]
        
        if not good_cars or not near_miss_cars:
            return None
        
        # Najdeme komponenty připojené k pozitivnímu příkladu
        good_car = good_cars[0]
        good_components = {}
        for link in good.links:
            if link.source == good_car.name:
                target_obj = next((o for o in good.objects if o.name == link.target), None)
                if target_obj and target_obj.class_name not in ["Series3", "Series5", "Series7", "X5", "X7"]:
                    good_components[target_obj.class_name] = target_obj
        
        # Najdeme komponenty připojené k negativnímu příkladu
        near_miss_car = near_miss_cars[0]
        near_miss_components = {}
        for link in near_miss.links:
            if link.source == near_miss_car.name:
                target_obj = next((o for o in near_miss.objects if o.name == link.target), None)
                if target_obj and target_obj.class_name not in ["Series3", "Series5", "Series7", "X5", "X7"]:
                    near_miss_components[target_obj.class_name] = target_obj
        
        # Nejprve kontrolujeme rozdíly v typech komponent (například ManualTransmission vs AutomaticTransmission)
        for component_class, nm_component in near_miss_components.items():
            # Zkontrolujeme, zda tato třída komponent existuje i v pozitivním příkladu
            if any(comp_class for comp_class, _ in good_components.items() if 
                  self.classification_tree.are_related(comp_class, component_class)):
                # Našli jsme komponentu stejného typu, ale jiné třídy - to je konkrétnější rozdíl
                # Například negativní příklad má ManualTransmission, zatímco pozitivní má AutomaticTransmission
                # Vrátíme vazbu (car_class, component_class) pro vytvoření MUST_NOT
                self._debug_log(f"Nalezen konkrétnější rozdíl: {car_class} -> {component_class}")
                return (car_class, component_class)
        
        # Pokud nenajdeme konkrétnější rozdíl, vrátíme None
        return None

    def _apply_forbid_link(self, model: Model, near_miss: Model):
        """
        Aplikuje forbid-link heuristiku.
        
        Podľa Winstonovej definície:
        "The forbid-link heuristic is used when a near miss has a link in a 
        place where an evolving model does not. A Must-not form is installed 
        in the evolving model."
        
        Metóda porovnáva near-miss príklad s aktuálnym modelom a vytvára
        MUST_NOT pravidlá pre spojenia, ktoré sú v near-miss, ale nie v modeli.
        
        Args:
            model: Aktuálný model
            near_miss: Near-miss príklad
            
        Returns:
            Aktualizovaný model
        """
        updated_model = model.copy()
        
        # Vytvoríme množinu spojení v modeli na úrovni tried
        model_class_links = set()
        
        # Zbierame všetky prepojenia medzi triedami v aktuálnom modeli
        for model_link in model.links:
            model_source = next((obj for obj in model.objects if obj.name == model_link.source), None)
            model_target = next((obj for obj in model.objects if obj.name == model_link.target), None)
            
            if model_source and model_target:
                # Pridáme dvojicu (trieda zdroja, trieda cieľa) do množiny spojení
                model_class_links.add((model_source.class_name, model_target.class_name))
        
        # Pre každé spojenie v near-miss príklade, kontrolujeme
        # či nejaké podobné spojenie existuje v modeli
        for near_miss_link in near_miss.links:
            near_miss_source = next((obj for obj in near_miss.objects if obj.name == near_miss_link.source), None)
            near_miss_target = next((obj for obj in near_miss.objects if obj.name == near_miss_link.target), None)
            
            if not near_miss_source or not near_miss_target:
                continue
            
            # Skontrolujeme, či takéto spojenie tried existuje v modeli
            if (near_miss_source.class_name, near_miss_target.class_name) not in model_class_links:
                # Ak spojenie tried existuje v near-miss, ale nie v modeli, 
                # vytvoríme MUST_NOT pravidlo
                
                # Najprv skontrolujeme, či je pravidlo konzistentné
                if self._is_rule_consistent(updated_model, near_miss_source.class_name, near_miss_target.class_name, LinkType.MUST_NOT):
                    must_not_link = Link(
                        source=near_miss_source.class_name,
                        target=near_miss_target.class_name,
                        link_type=LinkType.MUST_NOT
                    )
                    
                    # Skontrolujeme, či takéto spojenie už neexistuje
                    if not any(link.source == must_not_link.source and 
                               link.target == must_not_link.target and 
                               link.link_type == must_not_link.link_type 
                               for link in updated_model.links):
                        updated_model.add_link(must_not_link)
                        self.applied_heuristics.append("forbid_link")
                        self._debug_log(f"Pridané MUST_NOT pravidlo (spojenie existuje v near-miss, ale nie v modeli): {near_miss_source.class_name} -> {near_miss_target.class_name}")
        
        return updated_model
    
    def _get_component_class_set(self, example: Model) -> Set[str]:
        """
        Vrátí množinu tříd komponent použitých v příkladu.
        
        Args:
            example: Model příkladu
            
        Returns:
            Množina názvů tříd komponent
        """
        component_classes = set()
        
        for obj in example.objects:
            # Přidáme všechny třídy objektů, které nejsou modely BMW
            if obj.class_name not in ["BMW", "Series3", "Series5", "Series7", "X5", "X7"]:
                component_classes.add(obj.class_name)
        
        return component_classes
    
    def _apply_drop_link(self, model: Model, good: Model):
        """
        Aplikuje drop-link heuristiku.
        
        Podľa Winstonovej definície:
        "The drop-link heuristic is used when the objects that are different 
        in an evolving model and in an example form an exhaustive set. The 
        drop-link heuristic is also used when an evolving model has a link that 
        is not in the example. The link is dropped from the model."
        
        Metóda odstráni z modelu spojenia, ktoré nie sú prítomné v príklade (good).
        
        Args:
            model: Aktuálný model
            good: Pozitívny príklad
            
        Returns:
            Aktualizovaný model
        """
        updated_model = model.copy()
        was_applied = False
        
        # Nájdeme všetky REGULAR spojenia v modeli
        regular_links = [link for link in updated_model.links 
                         if link.link_type == LinkType.REGULAR]
        
        # Pre každé spojenie v modeli skontrolujeme, či existuje v príklade
        links_to_remove = []
        
        for model_link in regular_links:
            # Zistíme, či existuje zodpovedajúce spojenie v príklade
            has_corresponding = False
            
            for good_link in good.links:
                if model_link.source == good_link.source and model_link.target == good_link.target:
                    has_corresponding = True
                    break
                    
            # Ak neexistuje zodpovedajúce spojenie, označíme ho na odstránenie
            if not has_corresponding:
                links_to_remove.append(model_link)
                
        # Teraz odstránime označené spojenia
        for link_to_remove in links_to_remove:
            # Získame objekty pre toto spojenie
            source_obj = next((obj for obj in updated_model.objects if obj.name == link_to_remove.source), None)
            target_obj = next((obj for obj in updated_model.objects if obj.name == link_to_remove.target), None)
            
            if source_obj and target_obj:
                # Kontrola, či existuje generické pravidlo medzi triedami objektov
                has_generic_rule = False
                
                for rule_link in updated_model.links:
                    # Kontrola pravidiel typu MUST pre tieto triedy
                    if (rule_link.link_type == LinkType.MUST and 
                        rule_link.source == source_obj.class_name and 
                        (rule_link.target == target_obj.class_name or 
                         self.classification_tree.is_subclass(target_obj.class_name, rule_link.target))):
                        has_generic_rule = True
                        self._debug_log(f"Ponechávam spojenie {link_to_remove.source} -> {link_to_remove.target} kvôli generickému pravidlu {rule_link.source} -> {rule_link.target}")
                        break
                
                # Ak neexistuje generické pravidlo, môžeme spojenie odstrániť
                if not has_generic_rule:
                    updated_model.remove_link(link_to_remove)
                    self.applied_heuristics.append("drop_link")
                    was_applied = True
                    self._debug_log(f"Odstránené spojenie z modelu: {link_to_remove.source} -> {link_to_remove.target}")
        
        # Zabezpečíme, že heuristika je označená ako aplikovaná, ak nejaké spojenie bolo odstránené
        if was_applied:
            self._debug_log("Drop-link heuristika bola úspešne aplikovaná")
            
        return updated_model

    def _apply_climb_tree(self, model: Model, good: Model):
        """
        Aplikuje climb-tree heuristiku.
        
        Podľa Winstonovej definície:
        "The climb-tree heuristic is used when an object in an evolving model
        corresponds to a different object in an example. Must-be-a links are
        routed to the most specific common class in the classification tree above
        the model object and the example object."
        
        Keď objekt v modeli zodpovedá inému objektu v príklade, nájdeme ich najbližšieho 
        spoločného predka v klasifikačnom strome a presmerujeme MUST_BE_A spojenia na túto 
        spoločnú triedu.
        
        Args:
            model: Aktuálny model
            good: Pozitívny príklad
            
        Returns:
            Aktualizovaný model
        """
        updated_model = model.copy()
        heuristic_applied = False
        
        print("\n[CLIMB_TREE] Skúšam aplikovať climb-tree heuristiku...")
        print(f"[CLIMB_TREE] Objekty v modeli: {[(obj.name, obj.class_name) for obj in updated_model.objects]}")
        print(f"[CLIMB_TREE] Objekty v príklade: {[(obj.name, obj.class_name) for obj in good.objects]}")
        
        # DEBUG: Vypíš obsah parent_map, aby sme videli, či hierarchia tried je správne načítaná
        print(f"[CLIMB_TREE] DEBUG - Obsah parent_map: {self.classification_tree.parent_map}")
        
        # Sledovanie tried, ktoré boli generalizované (na aktualizáciu MUST pravidiel neskôr)
        generalized_classes = {}
        
        # Prejdeme všetky objekty v modeli a hľadáme zodpovedajúce objekty v príklade
        for model_obj in updated_model.objects:
            matching_example_objs = [obj for obj in good.objects if obj.name == model_obj.name]
            
            if not matching_example_objs:
                print(f"[CLIMB_TREE] Objekt {model_obj.name} neexistuje v príklade")
                continue
            
            matching_example_obj = matching_example_objs[0]
            
            print(f"[CLIMB_TREE] Našiel som objekt {model_obj.name} v oboch modeloch:")
            print(f"[CLIMB_TREE]   - V modeli: trieda {model_obj.class_name}")
            print(f"[CLIMB_TREE]   - V príklade: trieda {matching_example_obj.class_name}")
            
            # Ak sme našli objekt s rovnakým menom ale inou triedou
            if model_obj.class_name != matching_example_obj.class_name:
                print(f"[CLIMB_TREE] Objekt {model_obj.name} má rôzne triedy v modeli a príklade")
                
                # Hľadáme spoločného predka v klasifikačnom strome
                common_ancestor = None
                
                # 1. Kontrola, či jedna trieda nie je podtriedou druhej
                if self.classification_tree.is_subclass(model_obj.class_name, matching_example_obj.class_name):
                    common_ancestor = matching_example_obj.class_name
                    print(f"[CLIMB_TREE] {model_obj.class_name} je podtriedou {matching_example_obj.class_name}, používam {common_ancestor} ako spoločného predka")
                elif self.classification_tree.is_subclass(matching_example_obj.class_name, model_obj.class_name):
                    common_ancestor = model_obj.class_name
                    print(f"[CLIMB_TREE] {matching_example_obj.class_name} je podtriedou {model_obj.class_name}, používam {common_ancestor} ako spoločného predka")
                else:
                    # 2. Hľadáme spoločného predka
                    common_ancestor = self.classification_tree.find_common_ancestor(
                        model_obj.class_name, 
                        matching_example_obj.class_name
                    )
                    
                    # 3. Ak metóda find_common_ancestor nenašla predka, skúsime to vlastnou logikou
                    if not common_ancestor:
                        model_parents = []
                        example_parents = []
                        
                        # Získame všetkých predkov modelu
                        parent = self.classification_tree.get_parent(model_obj.class_name)
                        while parent:
                            model_parents.append(parent)
                            parent = self.classification_tree.get_parent(parent)
                        
                        # Získame všetkých predkov príkladu
                        parent = self.classification_tree.get_parent(matching_example_obj.class_name)
                        while parent:
                            example_parents.append(parent)
                            parent = self.classification_tree.get_parent(parent)
                        
                        # Hľadáme spoločného predka v zoznamoch predkov
                        for model_parent in model_parents:
                            if model_parent in example_parents:
                                common_ancestor = model_parent
                                print(f"[CLIMB_TREE] Našiel som spoločného predka cez predkov: {common_ancestor}")
                                break
                        
                        if common_ancestor:
                            self._debug_log(f"Nájdený spoločný predok: {common_ancestor} pre triedy {model_obj.class_name} a {matching_example_obj.class_name}")
                            
                            # Pôvodná trieda objektu
                            original_class = model_obj.class_name
                            
                            # Pridáme informáciu o generalizácii triedy pre neskoršie použitie
                            generalized_classes[original_class] = common_ancestor
                            
                            # Aktualizujeme triedu objektu na spoločného predka
                            model_obj.class_name = common_ancestor
                                                
                            # Aktualizujeme aj MUST_BE_A spojenia pre tento objekt
                            for link in updated_model.links:
                                if link.source == model_obj.name and link.link_type == LinkType.MUST_BE_A:
                                    link.target = common_ancestor
                                    self._debug_log(f"Aktualizované MUST_BE_A spojenie: {link.source} -> {common_ancestor}")
                            
                            # Zaznamenáme podtriedu do known_subclasses
                            if common_ancestor not in updated_model.known_subclasses:
                                updated_model.known_subclasses[common_ancestor] = set()
                            
                            # Pridaj obe triedy ako známe podtriedy, ale len ak nie sú identické so spoločným predkom
                            if original_class != common_ancestor:
                                updated_model.known_subclasses[common_ancestor].add(original_class)
                            
                            if matching_example_obj.class_name != common_ancestor:
                                updated_model.known_subclasses[common_ancestor].add(matching_example_obj.class_name)
                            
                            print(f"[CLIMB_TREE] Zaznamenávam známe podtriedy pre {common_ancestor}: {updated_model.known_subclasses[common_ancestor]}")
                            
                            heuristic_applied = True
                            self._debug_log(f"Aplikovaná climb-tree heuristika: objekt {model_obj.name} zmenený z {original_class} na {common_ancestor}")
                        else:
                            print(f"[CLIMB_TREE] Nenašiel som spoločného predka pre {model_obj.class_name} a {matching_example_obj.class_name}")
            else:
                print(f"[CLIMB_TREE] Objekt {model_obj.name} má rovnakú triedu {model_obj.class_name} v oboch modeloch, nič nerobím")
        
        # Teraz aktualizujeme všetky MUST a MUST_NOT pravidlá pre generalizované triedy
        if generalized_classes:
            print("[CLIMB_TREE] Aktualizujem MUST a MUST_NOT pravidlá pre generalizované triedy...")
            links_to_update = []
            
            # Vytvoríme množinu pre sledovanie už spracovaných pravidiel, aby sa zabránilo duplicitám
            processed_rules = set()
            
            for link in updated_model.links:
                if link.link_type in [LinkType.MUST, LinkType.MUST_NOT]:
                    # Ak zdrojová trieda bola generalizovaná
                    if link.source in generalized_classes:
                        original_source = link.source
                        new_source = generalized_classes[original_source]
                        
                        # Vytvoríme kľúč pre pravidlo aby sme vedeli sledovať duplicity
                        rule_key = (new_source, link.target, link.link_type)
                        if rule_key not in processed_rules:
                            links_to_update.append((link, 'source', original_source, new_source))
                            processed_rules.add(rule_key)
                    
                    # Ak cieľová trieda bola generalizovaná
                    if link.target in generalized_classes:
                        original_target = link.target
                        new_target = generalized_classes[original_target]
                        
                        # Vytvoríme kľúč pre pravidlo aby sme vedeli sledovať duplicity
                        rule_key = (link.source, new_target, link.link_type)
                        if rule_key not in processed_rules:
                            links_to_update.append((link, 'target', original_target, new_target))
                            processed_rules.add(rule_key)
            
            # Aktualizujeme odkazy
            for link, field, original, new in links_to_update:
                print(f"[CLIMB_TREE] Aktualizujem pravidlo: {link.source} -> {link.target} ({link.link_type.value})")
                
                # Najprv si zapamätáme staré hodnoty pre kontrolu duplicít
                old_source = link.source
                old_target = link.target
                
                if field == 'source':
                    link.source = new
                else:
                    link.target = new
                
                # Skontrolujeme, či už takéto pravidlo neexistuje v modeli
                duplicate_exists = any(l != link and 
                                       l.source == link.source and 
                                       l.target == link.target and 
                                       l.link_type == link.link_type 
                                       for l in updated_model.links)
                
                # Ak je to duplicita, obnovíme pôvodné hodnoty a preskočíme aktualizáciu
                if duplicate_exists:
                    print(f"[CLIMB_TREE] Preskakujem duplicitné pravidlo: {link.source} -> {link.target} ({link.link_type.value})")
                    if field == 'source':
                        link.source = old_source
                    else:
                        link.target = old_target
                    continue
                
                print(f"[CLIMB_TREE] Pravidlo aktualizované na: {link.source} -> {link.target} ({link.link_type.value})")
                self._debug_log(f"Aktualizované {link.link_type.value} pravidlo: {original} -> {new}")
                
                # Zaznamenáme aj tieto generalizácie do known_subclasses
                if field == 'source':
                    if new not in updated_model.known_subclasses:
                        updated_model.known_subclasses[new] = set()
                    if original != new:  # Nepridávame triedu ako podtriedu samej seba
                        updated_model.known_subclasses[new].add(original)
                else:
                    if new not in updated_model.known_subclasses:
                        updated_model.known_subclasses[new] = set()
                    if original != new:  # Nepridávame triedu ako podtriedu samej seba
                        updated_model.known_subclasses[new].add(original)
                
                heuristic_applied = True
        
        if heuristic_applied:
            self.applied_heuristics.append("climb_tree")
            print("[CLIMB_TREE] Heuristika bola úspešne aplikovaná!")
            print(f"[CLIMB_TREE] Známe podtriedy: {updated_model.known_subclasses}")
        else:
            print("[CLIMB_TREE] Heuristika nebola aplikovaná - nenašli sa vhodné objekty")
        
        return updated_model 