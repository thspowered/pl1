from backend.model import Model, Link, LinkType, ClassificationTree, Object
from backend.pl1_parser import Formula, Predicate
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
        Aktualizuje model na základě pozitívneho príkladu a near-miss príkladu.
        
        Postupne aplikuje heuristiky v optimalizovanom pořadí na základe jejich důležitosti:
        1. add_missing_objects - když model je prázdný, přidá všechny objekty z first example
        2. check_consistency - zkontroluje a vyřeší konflikty v hierarchii
        3. climb_tree - zobecnění na vyšší úroveň hierarchie včetně Device
        4. require_link - přidá pozitivní vazby
        5. close_interval - zúží intervaly numerických atributů
        6. enlarge_set - rozšíří množiny přijatelných hodnot atributů
        7. forbid_link - přidá negativní vazby
        8. drop_link - odstraní nepotřebné vazby
        9. propagate_to_common_ancestor - propaguje pravidla na nejvyšší společný předek
        10. backup_rule - vrátí se k lepšímu předchozímu pravidlu, pokud je to potřeba
        
        Args:
            model: Aktuálny model znalostí
            good: Pozitívny príklad
            near_miss: Near-miss príklad
            
        Returns:
            Aktualizovaný model
        """
        # Reset zoznamu aplikovaných heuristík
        self.applied_heuristics = []
        
        # Hlboká kópia modelu
        updated_model = model.copy()
        
        # Uložení aktuálního modelu do historie před změnami
        if len(model.objects) > 0:  # Ukládáme pouze neprázdné modely
            self._add_to_history(model)
        
        # Debugovanie
        self._debug_log("Začínam aktualizáciu modelu")
        self._debug_log(f"Pozitívny príklad: {good}")
        if near_miss:
            self._debug_log(f"Near-miss príklad: {near_miss}")
        else:
            self._debug_log("Near-miss príklad: None")
        
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
        
        # 7. Propagace vlastností na nejvyšší úroveň hierarchie
        updated_model = self._propagate_to_common_ancestor(updated_model)
            
        # 8. Forbid-link - identifikuje, co by objekt neměl mít
        if near_miss:
            self._debug_log("Skúšam forbid-link heuristiku...")
            updated_model = self._apply_forbid_link(updated_model, good, near_miss)
            
        # 9. Drop-link - nejnižší priorita, odstraní nepotřebné vazby
        if not self.applied_heuristics:
            self._debug_log("Skúšam drop-link heuristiku...")
            updated_model = self._apply_drop_link(updated_model, good, near_miss)
        
        # 10. BackUp Rule - kontrola, zda nové změny nezhoršily přesnost modelu
        updated_model = self._apply_backup_rule(updated_model, good, near_miss)
        
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
        
        Rozšiřuje množinu přijatelných hodnot atributů na základě pozitivních příkladů.
        Pokud má objekt v pozitivním příkladu atribut s jinou hodnotou než v modelu,
        heuristika přidá tuto hodnotu do množiny přijatelných hodnot.
        
        Args:
            model: Aktuální model
            good: Pozitivní příklad
            
        Returns:
            Aktualizovaný model
        """
        updated_model = model.copy()
        
        # Nejprve projdeme pozitivní příklad a hledáme nové hodnoty atributů
        for good_obj in good.objects:
            if not good_obj.attributes:
                continue
                
            for attr_name, attr_value in good_obj.attributes.items():
                # Přeskočíme numerické hodnoty (intervaly) a množiny - ty zpracováváme jinde
                if isinstance(attr_value, tuple) or isinstance(attr_value, set):
                    continue
                
                # Najdeme všechny objekty stejné třídy v modelu
                for model_obj in updated_model.objects:
                    if model_obj.class_name == good_obj.class_name:
                        # Pokud objekt ještě nemá atributy, vytvoříme slovník
                        if not model_obj.attributes:
                            model_obj.attributes = {}
                        
                        # Pokud atribut v objektu neexistuje, vytvoříme ho jako množinu s novou hodnotou
                        if attr_name not in model_obj.attributes:
                            model_obj.attributes[attr_name] = {attr_value}
                            self.applied_heuristics.append("enlarge_set")
                            self._debug_log(f"Vytvořena nová množina hodnot pro atribut {attr_name} třídy {good_obj.class_name}")
                        else:
                            current_value = model_obj.attributes[attr_name]
                            
                            # Pokud je současná hodnota interval (tuple), přeskočíme
                            if isinstance(current_value, tuple):
                                continue
                            
                            # Pokud je současná hodnota již množina, přidáme novou hodnotu
                            if isinstance(current_value, set):
                                if attr_value not in current_value:
                                    current_value.add(attr_value)
                                    self.applied_heuristics.append("enlarge_set")
                                    self._debug_log(f"Rozšířena množina hodnot atributu {attr_name} pro třídu {good_obj.class_name} o hodnotu {attr_value}")
                            
                            # Pokud je současná hodnota jednoduchá (ne množina, ne interval)
                            # a liší se od nové hodnoty, vytvoříme množinu obsahující obě hodnoty
                            elif current_value != attr_value:
                                model_obj.attributes[attr_name] = {current_value, attr_value}
                                self.applied_heuristics.append("enlarge_set")
                                self._debug_log(f"Rozšířena množina hodnot atributu {attr_name} pro třídu {good_obj.class_name} o hodnotu {attr_value}")
        
        return updated_model

    def _apply_close_interval(self, model: Model, good: Model, near_miss: Model = None) -> Model:
        """
        Aplikuje close-interval heuristiku.
        
        Zužuje intervaly numerických atributů na základě pozitivních a negativních příkladů.
        Pro každý numerický atribut v pozitivním příkladu, pokud jeho hodnota spadá do intervalu v modelu,
        ponechá interval nezměněný. Pokud je hodnota mimo interval, rozšíří interval.
        Pro negativní příklad naopak vyloučí hodnoty, které jsou v příkladu, pokud interval překrývá tuto hodnotu.
        
        Args:
            model: Aktuální model
            good: Pozitivní příklad
            near_miss: Negativní příklad (volitelný)
            
        Returns:
            Aktualizovaný model
        """
        updated_model = model.copy()
        
        # 1. Zpracování pozitivních příkladů - úprava intervalů
        for good_obj in good.objects:
            if not good_obj.attributes:
                continue
                
            for attr_name, attr_value in good_obj.attributes.items():
                # Zajímají nás pouze numerické hodnoty
                if not isinstance(attr_value, (int, float)):
                    continue
                
                # Najdeme odpovídající objekty v modelu
                for obj in updated_model.objects:
                    if obj.class_name == good_obj.class_name and obj.attributes:
                        # Pokud atribut existuje a je to interval
                        if attr_name in obj.attributes and isinstance(obj.attributes[attr_name], tuple) and len(obj.attributes[attr_name]) == 2:
                            current_min, current_max = obj.attributes[attr_name]
                            
                            # Pokud hodnota pozitivního příkladu je mimo interval, aktualizujeme ho
                            if attr_value < current_min or attr_value > current_max:
                                # Rozšíříme interval tak, aby zahrnoval novou hodnotu
                                new_min = min(current_min, attr_value)
                                new_max = max(current_max, attr_value)
                                obj.attributes[attr_name] = (new_min, new_max)
                                self.applied_heuristics.append("close_interval")
                                self._debug_log(f"Rozšířen interval atributu {attr_name} pro třídu {good_obj.class_name} na ({new_min}, {new_max})")
                        
                        # Pokud atribut neexistuje nebo není interval, vytvoříme nový interval
                        elif attr_name not in obj.attributes or not isinstance(obj.attributes[attr_name], tuple):
                            # Pro nový atribut vytvoříme interval s malou tolerancí
                            tolerance = max(0.1, abs(attr_value) * 0.05)  # 5% tolerance nebo minimálně 0.1
                            new_min = attr_value - tolerance
                            new_max = attr_value + tolerance
                            obj.attributes[attr_name] = (new_min, new_max)
                            self.applied_heuristics.append("close_interval")
                            self._debug_log(f"Vytvořen nový interval pro atribut {attr_name} třídy {good_obj.class_name}: ({new_min}, {new_max})")
        
        # 2. Zpracování near-miss příkladů - vyloučení hodnot
        if near_miss:
            for near_miss_obj in near_miss.objects:
                if not near_miss_obj.attributes:
                    continue
                    
                for attr_name, attr_value in near_miss_obj.attributes.items():
                    # Zajímají nás pouze numerické hodnoty
                    if not isinstance(attr_value, (int, float)):
                        continue
                    
                    # Najdeme odpovídající objekty v modelu
                    for obj in updated_model.objects:
                        if obj.class_name == near_miss_obj.class_name and obj.attributes and attr_name in obj.attributes:
                            # Pokud atribut existuje a je to interval
                            if isinstance(obj.attributes[attr_name], tuple) and len(obj.attributes[attr_name]) == 2:
                                current_min, current_max = obj.attributes[attr_name]
                                
                                # Pokud hodnota near-miss příkladu je v intervalu, zúžíme interval
                                if current_min <= attr_value <= current_max:
                                    # Vyloučíme hodnotu z intervalu s malou tolerancí
                                    tolerance = max(0.01, abs(attr_value) * 0.01)  # 1% tolerance nebo minimálně 0.01
                                    
                                    # Určíme, na kterou stranu zúžit interval
                                    if attr_value - current_min < current_max - attr_value:
                                        # Hodnota je blíže k dolní hranici, posuneme dolní hranici nad hodnotu
                                        new_min = attr_value + tolerance
                                        if new_min < current_max:  # Ujistíme se, že interval je stále platný
                                            obj.attributes[attr_name] = (new_min, current_max)
                                            self.applied_heuristics.append("close_interval")
                                            self._debug_log(f"Zúžen interval atributu {attr_name} pro třídu {near_miss_obj.class_name} vyloučením hodnoty {attr_value}")
                                    else:
                                        # Hodnota je blíže k horní hranici, posuneme horní hranici pod hodnotu
                                        new_max = attr_value - tolerance
                                        if new_max > current_min:  # Ujistíme se, že interval je stále platný
                                            obj.attributes[attr_name] = (current_min, new_max)
                                            self.applied_heuristics.append("close_interval")
                                            self._debug_log(f"Zúžen interval atributu {attr_name} pro třídu {near_miss_obj.class_name} vyloučením hodnoty {attr_value}")
        
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
                    new_link = Link(source=ancestor, target=target, link_type=LinkType.MUST)
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

    def _apply_forbid_link(self, model: Model, good: Model, near_miss: Model):
        """
        Vylepšená implementace forbid-link heuristiky.
        
        Identifikuje klíčové rozdíly mezi pozitivním a near-miss příkladem
        a vytváří MUST_NOT pravidla, ale s lepší kontrolou konfliktu.
        
        Args:
            model: Aktuální model
            good: Pozitivní příklad
            near_miss: Near-miss příklad
            
        Returns:
            Aktualizovaný model
        """
        updated_model = model.copy()
        
        # Safety check
        if near_miss is None:
            self._debug_log("Přeskakuji forbid-link: chybí near-miss příklad")
            return updated_model
        
        # 1. Identifikujeme komponenty, které jsou v near-miss, ale ne v good příkladu
        near_miss_components = self._get_component_class_set(near_miss)
        good_components = self._get_component_class_set(good)
        
        # Unikátní komponenty v near-miss
        unique_components = near_miss_components - good_components
        
        # 2. Pro klíčové rozdíly vytvořit MUST_NOT pravidla
        for near_miss_link in near_miss.links:
            near_miss_source = next((obj for obj in near_miss.objects if obj.name == near_miss_link.source), None)
            near_miss_target = next((obj for obj in near_miss.objects if obj.name == near_miss_link.target), None)
            
            if not near_miss_source or not near_miss_target:
                continue
                
            # Zaměřit se na unikátní komponenty - významné rozdíly
            if near_miss_target.class_name in unique_components:
                # Kontrola existujících MUST pravidel
                has_conflict = False
                
                # Kontrolujeme konflikt s MUST pravidly
                for link in updated_model.links:
                    if (link.link_type == LinkType.MUST and
                        (link.source == near_miss_source.class_name and link.target == near_miss_target.class_name or
                         link.source == near_miss_source.class_name and self.classification_tree.is_subclass(near_miss_target.class_name, link.target) or
                         link.source == near_miss_source.class_name and self.classification_tree.is_subclass(link.target, near_miss_target.class_name))):
                        has_conflict = True
                        self._debug_log(f"Přeskakuji MUST_NOT pravidlo kvůli konfliktu: {near_miss_source.class_name} -> {near_miss_target.class_name}")
                        break
                
                if not has_conflict:
                    # Vytvořit MUST_NOT pravidlo na úrovni tříd
                    must_not_link = Link(
                        source=near_miss_source.class_name,
                        target=near_miss_target.class_name,
                        link_type=LinkType.MUST_NOT
                    )
                    
                    # Ověřit, že pravidlo ještě neexistuje
                    if not any(link.source == must_not_link.source and 
                               link.target == must_not_link.target and 
                               link.link_type == must_not_link.link_type 
                               for link in updated_model.links):
                        updated_model.add_link(must_not_link)
                        self.applied_heuristics.append("forbid_link")
                        self._debug_log(f"Přidáno pravidlo MUST_NOT pro klíčový rozdíl: {near_miss_source.class_name} -> {near_miss_target.class_name}")
        
                    # Přidat také konkrétní vazbu na úrovni objektů
                    inst_link = Link(
                        source=near_miss_link.source,
                        target=near_miss_link.target,
                        link_type=LinkType.MUST_NOT
                    )
                    
                    if not updated_model.has_link(inst_link):
                        updated_model.add_link(inst_link)
                        self.applied_heuristics.append("forbid_link")
                        self._debug_log(f"Přidána MUST_NOT vazba na úrovni objektů: {near_miss_link.source} -> {near_miss_link.target}")
        
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
            # Ověřit, zda třída je komponenta
            parent_class = obj.class_name
            while parent_class:
                if parent_class == "Component":
                    component_classes.add(obj.class_name)
                    break
                parent_class = self.classification_tree.get_parent(parent_class)
        
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