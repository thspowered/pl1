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
        self.rules = model.extract_model_rules()
        
    def validate_example(self, example: Model) -> Dict[str, Any]:
        """
        Validuje příklad proti pravidlům naučeného modelu pro konkrétní model auta.
        
        Args:
            example: Příklad k validaci
            
        Returns:
            Slovník s výsledky validace, obsahující:
            - is_valid: True pokud příklad splňuje všechna relevantní pravidla
            - model_type: Detekovaný typ modelu auta (Series3, X5, apod.)
            - violations: Seznam porušených pravidel, pokud is_valid je False
            - satisfied_rules: Seznam splněných pravidel
        """
        # Zjistíme, o jaký model auta se jedná
        car_model = self._identify_car_model(example)
        
        if not car_model:
            return {
                "is_valid": False,
                "model_type": None,
                "violations": ["Nepodařilo se identifikovat typ modelu auta v příkladu"],
                "satisfied_rules": []
            }
        
        # Validujeme příklad proti pravidlům pro konkrétní model auta
        validation_result = self._validate_against_model_rules(example, car_model)
        
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
    
    def _validate_against_model_rules(self, example: Model, model_type: str) -> Dict[str, Any]:
        """
        Validuje příklad proti pravidlům pro konkrétní model auta.
        
        Args:
            example: Příklad k validaci
            model_type: Typ modelu auta (Series3, X5, apod.)
            
        Returns:
            Slovník s výsledky validace
        """
        if model_type not in self.rules:
            return {
                "is_valid": False,
                "model_type": model_type,
                "violations": [f"Pravidla pro model {model_type} nejsou k dispozici"],
                "satisfied_rules": []
            }
        
        # Kontrola MUST vztahů
        must_violations = self._check_must_relationships(example, model_type)
        
        # Kontrola MUST_NOT vztahů
        must_not_violations = self._check_must_not_relationships(example, model_type)
        
        # Kontrola komponentů (různé typy motorů, převodovek, pohonů)
        component_violations = self._check_component_requirements(example, model_type)
        
        # Spojíme všechny porušení
        all_violations = must_violations + must_not_violations + component_violations
        
        # Připravíme seznam splněných pravidel
        satisfied_rules = self._collect_satisfied_rules(example, model_type, all_violations)
        
        return {
            "is_valid": len(all_violations) == 0,
            "model_type": model_type,
            "violations": all_violations,
            "satisfied_rules": satisfied_rules
        }
    
    def _check_must_relationships(self, example: Model, model_type: str) -> List[str]:
        """
        Kontroluje, zda příklad splňuje všechny povinné vztahy (MUST).
        Zaměřuje se pouze na vztahy relevantní pro konkrétní model auta.
        
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
                
            for model_obj in model_objects:
                has_component = False
                
                # Kontrola, zda model má vyžadovaný komponent
                for example_link in example.links:
                    if example_link.source == model_obj.name:
                        target_obj = next((obj for obj in example.objects if obj.name == example_link.target), None)
                        if target_obj and target_obj.class_name == required_component:
                            has_component = True
                            break
                
                if not has_component:
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
        
        # Definujeme specifické požadavky podle modelu
        component_requirements = {
            "X5": {
                "engines": ["PetrolEngine", "DieselEngine", "HybridEngine"],
                "transmission": ["AutomaticTransmission"],
                "drive": ["XDrive"]
            },
            "X7": {
                "engines": ["PetrolEngine", "HybridEngine"],
                "transmission": ["AutomaticTransmission"],
                "drive": ["XDrive"]
            },
            "Series3": {
                "engines": ["PetrolEngine", "DieselEngine"],
                "transmission": ["AutomaticTransmission", "ManualTransmission"],
                "drive": ["RWD"]
            },
            "Series5": {
                "engines": ["PetrolEngine", "DieselEngine", "HybridEngine"],
                "transmission": ["AutomaticTransmission"],
                "drive": ["RWD", "AWD"]
            },
            "Series7": {
                "engines": ["PetrolEngine", "HybridEngine"],
                "transmission": ["AutomaticTransmission"],
                "drive": ["AWD"]
            }
        }
        
        # Kontrolujeme, zda příklad splňuje požadavky na komponenty
        model_objects = [obj for obj in example.objects if obj.class_name == model_type]
        if not model_objects:
            return []
            
        for model_obj in model_objects:
            # Kontrola motorů
            has_valid_engine = False
            for example_link in example.links:
                if example_link.source == model_obj.name:
                    target_obj = next((obj for obj in example.objects if obj.name == example_link.target), None)
                    if target_obj and target_obj.class_name in component_requirements.get(model_type, {}).get("engines", []):
                        has_valid_engine = True
                        break
            
            if not has_valid_engine and "engines" in component_requirements.get(model_type, {}):
                allowed_engines = ", ".join(component_requirements[model_type]["engines"])
                violations.append(f"Model {model_type} musí mít jeden z motorů: {allowed_engines}")
            
            # Kontrola převodovky
            has_valid_transmission = False
            for example_link in example.links:
                if example_link.source == model_obj.name:
                    target_obj = next((obj for obj in example.objects if obj.name == example_link.target), None)
                    if target_obj and target_obj.class_name in component_requirements.get(model_type, {}).get("transmission", []):
                        has_valid_transmission = True
                        break
            
            if not has_valid_transmission and "transmission" in component_requirements.get(model_type, {}):
                allowed_transmissions = ", ".join(component_requirements[model_type]["transmission"])
                violations.append(f"Model {model_type} musí mít jednu z převodovek: {allowed_transmissions}")
            
            # Kontrola pohonu
            has_valid_drive = False
            for example_link in example.links:
                if example_link.source == model_obj.name:
                    target_obj = next((obj for obj in example.objects if obj.name == example_link.target), None)
                    if target_obj and target_obj.class_name in component_requirements.get(model_type, {}).get("drive", []):
                        has_valid_drive = True
                        break
            
            if not has_valid_drive and "drive" in component_requirements.get(model_type, {}):
                allowed_drives = ", ".join(component_requirements[model_type]["drive"])
                violations.append(f"Model {model_type} musí mít jeden z pohonů: {allowed_drives}")
        
        return violations
    
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
        
        # Definujeme specifické požadavky podle modelu
        component_requirements = {
            "X5": {
                "engines": ["PetrolEngine", "DieselEngine", "HybridEngine"],
                "transmission": ["AutomaticTransmission"],
                "drive": ["XDrive"]
            },
            "X7": {
                "engines": ["PetrolEngine", "HybridEngine"],
                "transmission": ["AutomaticTransmission"],
                "drive": ["XDrive"]
            },
            "Series3": {
                "engines": ["PetrolEngine", "DieselEngine"],
                "transmission": ["AutomaticTransmission", "ManualTransmission"],
                "drive": ["RWD"]
            },
            "Series5": {
                "engines": ["PetrolEngine", "DieselEngine", "HybridEngine"],
                "transmission": ["AutomaticTransmission"],
                "drive": ["RWD", "AWD"]
            },
            "Series7": {
                "engines": ["PetrolEngine", "HybridEngine"],
                "transmission": ["AutomaticTransmission"],
                "drive": ["AWD"]
            }
        }
        
        # Kontrolujeme, které komponenty příklad obsahuje
        model_objects = [obj for obj in example.objects if obj.class_name == model_type]
        if not model_objects:
            return satisfied
            
        for model_obj in model_objects:
            # Kontrola motorů
            for example_link in example.links:
                if example_link.source == model_obj.name:
                    target_obj = next((obj for obj in example.objects if obj.name == example_link.target), None)
                    if target_obj and target_obj.class_name in component_requirements.get(model_type, {}).get("engines", []):
                        engine_rule = f"Model {model_type} má validní motor typu {target_obj.class_name}"
                        if not any(v.startswith(f"Model {model_type} musí mít jeden z motorů") for v in violations):
                            satisfied.append(engine_rule)
                    
                    # Kontrola převodovky
                    if target_obj and target_obj.class_name in component_requirements.get(model_type, {}).get("transmission", []):
                        transmission_rule = f"Model {model_type} má validní převodovku typu {target_obj.class_name}"
                        if not any(v.startswith(f"Model {model_type} musí mít jednu z převodovek") for v in violations):
                            satisfied.append(transmission_rule)
                    
                    # Kontrola pohonu
                    if target_obj and target_obj.class_name in component_requirements.get(model_type, {}).get("drive", []):
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

def compare_example(model: Model, example_formula: str) -> Dict[str, Any]:
    """
    Validuje PL1 formuli proti naučenému modelu se zaměřením na konkrétní model auta.
    
    Args:
        model: Naučený model
        example_formula: PL1 formule příkladu k validaci
        
    Returns:
        Výsledek validace s konkrétním vysvětlením pro daný model auta
    """
    # Parsování PL1 formule
    formula = parse_pl1_formula(example_formula)
    
    # Konverze formule na model
    from backend.model import formula_to_model
    example_model = formula_to_model(formula)
    
    # Validace
    validator = ExampleValidator(model)
    result = validator.validate_example(example_model)
    
    # Přidáme formuli pro lepší kontext
    result["formula"] = example_formula
    
    return result 