#!/usr/bin/env python3
from typing import Dict, List, Tuple, Set, Any, Optional
import traceback

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
        self.component_requirements = self._extract_component_requirements()
        self.attribute_values = self._extract_attribute_values()
        
    def _extract_rules(self) -> Dict[str, str]:
        """
        Dynamicky extrahuje pravidla pro každý model auta z natrénovaného modelu.
        
        Returns:
            Slovník s pravidly pro každý model auta
        """
        rules = {}
        car_models = ["Series3", "Series5", "Series7", "X5", "X7"]
        
        for obj in self.model.objects:
            if obj.class_name in car_models:
                if obj.attributes is not None and "rule" in obj.attributes:
                    rules[obj.class_name] = obj.attributes.get("rule", "")
        
        for model_type in car_models:
            if model_type not in rules or not rules[model_type]:
                rule_parts = []
                
                must_components = []
                for link in self.model.links:
                    if link.link_type == LinkType.MUST and link.source == model_type:
                        if link.target not in ["Component", "Engine", "Transmission", "DriveSystem"]:
                            must_components.append(f"must have {link.target}")
                
                must_not_components = []
                for link in self.model.links:
                    if link.link_type == LinkType.MUST_NOT and link.source == model_type:
                        must_not_components.append(f"must not have {link.target}")
                
                if hasattr(self, 'component_requirements') and model_type in self.component_requirements:
                    req = self.component_requirements[model_type]
                    
                    if "engines" in req and req["engines"]:
                        engine_options = ", ".join(req["engines"])
                        rule_parts.append(f"must have one of these engines: {engine_options}")
                    
                    if "transmission" in req and req["transmission"]:
                        transmission_options = ", ".join(req["transmission"])
                        rule_parts.append(f"must have one of these transmissions: {transmission_options}")
                    
                    if "drive" in req and req["drive"]:
                        drive_options = ", ".join(req["drive"])
                        rule_parts.append(f"must have one of these drives: {drive_options}")
                
                if must_components:
                    rule_parts.extend(must_components)
                
                if must_not_components:
                    rule_parts.extend(must_not_components)
                
                if rule_parts:
                    rules[model_type] = f"The {model_type} {' and '.join(rule_parts)}"
                else:
                    rules[model_type] = f"The {model_type} must follow BMW specifications"
        
        print("Extracted rules for models:", list(rules.keys()))
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
            component_requirements[model_type] = {
                "engines": [],
                "transmission": [],
                "drive": []
            }
            
            for link in self.model.links:
                if link.link_type == LinkType.MUST and link.source == model_type:
                    target = link.target
                    
                    if "Engine" in target:
                        component_requirements[model_type]["engines"].append(target)
                        print(f"  {model_type} - MUST Engine: {target}")
                    elif "Transmission" in target:
                        component_requirements[model_type]["transmission"].append(target)
                        print(f"  {model_type} - MUST Transmission: {target}")
                    elif target in ["XDrive", "AWD", "RWD"]:
                        component_requirements[model_type]["drive"].append(target)
                        print(f"  {model_type} - MUST Drive: {target}")
            
            for obj in self.model.objects:
                if obj.class_name == model_type and obj.attributes is not None:
                    for attr_name, attr_value in obj.attributes.items():
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
            
            if not component_requirements[model_type]["engines"]:
                car_object = next((obj for obj in self.model.objects if obj.class_name == model_type), None)
                if car_object:
                    for link in self.model.links:
                        if link.source == car_object.name:
                            target_obj = next((obj for obj in self.model.objects if obj.name == link.target), None)
                            if target_obj and "Engine" in target_obj.class_name:
                                component_requirements[model_type]["engines"].append(target_obj.class_name)
                                print(f"  {model_type} - Found Engine in links: {target_obj.class_name}")
            
            if model_type in ["X5", "X7"] and not component_requirements[model_type]["drive"]:
                component_requirements[model_type]["drive"].append("XDrive")
                print(f"  {model_type} - Default Drive: XDrive")
            
            if model_type == "Series7" and not component_requirements[model_type]["drive"]:
                component_requirements[model_type]["drive"].append("AWD")
                print(f"  {model_type} - Default Drive: AWD")
            
            if model_type == "Series3" and not component_requirements[model_type]["drive"]:
                component_requirements[model_type]["drive"].append("RWD")
                print(f"  {model_type} - Default Drive: RWD")
            
            if model_type == "Series5" and not component_requirements[model_type]["drive"]:
                component_requirements[model_type]["drive"].extend(["RWD", "AWD"])
                print(f"  {model_type} - Default Drives: RWD, AWD")
            
            if not component_requirements[model_type]["transmission"]:
                if model_type in ["X5", "X7", "Series7", "Series5"]:
                    component_requirements[model_type]["transmission"].append("AutomaticTransmission")
                    print(f"  {model_type} - Default Transmission: AutomaticTransmission")
                elif model_type == "Series3":
                    component_requirements[model_type]["transmission"].extend(["AutomaticTransmission", "ManualTransmission"])
                    print(f"  {model_type} - Default Transmissions: AutomaticTransmission, ManualTransmission")
            
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
        
        for link in self.model.links:
            if link.link_type == LinkType.MUST_BE_A:
                parent_map[link.source] = link.target
        
        class_hierarchy = {}
        for obj_name, parent_name in parent_map.items():
            if obj_name not in class_hierarchy and obj_name[0].isupper():
                class_hierarchy[obj_name] = parent_name
        
        print("\nExtrahujem hodnoty atribútov z modelu - vrátane hodnôt z rodičovských tried:")
        
        for obj in self.model.objects:
            if obj.attributes is not None:
                class_name = obj.class_name
                print(f"  Našiel som objekt triedy {class_name} s atribútmi: {obj.attributes}")
                
                if class_name not in attribute_values:
                    attribute_values[class_name] = {}
                
                for attr_name, attr_value in obj.attributes.items():
                    if isinstance(attr_value, (int, float)) or isinstance(attr_value, set) or (isinstance(attr_value, tuple) and len(attr_value) == 2):
                        attribute_values[class_name][attr_name] = attr_value
                        print(f"    Uložil som atribút {attr_name} = {attr_value}")
        
        all_classes = set()
        for link in self.model.links:
            if link.source[0].isupper() and link.target[0].isupper():
                all_classes.add(link.source)
                all_classes.add(link.target)
        
        print("\nRozširujem hodnoty atribútov z rodičovských tried:")
        
        for class_name in all_classes:
            if class_name not in attribute_values:
                attribute_values[class_name] = {}
            
            current_class = class_name
            while current_class in class_hierarchy:
                parent_class = class_hierarchy[current_class]
                print(f"  Kontrolujem rodičovskú triedu {parent_class} pre {class_name}")
                
                if parent_class in attribute_values:
                    for attr_name, attr_value in attribute_values[parent_class].items():
                        if attr_name not in attribute_values[class_name]:
                            attribute_values[class_name][attr_name] = attr_value
                            print(f"    Dedím atribút {attr_name} = {attr_value} z triedy {parent_class} pre triedu {class_name}")
                
                current_class = parent_class
        
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
            if attrs:
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
        
        self.attribute_values = self._extract_attribute_values()
        
        car_model = self._identify_car_model(example)
        
        if not car_model:
            print("Nepodarilo sa identifikovať typ modelu auta v príklade")
            return {
                "is_valid": False,
                "model_type": None,
                "violations": ["Nepodařilo se identifikovat typ modelu auta v příkladu"],
                "satisfied_rules": [],
                "allowed_alternatives": {},
                "categorized_violations": {},
                "highlighted_formula": {
                    "formula": "",
                    "tokens": []
                }
            }
        
        print(f"Identifikovaný model auta: {car_model}")
        
        validation_result = self._validate_against_model_rules(example, car_model, validate_attributes)
        
        model_formula = self.model.to_formula() if hasattr(self.model, 'to_formula') else ""
        
        highlighted_formula = self._generate_highlighted_formula(example, car_model, model_formula)
        
        validation_result["highlighted_formula"] = highlighted_formula
        
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
        bmw_models = ["Series3", "Series5", "Series7", "X5", "X7"]
        
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
            print(f"Pravidla pro model {model_type} nejsou k dispozici, budu vygenerovány dynamicky")
            if not hasattr(self, 'component_requirements') or model_type not in self.component_requirements:
                self.component_requirements = self._extract_component_requirements()
            
            self.rules = self._extract_rules()
        
        must_violations = self._check_must_relationships(example, model_type)
        
        must_not_violations = self._check_must_not_relationships(example, model_type)
        
        component_violations = self._check_component_requirements(example, model_type)
        
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
        
        all_violations = must_violations + must_not_violations + component_violations + attribute_violations
        
        satisfied_rules = self._collect_satisfied_rules(example, model_type, all_violations)
        
        if validate_attributes:
            satisfied_rules.extend(attribute_satisfied)
        
        allowed_alternatives = {
            "engines": self.component_requirements.get(model_type, {}).get("engines", []),
            "transmissions": self.component_requirements.get(model_type, {}).get("transmission", []),
            "drives": self.component_requirements.get(model_type, {}).get("drive", [])
        }
        
        categorized_violations = {
            "must_violations": must_violations,
            "must_not_violations": must_not_violations,
            "component_violations": component_violations,
            "attribute_violations": attribute_violations
        }
        
        print(f"\nCelkový počet porušení: {len(all_violations)}")
        print(f"Z toho porušenia validácie atribútov: {len(attribute_violations)}")
        
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
        
        model_objects = [obj for obj in example.objects if obj.class_name == model_type]
        if not model_objects:
            return [f"Příklad neobsahuje objekt typu {model_type}"]
        
        must_links = []
        for link in self.model.links:
            if link.link_type == LinkType.MUST and link.source == model_type:
                must_links.append(link)
        
        for must_link in must_links:
            required_component = must_link.target
            
            if required_component in ["Component", "Engine", "Transmission", "DriveSystem"]:
                continue
            
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
                
                for example_link in example.links:
                    if example_link.source == model_obj.name:
                        target_obj = next((obj for obj in example.objects if obj.name == example_link.target), None)
                        if not target_obj:
                            continue
                        
                        if target_obj.class_name == required_component:
                            has_component = True
                            break
                        
                        if component_category and target_obj.class_name in self.component_requirements.get(model_type, {}).get(component_category, []):
                            has_alternative = True
                
                if has_alternative:
                    continue
                
                if not has_component and not has_alternative:
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
        
        model_objects = [obj for obj in example.objects if obj.class_name == model_type]
        if not model_objects:
            return []
        
        must_not_links = []
        for link in self.model.links:
            if link.link_type == LinkType.MUST_NOT and link.source == model_type:
                must_not_links.append(link)
        
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
        
        if model_type not in self.rules:
            return []
            
        rule_text = self.rules[model_type]
        
        model_objects = [obj for obj in example.objects if obj.class_name == model_type]
        if not model_objects:
            return []
        
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
        
        for model_obj in model_objects:
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
        
        print(f"\nDEBUG: Checking {len(example.objects)} objects in example")
        for example_obj in example.objects:
            print(f"\nDEBUG: Checking object {example_obj.name} of class {example_obj.class_name}")
            if example_obj.attributes is not None:
                class_name = example_obj.class_name
                print(f"  Kontrolujem objekt {example_obj.name} triedy {class_name}, atribúty: {example_obj.attributes}")
                
                if class_name in self.attribute_values and self.attribute_values[class_name]:
                    print(f"    Trieda {class_name} má definované hodnoty atribútov v modeli:")
                    for name, value in self.attribute_values[class_name].items():
                        print(f"      - {name}: {value} (typ: {type(value).__name__})")
                    
                    for attr_name, example_value in example_obj.attributes.items():
                        print(f"    Kontrolujem atribút {attr_name} s hodnotou {example_value} (typ: {type(example_value).__name__})")
                        
                        if attr_name in self.attribute_values[class_name]:
                            model_value = self.attribute_values[class_name][attr_name]
                            print(f"      Model definuje atribút {attr_name} s očakávanou hodnotou {model_value} (typ: {type(model_value).__name__})")
                            
                            is_valid_value = False
                            
                            if isinstance(model_value, set):
                                if example_value in model_value:
                                    is_valid_value = True
                                    satisfied.append(f"Objekt {example_obj.name} ({class_name}) má platnú hodnotu atribútu {attr_name}: {example_value}")
                                    print(f"      ✅ Hodnota {example_value} je platná, je v množine povolených hodnôt")
                                else:
                                    violations.append(f"Objekt {example_obj.name} ({class_name}) má neplatnú hodnotu atribútu {attr_name}: {example_value}, povolené hodnoty sú: {', '.join(map(str, model_value))}")
                                    print(f"      ❌ Hodnota {example_value} je neplatná, nie je v množine povolených hodnôt: {model_value}")
                            
                            elif isinstance(model_value, tuple) and len(model_value) == 2:
                                min_val, max_val = model_value
                                if isinstance(example_value, (int, float)) and min_val <= example_value <= max_val:
                                    is_valid_value = True
                                    satisfied.append(f"Objekt {example_obj.name} ({class_name}) má platnú hodnotu atribútu {attr_name}: {example_value} (v intervale {min_val}-{max_val})")
                                    print(f"      ✅ Hodnota {example_value} je platná, je v intervale {min_val}-{max_val}")
                                else:
                                    violations.append(f"Objekt {example_obj.name} ({class_name}) má neplatnú hodnotu atribútu {attr_name}: {example_value}, povolený interval je: {min_val}-{max_val}")
                                    print(f"      ❌ Hodnota {example_value} je neplatná, nie je v intervale {min_val}-{max_val}")
                            
                            elif isinstance(model_value, (int, float)) and isinstance(example_value, (int, float)):
                                if example_value == model_value:
                                    is_valid_value = True
                                    satisfied.append(f"Objekt {example_obj.name} ({class_name}) má platnú číselnú hodnotu atribútu {attr_name}: {example_value}")
                                    print(f"      ✅ Číselná hodnota {example_value} je platná, rovná sa očakávanej hodnote {model_value}")
                                else:
                                    violations.append(f"Objekt {example_obj.name} ({class_name}) má neplatnú číselnú hodnotu atribútu {attr_name}: {example_value}, očakávaná hodnota je presne: {model_value}")
                                    print(f"      ❌ Číselná hodnota {example_value} je neplatná, očakávaná hodnota: {model_value}, rozdiel: {example_value - model_value}")
                            
                            elif example_value == model_value:
                                is_valid_value = True
                                satisfied.append(f"Objekt {example_obj.name} ({class_name}) má platnú hodnotu atribútu {attr_name}: {example_value}")
                                print(f"      ✅ Hodnota {example_value} je platná")
                            else:
                                violations.append(f"Objekt {example_obj.name} ({class_name}) má neplatnú hodnotu atribútu {attr_name}: {example_value}, očakávaná hodnota je presne: {model_value}")
                                print(f"      ❌ Hodnota {example_value} je neplatná, očakávaná hodnota: {model_value}")
                        
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
        
        satisfied.append(f"Příklad obsahuje objekt typu {model_type}")
        
        model_objects = [obj for obj in example.objects if obj.class_name == model_type]
        if not model_objects:
            return satisfied
        
        present_engines = set()
        present_transmissions = set()
        present_drives = set()
        
        for model_obj in model_objects:
            added_component_rules = {
                "engines": False,
                "transmission": False,
                "drive": False
            }
            
            for example_link in example.links:
                if example_link.source == model_obj.name:
                    target_obj = next((obj for obj in example.objects if obj.name == example_link.target), None)
                    if not target_obj:
                        continue
                    
                    if (target_obj.class_name in self.component_requirements.get(model_type, {}).get("engines", [])):
                        present_engines.add(target_obj.class_name)
                        engine_rule = f"Model {model_type} má validní motor typu {target_obj.class_name}"
                        if not any(v.startswith(f"Model {model_type} musí mít jeden z motorů") for v in violations):
                            if not added_component_rules["engines"]:
                                satisfied.append(engine_rule)
                                added_component_rules["engines"] = True
                    
                    if (target_obj.class_name in self.component_requirements.get(model_type, {}).get("transmission", [])):
                        present_transmissions.add(target_obj.class_name)
                        transmission_rule = f"Model {model_type} má validní převodovku typu {target_obj.class_name}"
                        if not any(v.startswith(f"Model {model_type} musí mít jednu z převodovek") for v in violations):
                            if not added_component_rules["transmission"]:
                                satisfied.append(transmission_rule)
                                added_component_rules["transmission"] = True
                    
                    if (target_obj.class_name in self.component_requirements.get(model_type, {}).get("drive", [])):
                        present_drives.add(target_obj.class_name)
                        drive_rule = f"Model {model_type} má validní pohon typu {target_obj.class_name}"
                        if not any(v.startswith(f"Model {model_type} musí mít jeden z pohonů") for v in violations):
                            if not added_component_rules["drive"]:
                                satisfied.append(drive_rule)
                                added_component_rules["drive"] = True
        
        for link in self.model.links:
            if link.link_type == LinkType.MUST and link.source == model_type:
                if link.target in ["Component", "Engine", "Transmission", "DriveSystem"]:
                    continue
                
                requirement_satisfied = False
                for model_obj in model_objects:
                    for example_link in example.links:
                        if example_link.source == model_obj.name:
                            target_obj = next((obj for obj in example.objects if obj.name == example_link.target), None)
                            if target_obj and target_obj.class_name == link.target:
                                requirement_satisfied = True
                                break
                
                if requirement_satisfied:
                    rule_text = f"Model {model_type} obsahuje požadovanou komponentu {link.target}"
                    if rule_text not in satisfied:
                        satisfied.append(rule_text)
        
        must_not_violations = [v for v in violations if "nesmí mít komponentu" in v]
        must_not_violation_components = []
        
        for violation in must_not_violations:
            parts = violation.split("nesmí mít komponentu")
            if len(parts) > 1:
                component = parts[1].strip()
                must_not_violation_components.append(component)
        
        for link in self.model.links:
            if link.link_type == LinkType.MUST_NOT and link.source == model_type:
                if link.target not in must_not_violation_components:
                    rule_text = f"Model {model_type} správně neobsahuje zakázanou komponentu {link.target}"
                    satisfied.append(rule_text)
        
        if present_engines and not any(v.startswith(f"Model {model_type} musí mít jeden z motorů") for v in violations):
            options = ", ".join(self.component_requirements.get(model_type, {}).get("engines", []))
            satisfied.append(f"Model {model_type} splňuje požadavek na motor (povolené: {options})")
            
        if present_transmissions and not any(v.startswith(f"Model {model_type} musí mít jednu z převodovek") for v in violations):
            options = ", ".join(self.component_requirements.get(model_type, {}).get("transmission", []))
            satisfied.append(f"Model {model_type} splňuje požadavek na převodovku (povolené: {options})")
            
        if present_drives and not any(v.startswith(f"Model {model_type} musí mít jeden z pohonů") for v in violations):
            options = ", ".join(self.component_requirements.get(model_type, {}).get("drive", []))
            satisfied.append(f"Model {model_type} splňuje požadavek na pohon (povolené: {options})")
        
        return satisfied

    def _generate_highlighted_formula(self, example: Model, model_type: str, model_formula: str) -> Dict[str, Any]:
        """
        Generuje zvýrazněnou verzi formule modelu s označením, které části jsou splněny a které porušeny v příkladu.
        Taktiež identifikuje prvky, ktoré sú v príklade navyše a nie sú v modeli.
        
        Args:
            example: Příklad k validaci
            model_type: Typ modelu auta
            model_formula: Formule modelu
            
        Returns:
            Slovník obsahující informace o zvýraznění formule
        """
        from backend.pl1_parser import parse_pl1_formula
        model_predicates = []
        try:
            parsed_formula = parse_pl1_formula(model_formula)
            if hasattr(parsed_formula, 'predicates'):
                model_predicates = parsed_formula.predicates
        except Exception as e:
            print(f"Chyba při parsování formule: {e}")
            return {"highlighted_formula": model_formula, "tokens": []}
        
        example_predicates = []
        for obj in example.objects:
            example_predicates.append(("Ι", obj.name, obj.class_name))
            
            for link in example.links:
                if link.source == obj.name:
                    target_obj = next((o for o in example.objects if o.name == link.target), None)
                    if target_obj:
                        example_predicates.append(("Π", obj.name, target_obj.name))
            
            if obj.attributes:
                for attr_name, attr_value in obj.attributes.items():
                    example_predicates.append(("Α", obj.name, attr_name, attr_value))
        
        extra_predicates = []
        model_classes = set()
        model_objects = set()
        
        for obj in self.model.objects:
            model_classes.add(obj.class_name)
            model_objects.add(obj.name)
        
        for pred in example_predicates:
            if pred[0] == "Ι":
                _, obj_name, class_name = pred
                if class_name not in model_classes:
                    extra_predicates.append(pred)
            elif pred[0] == "Π":
                _, parent, child = pred
                if parent not in model_objects or child not in model_objects:
                    extra_predicates.append(pred)
        
        tokens = []
        matched_components = set()
        unmatched_components = set()
        extra_components = set()
        
        if not model_predicates:
            return {"highlighted_formula": model_formula, "tokens": []}
        
        for pred_idx, pred in enumerate(model_predicates):
            pred_str = str(pred)
            pred_type = pred.predicate
            pred_args = pred.args
            
            is_satisfied = False
            
            if pred_type == "Ι":
                obj_name, class_name = pred_args
                if ("Ι", obj_name, class_name) in example_predicates:
                    is_satisfied = True
                    matched_components.add(class_name)
                else:
                    unmatched_components.add(class_name)
            
            elif pred_type == "Π":
                parent, child = pred_args
                if ("Π", parent, child) in example_predicates:
                    is_satisfied = True
                    matched_components.add(parent)
                    matched_components.add(child)
                else:
                    unmatched_components.add(parent)
                    unmatched_components.add(child)
            
            elif pred_type == "Α":
                obj_name, attr_name, attr_value = pred_args
                is_satisfied = False
                for ex_pred in example_predicates:
                    if len(ex_pred) == 4 and ex_pred[0] == "Α" and ex_pred[1] == obj_name and ex_pred[2] == attr_name:
                        if ex_pred[3] == attr_value:
                            is_satisfied = True
                            break
            
            tokens.append({
                "text": pred_str,
                "is_satisfied": is_satisfied,
                "type": "predicate"
            })
            
            if pred_idx < len(model_predicates) - 1:
                tokens.append({
                    "text": " ∧ ",
                    "is_satisfied": None,
                    "type": "connector"
                })
        
        for pred in extra_predicates:
            if pred[0] == "Ι":
                _, _, class_name = pred
                extra_components.add(class_name)
        
        highlighted_formula = "".join([token["text"] for token in tokens])
        
        stats = {
            "matched_components": list(matched_components),
            "unmatched_components": list(unmatched_components),
            "extra_components": list(extra_components),
            "total_predicates": len(model_predicates),
            "satisfied_predicates": sum(1 for token in tokens if token.get("is_satisfied") == True)
        }
        
        return {
            "highlighted_formula": highlighted_formula,
            "tokens": tokens,
            "stats": stats
        }

def compare_example(model: Model, example_formula: str, validate_attributes: bool = True) -> Dict[str, Any]:
    """
    Zjednodušená validácia príkladu voči hypotéze modelu.
    
    Args:
        model: Aktuálny model (hypotéza)
        example_formula: Formula príkladu na validáciu
        validate_attributes: Parameter zachovaný pre spätnú kompatibilitu, vždy True
        
    Returns:
        Výsledok porovnania
    """
    try:
        from backend.pl1_parser import parse_pl1_formula
        from backend.model import formula_to_model
        
        import sys
        classification_tree = None
        
        try:
            from backend.app import classification_tree as global_tree
            classification_tree = global_tree
            print("Získaný klasifikačný strom z app.py")
        except (ImportError, AttributeError):
            print("Nepodarilo sa získať klasifikačný strom z app.py")
            from backend.model import ClassificationTree
            classification_tree = ClassificationTree()
            classification_tree.add_relationship("Motor", None)
            classification_tree.add_relationship("DieselovyMotor", "Motor")
            classification_tree.add_relationship("BenzinovyMotor", "Motor")
            classification_tree.add_relationship("HybridnyMotor", "Motor")
            classification_tree.add_relationship("Prevodovka", None)
            classification_tree.add_relationship("AutomatickaPrevodovka", "Prevodovka")
            classification_tree.add_relationship("ManualnaPrevodovka", "Prevodovka")
            classification_tree.add_relationship("Pohon", None)
            classification_tree.add_relationship("RWD", "Pohon")
            classification_tree.add_relationship("AWD", "Pohon")
            classification_tree.add_relationship("XDrive", "AWD")
            classification_tree.add_relationship("Vybava", None)
            classification_tree.add_relationship("Basic", "Vybava")
            classification_tree.add_relationship("Sport", "Vybava")
            classification_tree.add_relationship("Lux", "Vybava")
            print("Vytvorený záložný klasifikačný strom")
        
        formula = parse_pl1_formula(example_formula)
        example_model = formula_to_model(formula)
        
        matched_predicates, unmatched_predicates, extra_predicates = compare_models_directly(model, example_model, classification_tree)
        
        is_valid = len(unmatched_predicates) == 0
        
        violations = []
        satisfied_rules = []
        
        for pred in unmatched_predicates:
            violations.append(f"Chýbajúci predikát v príklade: {pred}")
        
        for pred in matched_predicates:
            satisfied_rules.append(f"Splnený predikát: {pred}")
        
        extra_components = []
        if extra_predicates:
            for pred in extra_predicates:
                if pred.startswith("Ι(") and "," in pred:
                    try:
                        class_name = pred.split(",")[1].strip().rstrip(")")
                        should_add = True
                        
                        if classification_tree:
                            for matched_pred in matched_predicates:
                                if matched_pred.startswith("Ι("):
                                    matched_class = matched_pred.split(",")[1].strip().rstrip(")")
                                    if classification_tree.is_subclass(class_name, matched_class):
                                        should_add = False
                                        break
                        
                        if should_add and class_name not in extra_components:
                            extra_components.append(class_name)
                    except Exception as e:
                        print(f"Chyba pri spracovaní extra komponentu: {e}")
        
        categorized_violations = {
            "must_violations": [],
            "must_not_violations": [],
            "component_violations": violations,
            "attribute_violations": [],
            "extra_components": [f"Príklad obsahuje nadbytočný komponent: {comp}" for comp in extra_components]
        }
        
        highlighted_formula = highlight_formula(model, example_model, model.to_formula(), classification_tree)
        
        result = {
            "is_valid": is_valid,
            "model_type": "General",
            "violations": violations,
            "satisfied_rules": satisfied_rules,
            "formula": example_formula,
            "validate_attributes": True,
            "categorized_violations": categorized_violations,
            "highlighted_formula": highlighted_formula,
            "model_formula": model.to_formula(),
            "extra_components": extra_components
        }
        
        return result
    except Exception as e:
        print(f"Error in compare_example: {e}")
        traceback.print_exc()
        return {
            "is_valid": False,
            "model_type": "General",
            "violations": [f"Chyba pri validácii príkladu: {str(e)}"],
            "satisfied_rules": [],
            "formula": example_formula,
            "validate_attributes": True,
            "highlighted_formula": {
                "highlighted_formula": "",
                "tokens": []
            },
            "model_formula": model.to_formula() if model else ""
        }

def compare_models_directly(model: Model, example_model: Model, classification_tree=None) -> Tuple[List[str], List[str], List[str]]:
    """
    Priame porovnanie modelu (hypotézy) a príkladu na úrovni predikátov.
    
    Args:
        model: Aktuálny model (hypotéza)
        example_model: Model príkladu
        classification_tree: Klasifikačný strom pre hierarchické vzťahy
        
    Returns:
        Trojica zoznamov: (splnené predikáty, nesplnené predikáty, predikáty navyše v príklade)
    """
    if classification_tree:
        print("\n===== KLASIFIKAČNÝ STROM =====")
        try:
            for child, parent in classification_tree.parent_map.items():
                print(f"Trieda {child} -> rodič {parent or 'NONE'}")
        except Exception as e:
            print(f"Chyba pri výpise klasifikačného stromu: {e}")
    else:
        print("UPOZORNENIE: Klasifikačný strom nie je dostupný!")
    
    model_predicates = set()
    example_predicates = set()
    
    model_numeric_predicates = {}
    
    model_set_predicates = {}
    
    model_is_a_relationships = {}
    example_is_a_relationships = {}
    
    print("\n===== SPRACOVANIE IS-A VZŤAHOV =====")
    
    for obj in model.objects:
        model_predicates.add(f"Ι({obj.name}, {obj.class_name})")
        model_is_a_relationships[obj.name] = obj.class_name
        print(f"Model objekt: {obj.name} je typu {obj.class_name}")
    
    for obj in example_model.objects:
        example_predicates.add(f"Ι({obj.name}, {obj.class_name})")
        example_is_a_relationships[obj.name] = obj.class_name
        print(f"Príklad objekt: {obj.name} je typu {obj.class_name}")
    
    for link in model.links:
        if link.link_type.value == "REGULAR":
            model_predicates.add(f"Π({link.source}, {link.target})")
    
    for link in example_model.links:
        if link.link_type.value == "REGULAR":
            example_predicates.add(f"Π({link.source}, {link.target})")
    
    for obj in model.objects:
        if obj.attributes:
            for attr_name, attr_value in obj.attributes.items():
                if isinstance(attr_value, (int, float)):
                    model_predicates.add(f"Α({obj.name}, {attr_name}, {attr_value})")
                    model_numeric_predicates[(obj.name, attr_name)] = (attr_value, attr_value)
                elif isinstance(attr_value, set):
                    values_str = ", ".join(sorted(str(v) for v in attr_value))
                    model_predicates.add(f"Α({obj.name}, {attr_name}, {{{values_str}}})")
                    model_set_predicates[(obj.name, attr_name)] = attr_value
                elif isinstance(attr_value, tuple) and len(attr_value) == 2:
                    min_val, max_val = attr_value
                    model_predicates.add(f"Α({obj.name}, {attr_name}, [{min_val}-{max_val}])")
                    model_numeric_predicates[(obj.name, attr_name)] = (min_val, max_val)
                else:
                    model_predicates.add(f"Α({obj.name}, {attr_name}, {attr_value})")
    
    example_numeric_attrs = {}
    example_set_attrs = {}
    
    for obj in example_model.objects:
        if obj.attributes:
            for attr_name, attr_value in obj.attributes.items():
                if isinstance(attr_value, (int, float)):
                    example_predicates.add(f"Α({obj.name}, {attr_name}, {attr_value})")
                    example_numeric_attrs[(obj.name, attr_name)] = attr_value
                elif isinstance(attr_value, set):
                    values_str = ", ".join(sorted(str(v) for v in attr_value))
                    example_predicates.add(f"Α({obj.name}, {attr_name}, {{{values_str}}})")
                    example_set_attrs[(obj.name, attr_name)] = attr_value
                elif isinstance(attr_value, tuple) and len(attr_value) == 2:
                    mid_value = (attr_value[0] + attr_value[1]) / 2
                    example_predicates.add(f"Α({obj.name}, {attr_name}, [{attr_value[0]}-{attr_value[1]}])")
                    example_numeric_attrs[(obj.name, attr_name)] = mid_value
                else:
                    example_predicates.add(f"Α({obj.name}, {attr_name}, {attr_value})")
                    example_set_attrs[(obj.name, attr_name)] = attr_value
    
    matched_predicates = []
    unmatched_predicates = []
    
    print("\n===== POROVNANIE IS-A PREDIKÁTOV =====")
    
    is_a_predicates_model = set(pred for pred in model_predicates if pred.startswith("Ι("))
    is_a_predicates_example = set(pred for pred in example_predicates if pred.startswith("Ι("))
    
    model_obj_to_pred = {}
    for pred in is_a_predicates_model:
        parts = pred.split(",", 1)
        if len(parts) >= 2:
            obj_name = parts[0][2:].strip()
            model_obj_to_pred[obj_name] = pred
    
    print(f"IS-A predikáty v modeli: {is_a_predicates_model}")
    print(f"IS-A predikáty v príklade: {is_a_predicates_example}")
    
    for obj_name, example_class in example_is_a_relationships.items():
        print(f"Kontrolujem objekt {obj_name} typu {example_class} z príkladu")
        
        if obj_name in model_is_a_relationships:
            model_class = model_is_a_relationships[obj_name]
            print(f"  Našiel som zodpovedajúci objekt v modeli typu {model_class}")
            
            if example_class == model_class:
                print(f"  Priama zhoda tried: {example_class} == {model_class}")
                if obj_name in model_obj_to_pred:
                    matched_predicates.append(model_obj_to_pred[obj_name])
                    
            elif classification_tree:
                is_subclass = False
                
                try:
                    if hasattr(classification_tree, 'is_subclass') and callable(getattr(classification_tree, 'is_subclass')):
                        is_subclass = classification_tree.is_subclass(example_class, model_class)
                        print(f"  classification_tree.is_subclass({example_class}, {model_class}) = {is_subclass}")
                except Exception as e:
                    print(f"  Chyba pri volaní is_subclass: {e}")
                
                if not is_subclass and hasattr(classification_tree, 'parent_map'):
                    current = example_class
                    while current and current in classification_tree.parent_map:
                        parent = classification_tree.parent_map.get(current)
                        print(f"  Hierarchia: {current} -> {parent}")
                        if parent == model_class:
                            is_subclass = True
                            break
                        current = parent
                
                if is_subclass:
                    print(f"  Hierarchická zhoda: {example_class} je podtriedou {model_class}")
                    if obj_name in model_obj_to_pred:
                        matched_predicates.append(model_obj_to_pred[obj_name])
                else:
                    print(f"  Bez zhody: {example_class} nie je podtriedou {model_class}")
                    if obj_name in model_obj_to_pred:
                        unmatched_predicates.append(model_obj_to_pred[obj_name])
            else:
                print(f"  Bez klasifikačného stromu, nemôžem overiť hierarchiu")
                if obj_name in model_obj_to_pred:
                    unmatched_predicates.append(model_obj_to_pred[obj_name])
        else:
            print(f"  Objekt {obj_name} neexistuje v modeli")
    
    for obj_name, pred in model_obj_to_pred.items():
        if pred not in matched_predicates and pred not in unmatched_predicates:
            unmatched_predicates.append(pred)
    
    model_predicates = model_predicates - is_a_predicates_model
    example_predicates = example_predicates - is_a_predicates_example
    
    print("\n===== POROVNANIE OSTATNÝCH PREDIKÁTOV =====")
    
    numeric_attr_predicates = set()
    set_attr_predicates = set()
    
    for pred in model_predicates:
        if pred.startswith("Α(") and "," in pred:
            parts = pred.split(",", 2)
            if len(parts) >= 3:
                obj_name = parts[0][2:].strip()
                attr_name = parts[1].strip()
                if (obj_name, attr_name) in model_numeric_predicates:
                    numeric_attr_predicates.add(pred)
                    continue
                if (obj_name, attr_name) in model_set_predicates:
                    set_attr_predicates.add(pred)
                    continue
        
        if pred in example_predicates:
            matched_predicates.append(pred)
        else:
            unmatched_predicates.append(pred)
    
    for obj_name, attr_name in model_numeric_predicates.keys():
        min_val, max_val = model_numeric_predicates[(obj_name, attr_name)]
        pred_text = f"Α({obj_name}, {attr_name}, "
        
        if (obj_name, attr_name) in example_numeric_attrs:
            example_value = example_numeric_attrs[(obj_name, attr_name)]
            
            if min_val <= example_value <= max_val:
                if min_val == max_val:
                    matched_predicates.append(f"{pred_text}{min_val})")
                else:
                    matched_predicates.append(f"{pred_text}[{min_val}-{max_val}])")
            else:
                if min_val == max_val:
                    unmatched_predicates.append(f"{pred_text}{min_val})")
                else:
                    unmatched_predicates.append(f"{pred_text}[{min_val}-{max_val}])")
        else:
            if min_val == max_val:
                unmatched_predicates.append(f"{pred_text}{min_val})")
            else:
                unmatched_predicates.append(f"{pred_text}[{min_val}-{max_val}])")
    
    for obj_name, attr_name in model_set_predicates.keys():
        allowed_values = model_set_predicates[(obj_name, attr_name)]
        values_str = ", ".join(sorted(str(v) for v in allowed_values))
        pred_text = f"Α({obj_name}, {attr_name}, {{{values_str}}})"
        
        if (obj_name, attr_name) in example_set_attrs:
            example_value = example_set_attrs[(obj_name, attr_name)]
            
            if isinstance(example_value, (set, list)):
                if any(val in allowed_values for val in example_value):
                    matched_predicates.append(pred_text)
                else:
                    unmatched_predicates.append(pred_text)
            else:
                if example_value in allowed_values:
                    matched_predicates.append(pred_text)
                else:
                    unmatched_predicates.append(pred_text)
        else:
            unmatched_predicates.append(pred_text)
    
    print("\n===== HĽADANIE NADBYTOČNÝCH PREDIKÁTOV =====")
    extra_predicates = []
    
    for pred in is_a_predicates_example:
        parts = pred.split(",", 1)
        if len(parts) >= 2:
            obj_name = parts[0][2:].strip()
            example_class = parts[1].strip().rstrip(")")
            
            print(f"Kontrolujem nadbytočnosť objektu {obj_name} typu {example_class}")
            is_extra = True
            
            if obj_name in model_is_a_relationships:
                model_class = model_is_a_relationships[obj_name]
                
                if example_class == model_class:
                    print(f"  Nie je nadbytočný - priama zhoda tried: {example_class} == {model_class}")
                    is_extra = False
                
                elif classification_tree:
                    is_subclass = False
                    
                    try:
                        if hasattr(classification_tree, 'is_subclass') and callable(getattr(classification_tree, 'is_subclass')):
                            is_subclass = classification_tree.is_subclass(example_class, model_class)
                            print(f"  classification_tree.is_subclass({example_class}, {model_class}) = {is_subclass}")
                    except Exception as e:
                        print(f"  Chyba pri volaní is_subclass: {e}")
                    
                    if not is_subclass and hasattr(classification_tree, 'parent_map'):
                        current = example_class
                        while current and current in classification_tree.parent_map:
                            parent = classification_tree.parent_map.get(current)
                            print(f"  Hierarchia: {current} -> {parent}")
                            if parent == model_class:
                                is_subclass = True
                                break
                            current = parent
                    
                    if is_subclass:
                        print(f"  Nie je nadbytočný - hierarchická zhoda: {example_class} je podtriedou {model_class}")
                        is_extra = False
            
            if is_extra:
                print(f"  NADBYTOČNÝ: {pred}")
                extra_predicates.append(pred)
    
    for pred in example_predicates:
        if pred.startswith("Α(") and "," in pred:
            parts = pred.split(",", 2)
            if len(parts) >= 3:
                obj_name = parts[0][2:].strip()
                attr_name = parts[1].strip()
                if (obj_name, attr_name) in model_numeric_predicates or (obj_name, attr_name) in model_set_predicates:
                    continue
        
        if pred not in model_predicates:
            extra_predicates.append(pred)
    
    print(f"\n===== VÝSLEDKY POROVNANIA =====")
    print(f"Matched: {len(matched_predicates)}")
    print(f"Unmatched: {len(unmatched_predicates)}")
    print(f"Extra: {len(extra_predicates)}")
    
    return matched_predicates, unmatched_predicates, extra_predicates

def highlight_formula(model: Model, example_model: Model, model_formula: str, classification_tree=None) -> Dict[str, Any]:
    """
    Zjednodušená funkcia na zvýraznenie formuly podľa splnených/nesplnených predikátov.
    
    Args:
        model: Aktuálny model (hypotéza)
        example_model: Model príkladu
        model_formula: Formula modelu na zvýraznenie
        classification_tree: Klasifikačný strom pre hierarchické vzťahy
        
    Returns:
        Slovník so zvýraznenou formulou
    """
    try:
        matched_predicates, unmatched_predicates, extra_predicates = compare_models_directly(model, example_model, classification_tree)
        
        from backend.pl1_parser import parse_pl1_formula
        parsed_formula = parse_pl1_formula(model_formula)
        model_predicates = []
        
        if hasattr(parsed_formula, 'predicates'):
            model_predicates = parsed_formula.predicates
        
        tokens = []
        
        for pred_idx, pred in enumerate(model_predicates):
            pred_str = str(pred)
            
            is_satisfied = any(pred_str in matched for matched in matched_predicates)

            tokens.append({
                "text": pred_str,
                "is_satisfied": is_satisfied,
                "type": "predicate"
            })
            
            if pred_idx < len(model_predicates) - 1:
                tokens.append({
                    "text": " ∧ ",
                    "is_satisfied": None,  
                    "type": "connector"
                })
        
        highlighted_formula = "".join([token["text"] for token in tokens])
        
        stats = {
            "total_predicates": len(model_predicates),
            "satisfied_predicates": sum(1 for token in tokens if token.get("is_satisfied") == True),
            "extra_components": extra_predicates
        }
        
        return {
            "highlighted_formula": highlighted_formula,
            "tokens": tokens,
            "stats": stats
        }
    except Exception as e:
        print(f"Error highlighting formula: {e}")
        traceback.print_exc()
        return {
            "highlighted_formula": model_formula,
            "tokens": [],
            "stats": {
                "total_predicates": 0,
                "satisfied_predicates": 0
            }
        } 
