from backend.model import Model, Link, LinkType, ClassificationTree, Object
from backend.pl1_parser import Formula, Predicate
from typing import List, Dict, Set, Tuple, Optional, Any
import traceback
from datetime import datetime
import time

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
    
    def _debug_log(self, message):
        """Debugovacie logovanie pre sledovanie priebehu algoritmu."""
        if self.debug_enabled:
            print(f"[WinstonLearner] {message}")

    def update_model(self, model: Model, good: Model, near_miss: Model) -> Model:
        """
        Aktualizuje model na základe pozitívneho príkladu a near-miss príkladu.
        
        Postupne aplikuje heuristiky v špecifickom poradí na základe ich dôležitosti:
        1. require-link
        2. forbid-link
        3. drop-link
        4. climb-tree
        5. close-interval
        6. enlarge-set
        
        Aplikuje všetky relevantné heuristiky a vráti aktualizovaný model.
        
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
        
        # Debugovanie
        self._debug_log("Začínam aktualizáciu modelu")
        self._debug_log(f"Pozitívny príklad: {good}")
        self._debug_log(f"Near-miss príklad: {near_miss}")
        
        # 1. Najprv skúsime require-link
        self._debug_log("Skúšam require-link heuristiku...")
        updated_model = self._apply_require_link(updated_model, good, near_miss)
            
        # 2. Skúsime forbid-link
        self._debug_log("Skúšam forbid-link heuristiku...")
        updated_model = self._apply_forbid_link(updated_model, good, near_miss)
            
        # 3. Skúsime drop-link
        self._debug_log("Skúšam drop-link heuristiku...")
        updated_model = self._apply_drop_link(updated_model, good, near_miss)
            
        # 4. Skúsime climb-tree
        self._debug_log("Skúšam climb-tree heuristiku...")
        updated_model = self._apply_climb_tree(updated_model, good, near_miss)
            
        # 5. Skúsime close-interval
        self._debug_log("Skúšam close-interval heuristiku...")
        updated_model = self._apply_close_interval(updated_model, good, near_miss)
            
        # 6. Skúsime enlarge-set
        self._debug_log("Skúšam enlarge-set heuristiku...")
        updated_model = self._apply_enlarge_set(updated_model, good, near_miss)
        
        # Výpis aplikovaných heuristík
        if self.applied_heuristics:
            self._debug_log(f"Aplikované heuristiky: {', '.join(self.applied_heuristics)}")
        else:
            self._debug_log("Žiadna heuristika nebola aplikovaná")
            
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
        # Kópia modelu
        updated_model = model.copy()
        
        # Najprv skontrolujeme, či sú v modeli spojenia typu REGULAR, ktoré by sme mali 
        # previesť na MUST na základe rozdielov medzi good a near_miss
        for good_link in good.links:
            # Nájdeme zodpovedajúce objekty v positive a near_miss
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
                    
                # Ak sú objekty rovnakého typu a smerujú k rovnakému cieľu, ale cieľ je iný
                if (good_source.class_name == near_miss_source.class_name and 
                    good_target.class_name != near_miss_target.class_name):
                    # Vytvoríme generické pravidlo typu MUST medzi triedami
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
                        self._debug_log(f"Pridané generické pravidlo MUST: {good_source.class_name} -> {good_target.class_name}")
                
                # Ak je spojenie medzi rovnakými objektmi, evidujeme to
                if (good_link.source == near_miss_link.source and 
                    good_link.target == near_miss_link.target):
                    near_miss_has_similar_link = True
            
            # Ak spojenie nie je v near_miss, pridáme zodpovedajúcu MUST väzbu
            if not near_miss_has_similar_link:
                # Vytvoríme generické pravidlo typu MUST medzi triedami
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
                    self._debug_log(f"Pridané generické pravidlo MUST (chýbajúce spojenie v near-miss): {good_source.class_name} -> {good_target.class_name}")
                
                # Pridáme tiež väzbu na úrovni konkrétnych objektov, ak ešte neexistuje
                new_link = Link(
                    source=good_link.source,
                    target=good_link.target,
                    link_type=LinkType.MUST
                )
                
                if not updated_model.has_link(new_link):
                    updated_model.add_link(new_link)
                    self.applied_heuristics.append("require_link")
                    self._debug_log(f"Pridaná MUST väzba na úrovni objektov: {good_link.source} -> {good_link.target}")
        
        return updated_model

    def _apply_forbid_link(self, model: Model, good: Model, near_miss: Model):
        """
        Aplikuje forbid-link heuristiku.
        
        Ak je v near-miss príklade spojenie, ktoré chýba v pozitívnom príklade,
        pridá ho ako zakázané MUST_NOT.
        
        Args:
            model: Aktuálny model
            good: Pozitívny príklad
            near_miss: Near-miss príklad
            
        Returns:
            Aktualizovaný model
        """
        # Kópia modelu
        updated_model = model.copy()
        
        # Podobný postup ako pri require-link, ale s opačnou logikou
        for near_miss_link in near_miss.links:
            # Nájdeme zodpovedajúce objekty v near_miss a good
            near_miss_source = next((obj for obj in near_miss.objects if obj.name == near_miss_link.source), None)
            near_miss_target = next((obj for obj in near_miss.objects if obj.name == near_miss_link.target), None)
            
            if not near_miss_source or not near_miss_target:
                continue
                
            # Skontrolujme, či rovnaké triedy objektov majú spojenie v positive
            good_has_similar_link = False
            
            for good_link in good.links:
                good_source = next((obj for obj in good.objects if obj.name == good_link.source), None)
                good_target = next((obj for obj in good.objects if obj.name == good_link.target), None)
                
                if not good_source or not good_target:
                    continue
                    
                # Ak sú objekty rovnakého typu a smerujú k rovnakému cieľu, ale cieľ je iný
                if (near_miss_source.class_name == good_source.class_name and 
                    near_miss_target.class_name != good_target.class_name):
                    # Vytvoríme generické pravidlo typu MUST_NOT medzi triedami
                    must_not_link = Link(
                        source=near_miss_source.class_name,
                        target=near_miss_target.class_name,
                        link_type=LinkType.MUST_NOT
                    )
                    
                    # Skontrolujeme, či pravidlo ešte nie je v modeli
                    if not any(link.source == must_not_link.source and 
                               link.target == must_not_link.target and 
                               link.link_type == must_not_link.link_type 
                               for link in updated_model.links):
                        updated_model.add_link(must_not_link)
                        self.applied_heuristics.append("forbid_link")
                        self._debug_log(f"Pridané generické pravidlo MUST_NOT: {near_miss_source.class_name} -> {near_miss_target.class_name}")
                
                # Ak je spojenie medzi rovnakými objektmi, evidujeme to
                if (near_miss_link.source == good_link.source and 
                    near_miss_link.target == good_link.target):
                    good_has_similar_link = True
            
            # Ak spojenie nie je v positive, pridáme zodpovedajúcu MUST_NOT väzbu
            if not good_has_similar_link:
                # Vytvoríme generické pravidlo typu MUST_NOT medzi triedami
                must_not_link = Link(
                    source=near_miss_source.class_name,
                    target=near_miss_target.class_name,
                    link_type=LinkType.MUST_NOT
                )
                
                # Skontrolujeme, či pravidlo ešte nie je v modeli
                if not any(link.source == must_not_link.source and 
                           link.target == must_not_link.target and 
                           link.link_type == must_not_link.link_type 
                           for link in updated_model.links):
                    updated_model.add_link(must_not_link)
                    self.applied_heuristics.append("forbid_link")
                    self._debug_log(f"Pridané generické pravidlo MUST_NOT (chýbajúce spojenie v good): {near_miss_source.class_name} -> {near_miss_target.class_name}")
                
                # Pridáme tiež väzbu na úrovni konkrétnych objektov, ak ešte neexistuje
                new_link = Link(
                    source=near_miss_link.source,
                    target=near_miss_link.target,
                    link_type=LinkType.MUST_NOT
                )
                
                if not updated_model.has_link(new_link):
                    updated_model.add_link(new_link)
                    self.applied_heuristics.append("forbid_link")
                    self._debug_log(f"Pridaná MUST_NOT väzba na úrovni objektov: {near_miss_link.source} -> {near_miss_link.target}")
        
        return updated_model
    
    def _apply_drop_link(self, model: Model, good: Model, near_miss: Model):
        """
        Aplikuje drop-link heuristiku.
        
        Odstráni z modelu spojenia, ktoré nie sú v pozitívnom príklade.
        
        Args:
            model: Aktuálny model
            good: Pozitívny príklad
            near_miss: Near-miss príklad
            
        Returns:
            Aktualizovaný model
        """
        # Kópia modelu
        updated_model = model.copy()
        
        # Nájdeme všetky REGULAR spojenia v modeli
        regular_links = [link for link in updated_model.links 
                         if link.link_type == LinkType.REGULAR]
        
        links_to_remove = []
        
        # Pre každé regulárne spojenie
        for model_link in regular_links:
            # Nájdeme zodpovedajúce spojenie v positive príklade
            has_corresponding = False
            for good_link in good.links:
                if (model_link.source == good_link.source and 
                    model_link.target == good_link.target):
                    has_corresponding = True
                    break
                    
            # Ak spojenie nemá zodpovedajúce spojenie v positive, môžeme ho odstrániť
            if not has_corresponding:
                links_to_remove.append(model_link)
                
        # Odstránime nepotrebné spojenia
        for link_to_remove in links_to_remove:
            # Odstránime spojenie
            updated_model.remove_link(link_to_remove)
            self.applied_heuristics.append("drop_link")
            self._debug_log(f"Odstránená nepodstatná väzba: {link_to_remove.source} -> {link_to_remove.target}")
        
        return updated_model

    def _apply_climb_tree(self, model: Model, good: Model, near_miss: Model):
        """
        Aplikuje climb-tree heuristiku.
        
        Ak sú v positive a near-miss príklade podobné objekty s rôznymi triedami,
        nájde spoločného predka v klasifikačnom strome a generalizuje model.
        
        Args:
            model: Aktuálny model
            good: Pozitívny príklad
            near_miss: Near-miss príklad
            
        Returns:
            Aktualizovaný model
        """
        # Kópia modelu
        updated_model = model.copy()
        
        # Najprv nájdeme možné páry objektov medzi positive a near-miss príkladmi
        potential_pairs = []
        
        for good_obj in good.objects:
            for near_miss_obj in near_miss.objects:
                # Ak majú rovnaký názov, ale rôzne triedy
                if (good_obj.name == near_miss_obj.name and 
                    good_obj.class_name != near_miss_obj.class_name):
                    potential_pairs.append((good_obj, near_miss_obj))
                    
        # Pre každý potenciálny pár
        for good_obj, near_miss_obj in potential_pairs:
            # Nájdeme spoločného predka v klasifikačnom strome
            common_ancestor = self.classification_tree.find_common_ancestor(
                good_obj.class_name,
                near_miss_obj.class_name
            )
            
            if common_ancestor:
                # Prejdeme všetky spojenia objektov v modeli
                for model_obj in updated_model.objects:
                    # Ak model obsahuje objekt s rovnakým názvom
                    if model_obj.name == good_obj.name:
                        # Ak model obsahuje spojenia s týmto objektom ako zdrojom
                        for link in list(updated_model.links):
                            if link.source == model_obj.name:
                                # Získame cieľový objekt
                                target_obj = next((obj for obj in updated_model.objects if obj.name == link.target), None)
                                
                                if target_obj:
                                    # Vytvoríme generické pravidlo medzi spoločným predkom a cieľom
                                    generic_link = Link(
                                        source=common_ancestor,
                                        target=target_obj.class_name,
                                        link_type=link.link_type
                                    )
                                    
                                    # Pridáme generické pravidlo do modelu
                                    if not updated_model.has_link(generic_link):
                                        updated_model.add_link(generic_link)
                                        self.applied_heuristics.append("climb_tree")
                                        self._debug_log(f"Pridané generické pravidlo (climb-tree): {common_ancestor} -> {target_obj.class_name}")
                            
                            # Ak model obsahuje spojenia s týmto objektom ako cieľom
                            elif link.target == model_obj.name:
                                # Získame zdrojový objekt
                                source_obj = next((obj for obj in updated_model.objects if obj.name == link.source), None)
                                
                                if source_obj:
                                    # Vytvoríme generické pravidlo medzi zdrojom a spoločným predkom
                                    generic_link = Link(
                                        source=source_obj.class_name,
                                        target=common_ancestor,
                                        link_type=link.link_type
                                    )
                                    
                                    # Pridáme generické pravidlo do modelu
                                    if not updated_model.has_link(generic_link):
                                        updated_model.add_link(generic_link)
                                        self.applied_heuristics.append("climb_tree")
                                        self._debug_log(f"Pridané generické pravidlo (climb-tree): {source_obj.class_name} -> {common_ancestor}")
        
        return updated_model
    
    def _apply_enlarge_set(self, model: Model, good: Model, near_miss: Model):
        """
        Aplikuje enlarge-set heuristiku.
        
        Ak sú v modeli a v pozitívnom príklade atribúty s rôznymi hodnotami,
        vytvorí množinu hodnôt pre tento atribút.
        
        Args:
            model: Aktuálny model
            good: Pozitívny príklad
            near_miss: Near-miss príklad (nie je potrebný pre túto heuristiku)
            
        Returns:
            Aktualizovaný model
        """
        # Kópia modelu
        updated_model = model.copy()
        
        # Najprv nájdeme, či má model nejaké atribúty s hodnotami množiny
        for obj in good.objects:
            # Skontrolujeme, či objekt má atribúty pred prístupom k items()
            if obj.attributes is None:
                continue
            
            for attr_name, attr_value in obj.attributes.items():
                # Preskočíme číselné hodnoty (tie spracováva close-interval)
                if isinstance(attr_value, (int, float)):
                    continue
                    
                # Nájdeme zodpovedajúci objekt v modeli
                model_obj = next((mo for mo in updated_model.objects if mo.name == obj.name), None)
                
                if model_obj and model_obj.attributes:
                    # Ak objekt v modeli má rovnaký atribút
                    if attr_name in model_obj.attributes:
                        model_attr = model_obj.attributes[attr_name]
                        
                        # Ak je atribút definovaný ako množina
                        if isinstance(model_attr, set):
                            # Ak hodnota ešte nie je v množine, pridáme ju
                            if attr_value not in model_attr:
                                new_set = model_attr.copy()
                                new_set.add(attr_value)
                                model_obj.attributes[attr_name] = new_set
                                self.applied_heuristics.append("enlarge_set")
                                self._debug_log(f"Rozšírená množina pre {obj.name}.{attr_name}: {new_set}")
                        
                        # Ak je atribút definovaný ako konkrétna hodnota, vytvoríme množinu
                        elif model_attr != attr_value:
                            model_obj.attributes[attr_name] = {model_attr, attr_value}
                            self.applied_heuristics.append("enlarge_set")
                            self._debug_log(f"Vytvorená množina pre {obj.name}.{attr_name}: {{{model_attr}, {attr_value}}}")
        
        return updated_model
    
    def _apply_close_interval(self, model: Model, good: Model, near_miss: Model):
        """
        Aplikuje close-interval heuristiku.
        
        Ak má atribút v pozitívnom príklade číselnú hodnotu, upraví interval
        pre tento atribút, aby zahŕňal hodnotu z pozitívneho príkladu.
        
        Args:
            model: Aktuálny model
            good: Pozitívny príklad
            near_miss: Near-miss príklad (nie je potrebný pre túto heuristiku, ale
                       pre konzistentnosť s ostatnými heuristikami)
            
        Returns:
            Aktualizovaný model
        """
        # Kópia modelu
        updated_model = model.copy()
        
        # Najprv nájdeme, či má model nejaké numerické atribúty
        for obj in good.objects:
            # Skontrolujeme, či objekt má atribúty pred prístupom k items()
            if obj.attributes is None:
                continue
            
            for attr_name, attr_value in obj.attributes.items():
                if isinstance(attr_value, (int, float)):
                    numeric_value = attr_value
                    
                    # Nájdeme zodpovedajúci objekt v modeli
                    model_obj = next((mo for mo in updated_model.objects if mo.name == obj.name), None)
                    
                    if model_obj and model_obj.attributes:
                        # Ak objekt v modeli má rovnaký atribút, ale s intervalom
                        if attr_name in model_obj.attributes:
                            model_attr = model_obj.attributes[attr_name]
                            
                            # Ak je atribút definovaný ako interval [min, max]
                            if isinstance(model_attr, list) and len(model_attr) == 2:
                                min_val, max_val = model_attr
                                
                                # Ak je hodnota mimo interval, upravíme ho
                                changed = False
                                if numeric_value < min_val:
                                    min_val = numeric_value
                                    changed = True
                                if numeric_value > max_val:
                                    max_val = numeric_value
                                    changed = True
                                    
                                if changed:
                                    model_obj.attributes[attr_name] = [min_val, max_val]
                                    self.applied_heuristics.append("close_interval")
                                    self._debug_log(f"Upravený interval pre {obj.name}.{attr_name}: [{min_val}, {max_val}]")
                            
                            # Ak je atribút definovaný ako konkrétna hodnota, vytvoríme interval
                            elif isinstance(model_attr, (int, float)) and model_attr != numeric_value:
                                min_val = min(model_attr, numeric_value)
                                max_val = max(model_attr, numeric_value)
                                model_obj.attributes[attr_name] = [min_val, max_val]
                                self.applied_heuristics.append("close_interval")
                                self._debug_log(f"Vytvorený interval pre {obj.name}.{attr_name}: [{min_val}, {max_val}]")
        
        return updated_model 