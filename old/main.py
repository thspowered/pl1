from models import Model, ClassificationTree, Link, LinkType
from pl1 import Predicate, PredicateType, Hypothesis, parse_pl1_input
from dataset import create_training_dataset

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
        for good_link in good.links:
            if good_link.link_type == LinkType.MUST_BE_A:
                continue
            
            has_equivalent = any(
                l.source == good_link.source and l.target == good_link.target 
                for l in near_miss.links
            )
            
            if not has_equivalent:
                # Skontroluj, ci spojenie uz existuje
                link_exists = model.has_link(Link(
                    good_link.source,
                    good_link.target,
                    LinkType.MUST
                ))
                
                if not link_exists:
                    model.add_link(Link(
                        good_link.source,
                        good_link.target,
                        LinkType.MUST
                    ))
                    changes_made += 1

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
        for bad_link in near_miss.links:
            if bad_link.link_type == LinkType.MUST_BE_A:
                continue
                
            has_equivalent = any(
                l.source == bad_link.source and l.target == bad_link.target 
                for l in good.links
            )
            
            if not has_equivalent:
                # Skontroluj, ci spojenie uz existuje
                link_exists = model.has_link(Link(
                    bad_link.source,
                    bad_link.target,
                    LinkType.MUST_NOT
                ))
                
                if not link_exists:
                    model.add_link(Link(
                        bad_link.source,
                        bad_link.target,
                        LinkType.MUST_NOT
                    ))
                    changes_made += 1

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
        
        Funkcia pouziva sofistikovany pristup, ktory:
        1. Identifikuje komponenty s podobnymi funkciami na zaklade ich atributov a nazvov
        2. Vypocita skore podobnosti medzi komponentmi
        3. Vytvori nove triedy pre vysoko podobne komponenty
        4. Vytvori hierarchicke vztahy medzi novymi triedami a povodnym komponentmi
        
        Parametre:
            model: Model, ktory sa ma aktualizovat
            good: Pozitivny priklad
            near_miss: Negativny priklad
            
        Navratova hodnota:
            None (modifikuje model priamo)
        """
        changes_made = 0
        
        # 1. Identifikuj komponenty s podobnou funkciou
        # Najprv vytvor slovniky komponentov a ich atributov zo vsetkych modelov
        model_components = {}
        good_components = {}
        
        # Extrahuj komponenty z modelu
        for obj in model.objects:
            if obj.attributes:
                model_components[obj.name] = {
                    'class': obj.class_name,
                    'attributes': obj.attributes
                }
        
        # Extrahuj komponenty z dobreho prikladu
        for obj in good.objects:
            if obj.attributes:
                good_components[obj.name] = {
                    'class': obj.class_name,
                    'attributes': obj.attributes
                }
        
        # 2. Porovnaj komponenty a hladaj podobne funkcie na zaklade atributov
        potential_equivalences = []
        
        for model_comp_name, model_comp_data in model_components.items():
            for good_comp_name, good_comp_data in good_components.items():
                # Preskoč, ak ide o ten isty komponent alebo su uz v hierarchickom vztahu
                if model_comp_name == good_comp_name:
                    continue
                
                if (model_comp_data['class'] == good_comp_data['class'] or 
                    self.classification_tree.are_related(model_comp_data['class'], good_comp_data['class'])):
                    continue
                
                # Skontroluj, ci su funkcne podobne na zaklade:
                # - podobne nazvy (napr. engine v nazve)
                # - podobne atributy (napr. power_kw, fuel_type)
                # - podobne hodnoty atributov
                
                # Analyza nazvu - hladaj spolocne klucove slova
                model_name_lower = model_comp_name.lower()
                good_name_lower = good_comp_name.lower()
                
                # Klucove kategorie komponentov
                name_categories = {
                    'engine': ['engine', 'motor', 'turbo'],
                    'transmission': ['transmission', 'gearbox', 'auto', 'manual', 'steptronic'],
                    'drive': ['drive', 'wheel', 'xdrive', 'awd', 'rwd', 'fwd']
                }
                
                # Zisti, ci komponenty patria do rovnakej kategorie
                component_category = None
                for category, keywords in name_categories.items():
                    if any(kw in model_name_lower for kw in keywords) and any(kw in good_name_lower for kw in keywords):
                        component_category = category
                        break
                
                if not component_category:
                    continue  # Nenasla sa spolocna kategoria
                
                # Kontrola atributov
                similarity_score = 0
                total_attrs = 0
                
                if not model_comp_data['attributes'] or not good_comp_data['attributes']:
                    continue  # Aspon jeden komponent nema atributy
                
                # Pre motory skontroluj vykon, objem, typ paliva
                if component_category == 'engine':
                    model_attrs = model_comp_data['attributes']
                    good_attrs = good_comp_data['attributes']
                    
                    # Kontrola typu paliva
                    if 'fuel_type' in model_attrs and 'fuel_type' in good_attrs:
                        if str(model_attrs['fuel_type']).lower() == str(good_attrs['fuel_type']).lower():
                            similarity_score += 3  # Vysoka vaha pre zhodny typ paliva
                        total_attrs += 3
                    
                    # Kontrola vykonu
                    if 'power_kw' in model_attrs and 'power_kw' in good_attrs:
                        try:
                            model_power = float(model_attrs['power_kw'])
                            good_power = float(good_attrs['power_kw'])
                            
                            # 20% tolerancia pre rozdiel vo vykone
                            power_diff_pct = abs(model_power - good_power) / max(model_power, good_power)
                            if power_diff_pct <= 0.2:
                                similarity_score += 2
                            elif power_diff_pct <= 0.4:
                                similarity_score += 1
                            total_attrs += 2
                        except (ValueError, TypeError):
                            pass
                    
                    # Kontrola objemu
                    if 'displacement' in model_attrs and 'displacement' in good_attrs:
                        try:
                            model_disp = float(model_attrs['displacement'])
                            good_disp = float(good_attrs['displacement'])
                            
                            # 20% tolerancia pre rozdiel v objeme
                            disp_diff_pct = abs(model_disp - good_disp) / max(model_disp, good_disp)
                            if disp_diff_pct <= 0.2:
                                similarity_score += 2
                            elif disp_diff_pct <= 0.4:
                                similarity_score += 1
                            total_attrs += 2
                        except (ValueError, TypeError):
                            pass
                
                # Pre prevodovky skontroluj typ prevodovky
                elif component_category == 'transmission':
                    model_attrs = model_comp_data['attributes']
                    good_attrs = good_comp_data['attributes']
                    
                    # Kontrola typu prevodovky
                    if 'type' in model_attrs and 'type' in good_attrs:
                        model_type = str(model_attrs['type']).lower()
                        good_type = str(good_attrs['type']).lower()
                        
                        # Skupiny podobnych typov prevodoviek
                        transmission_groups = [
                            ['auto', 'automatic', 'steptronic', 'sport_automatic'],
                            ['manual', 'stick_shift', 'standard'],
                            ['dct', 'dual_clutch', 'double_clutch']
                        ]
                        
                        for group in transmission_groups:
                            if any(t in model_type for t in group) and any(t in good_type for t in group):
                                similarity_score += 3
                                break
                        total_attrs += 3
                
                # Pre pohony skontroluj typ pohonu
                elif component_category == 'drive':
                    model_attrs = model_comp_data['attributes']
                    good_attrs = good_comp_data['attributes']
                    
                    # Kontrola typu pohonu
                    if 'drive_type' in model_attrs and 'drive_type' in good_attrs:
                        model_drive = str(model_attrs['drive_type']).lower()
                        good_drive = str(good_attrs['drive_type']).lower()
                        
                        # Skupiny podobnych typov pohonu
                        drive_groups = [
                            ['all_wheel', 'awd', 'xdrive', '4wd', '4x4', 'quattro', '4motion'],
                            ['rear_wheel', 'rwd', 'rear'],
                            ['front_wheel', 'fwd', 'front']
                        ]
                        
                        for group in drive_groups:
                            if any(d in model_drive for d in group) and any(d in good_drive for d in group):
                                similarity_score += 3
                                break
                        total_attrs += 3
                
                # Vypocitaj percentualnu podobnost
                similarity_percentage = (similarity_score / total_attrs * 100) if total_attrs > 0 else 0
                
                # Ak je podobnost dostatocne vysoka (>= 70%), povazujeme komponenty za funkcne ekvivalentne
                if similarity_percentage >= 70:
                    potential_equivalences.append({
                        'model_component': model_comp_name,
                        'good_component': good_comp_name,
                        'category': component_category,
                        'similarity': similarity_percentage
                    })
        
        # 3. Vytvor nove triedy pre funkcne ekvivalentne komponenty
        # Zorad potencialne ekvivalencie podla skore podobnosti (od najvyssieho)
        potential_equivalences.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Vytvor nove triedy pre najlepsie zhody
        processed_components = set()
        
        for equiv in potential_equivalences:
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
        
        # 4. Najdi pary objektov v modeli a dobrom priklade, ktore nie su v hierarchickom vztahu
        # Toto je povodna implementacia, ktora pracuje s hlavnymi objektmi
        if changes_made == 0:  # Len ak sme nenasli funkcne ekvivalentne komponenty
            for model_obj in model.objects:
                for good_obj in good.objects:
                    # Ak rozne triedy ale podobne funkcie
                    if model_obj.class_name != good_obj.class_name and not self.classification_tree.are_related(model_obj.class_name, good_obj.class_name):
                        # Vytvor novu spolocnu triedu
                        new_class_name = f"{model_obj.class_name}Or{good_obj.class_name}"
                        
                        # Pridaj novu triedu do klasifikacneho stromu
                        self.classification_tree.add_union_class(new_class_name, [model_obj.class_name, good_obj.class_name])
                        
                        # Aktualizuj zodpovedajuce objekty v modeli
                        model.add_link(Link(model_obj.name, new_class_name, LinkType.MUST_BE_A))
                        
                        changes_made += 1
                        
                        # Aby sme nespracovali tu istu dvojicu viackrat
                        break
                if changes_made > 0:
                    break