#!/usr/bin/env python3
from typing import Dict, List, Tuple, Set, Any, Optional

from backend.model import Model, Link, LinkType, Object
from backend.pl1_parser import parse_pl1_formula, Formula


class ExampleValidator:
    """
    Třída pro validaci příkladů proti naučenému modelu.
    
    Tato třída kontroluje, zda příklad splňuje pravidla pro konkrétní model auta
    a poskytuje vysvětlení, proč příklad případně nesplňuje tato pravidla.
    """
    
    def __init__(self, model: Model):
        """
        Inicializace validátoru s naučeným modelem.
        
        Args:
            model: Naučený model, vůči kterému budeme validovat příklady
        """
        self.model = model
        self.rules = self._extract_rules()
        # Dynamicky extrahujeme povolené komponenty pro každý model auta
        self.component_requirements = self._extract_component_requirements()
        # Extrahujeme atributové hodnoty z modelu pro porovnanie
        self.attribute_values = self._extract_attribute_values()
        
    def _extract_rules(self) -> Dict[str, str]:
        """
        Dynamicky extrahuje pravidla pro každý model auta z natrénovaného modelu.
        
        Returns:
            Slovník s pravidly pro každý model auta
        """
        rules = {}
        for obj in self.model.objects:
            if obj.class_name in ["Series3", "Series5", "Series7", "X5", "X7"]:
                # Kontrola, že objekt má atributy
                if obj.attributes is not None:
                    rules[obj.class_name] = obj.attributes.get("rule", "")
                else:
                    rules[obj.class_name] = ""  # Prázdné pravidlo, pokud attributes je None
        return rules
    
    def _extract_component_requirements(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Dynamicky extrahuje povolené komponenty pro každý model auta z natrénovaného modelu.
        
        Returns:
            Slovník s povolenými komponentami pro každý model auta
        """
        component_requirements = {}
        car_models = ["X5", "X7", "Series3", "Series5", "Series7"]
        
        print("Extrahujeme povolené komponenty z modelu:")
        
        for model_type in car_models:
            # Inicializácia požiadaviek pre model
            component_requirements[model_type] = {
                "engines": [],
                "transmission": [],
                "drive": []
            }
            
            # Kontrola MUST vzťahov
            for link in self.model.links:
                if link.link_type == LinkType.MUST and link.source == model_type:
                    target = link.target
                    
                    # Zaradenie komponentu do správnej kategórie
                    if "Engine" in target:
                        component_requirements[model_type]["engines"].append(target)
                        print(f"  {model_type} - MUST Engine: {target}")
                    elif "Transmission" in target:
                        component_requirements[model_type]["transmission"].append(target)
                        print(f"  {model_type} - MUST Transmission: {target}")
                    elif target in ["XDrive", "AWD", "RWD"]:
                        component_requirements[model_type]["drive"].append(target)
                        print(f"  {model_type} - MUST Drive: {target}")
            
            # Kontrola špecifických atribútov objektov modelu
            for obj in self.model.objects:
                if obj.class_name == model_type and obj.attributes is not None:
                    for attr_name, attr_value in obj.attributes.items():
                        # Spracovanie množinových atribútov (disjunkcií)
                        if isinstance(attr_value, set) and "allowed" in attr_name:
                            if "engine" in attr_name:
                                component_requirements[model_type]["engines"].extend(list(attr_value))
                                print(f"  {model_type} - Allowed Engines (attr): {list(attr_value)}")
                            elif "transmission" in attr_name:
                                component_requirements[model_type]["transmission"].extend(list(attr_value))
                                print(f"  {model_type} - Allowed Transmissions (attr): {list(attr_value)}")
                            elif "drive" in attr_name:
                                component_requirements[model_type]["drive"].extend(list(attr_value))
                                print(f"  {model_type} - Allowed Drives (attr): {list(attr_value)}")
            
            # Ak nemáme žiadne špecifické motory, pridáme všeobecné motory
            if not component_requirements[model_type]["engines"]:
                # Iterácia cez objekty modelu auta v modeli
                car_object = next((obj for obj in self.model.objects if obj.class_name == model_type), None)
                if car_object:
                    # Hľadanie všetkých spojení tohto objektu
                    for link in self.model.links:
                        if link.source == car_object.name:
                            target_obj = next((obj for obj in self.model.objects if obj.name == link.target), None)
                            if target_obj and "Engine" in target_obj.class_name:
                                component_requirements[model_type]["engines"].append(target_obj.class_name)
                                print(f"  {model_type} - Found Engine in links: {target_obj.class_name}")
            
            # Dedukcia pre BMW modely - tieto sa použijú len ak model neobsahuje explicitné informácie
            # X5, X7 musia mať XDrive
            if model_type in ["X5", "X7"] and not component_requirements[model_type]["drive"]:
                component_requirements[model_type]["drive"].append("XDrive")
                print(f"  {model_type} - Default Drive: XDrive")
            
            # Series7 môže mať AWD
            if model_type == "Series7" and not component_requirements[model_type]["drive"]:
                component_requirements[model_type]["drive"].append("AWD")
                print(f"  {model_type} - Default Drive: AWD")
            
            # Series3 môže mať RWD
            if model_type == "Series3" and not component_requirements[model_type]["drive"]:
                component_requirements[model_type]["drive"].append("RWD")
                print(f"  {model_type} - Default Drive: RWD")
            
            # Series5 môže mať RWD alebo AWD
            if model_type == "Series5" and not component_requirements[model_type]["drive"]:
                component_requirements[model_type]["drive"].extend(["RWD", "AWD"])
                print(f"  {model_type} - Default Drives: RWD, AWD")
            
            # Ak nemáme žiadne prevodovky, pridáme štandardné prevodovky
            if not component_requirements[model_type]["transmission"]:
                if model_type in ["X5", "X7", "Series7", "Series5"]:
                    component_requirements[model_type]["transmission"].append("AutomaticTransmission")
                    print(f"  {model_type} - Default Transmission: AutomaticTransmission")
                elif model_type == "Series3":
                    component_requirements[model_type]["transmission"].extend(["AutomaticTransmission", "ManualTransmission"])
                    print(f"  {model_type} - Default Transmissions: AutomaticTransmission, ManualTransmission")
            
            # Štandardné motory ak nemáme žiadne
            if not component_requirements[model_type]["engines"]:
                if model_type in ["X5", "X7"]:
                    component_requirements[model_type]["engines"].extend(["PetrolEngine", "DieselEngine", "HybridEngine"])
                    print(f"  {model_type} - Default Engines: PetrolEngine, DieselEngine, HybridEngine")
                elif model_type == "Series3":
                    component_requirements[model_type]["engines"].extend(["PetrolEngine", "DieselEngine"])
                    print(f"  {model_type} - Default Engines: PetrolEngine, DieselEngine")
                elif model_type == "Series5":
                    component_requirements[model_type]["engines"].extend(["PetrolEngine", "DieselEngine", "HybridEngine"])
                    print(f"  {model_type} - Default Engines: PetrolEngine, DieselEngine, HybridEngine")
                elif model_type == "Series7":
                    component_requirements[model_type]["engines"].extend(["PetrolEngine", "HybridEngine"])
                    print(f"  {model_type} - Default Engines: PetrolEngine, HybridEngine")
            
            # Odstránenie duplicít
            component_requirements[model_type]["engines"] = list(set(component_requirements[model_type]["engines"]))
            component_requirements[model_type]["transmission"] = list(set(component_requirements[model_type]["transmission"]))
            component_requirements[model_type]["drive"] = list(set(component_requirements[model_type]["drive"]))
            
            print(f"Finálne komponenty pre {model_type}:")
            print(f"  Engines: {component_requirements[model_type]['engines']}")
            print(f"  Transmissions: {component_requirements[model_type]['transmission']}")
            print(f"  Drives: {component_requirements[model_type]['drive']}")
        
        return component_requirements
    
    def _extract_attribute_values(self) -> Dict[str, Dict[str, Any]]:
        """
        Extrahuje hodnoty atribútov z modelu pre každý typ komponentu.
        Ak konkrétna trieda nemá definované hodnoty, budú prebrané z rodičovskej triedy.
        
        Returns:
            Slovník s hodnotami atribútov pre typy komponentov
        """
        attribute_values = {}
        parent_map = {}
        
        # Najprv vytvoríme mapu tried a ich rodičov
        for link in self.model.links:
            if link.link_type == LinkType.MUST_BE_A:
                parent_map[link.source] = link.target
        
        # Vytvoríme mapu tried
        class_hierarchy = {}
        for obj_name, parent_name in parent_map.items():
            if obj_name not in class_hierarchy and obj_name[0].isupper():
                class_hierarchy[obj_name] = parent_name
        
        print("\nExtrahujem hodnoty atribútov z modelu - vrátane hodnôt z rodičovských tried:")
        
        # Prejdeme všetky objekty v modeli
        for obj in self.model.objects:
            if obj.attributes is not None:
                # Ak objekt je komponent, uložíme jeho atribúty
                class_name = obj.class_name
                print(f"  Našiel som objekt triedy {class_name} s atribútmi: {obj.attributes}")
                
                if class_name not in attribute_values:
                    attribute_values[class_name] = {}
                
                # Uložíme všetky atribúty objektu
                for attr_name, attr_value in obj.attributes.items():
                    # Numerické atribúty alebo množiny hodnôt
                    if isinstance(attr_value, (int, float)) or isinstance(attr_value, set) or (isinstance(attr_value, tuple) and len(attr_value) == 2):
                        attribute_values[class_name][attr_name] = attr_value
                        print(f"    Uložil som atribút {attr_name} = {attr_value}")
        
        # Teraz rozšírime hodnoty atribútov pre konkrétne triedy z ich rodičovských tried
        # Vytvoríme list všetkých známych tried, ktoré môžu mať atribúty
        all_classes = set()
        for link in self.model.links:
            if link.source[0].isupper() and link.target[0].isupper():  # Triedy začínajú veľkým písmenom
                all_classes.add(link.source)
                all_classes.add(link.target)
        
        print("\nRozširujem hodnoty atribútov z rodičovských tried:")
        
        # Pre každú triedu skúsime nájsť hodnoty atribútov z rodičovských tried
        for class_name in all_classes:
            # Ak trieda nemá definované atribúty, skúsime ich nájsť v rodičovskej triede
            if class_name not in attribute_values:
                attribute_values[class_name] = {}
            
            # Nájdeme rodičovskú triedu
            current_class = class_name
            while current_class in class_hierarchy:
                parent_class = class_hierarchy[current_class]
                print(f"  Kontrolujem rodičovskú triedu {parent_class} pre {class_name}")
                
                # Ak rodičovská trieda má definované atribúty, použijeme ich
                if parent_class in attribute_values:
                    for attr_name, attr_value in attribute_values[parent_class].items():
                        # Pridáme len ak trieda ešte nemá definovaný tento atribút
                        if attr_name not in attribute_values[class_name]:
                            attribute_values[class_name][attr_name] = attr_value
                            print(f"    Dedím atribút {attr_name} = {attr_value} z triedy {parent_class} pre triedu {class_name}")
                
                # Pokračujeme s rodičovskou triedou rodičovskej triedy
                current_class = parent_class
        
        # Manuálna definícia vzťahov dedičnosti pre najčastejšie typy
        engine_inheritance = {
            "DieselEngine": "Engine",
            "PetrolEngine": "Engine",
            "HybridEngine": "Engine"
        }
        
        transmission_inheritance = {
            "AutomaticTransmission": "Transmission",
            "ManualTransmission": "Transmission"
        }
        
        drive_inheritance = {
            "XDrive": "AWD",
            "AWD": "DriveSystem",
            "RWD": "DriveSystem"
        }
        
        # Aplikujeme manuálne dedenie
        for child, parent in engine_inheritance.items():
            if parent in attribute_values:
                if child not in attribute_values:
                    attribute_values[child] = {}
                for attr_name, attr_value in attribute_values[parent].items():
                    if attr_name not in attribute_values[child]:
                        attribute_values[child][attr_name] = attr_value
                        print(f"    Manuálne dedím atribút {attr_name} = {attr_value} z triedy {parent} pre triedu {child}")
        
        for child, parent in transmission_inheritance.items():
            if parent in attribute_values:
                if child not in attribute_values:
                    attribute_values[child] = {}
                for attr_name, attr_value in attribute_values[parent].items():
                    if attr_name not in attribute_values[child]:
                        attribute_values[child][attr_name] = attr_value
                        print(f"    Manuálne dedím atribút {attr_name} = {attr_value} z triedy {parent} pre triedu {child}")
        
        for child, parent in drive_inheritance.items():
            if parent in attribute_values:
                if child not in attribute_values:
                    attribute_values[child] = {}
                for attr_name, attr_value in attribute_values[parent].items():
                    if attr_name not in attribute_values[child]:
                        attribute_values[child][attr_name] = attr_value
                        print(f"    Manuálne dedím atribút {attr_name} = {attr_value} z triedy {parent} pre triedu {child}")
        
        print("\nFinálne extrahované hodnoty atribútov z modelu (vrátane zdedených hodnôt):")
        for class_name, attrs in attribute_values.items():
            if attrs:  # Zobrazíme len triedy s neprázdnymi atribútmi
                print(f"  {class_name}:")
                for attr_name, attr_value in attrs.items():
                    print(f"    {attr_name}: {attr_value}")
        
        return attribute_values
    
    def validate_example(self, example: Model, validate_attributes: bool = True) -> Dict[str, Any]:
        """
        Validuje príklad voči modelu, zisťuje, či je s modelom konzistentný.
        
        Args:
            example: Príklad na validáciu
            validate_attributes: Či sa majú overovať aj hodnoty atribútov
            
        Returns:
            Dict s výsledkami validácie
        """
        print(f"\n===== Začínam validáciu príkladu, validate_attributes={validate_attributes} =====")
        
        # Najprv extrahujeme hodnoty atribútov z modelu, ktoré budeme používať na validáciu
        self.attribute_values = self._extract_attribute_values()
        
        # Identifikujeme typ auta (napr. X5, Series5, ...)
        car_model = self._identify_car_model(example)
        
        if not car_model:
            print("Nepodarilo sa identifikovať typ modelu auta v príklade")
            return {
                "is_valid": False,
                "model_type": None,
                "violations": ["Nepodařilo se identifikovat typ modelu auta v příkladu"],
                "satisfied_rules": [],
                "allowed_alternatives": {},
                "categorized_violations": {}  # Prázdne kategorizované porušenia, keďže validácia nemohla byť vykonaná
            }
        
        print(f"Identifikovaný model auta: {car_model}")
        
        # Validujeme príklad voči pravidlám
        validation_result = self._validate_against_model_rules(example, car_model, validate_attributes)
        
        print(f"\n===== Validácia príkladu dokončená =====")
        
        return validation_result
    
    def _identify_car_model(self, example: Model) -> Optional[str]:
        """
        Identifikuje, o jaký model auta se v příkladu jedná.
        Vrací pouze jeden model (první nalezený).
        
        Args:
            example: Příklad k analýze
            
        Returns:
            Název modelu auta nebo None, pokud nebyl nalezen
        """
        # Seznam známých modelů BMW
        bmw_models = ["Series3", "Series5", "Series7", "X5", "X7"]
        
        # Hledáme objekty, které jsou přímo modely aut
        for obj in example.objects:
            if obj.class_name in bmw_models:
                return obj.class_name
        
        return None
    
    def _validate_against_model_rules(self, example: Model, model_type: str, validate_attributes: bool = True) -> Dict[str, Any]:
        """
        Validuje príklad proti pravidlám pre konkrétny model auta.
        
        Args:
            example: Príklad na validáciu
            model_type: Typ modelu auta
            validate_attributes: Či sa majú kontrolovať aj hodnoty atribútov
            
        Returns:
            Slovník s výsledkami validácie
        """
        print(f"\nValidujem príklad proti pravidlám pre model {model_type}, validate_attributes={validate_attributes}")
        
        if model_type not in self.rules:
            return {
                "is_valid": False,
                "model_type": model_type,
                "violations": [f"Pravidla pro model {model_type} nejsou k dispozici"],
                "satisfied_rules": [],
                "allowed_alternatives": {}
            }
        
        # Kontrola MUST vztahů
        must_violations = self._check_must_relationships(example, model_type)
        
        # Kontrola MUST_NOT vztahů
        must_not_violations = self._check_must_not_relationships(example, model_type)
        
        # Kontrola komponentů (různé typy motorů, převodovek, pohonů)
        component_violations = self._check_component_requirements(example, model_type)
        
        # Kontrola hodnôt atribútov, ak je povolené
        attribute_violations = []
        attribute_satisfied = []
        if validate_attributes:
            print(f"Vykonávam validáciu hodnôt atribútov...")
            attribute_results = self._check_attribute_values(example)
            attribute_violations = attribute_results["violations"]
            attribute_satisfied = attribute_results["satisfied"]
            print(f"Výsledky validácie atribútov: {len(attribute_violations)} porušení, {len(attribute_satisfied)} splnených pravidiel")
        else:
            print(f"Validácia hodnôt atribútov je vypnutá")
        
        # Spojíme všechny porušení
        all_violations = must_violations + must_not_violations + component_violations + attribute_violations
        
        # Připravíme seznam splněných pravidel
        satisfied_rules = self._collect_satisfied_rules(example, model_type, all_violations)
        
        # Pridáme splnené pravidlá pre atribúty
        if validate_attributes:
            satisfied_rules.extend(attribute_satisfied)
        
        # Připravíme seznam povolených alternativních komponent pro model
        allowed_alternatives = {
            "engines": self.component_requirements.get(model_type, {}).get("engines", []),
            "transmissions": self.component_requirements.get(model_type, {}).get("transmission", []),
            "drives": self.component_requirements.get(model_type, {}).get("drive", [])
        }
        
        # Pro lepší přehled, přidáme kategorizované porušení
        categorized_violations = {
            "must_violations": must_violations,
            "must_not_violations": must_not_violations,
            "component_violations": component_violations,
            "attribute_violations": attribute_violations
        }
        
        print(f"\nCelkový počet porušení: {len(all_violations)}")
        print(f"Z toho porušenia validácie atribútov: {len(attribute_violations)}")
        
        # Vypíšme porušenia validácie atribútov
        if attribute_violations:
            print("Porušenia validácie atribútov:")
            for violation in attribute_violations:
                print(f"  - {violation}")
        
        return {
            "is_valid": len(all_violations) == 0,
            "model_type": model_type,
            "violations": all_violations,
            "categorized_violations": categorized_violations,
            "satisfied_rules": satisfied_rules,
            "allowed_alternatives": allowed_alternatives
        }
    
    def _check_must_relationships(self, example: Model, model_type: str) -> List[str]:
        """
        Kontroluje, zda příklad splňuje všechny povinné vztahy (MUST).
        Zaměřuje se pouze na vztahy relevantní pro konkrétní model auta.
        Kontroluje také alternativy (disjunkce) komponentů.
        
        Args:
            example: Příklad k validaci
            model_type: Typ modelu auta
            
        Returns:
            Seznam porušených pravidel MUST
        """
        violations = []
        
        # Najdeme objekt modelu v příkladu
        model_objects = [obj for obj in example.objects if obj.class_name == model_type]
        if not model_objects:
            return [f"Příklad neobsahuje objekt typu {model_type}"]
        
        # Najdeme MUST vztahy v modelu pro daný typ
        must_links = []
        for link in self.model.links:
            if link.link_type == LinkType.MUST and link.source == model_type:
                must_links.append(link)
        
        # Pro každý MUST vztah zkontrolujeme, zda je splněn v příkladu
        for must_link in must_links:
            required_component = must_link.target
            
            # Přeskočíme obecné komponenty, které nejsou konkrétní typy
            if required_component in ["Component", "Engine", "Transmission", "DriveSystem"]:
                continue
            
            # Zjistíme, zda komponent patří do nějaké kategorie s alternativami
            component_category = None
            if "Engine" in required_component:
                component_category = "engines"
            elif "Transmission" in required_component:
                component_category = "transmission"
            elif required_component in ["XDrive", "AWD", "RWD"]:
                component_category = "drive"
            
            for model_obj in model_objects:
                has_component = False
                has_alternative = False
                
                # Kontrola, zda model má vyžadovaný komponent nebo alternativu
                for example_link in example.links:
                    if example_link.source == model_obj.name:
                        target_obj = next((obj for obj in example.objects if obj.name == example_link.target), None)
                        if not target_obj:
                            continue
                        
                        # Kontrola přímé shody komponenty
                        if target_obj.class_name == required_component:
                            has_component = True
                            break
                        
                        # Kontrola alternativy, pokud komponent patří do kategorie s alternativami
                        if component_category and target_obj.class_name in self.component_requirements.get(model_type, {}).get(component_category, []):
                            has_alternative = True
                
                # Pokud má alternativu, přeskočíme přidání porušení
                if has_alternative:
                    continue
                
                # Pokud nemá ani komponent ani alternativu, přidáme porušení
                if not has_component and not has_alternative:
                    # Pro komponenty s alternativami zobrazíme všechny možnosti
                    if component_category and self.component_requirements.get(model_type, {}).get(component_category, []):
                        allowed_components = ", ".join(self.component_requirements[model_type][component_category])
                        if component_category == "engines":
                            violations.append(f"Model {model_type} musí mít jeden z motorů: {allowed_components}")
                        elif component_category == "transmission":
                            violations.append(f"Model {model_type} musí mít jednu z převodovek: {allowed_components}")
                        elif component_category == "drive":
                            violations.append(f"Model {model_type} musí mít jeden z pohonů: {allowed_components}")
                    else:
                        violations.append(f"Model {model_type} musí mít komponentu {required_component}")
        
        return violations
    
    def _check_must_not_relationships(self, example: Model, model_type: str) -> List[str]:
        """
        Kontroluje, zda příklad neobsahuje zakázané vztahy (MUST_NOT).
        Zaměřuje se pouze na vztahy relevantní pro konkrétní model auta.
        
        Args:
            example: Příklad k validaci
            model_type: Typ modelu auta
            
        Returns:
            Seznam porušených pravidel MUST_NOT
        """
        violations = []
        
        # Najdeme objekt modelu v příkladu
        model_objects = [obj for obj in example.objects if obj.class_name == model_type]
        if not model_objects:
            return []  # Už jsme kontrolovali v _check_must_relationships
        
        # Najdeme MUST_NOT vztahy v modelu pro daný typ
        must_not_links = []
        for link in self.model.links:
            if link.link_type == LinkType.MUST_NOT and link.source == model_type:
                must_not_links.append(link)
        
        # Pro každý MUST_NOT vztah zkontrolujeme, zda není porušen v příkladu
        for must_not_link in must_not_links:
            forbidden_component = must_not_link.target
            
            for model_obj in model_objects:
                for example_link in example.links:
                    if example_link.source == model_obj.name:
                        target_obj = next((obj for obj in example.objects if obj.name == example_link.target), None)
                        if target_obj and target_obj.class_name == forbidden_component:
                            violations.append(f"Model {model_type} nesmí mít komponentu {forbidden_component}")
        
        return violations
    
    def _check_component_requirements(self, example: Model, model_type: str) -> List[str]:
        """
        Kontroluje specifické požadavky na komponenty pro daný model auta.
        Tato metoda se soustředí zejména na kontrolu alternativ.
        
        Args:
            example: Příklad k validaci
            model_type: Typ modelu auta
            
        Returns:
            Seznam porušených požadavků na komponenty
        """
        violations = []
        
        # Získáme pravidlo pro daný model
        if model_type not in self.rules:
            return []
            
        rule_text = self.rules[model_type]
        
        # Kontrolujeme, zda příklad splňuje požadavky na komponenty
        model_objects = [obj for obj in example.objects if obj.class_name == model_type]
        if not model_objects:
            return []
        
        # Kontrola, zda MUST vztahy už neobsahují požadavky na motory, převodovky nebo pohony
        # Pokud ano, přeskočíme duplikátní kontroly
        must_categories_covered = {
            "engines": False,
            "transmission": False,
            "drive": False
        }
        
        for link in self.model.links:
            if link.link_type == LinkType.MUST and link.source == model_type:
                target = link.target
                
                if "Engine" in target and target != "Engine":
                    must_categories_covered["engines"] = True
                elif "Transmission" in target and target != "Transmission":
                    must_categories_covered["transmission"] = True
                elif target in ["XDrive", "AWD", "RWD"]:
                    must_categories_covered["drive"] = True
        
        print(f"MUST vztahy pokrývají následující kategorie pro {model_type}:")
        print(f"  Engines: {must_categories_covered['engines']}")
        print(f"  Transmissions: {must_categories_covered['transmission']}")
        print(f"  Drives: {must_categories_covered['drive']}")
            
        for model_obj in model_objects:
            # Kontrola motorů - jen pokud nejsou pokryty MUST vztahy
            if not must_categories_covered["engines"]:
                has_valid_engine = False
                for example_link in example.links:
                    if example_link.source == model_obj.name:
                        target_obj = next((obj for obj in example.objects if obj.name == example_link.target), None)
                        if target_obj and target_obj.class_name in self.component_requirements.get(model_type, {}).get("engines", []):
                            has_valid_engine = True
                            break
                
                if not has_valid_engine and self.component_requirements.get(model_type, {}).get("engines", []):
                    allowed_engines = ", ".join(self.component_requirements[model_type]["engines"])
                    violations.append(f"Model {model_type} musí mít jeden z motorů: {allowed_engines}")
            
            # Kontrola převodovky - jen pokud nejsou pokryty MUST vztahy
            if not must_categories_covered["transmission"]:
                has_valid_transmission = False
                for example_link in example.links:
                    if example_link.source == model_obj.name:
                        target_obj = next((obj for obj in example.objects if obj.name == example_link.target), None)
                        if target_obj and target_obj.class_name in self.component_requirements.get(model_type, {}).get("transmission", []):
                            has_valid_transmission = True
                            break
                
                if not has_valid_transmission and self.component_requirements.get(model_type, {}).get("transmission", []):
                    allowed_transmissions = ", ".join(self.component_requirements[model_type]["transmission"])
                    violations.append(f"Model {model_type} musí mít jednu z převodovek: {allowed_transmissions}")
            
            # Kontrola pohonu - jen pokud nejsou pokryty MUST vztahy
            if not must_categories_covered["drive"]:
                has_valid_drive = False
                for example_link in example.links:
                    if example_link.source == model_obj.name:
                        target_obj = next((obj for obj in example.objects if obj.name == example_link.target), None)
                        if target_obj and target_obj.class_name in self.component_requirements.get(model_type, {}).get("drive", []):
                            has_valid_drive = True
                            break
                
                if not has_valid_drive and self.component_requirements.get(model_type, {}).get("drive", []):
                    allowed_drives = ", ".join(self.component_requirements[model_type]["drive"])
                    violations.append(f"Model {model_type} musí mít jeden z pohonů: {allowed_drives}")
        
        return violations
    
    def _check_attribute_values(self, example: Model) -> Dict[str, List[str]]:
        """
        Kontroluje, či hodnoty atribútov v príklade zodpovedajú hodnotám v modeli.
        Porovnáva hodnoty atribútov v príklade s hodnotami v modeli (vrátane zdedených hodnôt).
        
        Args:
            example: Príklad na validáciu
            
        Returns:
            Slovník s porušenými a splnenými pravidlami pre atribúty
        """
        violations = []
        satisfied = []
        
        print("\n==================== DEBUG: _check_attribute_values START ====================")
        print("Kontrolovanie hodnôt atribútov v príklade - porovnávam s hodnotami z modelu (vrátane zdedených):")
        print(f"Počet objektov v attribute_values: {len(self.attribute_values)}")
        print(f"Triedy s atribútmi: {[cls for cls in self.attribute_values if self.attribute_values[cls]]}")
        
        # Prejdeme všetky objekty v príklade
        print(f"\nDEBUG: Checking {len(example.objects)} objects in example")
        for example_obj in example.objects:
            print(f"\nDEBUG: Checking object {example_obj.name} of class {example_obj.class_name}")
            # Ak objekt má atribúty, kontrolujeme ich
            if example_obj.attributes is not None:
                class_name = example_obj.class_name
                print(f"  Kontrolujem objekt {example_obj.name} triedy {class_name}, atribúty: {example_obj.attributes}")
                
                # Ak máme definované hodnoty atribútov pre tento typ objektu v modeli
                if class_name in self.attribute_values and self.attribute_values[class_name]:
                    print(f"    Trieda {class_name} má definované hodnoty atribútov v modeli:")
                    for name, value in self.attribute_values[class_name].items():
                        print(f"      - {name}: {value} (typ: {type(value).__name__})")
                    
                    # Kontrolujeme každý atribút
                    for attr_name, example_value in example_obj.attributes.items():
                        print(f"    Kontrolujem atribút {attr_name} s hodnotou {example_value} (typ: {type(example_value).__name__})")
                        
                        # Ak model definuje tento atribút
                        if attr_name in self.attribute_values[class_name]:
                            model_value = self.attribute_values[class_name][attr_name]
                            print(f"      Model definuje atribút {attr_name} s očakávanou hodnotou {model_value} (typ: {type(model_value).__name__})")
                            
                            is_valid_value = False
                            
                            # Kontrola rôznych typov hodnôt
                            # 1. Množina povolených hodnôt
                            if isinstance(model_value, set):
                                if example_value in model_value:
                                    is_valid_value = True
                                    satisfied.append(f"Objekt {example_obj.name} ({class_name}) má platnú hodnotu atribútu {attr_name}: {example_value}")
                                    print(f"      ✅ Hodnota {example_value} je platná, je v množine povolených hodnôt")
                                else:
                                    violations.append(f"Objekt {example_obj.name} ({class_name}) má neplatnú hodnotu atribútu {attr_name}: {example_value}, povolené hodnoty sú: {', '.join(map(str, model_value))}")
                                    print(f"      ❌ Hodnota {example_value} je neplatná, nie je v množine povolených hodnôt: {model_value}")
                            
                            # 2. Numerický interval (minimum, maximum)
                            elif isinstance(model_value, tuple) and len(model_value) == 2:
                                min_val, max_val = model_value
                                if isinstance(example_value, (int, float)) and min_val <= example_value <= max_val:
                                    is_valid_value = True
                                    satisfied.append(f"Objekt {example_obj.name} ({class_name}) má platnú hodnotu atribútu {attr_name}: {example_value} (v intervale {min_val}-{max_val})")
                                    print(f"      ✅ Hodnota {example_value} je platná, je v intervale {min_val}-{max_val}")
                                else:
                                    violations.append(f"Objekt {example_obj.name} ({class_name}) má neplatnú hodnotu atribútu {attr_name}: {example_value}, povolený interval je: {min_val}-{max_val}")
                                    print(f"      ❌ Hodnota {example_value} je neplatná, nie je v intervale {min_val}-{max_val}")
                            
                            # 3. Priama hodnota - numerická 
                            elif isinstance(model_value, (int, float)) and isinstance(example_value, (int, float)):
                                # Porovnanie číselných hodnôt - musí byť presná zhoda, žiadne intervaly
                                if example_value == model_value:
                                    is_valid_value = True
                                    satisfied.append(f"Objekt {example_obj.name} ({class_name}) má platnú číselnú hodnotu atribútu {attr_name}: {example_value}")
                                    print(f"      ✅ Číselná hodnota {example_value} je platná, rovná sa očakávanej hodnote {model_value}")
                                else:
                                    violations.append(f"Objekt {example_obj.name} ({class_name}) má neplatnú číselnú hodnotu atribútu {attr_name}: {example_value}, očakávaná hodnota je presne: {model_value}")
                                    print(f"      ❌ Číselná hodnota {example_value} je neplatná, očakávaná hodnota: {model_value}, rozdiel: {example_value - model_value}")
                            
                            # 4. Nečíselné hodnoty (stringy, boolean, atď.)
                            elif example_value == model_value:
                                is_valid_value = True
                                satisfied.append(f"Objekt {example_obj.name} ({class_name}) má platnú hodnotu atribútu {attr_name}: {example_value}")
                                print(f"      ✅ Hodnota {example_value} je platná")
                            else:
                                violations.append(f"Objekt {example_obj.name} ({class_name}) má neplatnú hodnotu atribútu {attr_name}: {example_value}, očakávaná hodnota je presne: {model_value}")
                                print(f"      ❌ Hodnota {example_value} je neplatná, očakávaná hodnota: {model_value}")
                        
                        # Ak model nemá definovaný atribút, ktorý sa nachádza v príklade, môžeme to ignorovať
                        else:
                            print(f"      ℹ️ Atribút {attr_name} nie je definovaný v modeli pre triedu {class_name} - preskakujem validáciu")
                else:
                    print(f"    Trieda {class_name} nemá definované žiadne atribúty v modeli - preskakujem validáciu")
            else:
                print(f"  Objekt {example_obj.name} nemá žiadne atribúty")
        
        print("\nVýsledky kontroly atribútov:")
        print(f"  Počet porušení: {len(violations)}")
        for v in violations:
            print(f"    - {v}")
        print(f"  Počet splnených pravidiel: {len(satisfied)}")
        
        print("==================== DEBUG: _check_attribute_values END ====================\n")
        
        return {
            "violations": violations,
            "satisfied": satisfied
        }
    
    def _collect_satisfied_rules(self, example: Model, model_type: str, violations: List[str]) -> List[str]:
        """
        Shromáždí pravidla, která příklad splňuje.
        
        Args:
            example: Příklad k validaci
            model_type: Typ modelu auta
            violations: Seznam porušených pravidel
            
        Returns:
            Seznam splněných pravidel
        """
        satisfied = []
        
        # Přidáme základní pravidlo o typu
        satisfied.append(f"Příklad obsahuje objekt typu {model_type}")
        
        # Kontrolujeme, které komponenty příklad obsahuje
        model_objects = [obj for obj in example.objects if obj.class_name == model_type]
        if not model_objects:
            return satisfied
            
        for model_obj in model_objects:
            # Kontrola motorů
            for example_link in example.links:
                if example_link.source == model_obj.name:
                    target_obj = next((obj for obj in example.objects if obj.name == example_link.target), None)
                    if (target_obj and 
                        target_obj.class_name in self.component_requirements.get(model_type, {}).get("engines", [])):
                        engine_rule = f"Model {model_type} má validní motor typu {target_obj.class_name}"
                        if not any(v.startswith(f"Model {model_type} musí mít jeden z motorů") for v in violations):
                            satisfied.append(engine_rule)
                    
                    # Kontrola převodovky
                    if (target_obj and 
                        target_obj.class_name in self.component_requirements.get(model_type, {}).get("transmission", [])):
                        transmission_rule = f"Model {model_type} má validní převodovku typu {target_obj.class_name}"
                        if not any(v.startswith(f"Model {model_type} musí mít jednu z převodovek") for v in violations):
                            satisfied.append(transmission_rule)
                    
                    # Kontrola pohonu
                    if (target_obj and 
                        target_obj.class_name in self.component_requirements.get(model_type, {}).get("drive", [])):
                        drive_rule = f"Model {model_type} má validní pohon typu {target_obj.class_name}"
                        if not any(v.startswith(f"Model {model_type} musí mít jeden z pohonů") for v in violations):
                            satisfied.append(drive_rule)
        
        # MUST vztahy
        for link in self.model.links:
            if link.link_type == LinkType.MUST and link.source == model_type:
                # Přeskočíme obecné komponenty
                if link.target in ["Component", "Engine", "Transmission", "DriveSystem"]:
                    continue
                    
                rule_text = f"Model {model_type} musí mít komponentu {link.target}"
                if rule_text not in violations and not any(v.startswith(f"Model {model_type} musí mít komponentu {link.target}") for v in violations):
                    satisfied.append(rule_text)
        
        # MUST_NOT vztahy
        for link in self.model.links:
            if link.link_type == LinkType.MUST_NOT and link.source == model_type:
                rule_text = f"Model {model_type} nesmí mít komponentu {link.target}"
                if rule_text not in violations:
                    satisfied.append(rule_text)
        
        return satisfied

def compare_example(model: Model, example_formula: str, validate_attributes: bool = True) -> Dict[str, Any]:
    """
    Validuje PL1 formuli proti naučenému modelu se zaměřením na konkrétní model auta.
    
    Args:
        model: Naučený model
        example_formula: PL1 formule příkladu k validaci
        validate_attributes: Zda se mají kontrolovat i hodnoty atributů (výkon, krouticí moment, ...)
        
    Returns:
        Výsledek validace s konkrétním vysvětlením pro daný model auta
    """
    print(f"\nSpúšťam porovnanie príkladu, validate_attributes={validate_attributes}")
    
    # Parsování PL1 formule
    formula = parse_pl1_formula(example_formula)
    
    # Konverze formule na model - explicitně nastavíme is_first_positive=False, protože validační příklad není první pozitivní
    from backend.model import formula_to_model
    example_model = formula_to_model(formula, is_first_positive=False)
    
    # Pridame explicitný výpis pre kontrolu
    print(f"Počet objektov v príklade: {len(example_model.objects)}")
    for obj in example_model.objects:
        print(f"  - Objekt {obj.name}, Trieda: {obj.class_name}, Atribúty: {obj.attributes}")
    
    # Validace
    validator = ExampleValidator(model)
    result = validator.validate_example(example_model, validate_attributes)
    
    # Přidáme formuli pro lepší kontext
    result["formula"] = example_formula
    result["validate_attributes"] = validate_attributes
    
    # Skontrolujme, či výsledok obsahuje porušenia validácie atribútov
    if validate_attributes and "categorized_violations" in result:
        print(f"Výsledok validácie atribútov: {len(result['categorized_violations'].get('attribute_violations', []))} porušení")
    
    return result 