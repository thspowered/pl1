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
        Aktualizuje model na základě pozitívneho príkladu a near-miss príkladu.
        
        Postupne aplikuje heuristiky v špecifickom poradí na základe ich dôležitosti:
        1. add-missing - když model je prázdný, přidá všechny objekty z first example
        2. check-consistency - zkontroluje a vyřeší konflikty v hierarchii
        3. climb-tree - zobecnění na vyšší úroveň
        4. require-link - přidá pozitivní vazby
        5. forbid-link - přidá negativní vazby
        6. drop-link - odstraní nepotřebné vazby
        
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
        
        # 3. Climb-tree - nejdůležitější heuristika pro generalizaci
        self._debug_log("Skúšam climb-tree heuristiku...")
        updated_model = self._apply_climb_tree(updated_model, good, near_miss)
            
        # 4. Require-link - přidá MUST spojení, pokud jsou v positive example
        self._debug_log("Skúšam require-link heuristiku...")
        updated_model = self._apply_require_link(updated_model, good, near_miss)
            
        # 5. Forbid-link - identifikuje, co by objekt neměl mít
        if near_miss:
            self._debug_log("Skúšam forbid-link heuristiku...")
            updated_model = self._apply_forbid_link(updated_model, good, near_miss)
            
        # 6. Drop-link - nejnižší priorita, odstraní nepotřebné vazby
        if not self.applied_heuristics:
            self._debug_log("Skúšam drop-link heuristiku...")
            updated_model = self._apply_drop_link(updated_model, good, near_miss)
        
        # Výpis aplikovaných heuristík
        if self.applied_heuristics:
            self._debug_log(f"Aplikované heuristiky: {', '.join(self.applied_heuristics)}")
        else:
            self._debug_log("Žiadna heuristika nebola aplikovaná")
            
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
            
            # Ak spojenie není v near_miss příkladu, může jít o klíčovou vazbu
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
        Aplikuje forbid-link heuristiku.
        
        Ak je v near-miss príklade spojenie, ktoré chýba v pozitívnom príklade,
        pridá ho ako zakázané MUST_NOT - ale jen pokud již neexistuje konfliktní MUST pravidlo.
        
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
        
        # Najdeme klíčové rozdíly mezi pozitivním a near-miss příkladem
        # Zaměříme se na spojení v near-miss, která nejsou v pozitivním příkladu
        for near_miss_link in near_miss.links:
            near_miss_source = next((obj for obj in near_miss.objects if obj.name == near_miss_link.source), None)
            near_miss_target = next((obj for obj in near_miss.objects if obj.name == near_miss_link.target), None)
            
            if not near_miss_source or not near_miss_target:
                continue
                
            # Zjistíme, zda podobné spojení existuje v pozitivním příkladu
            has_similar_link = False
            
            for good_link in good.links:
                good_source = next((obj for obj in good.objects if obj.name == good_link.source), None)
                good_target = next((obj for obj in good.objects if obj.name == good_link.target), None)
                
                if not good_source or not good_target:
                    continue
                
                # Kontrolujeme, zda nejde o stejný typ vazby
                if (good_source.class_name == near_miss_source.class_name and
                    good_target.class_name == near_miss_target.class_name):
                    has_similar_link = True
                    break
            
            # Pokud podobná vazba v pozitivním příkladu neexistuje, mohlo by jít o klíčový rozdíl
            if not has_similar_link:
                # Nejprve zkontrolujeme, zda by nové MUST_NOT pravidlo nebylo v konfliktu s existujícím MUST
                has_conflict = False
                
                # Kontrola existujících MUST pravidel, aby nedošlo ke konfliktu
                for link in updated_model.links:
                    if (link.link_type == LinkType.MUST and
                        (link.source == near_miss_source.class_name and link.target == near_miss_target.class_name or
                         link.source == near_miss_source.class_name and self.classification_tree.is_subclass(near_miss_target.class_name, link.target) or
                         link.source == near_miss_source.class_name and self.classification_tree.is_subclass(link.target, near_miss_target.class_name))):
                        has_conflict = True
                        self._debug_log(f"Přeskakuji MUST_NOT pravidlo kvůli konfliktu: {near_miss_source.class_name} -> {near_miss_target.class_name}")
                        break
                
                if not has_conflict:
                    # Vytvoříme generické pravidlo MUST_NOT
                    must_not_link = Link(
                        source=near_miss_source.class_name,
                        target=near_miss_target.class_name,
                        link_type=LinkType.MUST_NOT
                    )
                    
                    # Zkontrolujeme, zda pravidlo už neexistuje
                    if not any(link.source == must_not_link.source and 
                               link.target == must_not_link.target and 
                               link.link_type == must_not_link.link_type 
                               for link in updated_model.links):
                        updated_model.add_link(must_not_link)
                        self.applied_heuristics.append("forbid_link")
                        self._debug_log(f"Přidáno pravidlo MUST_NOT: {near_miss_source.class_name} -> {near_miss_target.class_name}")
                    
                    # Vytvoříme i konkrétní vazbu na úrovni objektů
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
            # Kontrola, zda existuje generické pravidlo pro tyto třídy
            source_obj = next((obj for obj in updated_model.objects if obj.name == link_to_remove.source), None)
            target_obj = next((obj for obj in updated_model.objects if obj.name == link_to_remove.target), None)
            
            if source_obj and target_obj:
                # Zjistíme, zda existuje generické pravidlo mezi třídami
                has_generic_rule = any(
                    link.source == source_obj.class_name and 
                    link.target == target_obj.class_name
                    for link in updated_model.links
                )
                
                if not has_generic_rule:
                    # Odstránime spojenie
                    updated_model.remove_link(link_to_remove)
                    self.applied_heuristics.append("drop_link")
                    self._debug_log(f"Odstránená nepodstatná väzba: {link_to_remove.source} -> {link_to_remove.target}")
                else:
                    self._debug_log(f"Ponechávám väzbu {link_to_remove.source} -> {link_to_remove.target} kvůli generickému pravidlu")
        
        return updated_model

    def _apply_climb_tree(self, model: Model, good: Model, near_miss: Model):
        """
        Aplikuje climb-tree heuristiku pro nalezení společných předků.
        
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
        
        # 2. Generalizace na základě hierarchie - vytvoření rodičovských vazeb
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
        
        return updated_model 