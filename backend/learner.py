from backend.model import Model, Link, LinkType, ClassificationTree, Object
from typing import List, Dict, Set, Tuple, Optional, Any
import traceback
from datetime import datetime
import time
import copy
import uuid

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
        
        # História pozitívnych a negatívnych príkladov - pridané pre sekvenčné spracovanie
        self.positive_examples = []  # Zoznam pozitívnych príkladov
        self.negative_examples = []  # Zoznam negatívnych príkladov
        
        # Inicializácia modelu a histórie trénovania
        self.model = Model()
        self.training_history = []  # História trénovania s aplikovanými heuristikami a modelmi
    
    def _debug_log(self, message):
        """Debugovacie logovanie pre sledovanie priebehu algoritmu."""
        if self.debug_enabled:
            print(f"[WinstonLearner] {message}")

    def update_model(self, example: Model, is_positive: bool) -> Dict:
        """
        Aktualizuje model na základe nového príkladu.

        Args:
            example: Nový príklad
            is_positive: True ak je príklad pozitívny, False ak je negatívny

        Returns:
            Dict obsahujúci aktualizovaný model, história a informácia o aplikovaných heuristikách
        """
        # Inicializujeme zoznam aplikovaných heuristík pre tento príklad
        self.applied_heuristics = []
        
        # Predpokladáme, že žiadna heuristika nebude aplikovaná
        was_applied = False
        updated_model = self.model.copy()
        
        # Logging pre typ príkladu
        example_type = "positive" if is_positive else "negative"
        self._debug_log(f"Updating model with {example_type} example")
        
        # Špeciálny prípad: prázdny model
        if not updated_model.objects or all(obj is None for obj in updated_model.objects):
            self._debug_log("Prázdny model, pokúšam sa aplikovať add_missing_objects")
            if is_positive:
                updated_model, was_applied = self._add_missing_objects_sequential(updated_model, example, is_positive)
                if was_applied:
                    self._debug_log("Prázdny model bol inicializovaný pomocou add_missing_objects")
        else:
            # Bežné spracovanie pre existujúci model
            self._debug_log(f"Spracovávam {'pozitívny' if is_positive else 'negatívny'} príklad")
            
            # Pre pozitívne príklady:
            if is_positive:
                # 1. add_missing_objects - pridáme nové objekty do modelu
                self._debug_log("Skúšam add_missing_objects heuristiku...")
                updated_model, was_applied = self._add_missing_objects_sequential(updated_model, example, is_positive)
                
                # 2. climb_tree - spracovanie hierarchie tried
                if not was_applied:
                    self._debug_log("Skúšam climb_tree heuristiku...")
                    updated_model, was_applied = self._apply_climb_tree_sequential(updated_model, example, is_positive)
                
                # 3. enlarge_set - rozšírenie množiny hodnôt
                if not was_applied:
                    self._debug_log("Skúšam enlarge_set heuristiku...")
                    updated_model, was_applied = self._apply_enlarge_set_sequential(updated_model, example, is_positive)
                
                # 4. close_interval - spracovanie numerických atribútov
                if not was_applied:
                    self._debug_log("Skúšam close_interval heuristiku...")
                    updated_model, was_applied = self._apply_close_interval_sequential(updated_model, example, is_positive)
            else:
                # Pre negatívne príklady:
                
                # 1. require_link - identifikácia povinných spojení
                self._debug_log("Skúšam require_link heuristiku...")
                updated_model, was_applied = self._apply_require_link_sequential(updated_model, example, is_positive)
                
                # 2. forbid_link - identifikácia zakázaných spojení
                if not was_applied:
                    self._debug_log("Skúšam forbid_link heuristiku...")
                    updated_model, was_applied = self._apply_forbid_link_sequential(updated_model, example, is_positive)
                
                # 3. close_interval - spracovanie numerických atribútov
                if not was_applied:
                    self._debug_log("Skúšam close_interval heuristiku...")
                    updated_model, was_applied = self._apply_close_interval_sequential(updated_model, example, is_positive)
        
        # Aktualizujeme model len ak bola aplikovaná aspoň jedna heuristika
        if was_applied:
            self.model = updated_model
            
            # Pridáme príklad do histórie
            if is_positive:
                self.positive_examples.append(example)
            else:
                self.negative_examples.append(example)
                
            # Zaznamenáme použité heuristiky
            self._debug_log(f"Aplikované heuristiky: {self.applied_heuristics}")
        else:
            self._debug_log("Žiadna heuristika nebola aplikovaná, model zostáva nezmenený")
            
        # Aktualizujeme stav modelu
        self.training_steps += 1
        
        # Vytvoríme a vrátime záznam o aktualizácii
        result = {
            "model": updated_model.to_dict(),
            "was_model_updated": was_applied,
            "applied_heuristics": self.applied_heuristics,
            "training_steps": self.training_steps
        }
        
        return result

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

    def _apply_close_interval(self, model: Model, good: Model, near_miss: Model = None) -> Model:
        """
        Implementácia close-interval heuristiky.
        
        Heuristika slúži na zistenie povolených rozsahov pre numerické atribúty
        ako je výkon motora alebo počet valcov. Vytvorí interval z minimálnej a
        maximálnej hodnoty, ktoré sú povolené pre daný atribút.
        
        Args:
            model: Aktuálný model
            good: Pozitívny príklad
            near_miss: Negativní příklad (volitelný)
            
        Returns:
            Aktualizovaný model s intervalom hodnôt pre numerické atribúty
        """
        updated_model = model.copy()
        heuristic_applied = False
        
        # Zbieranie numerických hodnôt atribútov podľa tried objektov
        class_numeric_attrs = {}
        
        print(f"Applying close-interval heuristic")
        
        # Najprv zozbierame hodnoty atribútov z existujúceho modelu
        for model_obj in updated_model.objects:
            if not model_obj.attributes:
                continue
                
            class_name = model_obj.class_name
            if class_name not in class_numeric_attrs:
                class_numeric_attrs[class_name] = {}
                
            for attr_name, attr_value in model_obj.attributes.items():
                # Spracovávame len numerické atribúty - kontrolujeme typ hodnoty
                if isinstance(attr_value, (int, float)):
                    if attr_name not in class_numeric_attrs[class_name]:
                        class_numeric_attrs[class_name][attr_name] = []
                    
                    # Pridáme hodnotu priamo
                    class_numeric_attrs[class_name][attr_name].append(attr_value)
                    print(f"  Found numeric value for {class_name}.{attr_name}: {attr_value}")
                # Ak hodnota je už interval, preskočíme ju
                elif isinstance(attr_value, tuple) and len(attr_value) == 2:
                    continue
                # Ak je to množina, pridáme všetky numerické hodnoty
                elif isinstance(attr_value, set):
                    if attr_name not in class_numeric_attrs[class_name]:
                        class_numeric_attrs[class_name][attr_name] = []
                        
                    for val in attr_value:
                        if isinstance(val, (int, float)):
                            class_numeric_attrs[class_name][attr_name].append(val)
                            print(f"  Extracted numeric value from set for {class_name}.{attr_name}: {val}")
        
        # Pridáme hodnoty z pozitívneho príkladu
        for good_obj in good.objects:
            if not good_obj.attributes:
                continue
                
            class_name = good_obj.class_name
            print(f"  Processing attributes from positive example for {class_name}")
            
            if class_name not in class_numeric_attrs:
                class_numeric_attrs[class_name] = {}
                
            for attr_name, attr_value in good_obj.attributes.items():
                # Spracovávame len numerické atribúty - kontrolujeme typ hodnoty
                if isinstance(attr_value, (int, float)):
                    if attr_name not in class_numeric_attrs[class_name]:
                        class_numeric_attrs[class_name][attr_name] = []
                    
                    # Pridáme hodnotu
                    class_numeric_attrs[class_name][attr_name].append(attr_value)
                    print(f"    Added numeric value for {attr_name}: {attr_value}")
                # Ak je to množina, pridáme všetky numerické hodnoty
                elif isinstance(attr_value, set):
                    if attr_name not in class_numeric_attrs[class_name]:
                        class_numeric_attrs[class_name][attr_name] = []
                        
                    for val in attr_value:
                        if isinstance(val, (int, float)):
                            class_numeric_attrs[class_name][attr_name].append(val)
                            print(f"    Extracted numeric value from set for {attr_name}: {val}")
        
        # Vytvorenie intervalov pre jednotlivé numerické atribúty
        for class_name, attrs in class_numeric_attrs.items():
            for attr_name, values in attrs.items():
                if len(values) >= 2:  # Na vytvorenie intervalu potrebujeme aspoň 2 hodnoty
                    min_val = min(values)
                    max_val = max(values)
                    
                    # Vytvoríme interval
                    interval = (min_val, max_val)
                    
                    # Aktualizujeme atribúty všetkých objektov danej triedy
                    for obj in updated_model.objects:
                        if obj.class_name == class_name:
                            if not obj.attributes:
                                obj.attributes = {}
                                
                            # Nastavíme interval pre atribút
                            obj.attributes[attr_name] = interval
                            heuristic_applied = True
                            print(f"Applied close_interval for {class_name}.{attr_name}: {interval}")
                            self._debug_log(f"Vytvorený interval pre atribút {attr_name} triedy {class_name}: {interval}")
                elif len(values) == 1:  # Ak máme len jednu hodnotu, použijeme ju ako je
                    # Aktualizujeme atribúty všetkých objektov danej triedy
                    for obj in updated_model.objects:
                        if obj.class_name == class_name:
                            if not obj.attributes:
                                obj.attributes = {}
                                
                            # Ak atribút neexistuje alebo má inú hodnotu, nastavíme jednu hodnotu
                            current = obj.attributes.get(attr_name)
                            if current is None or (not isinstance(current, tuple) and current != values[0]):
                                obj.attributes[attr_name] = values[0]
                                heuristic_applied = True
                                print(f"Set single numeric value for {class_name}.{attr_name}: {values[0]}")
                                self._debug_log(f"Nastavená jedna číselná hodnota pre atribút {attr_name} triedy {class_name}: {values[0]}")
        
        if heuristic_applied:
            self.applied_heuristics.append("close_interval")
            
        return updated_model

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
        
        # 1. Zbieranie hodnôt atribútov podľa tried objektov (okrem numerických)
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
                # Preskočíme numerické hodnoty, tie spracováva close_interval
                if isinstance(attr_value, (int, float)):
                    continue
                    
                if attr_name not in class_attributes[class_name]:
                    class_attributes[class_name][attr_name] = set()
                    
                # Ak hodnota je už množina, pridáme všetky jej prvky
                if isinstance(attr_value, set):
                    # Pri množinách skontrolujeme, či neobsahujú numerické hodnoty
                    non_numeric_values = {v for v in attr_value if not isinstance(v, (int, float))}
                    if non_numeric_values:
                        class_attributes[class_name][attr_name].update(non_numeric_values)
                        print(f"  Found existing set for {class_name}.{attr_name}: {non_numeric_values}")
                else:
                    # Inak pridáme hodnotu ako je
                    class_attributes[class_name][attr_name].add(attr_value)
                    print(f"  Added value {attr_value} for {class_name}.{attr_name}")
        
        # 2. Pridáme hodnoty atribútov z pozitívneho príkladu (okrem numerických)
        for good_obj in good.objects:
            if not good_obj.attributes:
                continue
                
            class_name = good_obj.class_name
            print(f"  Processing attributes from positive example for {class_name}")
            
            if class_name not in class_attributes:
                class_attributes[class_name] = {}
                
            for attr_name, attr_value in good_obj.attributes.items():
                # Preskočíme numerické hodnoty
                if isinstance(attr_value, (int, float)):
                    continue
                    
                if attr_name not in class_attributes[class_name]:
                    class_attributes[class_name][attr_name] = set()
                
                # Pridáme nenumerické hodnoty do množiny
                if isinstance(attr_value, set):
                    # Pri množinách skontrolujeme, či neobsahujú numerické hodnoty
                    non_numeric_values = {v for v in attr_value if not isinstance(v, (int, float))}
                    if non_numeric_values:
                        class_attributes[class_name][attr_name].update(non_numeric_values)
                        print(f"    Added set values for {attr_name}: {non_numeric_values}")
                else:
                    # Pridáme hodnotu do množiny
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
                    # Pre všetky atribúty štandardné spracovanie - numerické by tu už nemali byť
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

    def _add_missing_objects_sequential(self, model: Model, example: Model, is_positive: bool) -> (Model, bool):
        """
        Sekvenčná implementácia heuristiky add-missing-objects.
        
        Táto heuristika sa aplikuje na pozitívne príklady a pridáva objekty a spojenia,
        ktoré ešte nie sú v modeli. Používa sa najmä pre inicializáciu modelu alebo 
        pridanie nových komponentov.
        
        Args:
            model: Aktuálny model
            example: Spracovávaný príklad
            is_positive: True ak je príklad pozitívny, False ak je negatívny
            
        Returns:
            (updated_model, was_applied) - Aktualizovaný model a indikátor, či bola heuristika aplikovaná
        """
        updated_model = model.copy()
        was_applied = False
        
        # Táto heuristika sa aplikuje len na pozitívne príklady
        if not is_positive:
            return updated_model, was_applied
            
        self._debug_log(f"Applying add-missing-objects heuristic on positive example")
        
        # 1. Prípad: model je prázdny, pridáme všetky objekty z príkladu
        if not model.objects or all(obj is None for obj in model.objects):
            self._debug_log(f"Prázdny model, inicializujem ho objektami z príkladu")
            
            for obj in example.objects:
                if obj is None:
                    continue
                    
                # Vytvoríme nový objekt rovnakej triedy
                new_obj = Object(
                    name=obj.class_name,  # Používame triedu ako meno objektu v modeli
                    class_name=obj.class_name,
                    attributes=obj.attributes.copy() if obj.attributes else None
                )
                updated_model.add_object(new_obj)
                
            # Pridáme aj spojenia
            for link in example.links:
                if link is None:
                    continue
                    
                # Získame triedy objektov
                source_obj = next((obj for obj in example.objects if obj is not None and obj.name == link.source), None)
                target_obj = next((obj for obj in example.objects if obj is not None and obj.name == link.target), None)
                
                if not source_obj or not target_obj:
                    continue
                    
                # Vytvoríme nové spojenie medzi triedami
                new_link = Link(
                    source=source_obj.class_name,
                    target=target_obj.class_name,
                    link_type=link.link_type
                )
                updated_model.add_link(new_link)
                
            was_applied = True
            self.applied_heuristics.append("add_missing_objects")
            self._debug_log(f"Add-missing-objects: Inicializovaný model objektami a spojeniami z príkladu")
            return updated_model, True
            
        # 2. Prípad: model už obsahuje objekty, ale chýbajú niektoré z príkladu
        # Získame triedy, ktoré už máme v modeli
        model_classes = {obj.class_name for obj in updated_model.objects if obj is not None}
        
        # Kontrola nových tried v príklade, ktoré ešte nie sú v modeli
        for example_obj in example.objects:
            if example_obj is None:
                continue
                
            # Ak trieda ešte nie je v modeli, pridáme ju
            if example_obj.class_name not in model_classes:
                new_obj = Object(
                    name=example_obj.class_name,  # Používame triedu ako meno objektu v modeli
                    class_name=example_obj.class_name,
                    attributes=example_obj.attributes.copy() if example_obj.attributes else None
                )
                updated_model.add_object(new_obj)
                was_applied = True
                self.applied_heuristics.append("add_missing_objects")
                self._debug_log(f"Add-missing-objects: Pridaný nový objekt triedy {example_obj.class_name}")
                
        # 3. Prípad: Kontrola nových komponentov a spojení
        # Extrahujeme všetky triedy z pozitívneho príkladu
        example_classes = {obj.class_name for obj in example.objects if obj is not None}
        example_objects = {obj.name: obj.class_name for obj in example.objects if obj is not None}
        
        # Prechádzame všetky spojenia v príklade
        for example_link in example.links:
            if example_link is None:
                continue
                
            # Získame triedy zdrojového a cieľového objektu
            if example_link.source not in example_objects or example_link.target not in example_objects:
                continue
                
            source_class = example_objects[example_link.source]
            target_class = example_objects[example_link.target]
            
            # Kontrola, či takéto spojenie už existuje v modeli
            exists = False
            for model_link in updated_model.links:
                if (model_link is not None and
                    model_link.source == source_class and
                    model_link.target == target_class and
                    model_link.link_type == example_link.link_type):
                    exists = True
                    break
                    
            # Ak spojenie ešte neexistuje, pridáme ho
            if not exists:
                new_link = Link(
                    source=source_class,
                    target=target_class,
                    link_type=example_link.link_type
                )
                updated_model.add_link(new_link)
                was_applied = True
                self.applied_heuristics.append("add_missing_objects")
                self._debug_log(f"Add-missing-objects: Pridané nové spojenie {source_class} -> {target_class}")
                
        # Ak sme niečo pridali, vrátime True
        return updated_model, was_applied

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
            model: Aktuálny model
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
            model: Aktuálny model
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
            model: Aktuálny model
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

    def update_model_sequential(self, model: Model, example: Model, is_positive: bool) -> tuple:
        """
        Sekvenčne aktualizuje model na základe nového príkladu.
        Používa sekvenčné implementácie heuristík podľa Winstonovho algoritmu.

        Args:
            model: Aktuálny model (môže byť odlišný od self.model)
            example: Nový príklad
            is_positive: True ak je príklad pozitívny, False ak je negatívny

        Returns:
            tuple (updated_model, was_applied) - Aktualizovaný model a informácia, 
            či bola aplikovaná nejaká heuristika
        """
        # Inicializujeme zoznam aplikovaných heuristík pre tento príklad
        self.applied_heuristics = []
        
        # Predpokladáme, že žiadna heuristika nebude aplikovaná
        was_applied = False
        updated_model = model.copy()  # Používame poskytnutý model, nie interný self.model
        
        # Logging pre typ príkladu
        example_type = "positive" if is_positive else "negative"
        self._debug_log(f"Updating model with {example_type} example (sequential)")
        
        # Špeciálny prípad: prázdny model
        if not updated_model.objects or all(obj is None for obj in updated_model.objects):
            self._debug_log("Prázdny model, pokúšam sa aplikovať add_missing_objects")
            if is_positive:
                updated_model, was_applied = self._add_missing_objects_sequential(updated_model, example, is_positive)
                if was_applied:
                    self._debug_log("Prázdny model bol inicializovaný pomocou add_missing_objects")
        else:
            # Bežné spracovanie pre existujúci model
            self._debug_log(f"Spracovávam {'pozitívny' if is_positive else 'negatívny'} príklad")
            
            # Pre pozitívne príklady:
            if is_positive:
                # 1. add_missing_objects - pridáme nové objekty do modelu
                self._debug_log("Skúšam add_missing_objects heuristiku...")
                updated_model, was_applied = self._add_missing_objects_sequential(updated_model, example, is_positive)
                
                # 2. climb_tree - spracovanie hierarchie tried
                if not was_applied:
                    self._debug_log("Skúšam climb_tree heuristiku...")
                    updated_model, was_applied = self._apply_climb_tree_sequential(updated_model, example, is_positive)
                
                # 3. enlarge_set - rozšírenie množiny hodnôt
                if not was_applied:
                    self._debug_log("Skúšam enlarge_set heuristiku...")
                    updated_model, was_applied = self._apply_enlarge_set_sequential(updated_model, example, is_positive)
                
                # 4. close_interval - spracovanie numerických atribútov
                if not was_applied:
                    self._debug_log("Skúšam close_interval heuristiku...")
                    updated_model, was_applied = self._apply_close_interval_sequential(updated_model, example, is_positive)
            else:
                # Pre negatívne príklady:
                
                # 1. require_link - identifikácia povinných spojení
                self._debug_log("Skúšam require_link heuristiku...")
                updated_model, was_applied = self._apply_require_link_sequential(updated_model, example, is_positive)
                
                # 2. forbid_link - identifikácia zakázaných spojení
                if not was_applied:
                    self._debug_log("Skúšam forbid_link heuristiku...")
                    updated_model, was_applied = self._apply_forbid_link_sequential(updated_model, example, is_positive)
                
                # 3. close_interval - spracovanie numerických atribútov
                if not was_applied:
                    self._debug_log("Skúšam close_interval heuristiku...")
                    updated_model, was_applied = self._apply_close_interval_sequential(updated_model, example, is_positive)
        
        # Aktualizujeme stav modelu a logovanie
        if was_applied:
            # Zaznamenáme použité heuristiky
            self._debug_log(f"Aplikované heuristiky: {self.applied_heuristics}")
        else:
            self._debug_log("Žiadna heuristika nebola aplikovaná, model zostáva nezmenený")
            
        # POZNÁMKA: Vo funkcii update_model_sequential nepripájame príklad do histórie
        # ani neinkrementujeme training_steps, pretože táto funkcia je volaná externým procesom
        # a nemanipuluje s interným stavom triedy WinstonLearner
            
        # Vrátime aktualizovaný model a informáciu o aplikovaní heuristík
        return updated_model, self.applied_heuristics

    def _legacy_update_model(self, model: Model, good: Model, near_miss: Model) -> Model:
        """
        Pôvodná metóda pre aktualizáciu modelu.
        
        Táto metóda je ponechaná pre spätnú kompatibilitu. Odporúča sa používať
        update_model_sequential pre presnejšiu implementáciu Winstonovho algoritmu.
        
        Args:
            model: Aktuálny model (hypotéza)
            good: Pozitívny príklad
            near_miss: Negativní příklad (volitelný)
            
        Returns:
            Aktualizovaný model
        """
        self._debug_log("Using legacy update_model")
        
        # Pridanie príkladov do histórie
        if good is not None:
            self.positive_examples.append(good)
        if near_miss is not None:
            self.negative_examples.append(near_miss)
            
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
        self._debug_log("Skúšam close-interval heuristiku...")
        updated_model = self._apply_close_interval(updated_model, good, near_miss)
            
        # 6. Enlarge-set - rozšíření množiny přijatelných hodnot atributů
        self._debug_log("Skúšam enlarge-set heuristiku...")
        updated_model = self._apply_enlarge_set(updated_model, good)
            
        # 7. Forbid-link - identifikuje, co by objekt neměl mít
        if near_miss:
            self._debug_log("Skúšam forbid-link heuristiku...")
            updated_model = self._apply_forbid_link(updated_model, good, near_miss)
            
        # 8. Drop-link - nejnižší priorita, odstraní nepotřebné vazby
        if not self.applied_heuristics:
            self._debug_log("Skúšam drop-link heuristiku...")
            updated_model = self._apply_drop_link(updated_model, good, near_miss)
        
        # Výpis aplikovaných heuristík
        if self.applied_heuristics:
            self._debug_log(f"Aplikované heuristiky: {', '.join(self.applied_heuristics)}")
        else:
            self._debug_log("Žiadna heuristika nebola aplikovaná")
            
        return updated_model

    def _check_consistency_sequential(self, model: Model, example: Model) -> (Model, bool):
        """
        Kontroluje konzistenciu modelu s novým príkladom a riešenie konfliktov.
        
        Args:
            model: Aktuálny model
            example: Nový príklad (pozitívny)
            
        Returns:
            (updated_model, was_applied) - Aktualizovaný model a informácia, či bola vykonaná nejaká zmena
        """
        updated_model = model.copy()
        was_applied = False
        
        # Kontrola konzistencie objektov
        for example_obj in example.objects:
            # Nájdeme zodpovedajúci objekt v modeli
            model_obj = next((obj for obj in updated_model.objects if obj.name == example_obj.name), None)
            
            # Ak objekt existuje v modeli a má rozdielnu triedu, riešime konflikt
            if model_obj and model_obj.class_name != example_obj.class_name:
                # Kontrola, či sú triedy v hierarchickom vzťahu
                if self.classification_tree.is_subclass(example_obj.class_name, model_obj.class_name):
                    # Pozitívny príklad má špecifickejšiu triedu, aktualizujeme
                    model_obj.class_name = example_obj.class_name
                    was_applied = True
                    self.applied_heuristics.append("resolve_class_conflict")
                    self._debug_log(f"Aktualizovaná trieda objektu {model_obj.name} na {example_obj.class_name}")
                    
                    # Aktualizujeme aj MUST_BE_A spojenia, ak existujú
                    for link in updated_model.links:
                        if link.source == model_obj.name and link.link_type == LinkType.MUST_BE_A:
                            link.target = example_obj.class_name
                            self._debug_log(f"Aktualizované MUST_BE_A spojenie: {link.source} -> {example_obj.class_name}")
                elif self.classification_tree.is_subclass(model_obj.class_name, example_obj.class_name):
                    # Model má špecifickejšiu triedu, ponecháme ju
                    pass
                else:
                    # Nenachádza sa v hierarchickom vzťahu, potrebujeme nájsť spoločného predka
                    common_ancestor = self.classification_tree.find_common_ancestor(
                        model_obj.class_name, example_obj.class_name
                    )
                    
                    if common_ancestor:
                        model_obj.class_name = common_ancestor
                        was_applied = True
                        self.applied_heuristics.append("find_common_ancestor")
                        self._debug_log(f"Našiel sa spoločný predok: {model_obj.name} nastavený na {common_ancestor}")
                        
                        # Aktualizujeme MUST_BE_A spojenia
                        for link in updated_model.links:
                            if link.source == model_obj.name and link.link_type == LinkType.MUST_BE_A:
                                link.target = common_ancestor
                                self._debug_log(f"Aktualizované MUST_BE_A spojenie: {link.source} -> {common_ancestor}")
            
            # Kontrola a aktualizácia atribútov
            if model_obj and example_obj.attributes:
                # Ak objekt má atribúty v príklade, aktualizujeme ich v modeli
                if not model_obj.attributes:
                    model_obj.attributes = {}
                    
                for attr_name, attr_value in example_obj.attributes.items():
                    # Ak atribút neexistuje v modeli alebo má inú hodnotu
                    if attr_name not in model_obj.attributes or model_obj.attributes[attr_name] != attr_value:
                        model_obj.attributes[attr_name] = attr_value
                        was_applied = True
                        self.applied_heuristics.append("update_attribute")
                        self._debug_log(f"Aktualizovaný atribút {attr_name} objektu {model_obj.name} na {attr_value}")
        
        return updated_model, was_applied 

    def _apply_climb_tree_sequential(self, model: Model, example: Model, is_positive: bool) -> (Model, bool):
        """
        Sekvenčná implementácia heuristiky climb-tree, ktorá generalizuje model podľa príkladu.
        
        Args:
            model: Aktuálny model
            example: Spracovávaný príklad
            is_positive: True ak je príklad pozitívny, False ak je negatívny
            
        Returns:
            (updated_model, was_applied) - Aktualizovaný model a informácia, či bola heuristika aplikovaná
        """
        updated_model = model.copy()
        was_applied = False
        
        # Climb-tree sa aplikuje len na pozitívne príklady
        if not is_positive:
            return updated_model, False
            
        # Najprv spracujeme vzťahy dedičnosti z príkladu
        for link in example.links:
            if link is None:
                continue
                
            # Hľadáme regulárne spojenia, ktoré reprezentujú dedičnosť tried
            # V PL1 je IS_A vyjadrený ako regulárne spojenie, nie ako špeciálny typ
            # Typické spojenie typu X5 -> SUV -> Car
            source_obj = next((obj for obj in example.objects if obj is not None and obj.name == link.source), None)
            target_obj = next((obj for obj in example.objects if obj is not None and obj.name == link.target), None)
            
            if source_obj and target_obj:
                source_class = source_obj.class_name
                target_class = target_obj.class_name
                
                # Pridáme vzťah do hierarchie tried, ak ešte neexistuje
                if not self.classification_tree.is_subclass(source_class, target_class):
                    self.classification_tree.add_relationship(source_class, target_class)
                    was_applied = True
                    self.applied_heuristics.append("climb_tree")
                    self._debug_log(f"Climb-tree: Pridaný vzťah dedičnosti: {source_class} je podtriedou {target_class}")
                    
                    # Pridáme aj MUST_BE_A vzťah do modelu
                    must_be_link = Link(
                        source=source_class,
                        target=target_class,
                        link_type=LinkType.MUST_BE_A
                    )
                    
                    # Kontrola, či také spojenie už neexistuje
                    if not any(l.source == must_be_link.source and
                               l.target == must_be_link.target and
                               l.link_type == must_be_link.link_type
                               for l in updated_model.links if l is not None):
                        updated_model.add_link(must_be_link)
                    
                    # Po pridaní jednej hierarchie končíme
                    return updated_model, True
                
        # Spracovanie generalizácie objektov medzi modelom a príkladom
        # Potrebujeme nájsť objekty rovnakých mien ale rôznych tried, ktoré nie sú v hierarchickom vzťahu
        for model_obj in updated_model.objects:
            if model_obj is None:
                continue
                
            # Nájdeme zodpovedajúci objekt v príklade
            example_obj = next((obj for obj in example.objects if obj is not None and obj.name == model_obj.name), None)
            
            if not example_obj:
                continue
                
            # Ak majú rovnaké triedy, preskočíme
            if model_obj.class_name == example_obj.class_name:
                continue
                
            # Ak je trieda objektu v príklade podtriedou triedy objektu v modeli, preskočíme
            # (model už používa všeobecnejšiu triedu, čo je správne)
            if self.classification_tree.is_subclass(example_obj.class_name, model_obj.class_name):
                continue
                
            # Ak je trieda objektu v modeli podtriedou triedy objektu v príklade,
            # mali by sme aktualizovať model na všeobecnejšiu triedu
            if self.classification_tree.is_subclass(model_obj.class_name, example_obj.class_name):
                previous_class = model_obj.class_name
                model_obj.class_name = example_obj.class_name
                was_applied = True
                self.applied_heuristics.append("climb_tree")
                self._debug_log(f"Climb-tree: {model_obj.name} generalizovaný z {previous_class} na {example_obj.class_name}")
                return updated_model, True
                
            # Ak triedy nie sú v hierarchickom vzťahu, hľadáme spoločného predka
            common_ancestor = self.classification_tree.find_common_ancestor(
                model_obj.class_name, example_obj.class_name
            )
            
            if common_ancestor:
                previous_class = model_obj.class_name
                model_obj.class_name = common_ancestor
                was_applied = True
                self.applied_heuristics.append("climb_tree")
                self._debug_log(f"Climb-tree: {model_obj.name} generalizovaný z {previous_class} na {common_ancestor} (spoločný predok s {example_obj.class_name})")
                
                # Aktualizujeme aj MUST_BE_A spojenia
                for link in updated_model.links:
                    if link is not None and link.source == model_obj.name and link.link_type == LinkType.MUST_BE_A:
                        link.target = common_ancestor
                
                return updated_model, True
        
        return updated_model, was_applied

    def _apply_require_link_sequential(self, model: Model, example: Model, is_positive: bool) -> (Model, bool):
        """
        Sekvenčná implementácia heuristiky require-link.
        
        Táto heuristika sa aplikuje na negatívne príklady a identifikuje spojenia, ktoré musia 
        existovať v správnom modeli. Porovnáva negatívny príklad s pozitívnymi príkladmi.
        
        Args:
            model: Aktuálny model
            example: Negatívny príklad
            is_positive: True ak je príklad pozitívny, False ak je negatívny
            
        Returns:
            (updated_model, was_applied) - Aktualizovaný model a indikátor, či bola heuristika aplikovaná
        """
        updated_model = model.copy()
        was_applied = False
        
        # Táto heuristika sa aplikuje len na negatívne príklady
        if is_positive or not self.positive_examples:
            return updated_model, was_applied
            
        self._debug_log(f"Applying require-link heuristic on negative example")
        
        # 1. Kontrola chýbajúcich objektov v negatívnom príklade
        # Najprv zistíme, aké triedy objektov sú v pozitívnych príkladoch, ale chýbajú v negatívnom
        neg_classes = {obj.class_name for obj in example.objects if obj is not None}
        
        # Zozbierame triedy z pozitívnych príkladov
        pos_classes_count = {}
        for pos_example in self.positive_examples:
            for obj in pos_example.objects:
                if obj is not None:
                    if obj.class_name not in pos_classes_count:
                        pos_classes_count[obj.class_name] = 0
                    pos_classes_count[obj.class_name] += 1
        
        # Ak niektorá trieda je vo všetkých pozitívnych príkladoch, ale chýba v negatívnom,
        # pridáme MUST pravidlo pre túto triedu
        required_classes = []
        for class_name, count in pos_classes_count.items():
            # Ak sa trieda vyskytuje vo väčšine pozitívnych príkladov, ale nie je v negatívnom
            if count >= len(self.positive_examples) * 0.7 and class_name not in neg_classes:
                required_classes.append(class_name)
        
        # Ak máme nejaké požadované triedy, vytvoríme MUST pravidlá
        for neg_obj in example.objects:
            if neg_obj is None:
                continue
                
            for required_class in required_classes:
                # Skontrolujeme, či také pravidlo už neexistuje
                if not any(link.source == neg_obj.class_name and 
                           link.target == required_class and 
                           link.link_type == LinkType.MUST 
                           for link in updated_model.links if link is not None):
                    
                    # Kontrola, či pravidlo nie je v konflikte s existujúcim MUST_NOT pravidlom
                    has_conflict = any(link.source == neg_obj.class_name and 
                                       link.target == required_class and 
                                       link.link_type == LinkType.MUST_NOT 
                                       for link in updated_model.links if link is not None)
                    
                    if not has_conflict:
                        # Pridáme MUST pravidlo
                        must_link = Link(
                            source=neg_obj.class_name,
                            target=required_class,
                            link_type=LinkType.MUST
                        )
                        updated_model.add_link(must_link)
                        was_applied = True
                        self.applied_heuristics.append("require_link")
                        self._debug_log(f"Require-link: Pridané MUST pravidlo: {neg_obj.class_name} -> {required_class}")
                        
                        # Po aplikovaní jednej heuristiky končíme
                        return updated_model, True
        
        # 2. Kontrola chýbajúcich spojení
        # Extrahujeme názvy a triedy objektov z negatívneho príkladu
        neg_objects = {obj.name: obj.class_name for obj in example.objects if obj is not None}
        neg_classes = set(obj.class_name for obj in example.objects if obj is not None)
        
        # Pre každý pozitívny príklad
        for pos_example in self.positive_examples:
            # Extrahujeme triedy a spojenia z pozitívneho príkladu
            pos_objects = {obj.name: obj.class_name for obj in pos_example.objects if obj is not None}
            pos_classes = set(obj.class_name for obj in pos_example.objects if obj is not None)
            
            # Nájdeme spoločné triedy objektov medzi pozitívnym a negatívnym príkladom
            common_classes = pos_classes.intersection(neg_classes)
            
            # Ak nemáme aspoň dve spoločné triedy, nemôžeme identifikovať spojenie, ktoré by malo byť povinné
            if len(common_classes) < 2:
                continue
                
            # Pre každý objekt z pozitívneho príkladu
            for pos_obj in pos_example.objects:
                if pos_obj is None:
                    continue
                    
                # Pre každé spojenie v pozitívnom príklade
                for pos_link in pos_example.links:
                    if pos_link is None:
                        continue
                        
                    pos_source = pos_link.source
                    pos_target = pos_link.target
                    
                    # Získame triedy zdrojového a cieľového objektu
                    if pos_source not in pos_objects or pos_target not in pos_objects:
                        continue
                        
                    source_class = pos_objects[pos_source]
                    target_class = pos_objects[pos_target]
                    
                    # Ak obidve triedy sú v negatívnom príklade
                    if source_class in neg_classes and target_class in neg_classes:
                        # Nájdeme objekty rovnakých tried v negatívnom príklade
                        source_objects_in_neg = [name for name, cls in neg_objects.items() if cls == source_class]
                        target_objects_in_neg = [name for name, cls in neg_objects.items() if cls == target_class]
                        
                        has_link_in_neg = False
                        
                        # Skontrolujeme, či existuje také spojenie v negatívnom príklade
                        for neg_source in source_objects_in_neg:
                            for neg_target in target_objects_in_neg:
                                if any(link.source == neg_source and link.target == neg_target for link in example.links if link is not None):
                                    has_link_in_neg = True
                                    break
                            if has_link_in_neg:
                                break
                                
                        # Ak spojenie medzi rovnakými triedami v pozitívnom príklade je, ale v negatívnom nie je
                        if not has_link_in_neg:
                            # Kontrola, či také pravidlo už neexistuje
                            if not any(link.source == source_class and 
                                       link.target == target_class and 
                                       link.link_type == LinkType.MUST 
                                       for link in updated_model.links if link is not None):
                                
                                # Kontrola, či pravidlo nie je v konflikte s existujúcim MUST_NOT pravidlom
                                has_conflict = any(link.source == source_class and 
                                                   link.target == target_class and 
                                                   link.link_type == LinkType.MUST_NOT 
                                                   for link in updated_model.links if link is not None)
                                
                                if not has_conflict:
                                    # Pridáme MUST pravidlo
                                    must_link = Link(
                                        source=source_class,
                                        target=target_class,
                                        link_type=LinkType.MUST
                                    )
                                    updated_model.add_link(must_link)
                                    was_applied = True
                                    self.applied_heuristics.append("require_link")
                                    self._debug_log(f"Require-link: Pridané MUST pravidlo: {source_class} -> {target_class}")
                                    
                                    # Po aplikovaní jednej heuristiky končíme
                                    return updated_model, True
        
        # Kontrola atribútov
        for pos_example in self.positive_examples:
            if pos_example is None or not pos_example.objects:
                continue
                
            for pos_obj in pos_example.objects:
                if pos_obj is None:
                    continue
                    
                # Nájdeme zodpovedajúci objekt rovnakej triedy v negatívnom príklade
                neg_obj_list = [obj for obj in example.objects if obj is not None and obj.class_name == pos_obj.class_name]
                if not neg_obj_list:
                    continue
                    
                # Pre každý atribút v pozitívnom príklade
                if pos_obj.attributes is None:
                    continue
                    
                for attr_name, pos_attr_value in pos_obj.attributes.items():
                    # Ak atribút chýba v negatívnom príklade, môže byť povinný
                    all_neg_missing_attr = True
                    for neg_obj in neg_obj_list:
                        if neg_obj.attributes is not None and attr_name in neg_obj.attributes:
                            all_neg_missing_attr = False
                            break
                            
                    if all_neg_missing_attr:
                        # Atribút chýba vo všetkých objektoch rovnakej triedy v negatívnom príklade
                        # Nájdeme objekt v modeli
                        model_obj = next((obj for obj in updated_model.objects if obj is not None and obj.class_name == pos_obj.class_name), None)
                        if not model_obj:
                            continue
                            
                        # Ak atribút ešte nie je v modeli, pridáme ho
                        if model_obj.attributes is None:
                            model_obj.attributes = {}
                            
                        if attr_name not in model_obj.attributes:
                            if isinstance(pos_attr_value, (int, float)):
                                # Pre numerické hodnoty vytvoríme interval
                                model_obj.attributes[attr_name] = {
                                    "type": "interval",
                                    "min": pos_attr_value,
                                    "max": pos_attr_value
                                }
                            else:
                                # Pre ostatné hodnoty vytvoríme množinu
                                model_obj.attributes[attr_name] = {
                                    "type": "set",
                                    "values": [pos_attr_value]
                                }
                            was_applied = True
                            self.applied_heuristics.append("require_link")
                            self._debug_log(f"Require-link: Pridaný atribút {attr_name} s hodnotou {pos_attr_value} objektu {model_obj.class_name}")
                            return updated_model, True
        
        return updated_model, was_applied

    def _apply_close_interval_sequential(self, model: Model, example: Model, is_positive: bool) -> (Model, bool):
        """
        Sekvenčná implementácia heuristiky close-interval pre spracovanie numerických atribútov.
        
        Args:
            model: Aktuálny model
            example: Spracovávaný príklad
            is_positive: True ak je príklad pozitívny, False ak je negatívny
            
        Returns:
            (updated_model, was_applied) - Aktualizovaný model a informácia, či bola heuristika aplikovaná
        """
        updated_model = model.copy()
        was_applied = False
        
        self._debug_log(f"Applying close-interval heuristic for {'positive' if is_positive else 'negative'} example")
        
        # V prípade negatívneho príkladu hľadáme hodnoty, ktoré sú mimo povolený interval
        if not is_positive:
            # Prechádzame všetky objekty v negatívnom príklade
            for example_obj in example.objects:
                if example_obj is None or not example_obj.attributes:
                    continue
                    
                # Prechádzame všetky numerické atribúty
                for attr_name, attr_value in example_obj.attributes.items():
                    if not isinstance(attr_value, (int, float)):
                        continue
                        
                    # Hľadáme objekty rovnakej triedy v modeli
                    model_objs = [obj for obj in updated_model.objects
                                  if obj is not None and obj.class_name == example_obj.class_name]
                    
                    for model_obj in model_objs:
                        if model_obj.attributes is None:
                            model_obj.attributes = {}
                            
                        # Ak atribút existuje v modeli ako interval
                        if attr_name in model_obj.attributes and isinstance(model_obj.attributes[attr_name], dict) and model_obj.attributes[attr_name].get("type") == "interval":
                            interval = model_obj.attributes[attr_name]
                            min_val = interval.get("min")
                            max_val = interval.get("max")
                            
                            # Ak hodnota z negatívneho príkladu je v intervale, musíme interval upraviť
                            if min_val <= attr_value <= max_val:
                                # Hľadáme bližšiu hranicu intervalu
                                if attr_value - min_val < max_val - attr_value:
                                    # Hodnota je bližšie k min, posunieme min
                                    interval["min"] = attr_value + 1
                                else:
                                    # Hodnota je bližšie k max, posunieme max
                                    interval["max"] = attr_value - 1
                                    
                                was_applied = True
                                self.applied_heuristics.append("close_interval")
                                self._debug_log(f"Close-interval: Upravený interval pre {attr_name} objektu {model_obj.class_name}: [{interval['min']}, {interval['max']}] (vylúčená hodnota {attr_value})")
                                return updated_model, True
                                
                        # Ak atribút neexistuje v modeli, ale máme pozitívne príklady s týmto atribútom
                        elif attr_name not in model_obj.attributes:
                            # Zbierame hodnoty atribútu z pozitívnych príkladov
                            pos_values = []
                            for pos_example in self.positive_examples:
                                for pos_obj in pos_example.objects:
                                    if (pos_obj is not None and pos_obj.class_name == example_obj.class_name and 
                                        pos_obj.attributes and attr_name in pos_obj.attributes):
                                        pos_value = pos_obj.attributes[attr_name]
                                        if isinstance(pos_value, (int, float)):
                                            pos_values.append(pos_value)
                            
                            # Ak máme hodnoty z pozitívnych príkladov, vytvoríme interval
                            if pos_values:
                                min_val = min(pos_values)
                                max_val = max(pos_values)
                                
                                # Upravíme interval vzhľadom na hodnotu z negatívneho príkladu
                                if attr_value < min_val:
                                    # Hodnota je pod intervalom, nastavíme min na vyššiu hodnotu
                                    model_obj.attributes[attr_name] = {
                                        "type": "interval",
                                        "min": min_val,
                                        "max": max_val
                                    }
                                    was_applied = True
                                    self.applied_heuristics.append("close_interval")
                                    self._debug_log(f"Close-interval: Vytvorený interval pre {attr_name} objektu {model_obj.class_name}: [{min_val}, {max_val}]")
                                    return updated_model, True
                                    
                                elif attr_value > max_val:
                                    # Hodnota je nad intervalom, nastavíme max na nižšiu hodnotu
                                    model_obj.attributes[attr_name] = {
                                        "type": "interval",
                                        "min": min_val,
                                        "max": max_val
                                    }
                                    was_applied = True
                                    self.applied_heuristics.append("close_interval")
                                    self._debug_log(f"Close-interval: Vytvorený interval pre {attr_name} objektu {model_obj.class_name}: [{min_val}, {max_val}]")
                                    return updated_model, True
                                    
                                else:
                                    # Hodnota je v intervale, musíme interval upraviť
                                    if attr_value - min_val < max_val - attr_value:
                                        # Hodnota je bližšie k min, posunieme min
                                        model_obj.attributes[attr_name] = {
                                            "type": "interval",
                                            "min": attr_value + 1,
                                            "max": max_val
                                        }
                                    else:
                                        # Hodnota je bližšie k max, posunieme max
                                        model_obj.attributes[attr_name] = {
                                            "type": "interval",
                                            "min": min_val,
                                            "max": attr_value - 1
                                        }
                                    was_applied = True
                                    self.applied_heuristics.append("close_interval")
                                    self._debug_log(f"Close-interval: Vytvorený interval pre {attr_name} objektu {model_obj.class_name}: [{model_obj.attributes[attr_name]['min']}, {model_obj.attributes[attr_name]['max']}] (vylúčená hodnota {attr_value})")
                                    return updated_model, True
        
        # Štandardné spracovanie pre pozitívne príklady
        if is_positive:
            # Pre pozitívne príklady - zúženie intervalu alebo vytvorenie nového
            # Prechádzame všetky objekty v príklade
            for example_obj in example.objects:
                if example_obj is None or not example_obj.attributes:
                    continue
                    
                # Hľadáme zodpovedajúce objekty v modeli (podľa názvu alebo triedy)
                model_objs = []
                
                # Najprv skúsime nájsť objekt podľa mena
                model_obj_by_name = next((obj for obj in updated_model.objects if obj is not None and obj.name == example_obj.name), None)
                if model_obj_by_name:
                    model_objs.append(model_obj_by_name)
                
                # Ak nenájdeme objekt podľa mena, skúsime hľadať podľa triedy
                if not model_objs:
                    model_objs = [obj for obj in updated_model.objects if obj is not None and obj.class_name == example_obj.class_name]
                
                # Pre každý zodpovedajúci objekt v modeli
                for model_obj in model_objs:
                    if model_obj.attributes is None:
                        model_obj.attributes = {}
                        
                    # Prechádzame numerické atribúty v príklade
                    for attr_name, attr_value in example_obj.attributes.items():
                        if not isinstance(attr_value, (int, float)):
                            continue
                            
                        # Ak atribút neexistuje v modeli, vytvoríme ho
                        if attr_name not in model_obj.attributes:
                            model_obj.attributes[attr_name] = {
                                "type": "interval",
                                "min": attr_value,
                                "max": attr_value
                            }
                            was_applied = True
                            self.applied_heuristics.append("close_interval")
                            self._debug_log(f"Close-interval: Vytvorený nový interval pre {attr_name} objektu {model_obj.class_name}: [{attr_value}, {attr_value}]")
                            return updated_model, True
                            
                        # Ak atribút existuje, skontrolujeme či ide o interval
                        model_attr = model_obj.attributes[attr_name]
                        
                        if isinstance(model_attr, dict) and model_attr.get("type") == "interval":
                            # Aktuálny interval
                            min_val = model_attr.get("min")
                            max_val = model_attr.get("max")
                            
                            # Kontrola, či hodnota je mimo intervalu
                            if attr_value < min_val:
                                # Hodnota je pod intervalom, rozšírime ho
                                model_attr["min"] = attr_value
                                was_applied = True
                                self.applied_heuristics.append("close_interval")
                                self._debug_log(f"Close-interval: Rozšírený interval pre {attr_name} objektu {model_obj.class_name}: [{attr_value}, {max_val}] (znížená min hodnota)")
                                return updated_model, True
                                
                            elif attr_value > max_val:
                                # Hodnota je nad intervalom, rozšírime ho
                                model_attr["max"] = attr_value
                                was_applied = True
                                self.applied_heuristics.append("close_interval")
                                self._debug_log(f"Close-interval: Rozšírený interval pre {attr_name} objektu {model_obj.class_name}: [{min_val}, {attr_value}] (zvýšená max hodnota)")
                                return updated_model, True
                                
                        elif not isinstance(model_attr, dict):
                            # Ak atribút nie je interval, ale má inú hodnotu (napr. fixná hodnota),
                            # konvertujeme ho na interval
                            if isinstance(model_attr, (int, float)) and model_attr != attr_value:
                                model_obj.attributes[attr_name] = {
                                    "type": "interval",
                                    "min": min(model_attr, attr_value),
                                    "max": max(model_attr, attr_value)
                                }
                                was_applied = True
                                self.applied_heuristics.append("close_interval")
                                self._debug_log(f"Close-interval: Konvertovaný atribút {attr_name} objektu {model_obj.class_name} na interval: [{model_obj.attributes[attr_name]['min']}, {model_obj.attributes[attr_name]['max']}]")
                                return updated_model, True
        
        return updated_model, was_applied
        
    def _apply_enlarge_set_sequential(self, model: Model, example: Model, is_positive: bool) -> (Model, bool):
        """
        Sekvenčná implementácia heuristiky enlarge-set.
        
        Táto heuristika rozširuje množiny povolených hodnôt pre atribúty na základe
        pozitívnych príkladov. Pre každý atribút objektu v pozitívnom príklade, ktorý
        ešte nie je v modeli, pridá novú povolenú hodnotu.
        
        Args:
            model: Aktuálny model
            example: Spracovávaný príklad
            is_positive: True ak je príklad pozitívny, False ak je negatívny
            
        Returns:
            (updated_model, was_applied) - Aktualizovaný model a informácia, či bola heuristika aplikovaná
        """
        updated_model = model.copy()
        was_applied = False
        
        # Enlarge-set sa aplikuje len na pozitívne príklady
        if not is_positive:
            return updated_model, was_applied
        
        self._debug_log(f"Applying enlarge-set heuristic on positive example")
        
        # Pre každý objekt v príklade
        for example_obj in example.objects:
            if example_obj is None or not example_obj.attributes:
                continue
                
            # Nájdeme zodpovedajúce objekty v modeli
            model_objs = []
            
            # Najprv skúsime nájsť objekt podľa mena
            model_obj_by_name = next((obj for obj in updated_model.objects 
                                    if obj is not None and obj.name == example_obj.name), None)
            if model_obj_by_name:
                model_objs.append(model_obj_by_name)
                
            # Ak nenájdeme podľa mena, skúsime hľadať podľa triedy
            if not model_objs:
                model_objs = [obj for obj in updated_model.objects 
                             if obj is not None and obj.class_name == example_obj.class_name]
                
            # Ak nenájdeme žiadny zodpovedajúci objekt, preskočíme (toto by malo byť riešené add_missing_objects)
            if not model_objs:
                continue
                
            # Pre každý zodpovedajúci objekt v modeli
            for model_obj in model_objs:
                if model_obj.attributes is None:
                    model_obj.attributes = {}
                    
                # Pre každý atribút v príklade
                for attr_name, attr_value in example_obj.attributes.items():
                    # Preskočíme numerické atribúty (tie sú riešené cez close-interval)
                    if isinstance(attr_value, (int, float)):
                        continue
                        
                    # Ak atribút ešte nie je v modeli, vytvoríme pre neho novú množinu
                    if attr_name not in model_obj.attributes:
                        model_obj.attributes[attr_name] = {
                            "type": "set",
                            "values": [attr_value]
                        }
                        was_applied = True
                        self.applied_heuristics.append("enlarge_set")
                        self._debug_log(f"Enlarge-set: Vytvorená nová množina pre atribút {attr_name} objektu {model_obj.class_name} s hodnotou {attr_value}")
                        return updated_model, True
                        
                    # Ak atribút už existuje, musíme zistiť, či sa jedná o množinu
                    model_attr = model_obj.attributes[attr_name]
                    
                    # Ak je to množina, skontrolujeme, či hodnota už existuje
                    if isinstance(model_attr, dict) and model_attr.get("type") == "set":
                        # Ak hodnota ešte nie je v množine, pridáme ju
                        if attr_value not in model_attr.get("values", []):
                            if "values" not in model_attr:
                                model_attr["values"] = []
                            model_attr["values"].append(attr_value)
                            was_applied = True
                            self.applied_heuristics.append("enlarge_set")
                            self._debug_log(f"Enlarge-set: Pridaná hodnota {attr_value} do množiny pre atribút {attr_name} objektu {model_obj.class_name}")
                            return updated_model, True
                            
                    # Ak nie je množina, ale má konkrétnu hodnotu, konvertujeme ju na množinu
                    elif model_attr != attr_value and not isinstance(model_attr, dict):
                        # Vytvoríme množinu s oboma hodnotami
                        model_obj.attributes[attr_name] = {
                            "type": "set",
                            "values": [model_attr, attr_value]
                        }
                        was_applied = True
                        self.applied_heuristics.append("enlarge_set")
                        self._debug_log(f"Enlarge-set: Konvertovaný atribút {attr_name} objektu {model_obj.class_name} na množinu s hodnotami {model_attr} a {attr_value}")
                        return updated_model, True
        
        # Kontrola spojení v príklade, ktoré sa môžu pridať do modelu
        for example_link in example.links:
            if example_link is None:
                continue
                
            # Získame zdrojový a cieľový objekt
            source_obj = next((obj for obj in example.objects if obj is not None and obj.name == example_link.source), None)
            target_obj = next((obj for obj in example.objects if obj is not None and obj.name == example_link.target), None)
            
            if not source_obj or not target_obj:
                continue
                
            source_class = source_obj.class_name
            target_class = target_obj.class_name
            
            # Kontrola, či také spojenie už existuje v modeli
            exists = False
            for model_link in updated_model.links:
                if (model_link is not None and 
                    model_link.source == source_class and 
                    model_link.target == target_class and 
                    model_link.link_type == example_link.link_type):
                    exists = True
                    break
                    
            if not exists:
                # Pridáme spojenie do modelu
                new_link = Link(
                    source=source_class,
                    target=target_class,
                    link_type=example_link.link_type
                )
                updated_model.add_link(new_link)
                was_applied = True
                self.applied_heuristics.append("enlarge_set")
                self._debug_log(f"Enlarge-set: Pridané spojenie {source_class} -> {target_class} typu {example_link.link_type}")
                return updated_model, True
        
        return updated_model, was_applied

    def _apply_forbid_link_sequential(self, model: Model, example: Model, is_positive: bool) -> (Model, bool):
        """
        Sekvenčná implementácia heuristiky forbid-link, ktorá identifikuje zakázané spojenia a atribúty.
        
        Args:
            model: Aktuálny model
            example: Negatívny príklad
            is_positive: True ak je príklad pozitívny, False ak je negatívny
            
        Returns:
            (updated_model, was_applied) - Aktualizovaný model a informácia, či bola heuristika aplikovaná
        """
        updated_model = model.copy()
        was_applied = False
        
        # Forbid-link sa aplikuje len na negatívne príklady
        if is_positive:
            return updated_model, was_applied
            
        self._debug_log("Applying forbid-link heuristic on negative example")
        
        # 1. Spracovanie spojení - hľadáme spojenia, ktoré sa nachádzajú v negatívnom príklade,
        # ale nemali by tam byť (podľa pozitívnych príkladov)
        
        # Najprv identifikujeme triedy objektov v negatívnom príklade
        neg_classes = {obj.class_name for obj in example.objects if obj is not None}
        neg_objects = {obj.name: obj.class_name for obj in example.objects if obj is not None}
        
        # Prechádzame všetky spojenia v negatívnom príklade
        for neg_link in example.links:
            if neg_link is None:
                continue
                
            # Získame zdrojový a cieľový objekt
            source_obj = next((obj for obj in example.objects if obj is not None and obj.name == neg_link.source), None)
            target_obj = next((obj for obj in example.objects if obj is not None and obj.name == neg_link.target), None)
            
            if not source_obj or not target_obj:
                continue
                
            source_class = source_obj.class_name
            target_class = target_obj.class_name
            
            # Ak spojenie medzi týmito triedami sa vyskytuje v negatívnom príklade, ale nemá sa vyskytovať
            should_forbid = True
            
            # Skontrolujeme, či sa spojenie medzi týmito triedami nachádza v pozitívnych príkladoch
            for pos_example in self.positive_examples:
                for pos_link in pos_example.links:
                    if pos_link is None:
                        continue
                        
                    pos_source = next((obj for obj in pos_example.objects if obj is not None and obj.name == pos_link.source), None)
                    pos_target = next((obj for obj in pos_example.objects if obj is not None and obj.name == pos_link.target), None)
                    
                    if not pos_source or not pos_target:
                        continue
                        
                    # Ak sa triedy zhodujú, spojenie je valídne a nemá byť zakázané
                    if pos_source.class_name == source_class and pos_target.class_name == target_class:
                        should_forbid = False
                        break
                
                if not should_forbid:
                    break
            
            # Ak spojenie má byť zakázané a ešte nie je v modeli
            if should_forbid:
                # Skontrolujeme, či také MUST_NOT pravidlo už neexistuje
                exists = any(link is not None and 
                             link.source == source_class and 
                             link.target == target_class and 
                             link.link_type == LinkType.MUST_NOT 
                             for link in updated_model.links)
                
                if not exists:
                    # Skontrolujeme, či pravidlo nie je v konflikte s MUST pravidlom
                    has_conflict = any(link is not None and 
                                       link.source == source_class and 
                                       link.target == target_class and 
                                       link.link_type == LinkType.MUST 
                                       for link in updated_model.links)
                    
                    if not has_conflict:
                        # Pridáme MUST_NOT pravidlo
                        forbid_link = Link(
                            source=source_class,
                            target=target_class,
                            link_type=LinkType.MUST_NOT
                        )
                        updated_model.add_link(forbid_link)
                        was_applied = True
                        self.applied_heuristics.append("forbid_link")
                        self._debug_log(f"Forbid-link: Pridané MUST_NOT pravidlo: {source_class} -> {target_class}")
                        return updated_model, True
                        
        # 2. Spracovanie atribútov - hľadáme nepovolené hodnoty atribútov
        
        # Prechádzame všetky objekty negatívneho príkladu
        for neg_obj in example.objects:
            if neg_obj is None or not neg_obj.attributes:
                continue
                
            # Prechádzame atribúty
            for attr_name, neg_value in neg_obj.attributes.items():
                # Hľadáme objekty rovnakého typu v modeli
                model_objects = [obj for obj in updated_model.objects 
                                 if obj is not None and obj.class_name == neg_obj.class_name]
                
                for model_obj in model_objects:
                    if model_obj.attributes is None:
                        model_obj.attributes = {}
                        
                    # Ak je to numerický atribút, spracujeme ho ako interval
                    if isinstance(neg_value, (int, float)):
                        # Ak atribút ešte neexistuje, vytvoríme ho ako interval vylučujúci túto hodnotu
                        if attr_name not in model_obj.attributes:
                            # Skontrolujeme pozitívne hodnoty, aby sme vedeli vytvoriť interval
                            positive_values = []
                            for pos_example in self.positive_examples:
                                for pos_obj in pos_example.objects:
                                    if (pos_obj is not None and pos_obj.class_name == neg_obj.class_name and 
                                        pos_obj.attributes and attr_name in pos_obj.attributes):
                                        pos_value = pos_obj.attributes[attr_name]
                                        if isinstance(pos_value, (int, float)):
                                            positive_values.append(pos_value)
                            
                            if positive_values:
                                # Vytvoríme interval podľa pozitívnych hodnôt, ktorý vylúči negatívnu hodnotu
                                min_val = min(positive_values)
                                max_val = max(positive_values)
                                
                                # Upravíme interval podľa negatívneho príkladu
                                if neg_value < min_val:
                                    # Min hranica sa nemení
                                    pass
                                elif neg_value > max_val:
                                    # Max hranica sa nemení
                                    pass
                                else:
                                    # Hodnota je v intervale, musíme upraviť hranice
                                    # Nájdeme bližšiu hranicu a posunieme ju za negatívnu hodnotu
                                    if neg_value - min_val < max_val - neg_value:
                                        # Bližšie k min, posunieme min
                                        min_val = neg_value + 1
                                    else:
                                        # Bližšie k max, posunieme max
                                        max_val = neg_value - 1
                                
                                model_obj.attributes[attr_name] = {
                                    "type": "interval",
                                    "min": min_val,
                                    "max": max_val
                                }
                                was_applied = True
                                self.applied_heuristics.append("forbid_link")
                                self._debug_log(f"Forbid-link: Vytvorený interval pre {attr_name} objektu {model_obj.class_name}: [{min_val}, {max_val}] (vylúčená hodnota {neg_value})")
                                return updated_model, True
                        else:
                            # Ak atribút už existuje, skontrolujeme či negatívna hodnota nie je v povolenom intervale
                            attr_value = model_obj.attributes[attr_name]
                            
                            if isinstance(attr_value, dict) and attr_value.get("type") == "interval":
                                min_val = attr_value.get("min")
                                max_val = attr_value.get("max")
                                
                                # Ak negatívna hodnota je v intervale, upravíme interval
                                if min_val <= neg_value <= max_val:
                                    # Nájdeme bližšiu hranicu a posunieme ju za negatívnu hodnotu
                                    if neg_value - min_val < max_val - neg_value:
                                        # Bližšie k min, posunieme min
                                        attr_value["min"] = neg_value + 1
                                    else:
                                        # Bližšie k max, posunieme max
                                        attr_value["max"] = neg_value - 1
                                    
                                    was_applied = True
                                    self.applied_heuristics.append("forbid_link")
                                    self._debug_log(f"Forbid-link: Upravený interval pre {attr_name} objektu {model_obj.class_name}: [{attr_value['min']}, {attr_value['max']}] (vylúčená hodnota {neg_value})")
                                    return updated_model, True
                    
                    # Ak je to nenumerický atribút, pridáme MUST_NOT pravidlo
                    elif attr_name in model_obj.attributes or isinstance(neg_value, str):
                        # Ak hodnota je v množine povolených hodnôt, odstránime ju
                        if isinstance(model_obj.attributes.get(attr_name), dict) and model_obj.attributes[attr_name].get("type") == "set":
                            if neg_value in model_obj.attributes[attr_name].get("values", []):
                                model_obj.attributes[attr_name]["values"].remove(neg_value)
                                was_applied = True
                                self.applied_heuristics.append("forbid_link")
                                self._debug_log(f"Forbid-link: Odstránená hodnota {neg_value} z množiny pre {attr_name} objektu {model_obj.class_name}")
                                return updated_model, True
                        
                        # Pridáme MUST_NOT pravidlo pre tento atribút a hodnotu
                        for link in updated_model.links:
                            if (link is not None and 
                                link.source == neg_obj.class_name and 
                                link.target == f"{attr_name}_{neg_value}" and 
                                link.link_type == LinkType.MUST_NOT):
                                # Pravidlo už existuje
                                break
                        else:
                            # Pravidlo neexistuje, pridáme ho
                            forbid_attr_link = Link(
                                source=neg_obj.class_name,
                                target=f"{attr_name}_{neg_value}",
                                link_type=LinkType.MUST_NOT
                            )
                            updated_model.add_link(forbid_attr_link)
                            was_applied = True
                            self.applied_heuristics.append("forbid_link")
                            self._debug_log(f"Forbid-link: Pridané MUST_NOT pravidlo pre atribút: {neg_obj.class_name} -> {attr_name}={neg_value}")
                            return updated_model, True
        
        return updated_model, was_applied

    def _apply_drop_link_sequential(self, model: Model, example: Model, is_positive: bool) -> (Model, bool):
        """
        Sekvenčná implementácia heuristiky drop-link.
        
        Táto heuristika má najnižšiu prioritu a aplikuje sa, keď žiadna iná 
        heuristika nebola aplikovaná. Identifikuje spojenia v modeli, ktoré 
        nemusia byť nevyhnutné pre rozpoznanie konceptu.
        
        Args:
            model: Aktuálny model
            example: Spracovávaný príklad
            is_positive: True ak je príklad pozitívny, False ak je negatívny
            
        Returns:
            (updated_model, was_applied) - Aktualizovaný model a indikátor, či bola heuristika aplikovaná
        """
        updated_model = model.copy()
        was_applied = False
        
        # Drop-link sa aplikuje len na pozitívne príklady
        if not is_positive:
            return updated_model, was_applied
            
        self._debug_log(f"Applying drop-link heuristic on positive example")
        
        # Extrahujeme triedy objektov z príkladu
        example_classes = set(obj.class_name for obj in example.objects)
        
        # Vytvoríme zoznam spojení v príklade na úrovni tried
        example_class_links = set()
        for link in example.links:
            source_obj = next((obj for obj in example.objects if obj.name == link.source), None)
            target_obj = next((obj for obj in example.objects if obj.name == link.target), None)
            
            if source_obj and target_obj:
                example_class_links.add((source_obj.class_name, target_obj.class_name))
        
        # Kontrolujeme spojenia v modeli
        model_links_to_remove = []
        
        for model_link in updated_model.links:
            # Uvažujeme len MUST spojenia a spojenia medzi triedami, ktoré sú v príklade
            if (model_link.link_type == LinkType.MUST and 
                model_link.source in example_classes and 
                model_link.target in example_classes):
                
                # Ak spojenie medzi týmito triedami nie je v príklade, je kandidátom na odstránenie
                if (model_link.source, model_link.target) not in example_class_links:
                    # Overíme, či odstránenie spojenia nespôsobí konflikty
                    # Pre jednoduchosť predpokladáme, že môžeme spojenie odstrániť
                    model_links_to_remove.append(model_link)
                    
        # Ak máme spojenia na odstránenie, odstránime jedno z nich
        if model_links_to_remove:
            link_to_remove = model_links_to_remove[0]  # Odstránime prvé spojenie zo zoznamu
            
            # Nájdeme index spojenia a odstránime ho
            for i, link in enumerate(updated_model.links):
                if (link.source == link_to_remove.source and 
                    link.target == link_to_remove.target and 
                    link.link_type == link_to_remove.link_type):
                    del updated_model.links[i]
                    was_applied = True
                    self.applied_heuristics.append("drop_link")
                    self._debug_log(f"Drop-link: Odstránené MUST spojenie: {link_to_remove.source} -> {link_to_remove.target}")
                    break
        
        return updated_model, was_applied

    def get_training_steps(self) -> List[Dict]:
        """
        Získa kroky trénovania pre aktuálnu iteráciu učenia.
        
        Táto metóda zhromažďuje informácie o aplikovaných heuristikách a príkladoch
        pre vizualizáciu procesu učenia v UI.
        
        Returns:
            List[Dict] - Zoznam krokov trénovania s informáciami o heuristikách a príkladoch
        """
        if not self.applied_heuristics:
            return []
            
        # Vytvoríme zoznam krokov na základe aplikovaných heuristík
        training_steps = []
        
        # Ak bola aplikovaná aspoň jedna heuristika, vytvoríme krok
        if self.applied_heuristics:
            # Získame aktuálny príklad (posledný v histórii)
            example = None
            example_type = None
            
            if self.positive_examples:
                example = self.positive_examples[-1]
                example_type = "positive"
            elif self.negative_examples:
                example = self.negative_examples[-1]
                example_type = "negative"
                
            if example:
                # Vytvoríme krok so všetkými aplikovanými heuristikami
                step = {
                    "example": example.to_dict() if hasattr(example, "to_dict") else str(example),
                    "example_type": example_type,
                    "heuristics": self.applied_heuristics.copy()
                }
                training_steps.append(step)
                
        return training_steps