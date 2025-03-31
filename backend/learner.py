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
        self.debug_enabled = False
        # Udržování historie modelů pro BackUp Rule
        self.model_history = []
        self.max_history_size = 5  # Maximální počet uložených historických modelů
    
    def _debug_log(self, message):
        """Debugovacie logovanie pre sledovanie priebehu algoritmu."""
        if self.debug_enabled:
            print(f"[WinstonLearner] {message}")

    def update_model(self, model: Model, good: Model, near_miss: Model) -> Model:
        """
        Aktualizuje model podle pozitivního a negativního příkladu.
        
        Důležité: Algoritmus aplikuje heuristiky v pořadí priorit, ale vždy jen jednu.
        Jakmile jedna heuristika vede ke změně, algoritmus se ukončí.
        
        Args:
            model: Aktuální model (hypotéza)
            good: Pozitivní příklad
            near_miss: Negativní příklad (near-miss)
            
        Returns:
            Aktualizovaný model
        """
        self._debug_log(f"Updating model with positive example {good} and negative example {near_miss}")
        updated_model = model.copy()
        self.applied_heuristics = []
        
        # 1. Nejprve přidáme objekty z prvního příkladu, pokud je model prázdný
        if len(model.objects) == 0:
            self._debug_log("Prázdný model, přidávám objekty z prvního příkladu...")
            updated_model = self._add_missing_objects(updated_model, good)
        
        # 2. Kontrola konzistence - vyriešime konflikty s existujúcimi pravidlami
        self._debug_log("Kontrolujem konzistenciu s hierarchiou...")
        updated_model = self._check_consistency(updated_model, good)
        
        # 3. Climb-tree - důležitá heuristika pro generalizaci
        self._debug_log("Skúšam climb-tree heuristiku...")
        updated_model = self._apply_climb_tree(updated_model, good, near_miss)
            
        # 4. Require-link - přidá MUST spojení, pokud jsou v positive example
        self._debug_log("Skúšam require-link heuristiku...")
        updated_model = self._apply_require_link(updated_model, good, near_miss)
        
        # 5. Close-interval - zúžení intervalu numerických atributů
        # COMMENTED OUT: Not a core Winston heuristic
        # self._debug_log("Skúšam close-interval heuristiku...")
        # updated_model = self._apply_close_interval(updated_model, good, near_miss)
        
        # 6. Enlarge-set - rozšíření množiny přijatelných hodnot atributů
        # COMMENTED OUT: Not a core Winston heuristic
        self._debug_log("Skúšam enlarge-set heuristiku...")
        updated_model = self._apply_enlarge_set(updated_model, good)
        
        # 7. Propagace vlastností na nejvyšší úroveň hierarchie
        # COMMENTED OUT: Not a core Winston heuristic
        # updated_model = self._propagate_to_common_ancestor(updated_model)
            
        # 8. Forbid-link - identifikuje, co by objekt neměl mít
        if near_miss:
            self._debug_log("Skúšam forbid-link heuristiku...")
            updated_model = self._apply_forbid_link(updated_model, good, near_miss)
            
        # 9. Drop-link - nejnižší priorita, odstraní nepotřebné vazby
        if not self.applied_heuristics:
            self._debug_log("Skúšam drop-link heuristiku...")
            updated_model = self._apply_drop_link(updated_model, good, near_miss)
        
        # 10. BackUp Rule - kontrola, zda nové změny nezhoršily přesnost modelu
        # COMMENTED OUT: Not a core Winston heuristic
        # updated_model = self._apply_backup_rule(updated_model, good, near_miss)
        
        # Výpis aplikovaných heuristík
        if self.applied_heuristics:
            self._debug_log(f"Aplikované heuristiky: {', '.join(self.applied_heuristics)}")
        else:
            self._debug_log("Žiadna heuristika nebola aplikovaná")
            
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

    def _apply_enlarge_set(self, model: Model, good: Model) -> Model:
        """
        Aplikuje enlarge-set heuristiku.
        
        Heuristika sa používa keď objekt vo vyvíjajúcom sa modeli zodpovedá inému objektu v príklade
        a tieto dva objekty nie sú navzájom prepojené prostredníctvom klasifikačného stromu.
        Vytvorí množinu prijateľných hodnôt z atribútov objektov.
        
        Príklad: Ak BMW môže mať motor s výkonom 230 alebo 250, vytvorí sa množina {230, 250}
        ako prijateľné hodnoty pre atribút výkonu motora.
        
        Args:
            model: Aktuálny model
            good: Pozitívny príklad
            
        Returns:
            Aktualizovaný model
        """
        updated_model = model.copy()
        
        # 1. Zbieranie hodnôt atribútov podľa tried objektov
        class_attributes = {}
        
        print(f"Applying enlarge-set heuristic")
        
        # Najprv zozbierame hodnoty atribútov z existujúceho modelu
        for model_obj in updated_model.objects:
            if not model_obj.attributes:
                continue
                
            class_name = model_obj.class_name
            if class_name not in class_attributes:
                class_attributes[class_name] = {}
                
            for attr_name, attr_value in model_obj.attributes.items():
                if attr_name not in class_attributes[class_name]:
                    class_attributes[class_name][attr_name] = set()
                    
                # Ak hodnota je už množina, pridáme všetky jej prvky
                if isinstance(attr_value, set):
                    class_attributes[class_name][attr_name].update(attr_value)
                    print(f"  Found existing set for {class_name}.{attr_name}: {attr_value}")
                # Ak je to interval, extrahujeme hodnoty
                elif isinstance(attr_value, tuple) and len(attr_value) == 2:
                    # Zistíme či ide o atribút, ktorý by mal byť diskrétny (cylinders)
                    if attr_name in ["cylinders"]:
                        # Pre cylinders použijeme celočíselné hodnoty z intervalu
                        min_val, max_val = attr_value
                        for val in range(int(min_val), int(max_val) + 1):
                            class_attributes[class_name][attr_name].add(val)
                        print(f"  Converted interval {attr_value} to discrete values for {class_name}.{attr_name}: {class_attributes[class_name][attr_name]}")
                    else:
                        # Pre ostatné atribúty použijeme interval ako je
                        class_attributes[class_name][attr_name].add(attr_value)
                        print(f"  Added interval {attr_value} for {class_name}.{attr_name}")
                else:
                    # Inak pridáme hodnotu ako je
                    class_attributes[class_name][attr_name].add(attr_value)
                    print(f"  Added value {attr_value} for {class_name}.{attr_name}")
        
        # 2. Pridáme hodnoty atribútov z pozitívneho príkladu
        for good_obj in good.objects:
            if not good_obj.attributes:
                continue
                
            class_name = good_obj.class_name
            print(f"  Processing attributes from positive example for {class_name}")
            
            if class_name not in class_attributes:
                class_attributes[class_name] = {}
                
            for attr_name, attr_value in good_obj.attributes.items():
                if attr_name not in class_attributes[class_name]:
                    class_attributes[class_name][attr_name] = set()
                
                # Spracujeme všetky typy hodnôt vrátane numerických
                if isinstance(attr_value, set):
                    # Ak je to už množina, pridáme všetky hodnoty
                    class_attributes[class_name][attr_name].update(attr_value)
                    print(f"    Added set values for {attr_name}: {attr_value}")
                elif isinstance(attr_value, tuple) and len(attr_value) == 2:
                    # Ak je to interval, pridáme ho do množiny
                    class_attributes[class_name][attr_name].add(attr_value)
                    print(f"    Added interval for {attr_name}: {attr_value}")
                else:
                    # Pridáme hodnotu do množiny
                    # Špeciálne spracovanie pre numerické atribúty, pre ktoré preferujeme vytvorenie množiny
                    if attr_name in ["cylinders", "power"]:
                        class_attributes[class_name][attr_name].add(attr_value)
                        print(f"    Added numerical value for {attr_name}: {attr_value}")
                    elif isinstance(attr_value, (int, float)):
                        # Ostatné numerické hodnoty pridáme tiež do množiny
                        class_attributes[class_name][attr_name].add(attr_value)
                        print(f"    Added numerical value for {attr_name}: {attr_value}")
                    else:
                        # Nenumerické hodnoty pridáme tiež
                        class_attributes[class_name][attr_name].add(attr_value)
                        print(f"    Added value for {attr_name}: {attr_value}")
                
        # 3. Aplikácia zozbieraných množín hodnôt naspäť do modelu
        heuristic_applied = False
        
        for model_obj in updated_model.objects:
            class_name = model_obj.class_name
            
            # Ak pre túto triedu nemáme zozbierané atribúty, preskočíme
            if class_name not in class_attributes:
                continue
                
            if not model_obj.attributes:
                model_obj.attributes = {}
            
            print(f"  Updating attributes for {model_obj.name} of class {class_name}")
                
            # Pre každý atribút, ktorý máme pre túto triedu
            for attr_name, values_set in class_attributes[class_name].items():
                # Ak máme viac ako jednu hodnotu, vytvoríme množinu
                if len(values_set) > 1:
                    # Špeciálne spracovanie pre niektoré numerické atribúty
                    if attr_name in ["cylinders", "power"]:
                        # Skontrolujeme, či všetky hodnoty sú čísla
                        all_numeric = all(isinstance(val, (int, float)) for val in values_set)
                        if all_numeric:
                            # Vytvoríme množinu numerických hodnôt
                            model_obj.attributes[attr_name] = values_set
                            heuristic_applied = True
                            print(f"    Created set of values for {attr_name}: {values_set}")
                            self._debug_log(f"Vytvorená množina hodnôt pre numerický atribút {attr_name} triedy {class_name}: {values_set}")
                        else:
                            # Ak máme zmiešané hodnoty, ponecháme pôvodné
                            print(f"    Mixed values for {attr_name}, skipping")
                    else:
                        # Pre ostatné atribúty štandardné spracovanie
                        current_value = model_obj.attributes.get(attr_name)
                        
                        # Ak aktuálna hodnota nie je množina, aktualizujeme ju
                        if not isinstance(current_value, set):
                            model_obj.attributes[attr_name] = values_set
                            heuristic_applied = True
                            print(f"    Created set of values for {attr_name}: {values_set}")
                            self._debug_log(f"Vytvorená množina hodnôt pre atribút {attr_name} triedy {class_name}: {values_set}")
                        # Ak už máme množinu, skontrolujeme, či treba pridať nové hodnoty
                        elif current_value != values_set:
                            # Pridáme chýbajúce hodnoty
                            missing_values = values_set - current_value
                            if missing_values:
                                current_value.update(missing_values)
                                heuristic_applied = True
                                print(f"    Extended set for {attr_name} with: {missing_values}")
                                self._debug_log(f"Rozšírená množina hodnôt atribútu {attr_name} pre triedu {class_name} o {missing_values}")
                # Ak máme len jednu hodnotu a atribút ešte neexistuje, pridáme ho
                elif len(values_set) == 1 and attr_name not in model_obj.attributes:
                    model_obj.attributes[attr_name] = next(iter(values_set))
                    heuristic_applied = True
                    print(f"    Added new attribute {attr_name} = {next(iter(values_set))}")
                    self._debug_log(f"Pridaný nový atribút {attr_name} s hodnotou {next(iter(values_set))} pre objekt triedy {class_name}")
        
        # 4. Osobitné spracovanie pre možnosti ekvivalentných komponentov (napr. rôzne typy motorov)
        # Zbierame komponenty podľa nadradených tried
        component_classes_by_parent = {}
        
        # Nájdeme všetky komponenty v modeli a príklade
        for obj in updated_model.objects + good.objects:
            # Získame rodičovskú triedu
            parent_class = self.classification_tree.get_parent(obj.class_name)
            
            # Ak nemá rodiča, preskočíme
            if not parent_class:
                continue
                
            # Pridáme triedu komponenty pod jej rodiča
            if parent_class not in component_classes_by_parent:
                component_classes_by_parent[parent_class] = set()
                
            component_classes_by_parent[parent_class].add(obj.class_name)
        
        # Ak máme viac ako jeden typ komponentu pre rodičovskú triedu, vytvoríme pravidlo
        for parent_class, subclasses in component_classes_by_parent.items():
            if len(subclasses) > 1:
                print(f"  Found equivalent components for {parent_class}: {subclasses}")
                self._debug_log(f"Nájdené ekvivalentné komponenty pre triedu {parent_class}: {subclasses}")
                
                # Pre každý objekt v modeli, ktorý má MUST spojenie s touto komponentou
                for link in updated_model.links:
                    if link.link_type == LinkType.MUST and link.target == parent_class:
                        source_class = link.source
                        
                        # Pre každý objekt tejto triedy aktualizujeme informáciu o povolených podtriedach
                        for obj in updated_model.objects:
                            if obj.class_name == source_class:
                                if not obj.attributes:
                                    obj.attributes = {}
                                    
                                # Vytvoríme alebo aktualizujeme atribút allowed_components
                                attr_name = f"allowed_{parent_class.lower()}_types"
                                
                                if attr_name not in obj.attributes or not isinstance(obj.attributes[attr_name], set):
                                    obj.attributes[attr_name] = subclasses
                                    heuristic_applied = True
                                    print(f"    Created set of allowed components {attr_name} = {subclasses}")
                                    self._debug_log(f"Vytvorená množina povolených komponentov {attr_name} pre triedu {source_class}: {subclasses}")
                                elif subclasses - obj.attributes[attr_name]:
                                    obj.attributes[attr_name].update(subclasses)
                                    heuristic_applied = True
                                    print(f"    Extended set of allowed components {attr_name}")
                                    self._debug_log(f"Rozšírená množina povolených komponentov {attr_name} pre triedu {source_class}")
        
        if heuristic_applied:
            self.applied_heuristics.append("enlarge_set")
            
        return updated_model

    def _apply_close_interval(self, model: Model, good: Model, near_miss: Model = None) -> Model:
        """
        POZNÁMKA: Táto metóda je dočasne zakomentovaná, pretože jej funkcionalitu preberá _apply_enlarge_set,
        ktorá efektívnejšie spracováva numerické hodnoty pre atribúty ako power a cylinders.
        
        Args:
            model: Aktuálný model
            good: Pozitívny príklad
            near_miss: Negativní příklad (volitelný)
            
        Returns:
            Aktualizovaný model bez zmien (prejde priamo na _apply_enlarge_set)
        """
        # Vrátime model bez zmien, pretože numerické hodnoty spracováva _apply_enlarge_set
        return model

    def _apply_backup_rule(self, model: Model, good: Model, near_miss: Model = None) -> Model:
        """
        Implementuje BackUp Rule heuristiku.
        
        Pokud aktuální model není kompatibilní s pozitivním příkladem nebo je příliš kompatibilní s negativním,
        vrátí se k předchozí verzi modelu, která byla lepší.
        
        Args:
            model: Aktuální model po aplikaci všech heuristik
            good: Pozitivní příklad
            near_miss: Negativní příklad (volitelný)
            
        Returns:
            Původní model, pokud je lepší než aktuální, jinak aktuální model
        """
        # Pokud nemáme historii nebo je prázdná, není k čemu se vracet
        if not self.model_history or len(self.model_history) == 0:
            return model
        
        # Zkontrolujeme, zda aktuální model správně klasifikuje pozitivní příklad
        is_good_valid = self._is_example_valid(model, good)
        
        # Zkontrolujeme, zda aktuální model správně vylučuje near-miss příklad (pokud existuje)
        is_nearmiss_invalid = True
        if near_miss:
            is_nearmiss_invalid = not self._is_example_valid(model, near_miss)
        
        # Pokud model správně klasifikuje pozitivní i negativní příklad, je v pořádku
        if is_good_valid and is_nearmiss_invalid:
            return model
        
        # Pokud máme problém, zkusíme najít lepší model v historii
        best_model = None
        
        for historical_model in reversed(self.model_history):
            # Zkontrolujeme, zda historický model správně klasifikuje příklady
            hist_good_valid = self._is_example_valid(historical_model, good)
            
            hist_nearmiss_invalid = True
            if near_miss:
                hist_nearmiss_invalid = not self._is_example_valid(historical_model, near_miss)
            
            # Pokud historický model je lepší, vrátíme se k němu
            if hist_good_valid and hist_nearmiss_invalid:
                best_model = historical_model
                self.applied_heuristics.append("backup_rule")
                self._debug_log("Aplikována BackUp Rule: návrat k předchozímu lepšímu modelu")
                break
        
        # Vrátíme lepší model, nebo ponecháme současný, pokud žádný lepší nebyl nalezen
        return best_model if best_model else model

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
                            if target_obj and (target_obj.class_name == link.target or 
                                               self.classification_tree.is_subclass(target_obj.class_name, link.target)):
                                has_target = True
                                break
                    
                    if not has_target:
                        return False
        
        # Kontrola, zda příklad neobsahuje zakázané MUST_NOT vazby
        for link in model.links:
            if link.link_type == LinkType.MUST_NOT:
                source_objects = [obj for obj in example.objects if obj.class_name == link.source]
                
                for source_obj in source_objects:
                    for example_link in example.links:
                        if example_link.source == source_obj.name:
                            target_obj = next((obj for obj in example.objects if obj.name == example_link.target), None)
                            if target_obj and (target_obj.class_name == link.target or 
                                               self.classification_tree.is_subclass(target_obj.class_name, link.target)):
                                return False
        
        # Kontrola atributů - pro každý objekt v modelu s definovanými atributy
        for model_obj in model.objects:
            if not model_obj.attributes:
                continue
                
            # Najdeme odpovídající objekty ve příkladu
            for example_obj in example.objects:
                if example_obj.class_name == model_obj.class_name:
                    # Kontrola numerických intervalů
                    for attr_name, model_value in model_obj.attributes.items():
                        if isinstance(model_value, tuple) and len(model_value) == 2:
                            # Je to interval
                            min_val, max_val = model_value
                            
                            # Pokud příklad má tento atribut, zkontrolujeme, zda hodnota je v intervalu
                            if example_obj.attributes and attr_name in example_obj.attributes:
                                example_value = example_obj.attributes[attr_name]
                                if isinstance(example_value, (int, float)) and (example_value < min_val or example_value > max_val):
                                    return False
                        
                        # Kontrola množin hodnot
                        elif isinstance(model_value, set):
                            # Je to množina přijatelných hodnot
                            if example_obj.attributes and attr_name in example_obj.attributes:
                                example_value = example_obj.attributes[attr_name]
                                if example_value not in model_value:
                                    return False
        
        # Pokud všechny kontroly prošly, příklad je platný
        return True

    def _propagate_to_common_ancestor(self, model: Model) -> Model:
        """
        Nová metoda pro propagaci pravidel na nejvyšší společný předek.
        Pokud mají třídy stejné pravidlo, pokusí se ho propagovat na jejich společné předky.
        
        Args:
            model: Aktuální model
            
        Returns:
            Aktualizovaný model s pravidly propagovanými na vyšší úroveň
        """
        updated_model = model.copy()
        
        # Najdeme všechny třídy, které mají MUST vazby
        classes_with_must = {}
        for link in model.links:
            if link.link_type == LinkType.MUST:
                if link.source not in classes_with_must:
                    classes_with_must[link.source] = []
                classes_with_must[link.source].append(link.target)
        
        # Pro každou dvojici tříd zkontrolujeme, zda mají stejné MUST vazby
        common_rules = {}
        for class1 in classes_with_must:
            for class2 in classes_with_must:
                if class1 != class2:
                    # Najdeme společného předka obou tříd
                    common_ancestor = self.classification_tree.find_common_ancestor(class1, class2)
                    if common_ancestor:
                        # Najdeme společné MUST vazby
                        common_targets = set(classes_with_must[class1]) & set(classes_with_must[class2])
                        for target in common_targets:
                            if common_ancestor not in common_rules:
                                common_rules[common_ancestor] = set()
                            common_rules[common_ancestor].add(target)
        
        # Přidáme pravidla na společné předky
        for ancestor, targets in common_rules.items():
            for target in targets:
                # Zkontrolujeme, zda pravidlo už neexistuje
                if not any(link.source == ancestor and link.target == target and link.link_type == LinkType.MUST 
                         for link in updated_model.links):
                    # Přidáme nové pravidlo
                    new_link = Link(
                        source=ancestor,
                        target=target,
                        link_type=LinkType.MUST
                    )
                    updated_model.add_link(new_link)
                    self.applied_heuristics.append("propagate_to_common_ancestor")
                    self._debug_log(f"Propagováno pravidlo na společného předka: {ancestor} MUST {target}")
        
        return updated_model

    def _check_consistency(self, model: Model, good: Model) -> Model:
        """
        Kontroluje, zda nový pozitivní příklad není v konfliktu s existujícími pravidly.
        Pokud konflikt najde, buď odstraní pravidlo nebo ho zobecní.
        
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
            self.applied_heuristics.append("resolve_conflict")
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
                    self.applied_heuristics.append("generalize_conflict")
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

    def _apply_require_link(self, model: Model, good: Model, near_miss: Model):
        """
        Aplikuje require-link heuristiku.
        
        Ak je v pozitívnom príklade spojenie, ktoré chýba v near-miss príklade,
        pridá ho ako požiadavku MUST.
        
        Args:
            model: Aktuálny model
            good: Pozitívny príklad
            near_miss: Near-miss príklad
            
        Returns:
            Aktualizovaný model
        """
        updated_model = model.copy()
        
        # Skip if no near-miss
        if near_miss is None:
            self._debug_log("Přeskakuji require-link: chybí near-miss příklad")
            return updated_model
        
        # Najprv skontrolujeme, či sú v modeli spojenia typu REGULAR, ktoré by sme mali 
        # previesť na MUST na základe rozdielov medzi good a near_miss
        for good_link in good.links:
            # Nájdeme zodpovedajúce objekty v positive
            good_source = next((obj for obj in good.objects if obj.name == good_link.source), None)
            good_target = next((obj for obj in good.objects if obj.name == good_link.target), None)
            
            if not good_source or not good_target:
                continue
                
            # Skontrolujme, či rovnaké triedy objektov majú spojenie v near_miss
            near_miss_has_similar_link = False
            
            for near_miss_link in near_miss.links:
                near_miss_source = next((obj for obj in near_miss.objects if obj.name == near_miss_link.source), None)
                near_miss_target = next((obj for obj in near_miss.objects if obj.name == near_miss_link.target), None)
                
                if not near_miss_source or not near_miss_target:
                    continue
                    
                # Ak je spojenie medzi objektami rovnakých typov, evidujeme to
                if (near_miss_source.class_name == good_source.class_name and
                    near_miss_target.class_name == good_target.class_name):
                    near_miss_has_similar_link = True
                    break
            
            # Ak spojenie není v near_miss příkladu, může jít o klíčovú vazbu
            if not near_miss_has_similar_link:
                # Zkontrolujeme, zda existující MUST_NOT konflikty
                has_conflict = False
                for link in updated_model.links:
                    if (link.link_type == LinkType.MUST_NOT and
                        link.source == good_source.class_name and
                        link.target == good_target.class_name):
                        has_conflict = True
                        self._debug_log(f"Přeskakuji MUST pravidlo kvůli konfliktu: {good_source.class_name} -> {good_target.class_name}")
                        break
                
                if not has_conflict:
                    # Vytvoříme generické pravidlo typu MUST mezi třídami
                    must_link = Link(
                        source=good_source.class_name,
                        target=good_target.class_name,
                        link_type=LinkType.MUST
                    )
                    
                    # Skontrolujeme, či pravidlo ešte nie je v modeli
                    if not any(link.source == must_link.source and 
                               link.target == must_link.target and 
                               link.link_type == must_link.link_type 
                               for link in updated_model.links):
                        updated_model.add_link(must_link)
                        self.applied_heuristics.append("require_link")
                        self._debug_log(f"Pridané pravidlo MUST: {good_source.class_name} -> {good_target.class_name}")
                
                # Pridáme tiež väzbu na úrovni konkrétnych objektov, ak ešte neexistuje
                inst_link = Link(
                    source=good_link.source,
                    target=good_link.target,
                    link_type=LinkType.MUST
                )
                
                if not updated_model.has_link(inst_link):
                    updated_model.add_link(inst_link)
                    self.applied_heuristics.append("require_link")
                    self._debug_log(f"Pridaná MUST väzba na úrovni objektov: {good_link.source} -> {good_link.target}")
        
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

    def _apply_forbid_link(self, model: Model, good: Model, near_miss: Model):
        """
        Aplikuje forbid-link heuristiku.
        
        Vytváří MUST_NOT vazby mezi třídami objektů v modelu na základě
        porovnání pozitivního a near-miss příkladu.
        
        Args:
            model: Aktuálný model
            good: Pozitívny príklad
            near_miss: Near-miss príklad
            
        Returns:
            Aktualizovaný model
        """
        updated_model = model.copy()
        
        # Safety check
        if near_miss is None:
            self._debug_log("Přeskakuji forbid-link: chybí near-miss příklad")
            return updated_model
        
        self._debug_log(f"Applying forbid-link heuristic")
        
        # 1. Získáme klasifikaci aut z pozitivního a negativního příkladu
        good_car_classes = set()
        near_miss_car_classes = set()
        
        for obj in good.objects:
            if obj.class_name in ["Series3", "Series5", "Series7", "X5", "X7"]:
                good_car_classes.add(obj.class_name)
        
        for obj in near_miss.objects:
            if obj.class_name in ["Series3", "Series5", "Series7", "X5", "X7"]:
                near_miss_car_classes.add(obj.class_name)
        
        # Pokud pozitivní a negativní příklad mají stejnou třídu auta,
        # můžeme porovnat jejich komponenty a vytvořit MUST_NOT vazby
        common_car_classes = good_car_classes.intersection(near_miss_car_classes)
        
        if not common_car_classes:
            self._debug_log("Přeskakuji forbid-link: pozitivní a negativní příklad nemají společnou třídu auta")
            return updated_model
        
        # 2. Pro každou třídu auta, která je společná pro oba příklady
        for car_class in common_car_classes:
            # Zkusíme najít konkrétnější rozdíl
            specific_difference = self._find_specific_difference(updated_model, car_class, good, near_miss)
            
            if specific_difference:
                source_class, target_class = specific_difference
                
                # Zkontrolujeme, zda je pravidlo konzistentní
                if self._is_rule_consistent(updated_model, source_class, target_class, LinkType.MUST_NOT):
                    must_not_link = Link(
                        source=source_class,
                        target=target_class,
                        link_type=LinkType.MUST_NOT
                    )
                    
                    # Ověříme, že taková vazba ještě neexistuje
                    if not any(link.source == must_not_link.source and 
                            link.target == must_not_link.target and 
                            link.link_type == must_not_link.link_type 
                            for link in updated_model.links):
                        updated_model.add_link(must_not_link)
                        self.applied_heuristics.append("forbid_link")
                        self._debug_log(f"Přidáno pravidlo MUST_NOT (konkrétní rozdíl): {source_class} -> {target_class}")
                        
                # Pokračujeme dalším modelem, už jsme přidali konkrétní pravidlo
                continue
            
            # Získáme komponenty z negativního příkladu, které se nevyskytují v pozitivním příkladu
            near_miss_components = {}
            good_components = {}
            
            # Mapování komponent podle třídy
            for obj in near_miss.objects:
                if obj.class_name not in ["Series3", "Series5", "Series7", "X5", "X7"]:
                    near_miss_components[obj.class_name] = obj.name
            
            for obj in good.objects:
                if obj.class_name not in ["Series3", "Series5", "Series7", "X5", "X7"]:
                    good_components[obj.class_name] = obj.name
            
            # Komponenty, které jsou v negativním příkladu, ale ne v pozitivním
            unique_component_classes = set(near_miss_components.keys()) - set(good_components.keys())
            
            self._debug_log(f"Unique components in near-miss: {unique_component_classes}")
            
            # 3. Kontrola konzistence s aktuálním modelem a přidání MUST_NOT vazeb
            for component_class in unique_component_classes:
                # Zkontrolujeme, zda neexistují jiné pozitivní příklady nebo pravidla v modelu,
                # které by mohly být v konfliktu s tímto pravidlem
                if self._is_rule_consistent(updated_model, car_class, component_class, LinkType.MUST_NOT):
                    must_not_link = Link(
                        source=car_class,
                        target=component_class,
                        link_type=LinkType.MUST_NOT
                    )
                    
                    # Ověříme, že taková vazba ještě neexistuje
                    if not any(link.source == must_not_link.source and 
                            link.target == must_not_link.target and 
                            link.link_type == must_not_link.link_type 
                            for link in updated_model.links):
                        updated_model.add_link(must_not_link)
                        self.applied_heuristics.append("forbid_link")
                        self._debug_log(f"Přidáno pravidlo MUST_NOT: {car_class} -> {component_class}")
        
        # 4. Analyzujeme vazby mezi objekty a vytvoříme další MUST_NOT vazby, ale s kontrolou konzistence
        for near_miss_link in near_miss.links:
            near_miss_source = next((obj for obj in near_miss.objects if obj.name == near_miss_link.source), None)
            near_miss_target = next((obj for obj in near_miss.objects if obj.name == near_miss_link.target), None)
            
            if not near_miss_source or not near_miss_target:
                continue
            
            # Pokud zdroj je model auta a cíl je komponenta
            if near_miss_source.class_name in ["Series3", "Series5", "Series7", "X5", "X7"] and \
               near_miss_target.class_name not in ["Series3", "Series5", "Series7", "X5", "X7"]:
                
                # Kontrolujeme, zda existuje podobná vazba v pozitivním příkladu
                has_similar_in_good = False
                for good_link in good.links:
                    good_source = next((obj for obj in good.objects if obj.name == good_link.source), None)
                    good_target = next((obj for obj in good.objects if obj.name == good_link.target), None)
                    
                    if good_source and good_target and \
                       good_source.class_name == near_miss_source.class_name and \
                       good_target.class_name == near_miss_target.class_name:
                        has_similar_in_good = True
                        break
                
                # Pokud neexistuje podobná vazba v pozitivním příkladu, vytvoříme MUST_NOT vazbu (s kontrolou konzistence)
                if not has_similar_in_good and self._is_rule_consistent(updated_model, near_miss_source.class_name, near_miss_target.class_name, LinkType.MUST_NOT):
                    must_not_link = Link(
                        source=near_miss_source.class_name,
                        target=near_miss_target.class_name,
                        link_type=LinkType.MUST_NOT
                    )
                    
                    # Ověříme, že taková vazba ještě neexistuje
                    if not any(link.source == must_not_link.source and 
                               link.target == must_not_link.target and 
                               link.link_type == must_not_link.link_type 
                               for link in updated_model.links):
                        updated_model.add_link(must_not_link)
                        self.applied_heuristics.append("forbid_link")
                        self._debug_log(f"Přidáno pravidlo MUST_NOT z vazeb: {near_miss_source.class_name} -> {near_miss_target.class_name}")
        
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
    
    def _apply_drop_link(self, model: Model, good: Model, near_miss: Model):
        """
        Aplikuje drop-link heuristiku.
        
        Odstráni z modelu spojenia, ktoré nie sú v pozitívnom príklade.
        Nižší priorita - použije se jen když není nic lepšího.
        
        Args:
            model: Aktuálný model
            good: Pozitívny príklad
            near_miss: Near-miss príklad
            
        Returns:
            Aktualizovaný model
        """
        updated_model = model.copy()
        
        # Sledujeme, zda byla heuristika aplikována
        was_applied = False
        
        # Nájdeme všetky REGULAR spojenia v modeli
        regular_links = [link for link in updated_model.links 
                         if link.link_type == LinkType.REGULAR]
        
        # Pro každou vazbu v modelu zkontrolujeme, zda je v pozitivním příkladu
        links_to_remove = []
        
        for model_link in regular_links:
            # Zjistíme, zda existuje odpovídající spojení v pozitivním příkladu
            has_corresponding = False
            
            for good_link in good.links:
                if model_link.source == good_link.source and model_link.target == good_link.target:
                    has_corresponding = True
                    break
                    
            # Pokud není odpovídající spojení, označíme ho k odstranění
            if not has_corresponding:
                links_to_remove.append(model_link)
                
        # Teď odstráníme označené spojení, ale nejprve zkontrolujeme generická pravidla
        for link_to_remove in links_to_remove:
            # Najdeme objekty pro tuto vazbu
            source_obj = next((obj for obj in updated_model.objects if obj.name == link_to_remove.source), None)
            target_obj = next((obj for obj in updated_model.objects if obj.name == link_to_remove.target), None)
            
            if source_obj and target_obj:
                # Kontrola, zda existuje generické pravidlo mezi třídami objektů
                has_generic_rule = False
                
                for rule_link in updated_model.links:
                    # Kontrola pravidel typu MUST pro tyto třídy
                    if (rule_link.link_type == LinkType.MUST and 
                        rule_link.source == source_obj.class_name and 
                        (rule_link.target == target_obj.class_name or 
                         self.classification_tree.is_subclass(target_obj.class_name, rule_link.target))):
                        has_generic_rule = True
                        self._debug_log(f"Ponechávám väzbu {link_to_remove.source} -> {link_to_remove.target} kvůli generickému pravidlu {rule_link.source} -> {rule_link.target}")
                        break
                
                # Pokud není generické pravidlo, můžeme spojení odstranit
                if not has_generic_rule:
                    updated_model.remove_link(link_to_remove)
                    self.applied_heuristics.append("drop_link")
                    was_applied = True
                    self._debug_log(f"Odstránená nepodstatná väzba: {link_to_remove.source} -> {link_to_remove.target}")
        
        # Zajistíme, že je heuristika označena jako aplikovaná, pokud nějaká vazba byla odstraněna
        if was_applied:
            self._debug_log("Drop-link heuristika byla úspěšně aplikována")
            
        return updated_model

    def _apply_climb_tree(self, model: Model, good: Model, near_miss: Model):
        """
        Vylepšená implementace climb-tree heuristiky pro efektivnější generalizaci
        a propagaci vlastností nahoru v hierarchii.
        
        Args:
            model: Aktuálný model
            good: Pozitívny príklad
            near_miss: Near-miss príklad
            
        Returns:
            Aktualizovaný model
        """
        updated_model = model.copy()
        
        # 1. Zpracování near-miss případu - nalezení společného předka pro objekty stejného jména
        if near_miss is not None:
            for good_obj in good.objects:
                for near_miss_obj in near_miss.objects:
                    # Pokud objekty se stejným jménem mají různé třídy, hledáme společného předka
                    if (good_obj.name == near_miss_obj.name and 
                        good_obj.class_name != near_miss_obj.class_name):
                        
                        # Najdeme společného předka v hierarchii
                        common_ancestor = self.classification_tree.find_common_ancestor(
                            good_obj.class_name,
                            near_miss_obj.class_name
                        )
                        
                        if common_ancestor:
                            self._debug_log(f"Nalezen společný předek: {common_ancestor} pro třídy {good_obj.class_name} a {near_miss_obj.class_name}")
                            
                            # Aktualizujeme třídu objektu v modelu
                            for model_obj in updated_model.objects:
                                if model_obj.name == good_obj.name:
                                    model_obj.class_name = common_ancestor
                                    self.applied_heuristics.append("climb_tree")
                                    self._debug_log(f"Aktualizována třída objektu {model_obj.name} na {common_ancestor}")
                                    
                                    # Aktualizujeme i spojení MUST_BE_A
                                    for link in updated_model.links:
                                        if link.source == model_obj.name and link.link_type == LinkType.MUST_BE_A:
                                            link.target = common_ancestor
                                            self._debug_log(f"Aktualizováno MUST_BE_A spojení: {link.source} -> {common_ancestor}")
        
        # 2. Generalizace na základě hierarchie - vytvoření rodičovských vazeb, propagace nahoru
        for good_link in good.links:
            source_obj = next((obj for obj in good.objects if obj.name == good_link.source), None)
            target_obj = next((obj for obj in good.objects if obj.name == good_link.target), None)
            
            if source_obj and target_obj:
                # Zjistíme, zda existují vazby na úrovni rodičovských tříd
                source_parent = self.classification_tree.get_parent(source_obj.class_name)
                target_parent = self.classification_tree.get_parent(target_obj.class_name)
                
                # Vytvoření generických vazeb mezi třídami
                if target_parent and source_obj.class_name:
                    parent_link = Link(
                        source=source_obj.class_name,
                        target=target_parent,
                        link_type=LinkType.MUST
                    )
                    
                    # Přidáme generické pravidlo, pokud ještě neexistuje
                    if not any(l.source == parent_link.source and 
                               l.target == parent_link.target and 
                               l.link_type == parent_link.link_type 
                               for l in updated_model.links):
                        # Zkontrolujeme, zda není v konfliktu s existujícím MUST_NOT
                        has_conflict = any(
                            l.source == parent_link.source and
                            l.target == parent_link.target and
                            l.link_type == LinkType.MUST_NOT
                            for l in updated_model.links
                        )
                        
                        if not has_conflict:
                            updated_model.add_link(parent_link)
                            self.applied_heuristics.append("climb_tree")
                            self._debug_log(f"Přidána generická vazba na rodičovskou třídu: {source_obj.class_name} -> {target_parent}")
                
                # 3. Nově: Propagace pravidel až k Device
                current_source_class = source_obj.class_name
                while current_source_class and current_source_class != "Device":
                    source_parent = self.classification_tree.get_parent(current_source_class)
                    if source_parent and target_parent:
                        # Pokud má nadřazená třída cílové komponenty také nadřazenou třídu, vytvoříme vazbu
                        target_grandparent = self.classification_tree.get_parent(target_parent)
                        if target_grandparent:
                            device_link = Link(
                                source=source_parent,
                                target=target_grandparent,
                                link_type=LinkType.MUST
                            )
                            
                            # Přidáme vazbu, pokud neexistuje
                            if not any(l.source == device_link.source and 
                                       l.target == device_link.target and 
                                       l.link_type == device_link.link_type 
                                       for l in updated_model.links):
                                # Zkontrolujeme konflikt s MUST_NOT
                                has_conflict = any(
                                    l.source == device_link.source and
                                    l.target == device_link.target and
                                    l.link_type == LinkType.MUST_NOT
                                    for l in updated_model.links
                                )
                                
                                if not has_conflict:
                                    updated_model.add_link(device_link)
                                    self.applied_heuristics.append("climb_tree")
                                    self._debug_log(f"Propagována vazba k vyšší úrovni hierarchie: {source_parent} -> {target_grandparent}")
                    
                    # Posun nahoru v hierarchii
                    current_source_class = source_parent
        
        return updated_model 