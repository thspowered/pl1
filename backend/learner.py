from backend.model import Model, Link, LinkType, ClassificationTree, Object
from backend.pl1_parser import Formula, Predicate
from typing import List, Dict, Set, Tuple, Optional, Any
import traceback
from datetime import datetime
import time

class WinstonLearner:
    """
    Implementacia Winstonovho algoritmu ucenia konceptov.
    
    Tato trieda poskytuje funkcionalitu na ucenie a aktualizaciu konceptualneho modelu na zaklade
    pozitivnych prikladov (dobre priklady) a negativnych prikladov (near miss). Implementuje niekolko 
    heuristik odvodenych od uciacej metody Patricka Winstona, ktore aktualizuju model tym, ze ho
    robia vseobecnejsim alebo presnejsim podla potreby.
    
    Algoritmus pouziva klasifikacny strom na pochopenie hierarchickych vztahov medzi
    rozlicnymi triedami objektov, co umoznuje sofistikovanejsie ucenie konceptov.
    """
    
    def __init__(self, classification_tree: ClassificationTree):
        """
        Inicializuje Winston Learner s klasifikacnym stromom.
        
        Parametre:
            classification_tree: Hierarchicka struktura reprezentujuca vztahy medzi triedami,
                                 pouzivana pre operacie generalizacie a klasifikacie.
        """
        self.classification_tree = classification_tree

    def update_model(self, current_model: Model, good_example: Model, near_miss: Model) -> Model:
        """
        Aktualizuje aktualny model aplikovanim vsetkych heuristik na zaklade dobreho prikladu a near miss.
        
        Toto je hlavna funkcia ucenia, ktora aplikuje vsetky Winstonove heuristiky na upresnenie modelu.
        Kazda heuristika specializuje alebo generalizuje model inym sposobom, s vyuzitim
        pozitivneho prikladu (good_example) a negativneho prikladu (near_miss).
        
        Parametre:
            current_model: Existujuci model, ktory sa ma aktualizovat
            good_example: Pozitivny priklad, ktory by mal byt klasifikovany ako platny
            near_miss: Negativny priklad, ktory by mal byt klasifikovany ako neplatny
            
        Navratova hodnota:
            Novy aktualizovany model obsahujuci naucene obmedzenia
        """
        new_model = current_model.copy()
        
        # Aplikuj vsetky heuristiky
        self._apply_require_link(new_model, good_example, near_miss)
        self._apply_forbid_link(new_model, good_example, near_miss)
        self._apply_climb_tree(new_model, good_example, near_miss)
        self._apply_close_interval(new_model, good_example)
        self._apply_drop_link(new_model, good_example, near_miss)
        self._apply_enlarge_set(new_model, good_example, near_miss)
        
        return new_model

    def update_model_with_multiple_negatives(self, current_model: Model, good_example: Model, near_misses: List[Model]) -> Model:
        """
        Aktualizuje aktualny model s jednym pozitivnym prikladom a viacerymi negativnymi prikladmi naraz.
        
        Táto metóda implementuje jadro Winstonovho algoritmu, kde jeden pozitívny príklad je
        porovnávaný so všetkými dostupnými negatívnymi príkladmi. Pre každý negatívny príklad
        sa aplikujú všetky heuristiky, čo vedie k postupnému upresňovaniu modelu.
        
        Parametre:
            current_model: Existujuci model, ktory sa ma aktualizovat
            good_example: Pozitivny priklad, ktory by mal byt klasifikovany ako platny
            near_misses: Zoznam negativnych prikladov, ktore by mali byt klasifikovane ako neplatne
            
        Navratova hodnota:
            Novy aktualizovany model obsahujuci naucene obmedzenia
        """
        if not near_misses:
            print("Warning: No negative examples provided for update")
            return current_model.copy()
        
        # Kontrola vstupu - pozitívny príklad
        if not good_example.objects:
            print("Warning: Positive example has no objects")
            return current_model.copy()
            
        # Kontrola vstupu - negatívne príklady
        valid_near_misses = []
        for i, near_miss in enumerate(near_misses):
            if not near_miss.objects:
                print(f"Warning: Negative example #{i} has no objects, skipping")
                continue
            valid_near_misses.append(near_miss)
            
        if not valid_near_misses:
            print("Warning: No valid negative examples after filtering")
            return current_model.copy()
        
        print(f"Updating model with 1 positive example and {len(valid_near_misses)} negative examples")
        
        # Začni s kópiou aktuálneho modelu
        new_model = current_model.copy()
        start_time = datetime.now()
        print(f"[TIMING] Start model update with multiple negatives: {start_time.isoformat()}")
        
        try:
            # Aplikuj close_interval, ktorá závisí iba od pozitívneho príkladu
            self._apply_close_interval(new_model, good_example)
        
            # Analýza objektov v pozitívnom príklade pre lepšie porozumenie jeho štruktúre
            print(f"Analyzing positive example with {len(good_example.objects)} objects and {len(good_example.links)} links")
            
            # Zmapujeme typy objektov v pozitívnom príklade pre rýchlejšie vyhľadávanie
            object_types_in_positive = {}
            for obj in good_example.objects:
                class_name = obj.class_name
                if class_name not in object_types_in_positive:
                    object_types_in_positive[class_name] = []
                object_types_in_positive[class_name].append(obj.name)
            
            print(f"Object types in positive example: {object_types_in_positive}")
            
            # Analýza chýbajúcich komponentov v negatívnych príkladoch
            missing_component_types = set()
            
            # Časomiera pre analýzu negatívnych príkladov
            analysis_start = time.time()
            
            # Analyzuj každý negatívny príklad
            for i, near_miss in enumerate(valid_near_misses):
                print(f"[TIMING] Analyzing negative example #{i+1}/{len(valid_near_misses)}")
                print(f"Comparing with negative example containing {len(near_miss.objects)} objects and {len(near_miss.links)} links")
                
                # Bezpečnostný časový limit
                if time.time() - analysis_start > 60:
                    print("Warning: Component analysis taking too long, aborting further analysis")
                    break
            
                # Zmapujeme typy objektov v negatívnom príklade
                object_types_in_negative = set()
                for obj in near_miss.objects:
                    object_types_in_negative.add(obj.class_name)
                
                # Nájdi chýbajúce typy objektov (komponenty, ktoré sú v pozitívnom ale nie v negatívnom príklade)
                for positive_type in object_types_in_positive:
                    if positive_type not in object_types_in_negative:
                        print(f"Missing component type in negative example: {positive_type}")
                        missing_component_types.add(positive_type)
            
            # Ak sme našli chýbajúce komponenty, pridaj MUST spojenia
            if missing_component_types:
                print(f"Found {len(missing_component_types)} missing component types: {missing_component_types}")
                # Najprv nájdi hlavný objekt v pozitívnom príklade (zvyčajne triedy BMW, auto, atď.)
                main_object = None
                for obj in good_example.objects:
                    if obj.class_name in ["BMW", "Car", "Vehicle", "Auto"]:
                        main_object = obj
                        break
        
                if main_object:
                    print(f"Found main object: {main_object.name} (class: {main_object.class_name})")
                    
                    # Pridaj generické MUST spojenia pre chýbajúce komponenty
                    added_links = 0
                    for missing_type in missing_component_types:
                        # Ak nejde o hlavný objekt, pridaj MUST spojenie
                        if missing_type != main_object.class_name:
                            print(f"Adding generic MUST link: {main_object.class_name} → {missing_type}")
                            # Pridaj generické MUST spojenie (napr. BMW MUST have Engine)
                            new_link = Link(source=main_object.class_name, target=missing_type, link_type=LinkType.MUST)
                            
                            # Kontrola, či už neexistuje rovnaké spojenie
                            exists = False
                            for link in new_model.links:
                                if (link.source == new_link.source and 
                                    link.target == new_link.target and 
                                    link.link_type == new_link.link_type):
                                    exists = True
                                    break
                            
                            if not exists:
                                new_model.links.append(new_link)
                                added_links += 1
                    
                    print(f"Added {added_links} generic MUST links based on missing component types")
            
            # Aplikuj Winstonove heuristiky pre každý negatívny príklad
            heuristic_start = time.time()
            total_changes = 0
            
            print(f"[TIMING] Starting heuristic application at {datetime.now().isoformat()}")
            
            for i, near_miss in enumerate(valid_near_misses):
                heuristic_iteration_start = time.time()
                print(f"[TIMING] Applying heuristics for negative example #{i+1}/{len(valid_near_misses)}")
                
                # Bezpečnostný časový limit pre celkový proces
                if time.time() - heuristic_start > 120:
                    print("Warning: Heuristic application taking too long, stopping further processing")
                    break
                
                # Monitoruj čas strávený v každej heuristike
                time_in_heuristics = {}
                    
                # Aplikuj require_link heuristiku - identifikuje spojenia, ktoré musia byť prítomné
                h_start = time.time()
                self._apply_require_link(new_model, good_example, near_miss)
                time_in_heuristics['require_link'] = time.time() - h_start
                
                # Aplikuj forbid_link heuristiku - identifikuje spojenia, ktoré nesmú byť prítomné
                h_start = time.time()
                self._apply_forbid_link(new_model, good_example, near_miss)
                time_in_heuristics['forbid_link'] = time.time() - h_start
                
                # Aplikuj climb_tree heuristiku - generalizuje hľadaním spoločných predkov
                h_start = time.time()
                self._apply_climb_tree(new_model, good_example, near_miss)
                time_in_heuristics['climb_tree'] = time.time() - h_start
                
                # Aplikuj drop_link heuristiku - eliminuje nepotrebné spojenia
                h_start = time.time()
                self._apply_drop_link(new_model, good_example, near_miss)
                time_in_heuristics['drop_link'] = time.time() - h_start
                
                # Aplikuj enlarge_set heuristiku - vytvára zjednotenia pre funkčne ekvivalentné komponenty
                h_start = time.time()
                self._apply_enlarge_set(new_model, good_example, near_miss)
                time_in_heuristics['enlarge_set'] = time.time() - h_start
                
                heuristic_iteration_time = time.time() - heuristic_iteration_start
                print(f"[TIMING] Completed heuristics in {heuristic_iteration_time:.2f}s: {time_in_heuristics}")
                
                # Kontrola pomalých heuristík
                slow_heuristics = [h for h, t in time_in_heuristics.items() if t > 5.0]
                if slow_heuristics:
                    print(f"Warning: Slow heuristics detected: {slow_heuristics}")
                
                total_changes += 1
            
            total_time = (datetime.now() - start_time).total_seconds()
            print(f"[TIMING] Completed model update in {total_time:.2f} seconds with {total_changes} changes")
            
            return new_model
            
        except Exception as e:
            print(f"Error in update_model_with_multiple_negatives: {str(e)}")
            traceback.print_exc()
            return current_model.copy()

    def update_model_with_new_negatives(self, current_model: Model, negative_examples: List[Model]) -> Tuple[Model, List[str]]:
        """
        Aktualizuje model pomocou nových negatívnych príkladov, pričom používa súčasný model ako pozitívny príklad.
        
        Táto metóda umožňuje pokračovať v trénovaní už existujúceho modelu iba s novými negatívnymi príkladmi.
        Je užitočná, keď chceme model vylepšiť bez potreby opakovať trénovanie so všetkými pozitívnymi príkladmi.
        
        Parametre:
            current_model: Aktuálny natrénovaný model, ktorý sa použije ako pozitívny príklad
            negative_examples: Zoznam nových negatívnych príkladov
            
        Navratové hodnoty:
            Tuple obsahujúci aktualizovaný model a zoznam správ z procesu tréningu
        """
        try:
            print(f"Updating model with {len(negative_examples)} new negative examples using current model as positive example")
            
            if not current_model.objects:
                print("Warning: Current model is empty, cannot use it as positive example")
                return current_model, ["Current model is empty, cannot use it as positive example"]
                
            updated_model = current_model.copy()
            messages = []
            
            # Použi iba validné negatívne príklady
            valid_negative_examples = [neg for neg in negative_examples if neg.objects]
            
            if len(valid_negative_examples) < len(negative_examples):
                print(f"Warning: {len(negative_examples) - len(valid_negative_examples)} empty negative examples were filtered out")
                messages.append(f"Warning: {len(negative_examples) - len(valid_negative_examples)} empty negative examples were filtered out")
                
            if not valid_negative_examples:
                print("Warning: No valid negative examples after filtering")
                return current_model, ["No valid negative examples to process"]
                
            # Postupne aplikuj každý negatívny príklad
            start_time = datetime.now()
            print(f"[TIMING] Starting update with new negatives at {start_time.isoformat()}")
            
            for i, negative_example in enumerate(valid_negative_examples):
                print(f"Processing negative example {i+1}/{len(valid_negative_examples)} with {len(negative_example.objects)} objects")
                messages.append(f"Processing negative example {i+1}/{len(valid_negative_examples)}")
                
                # Kontrola, či obsahuje objekty
                if not negative_example.objects:
                    print(f"Warning: Negative example {i+1} has no objects, skipping")
                    messages.append(f"Warning: Negative example {i+1} has no objects, skipping")
                    continue
                    
                # Použi current_model ako pozitívny príklad a aplikuj Winstonove heuristiky
                example_start_time = time.time()
                print(f"Applying heuristics for negative example {i+1}")
                
                try:
                    # Aplikuj heuristiky v logickom poradí
                    self._apply_forbid_link(updated_model, current_model, negative_example)  # Najprv zakáž nesprávne spojenia
                    self._apply_require_link(updated_model, current_model, negative_example)  # Potom požaduj chýbajúce spojenia
                    self._apply_drop_link(updated_model, current_model, negative_example)  # Odstráň nepotrebné spojenia
                    self._apply_climb_tree(updated_model, current_model, negative_example)  # Generalizuj koncepty
                    
                    # Uprav numerické intervaly - táto heuristika závisí len od pozitívneho príkladu
                    self._apply_close_interval(updated_model, current_model)
                    
                    # Vytvor zjednotenia pre podobné komponenty
                    # Poznámka: táto heuristika môže byť časovo náročná, takže ju používame opatrne
                    if len(updated_model.objects) < 100 and len(negative_example.objects) < 100:
                        self._apply_enlarge_set(updated_model, current_model, negative_example)
                    else:
                        print(f"Skipping enlarge_set heuristic for large model (objects: {len(updated_model.objects)})")
                    
                    elapsed_time = time.time() - example_start_time
                    print(f"Applied heuristics for negative example {i+1} in {elapsed_time:.2f} seconds")
                    messages.append(f"Applied heuristics for negative example {i+1} in {elapsed_time:.2f} seconds")
                except Exception as e:
                    print(f"Error applying heuristics to negative example {i+1}: {str(e)}")
                    traceback.print_exc()
                    messages.append(f"Error with negative example {i+1}: {str(e)}")
                
            total_time = (datetime.now() - start_time).total_seconds()
            print(f"[TIMING] Completed model update with new negatives in {total_time:.2f} seconds")
            messages.append(f"Completed model update with new negatives in {total_time:.2f} seconds")
            
            return updated_model, messages
        except Exception as e:
            print(f"Error in update_model_with_new_negatives: {str(e)}")
            traceback.print_exc()
            return current_model, [f"Error during training: {str(e)}"]

    def _apply_require_link(self, model: Model, good: Model, near_miss: Model):
        """
        Aplikuje heuristiku 'require-link' - identifikuje spojenia, ktore musia byt pritomne.
        
        Tato heuristika hlada spojenia, ktore su pritomne v dobrom priklade, ale chybaju 
        v near miss. Taketo spojenia su potom pridane do modelu ako pozadovane spojenia (typ MUST).
        Toto pomaha identifikovat komponenty alebo spojenia, ktore su nevyhnutne pre koncept.
        
        Parametre:
            model: Model, ktory sa ma aktualizovat
            good: Pozitivny priklad
            near_miss: Negativny priklad
            
        Navratova hodnota:
            None (modifikuje model priamo)
        """
        changes_made = 0
        print(f"Applying require-link heuristic")
        print(f"Good example has {len(good.objects)} objects and {len(good.links)} links")
        print(f"Near miss has {len(near_miss.objects)} objects and {len(near_miss.links)} links")
        
        # Vytvorím zoznam objektov z pozitívneho príkladu, ktoré chýbajú v negatívnom
        good_objects = {obj.name for obj in good.objects}
        near_miss_objects = {obj.name for obj in near_miss.objects}
        missing_objects = good_objects - near_miss_objects
        
        if missing_objects:
            print(f"Found missing objects in near miss: {missing_objects}")
            
        for good_link in good.links:
            if good_link.link_type == LinkType.MUST_BE_A:
                continue
            
            # Ak jeden z objektov v spojení chýba v negatívnom príklade, považujeme to za chýbajúce spojenie
            if good_link.source in missing_objects or good_link.target in missing_objects:
                print(f"Link {good_link.source} -> {good_link.target} is implicitly missing in near miss because object(s) are missing")
                has_equivalent = False
            else:
                has_equivalent = any(
                    l.source == good_link.source and l.target == good_link.target 
                    for l in near_miss.links
                )
            
            if not has_equivalent:
                print(f"Found missing link {good_link.source} -> {good_link.target} in near miss")
                # Skontroluj, ci spojenie uz existuje
                link_exists = model.has_link(Link(
                    good_link.source,
                    good_link.target,
                    LinkType.MUST
                ))
                
                if not link_exists:
                    print(f"Adding MUST link: {good_link.source} -> {good_link.target}")
                    model.add_link(Link(
                        good_link.source,
                        good_link.target,
                        LinkType.MUST
                    ))
                    changes_made += 1
        
        if changes_made:
            print(f"Made {changes_made} changes to the model with require-link heuristic")
        else:
            print(f"No changes made to the model with require-link heuristic")

    def _apply_forbid_link(self, model: Model, good: Model, near_miss: Model):
        """
        Aplikuje heuristiku 'forbid-link' - identifikuje spojenia, ktore nesmú byt pritomne.
        
        Tato heuristika hlada spojenia, ktore su pritomne v near miss, ale chybaju 
        v dobrom priklade. Taketo spojenia su potom pridane do modelu ako zakazane spojenia 
        (typ MUST_NOT). Toto pomaha identifikovat komponenty alebo spojenia, ktore porusuju koncept.
        
        Parametre:
            model: Model, ktory sa ma aktualizovat
            good: Pozitivny priklad
            near_miss: Negativny priklad
            
        Navratova hodnota:
            None (modifikuje model priamo)
        """
        changes_made = 0
        print(f"Applying forbid-link heuristic")
        
        # Vytvorím zoznam objektov z negatívneho príkladu, ktoré chýbajú v pozitívnom
        near_miss_objects = {obj.name for obj in near_miss.objects}
        good_objects = {obj.name for obj in good.objects}
        objects_only_in_near_miss = near_miss_objects - good_objects
        
        if objects_only_in_near_miss:
            print(f"Found objects only in near miss: {objects_only_in_near_miss}")
            
            # Pre objekty, ktoré sú iba v negatívnom príklade, pridáme MUST_NOT spojenia
            # na ich rodičovské objekty, ktoré existujú aj v pozitívnom príklade
            for near_miss_link in near_miss.links:
                if near_miss_link.link_type == LinkType.MUST_BE_A:
                    continue
                    
                # Ak cieľový objekt spojenia je iba v negatívnom príklade a zdrojový objekt
                # existuje v oboch príkladoch, pridáme MUST_NOT spojenie
                if near_miss_link.target in objects_only_in_near_miss and near_miss_link.source in good_objects:
                    print(f"Found connection to object that only exists in near miss: {near_miss_link.source} -> {near_miss_link.target}")
                    
                    # Skontroluj, či spojenie už existuje
                    link_exists = model.has_link(Link(
                        near_miss_link.source,
                        near_miss_link.target,
                        LinkType.MUST_NOT
                    ))
                    
                    if not link_exists:
                        print(f"Adding MUST_NOT link: {near_miss_link.source} -> {near_miss_link.target}")
                        model.add_link(Link(
                            near_miss_link.source,
                            near_miss_link.target,
                            LinkType.MUST_NOT
                        ))
                        changes_made += 1
                        
        # Štandardné spracovanie spojení, ktoré sú v negatívnom príklade ale nie v pozitívnom
        for bad_link in near_miss.links:
            if bad_link.link_type == LinkType.MUST_BE_A:
                continue
                
            # Preskočíme spojenia, ktoré zahŕňajú objekty, ktoré sú iba v negatívnom príklade
            # (tieto sme už riešili vyššie)
            if bad_link.source in objects_only_in_near_miss or bad_link.target in objects_only_in_near_miss:
                continue
                
            has_equivalent = any(
                l.source == bad_link.source and l.target == bad_link.target 
                for l in good.links
            )
            
            if not has_equivalent:
                print(f"Found link in near miss not present in good example: {bad_link.source} -> {bad_link.target}")
                # Skontroluj, ci spojenie uz existuje
                link_exists = model.has_link(Link(
                    bad_link.source,
                    bad_link.target,
                    LinkType.MUST_NOT
                ))
                
                if not link_exists:
                    print(f"Adding MUST_NOT link: {bad_link.source} -> {bad_link.target}")
                    model.add_link(Link(
                        bad_link.source,
                        bad_link.target,
                        LinkType.MUST_NOT
                    ))
                    changes_made += 1
                    
        if changes_made:
            print(f"Made {changes_made} changes to the model with forbid-link heuristic")
        else:
            print(f"No changes made to the model with forbid-link heuristic")

    def _apply_climb_tree(self, model: Model, good: Model, near_miss: Model):
        """
        Aplikuje heuristiku 'climb-tree' - generalizuje najdenim spolocnych predkov.
        
        Ked objekty s rovnakym nazvom maju rozne triedy v modeli a v dobrom priklade,
        tato heuristika najde spolocneho predka v klasifikacnom strome a aktualizuje
        triedu objektu v modeli. Toto umoznuje modelu generalizovat koncept
        postupom nahor v klasifikacnej hierarchii.
        
        Parametre:
            model: Model, ktory sa ma aktualizovat
            good: Pozitivny priklad
            near_miss: Negativny priklad
            
        Navratova hodnota:
            None (modifikuje model priamo)
        """
        changes_made = 0
        
        # Sleduj objekty v modeli aj v priklade
        for model_obj in model.objects:
            for good_obj in good.objects:
                # Ak maju rovnaky nazov, ale rozne triedy
                if model_obj.name == good_obj.name and model_obj.class_name != good_obj.class_name:
                    # Najdi spolocneho predka v strome
                    common_ancestor = self.classification_tree.find_common_ancestor(model_obj.class_name, good_obj.class_name)
                    
                    if common_ancestor:
                        # Aktualizuj triedu objektu v modeli
                        old_class = model_obj.class_name
                        model.update_object_class(model_obj.name, common_ancestor)
                        
                        # Pridaj spojenie MUST_BE_A na spolocneho predka
                        model.add_link(Link(model_obj.name, common_ancestor, LinkType.MUST_BE_A))
                        
                        changes_made += 1

    def _apply_close_interval(self, model: Model, good: Model):
        """
        Aplikuje heuristiku 'close-interval' - spracovava numericke atributy vytvaranim intervalov.
        
        Tato heuristika spravuje numericke atributy vytvaranim intervalov (min, max), ked 
        narazi na rozne hodnoty. Bud vytvori novy interval z jednotlivych hodnot,
        alebo rozsiri existujuce intervaly tak, aby zahrnali nove hodnoty, cim zabezpeci, ze model moze
        spracovat rozsah platnych numerickych hodnot namiesto presnych zhod.
        
        Parametre:
            model: Model, ktory sa ma aktualizovat
            good: Pozitivny priklad
            
        Navratova hodnota:
            None (modifikuje model priamo)
        """
        changes_made = 0
        
        # Spracuj vsetky objekty a ich atributy
        for good_obj in good.objects:
            if not good_obj.attributes:
                continue
                
            for attr_name, attr_value in good_obj.attributes.items():
                # Ak je atribut numericky
                if isinstance(attr_value, (int, float)) or (isinstance(attr_value, tuple) and all(isinstance(v, (int, float)) for v in attr_value)):
                    # Najdi zodpovedajuci objekt v modeli
                    model_obj = next((obj for obj in model.objects if obj.name == good_obj.name), None)
                    
                    if model_obj:
                        if not model_obj.attributes:
                            model_obj.attributes = {}
                            
                        # Ak model uz ma tento atribut
                        if attr_name in model_obj.attributes:
                            model_value = model_obj.attributes[attr_name]
                            
                            # Ak je aktualna hodnota v modeli tiez numericka
                            if isinstance(model_value, (int, float)) or (isinstance(model_value, tuple) and all(isinstance(v, (int, float)) for v in model_value)):
                                # Ak je v modeli cislo a v priklade cislo
                                if isinstance(model_value, (int, float)) and isinstance(attr_value, (int, float)):
                                    min_val = min(model_value, attr_value)
                                    max_val = max(model_value, attr_value)
                                    model_obj.attributes[attr_name] = (min_val, max_val)
                                    changes_made += 1
                                
                                # Ak je v modeli interval a v priklade cislo
                                elif isinstance(model_value, tuple) and isinstance(attr_value, (int, float)):
                                    model_min, model_max = model_value
                                    new_min = min(model_min, attr_value)
                                    new_max = max(model_max, attr_value)
                                    
                                    if new_min != model_min or new_max != model_max:
                                        model_obj.attributes[attr_name] = (new_min, new_max)
                                        changes_made += 1
                        else:
                            # Ak model este nema tento atribut, pridame ho
                            model_obj.attributes[attr_name] = attr_value
                            changes_made += 1

    def _apply_drop_link(self, model: Model, good: Model, near_miss: Model):
        """
        Aplikuje heuristiku 'drop-link' - eliminuje nepotrebne spojenia.
        
        Tato heuristika odstranuje spojenia z modelu, ktore nie su pritomne v dobrom priklade.
        Pomaha zjednodusit model odstranenim spojeni, ktore nie su nevyhnutne pre koncept,
        a sustredi sa na skutocne potrebne vztahy.
        
        Parametre:
            model: Model, ktory sa ma aktualizovat
            good: Pozitivny priklad
            near_miss: Negativny priklad
            
        Navratova hodnota:
            None (modifikuje model priamo)
        """
        changes_made = 0
        
        # Spracuj vsetky spojenia v modeli
        regular_links = [l for l in model.links if l.link_type not in (LinkType.MUST, LinkType.MUST_NOT, LinkType.MUST_BE_A)]
        
        for link in regular_links:
            # Ak spojenie nie je v dobrom priklade, mozeme ho odstranit
            has_equivalent_in_good = any(
                l.source == link.source and l.target == link.target 
                for l in good.links
            )
            
            if not has_equivalent_in_good:
                model.remove_link(link)
                changes_made += 1

    def _apply_enlarge_set(self, model: Model, good: Model, near_miss: Model):
        """
        Aplikuje heuristiku 'enlarge-set' - vytvara zjednotenia pre funkcne ekvivalentne komponenty.
        
        Tato pokrocila heuristika identifikuje komponenty s podobnymi funkciami napriec roznymi prikladmi
        a vytvara nove triedy, ktore reprezentuju zjednotenie tychto komponentov. Je obzvlast uzitocna
        pri rozpoznavani, kedy rozne komponenty sluzia rovnakemu funkcnemu ucelu
        (napr. rozne typy motorov, prevodoviek alebo pohonnych systemov).
        
        Parametre:
            model: Model, ktory sa ma aktualizovat
            good: Pozitivny priklad
            near_miss: Negativny priklad
            
        Navratova hodnota:
            None (modifikuje model priamo)
        """
        import time
        
        changes_made = 0
        # ODSTRÁNENÉ: Obmedzenie na počet komponentov na spracovanie
        start_time = time.time()
        
        print("Applying enlarge-set heuristic")
        
        # OPTIMALIZÁCIA: Pre veľmi veľké modely môžeme funkciu stále ukončiť predčasne
        # aby nedošlo k preťaženiu systému
        if len(model.objects) > 100 or len(good.objects) > 100:
            print(f"Warning: Model too large for enlarge-set heuristic (model: {len(model.objects)}, good: {len(good.objects)} objects)")
            # Pre extrémne veľké modely preskočíme túto heuristiku
            return
        
        # 1. Identifikuj komponenty s podobnou funkciou
        # Najprv vytvor slovniky komponentov a ich atributov zo vsetkych modelov
        model_components = {}
        good_components = {}
        
        # Extrahuj komponenty z modelu (bez obmedzenia)
        for obj in model.objects:
            if obj.attributes:
                model_components[obj.name] = {
                    'class': obj.class_name,
                    'attributes': obj.attributes
                }
        
        # Extrahuj komponenty z dobreho prikladu (bez obmedzenia)
        for obj in good.objects:
            if obj.attributes:
                good_components[obj.name] = {
                    'class': obj.class_name,
                    'attributes': obj.attributes
                }
        
        # Kontrola času - ak trvá príliš dlho, preruš
        if time.time() - start_time > 5.0:  # Zvýšil som limit na 5 sekúnd
            print(f"Warning: enlarge-set component extraction taking too long ({time.time() - start_time:.2f}s)")
            return
        
        # 2. Porovnaj komponenty a hladaj podobne funkcie na zaklade atributov
        potential_equivalences = []
        component_comparisons = 0
        # ODSTRÁNENÉ: Maximálny počet porovnaní
        
        for model_comp_name, model_comp_data in model_components.items():
            # ODSTRÁNENÉ: Obmedzenie na počet porovnaní
            for good_comp_name, good_comp_data in good_components.items():
                component_comparisons += 1
                # ODSTRÁNENÉ: Kontrola počtu porovnaní
                
                # Preskoč, ak ide o ten isty komponent alebo su uz v hierarchickom vztahu
                if model_comp_name == good_comp_name:
                    continue
                
                if (model_comp_data['class'] == good_comp_data['class'] or 
                    self.classification_tree.are_related(model_comp_data['class'], good_comp_data['class'])):
                    continue
                
                # Kontrola času - ak trvá príliš dlho, preruš
                if time.time() - start_time > 10.0:  # Zvýšil som limit na 10 sekúnd
                    print(f"Warning: enlarge-set component comparison taking too long ({time.time() - start_time:.2f}s)")
                    return
                
                # Skrátená a optimalizovaná verzia analýzy komponentov
                # Analyzuj názvy - hľadaj spoločné kľúčové slová
                model_name_lower = model_comp_name.lower()
                good_name_lower = good_comp_name.lower()
                
                # Kľúčové kategórie komponentov
                name_categories = {
                    'engine': ['engine', 'motor'],
                    'transmission': ['transmission', 'gearbox'],
                    'drive': ['drive', 'wheel']
                }
                
                # Zistí, či komponenty patria do rovnakej kategórie
                component_category = None
                for category, keywords in name_categories.items():
                    if any(kw in model_name_lower for kw in keywords) and any(kw in good_name_lower for kw in keywords):
                        component_category = category
                        break
                
                if not component_category:
                    continue  # Nenašla sa spoločná kategória
                
                # Zjednodušené prepočítanie podobnosti
                similarity_score = 0.7  # Predefinovaná podobnosť pre komponenty rovnakého typu
                
                # Pridaj do potenciálnych ekvivalencií
                potential_equivalences.append({
                        'model_component': model_comp_name,
                        'good_component': good_comp_name,
                        'category': component_category,
                    'similarity': similarity_score * 100
                    })
        
        # Kontrola času - ak trvá príliš dlho, preruš
        if time.time() - start_time > 15.0:  # Zvýšil som limit na 15 sekúnd
            print(f"Warning: enlarge-set equivalence analysis taking too long ({time.time() - start_time:.2f}s)")
            return
        
        # 3. Vytvor nove triedy pre funkcne ekvivalentne komponenty
        # Zorad potencialne ekvivalencie podla skore podobnosti (od najvyssieho)
        potential_equivalences.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Vytvor nove triedy pre najlepsie zhody (odstránené obmedzenie na počet)
        processed_components = set()
        
        for equiv in potential_equivalences:
            # ODSTRÁNENÉ: Maximálny počet nových tried
            
            model_comp = equiv['model_component']
            good_comp = equiv['good_component']
            
            # Preskoc, ak bol nejaky z komponentov uz spracovany
            if model_comp in processed_components or good_comp in processed_components:
                continue
            
            # Vytvor novu triedu pre funkcne ekvivalentne komponenty
            new_component_class = None
            
            if equiv['category'] == 'engine':
                new_component_class = "EquivalentEngine"
            elif equiv['category'] == 'transmission':
                new_component_class = "EquivalentTransmission"
            elif equiv['category'] == 'drive':
                new_component_class = "EquivalentDrive"
            else:
                new_component_class = f"Equivalent{equiv['category'].capitalize()}"
            
            # Pridaj novu triedu do klasifikacneho stromu
            self.classification_tree.add_union_class(new_component_class, [model_comp, good_comp])
            
            # Vytvor spojenia MUST_BE_A pre oba komponenty
            model.add_link(Link(model_comp, new_component_class, LinkType.MUST_BE_A))
            model.add_link(Link(good_comp, new_component_class, LinkType.MUST_BE_A))
            
            processed_components.add(model_comp)
            processed_components.add(good_comp)
            
            changes_made += 1
        
        # Kontrola času - ak trvá príliš dlho, preruš
        total_time = time.time() - start_time
        if total_time > 1.0:  # Zvýšil som limit na 1 sekundu
            print(f"Warning: enlarge-set heuristic completed in {total_time:.2f} seconds (slow)")
        
        if changes_made:
            print(f"Made {changes_made} changes with enlarge-set heuristic")
        else:
            print("No changes made with enlarge-set heuristic")
        
        # 4. Najdi pary objektov v modeli a dobrom priklade, ktore nie su v hierarchickom vztahu
        # Tento posledný krok preskakujeme pre optimalizáciu výkonu 