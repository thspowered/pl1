from dataclasses import dataclass, field
from typing import List, Set, Dict, Tuple, Optional, Union, Any
from enum import Enum
from copy import deepcopy
from backend.pl1_parser import Predicate, Formula, PredicateType

class LinkType(Enum):
    """
    Enum reprezentujuci typy spojeni medzi objektmi v modeli.
    
    Hodnoty:
        MUST: Povinne spojenie - objekt musi mat tento komponent
        MUST_NOT: Zakazane spojenie - objekt nesmie mat tento komponent
        MUST_BE_A: Triedne spojenie - objekt musi byt instanciou tejto triedy
        REGULAR: Bezne spojenie bez specialneho vyznamu
    """
    MUST = "must"
    MUST_NOT = "must_not"
    MUST_BE_A = "must_be_a"
    REGULAR = "regular"

@dataclass
class Link:
    """
    Trieda reprezentujuca spojenie medzi dvoma objektmi v modeli.
    
    Atributy:
        source: Nazov zdrojoveho objektu spojenia
        target: Nazov cieloveho objektu spojenia
        link_type: Typ spojenia (predvolene REGULAR)
    """
    source: str
    target: str
    link_type: LinkType = LinkType.REGULAR

    def __eq__(self, other):
        if not isinstance(other, Link):
            return False
        return (self.source == other.source and 
                self.target == other.target and 
                self.link_type == other.link_type)

# Definujeme typy pre atributy
AttributeValue = Union[str, int, float, Tuple[float, float]]  # Hodnota atributu moze byt retazec, cislo alebo interval
Attributes = Dict[str, AttributeValue]  # Slovnik atributov pre objekt

@dataclass
class Object:
    """
    Trieda reprezentujuca objekt v modeli.
    
    Atributy:
        name: Jedinecny nazov objektu
        class_name: Nazov triedy, do ktorej objekt patri
        attributes: Volitelny slovnik atributov objektu
    """
    name: str
    class_name: str
    attributes: Optional[Attributes] = None

    def __eq__(self, other):
        if not isinstance(other, Object):
            return False
        return (self.name == other.name and 
                self.class_name == other.class_name and 
                self.attributes == other.attributes)

@dataclass
class Model:
    """
    Trieda reprezentujuca model zlozeny z objektov a spojeni.
    
    Tato trieda je jadrom reprezentacie modelov. Obsahuje zoznam
    objektov a spojeni medzi nimi, ktore vyjadruju vztahy a poziadavky.
    
    Atributy:
        objects: Zoznam objektov v modeli
        links: Zoznam spojeni medzi objektmi
        known_subclasses: Slovnik mapujuci generalizovane triedy na ich zname konkretne instancie
    """
    objects: List[Object] = field(default_factory=list)
    links: List[Link] = field(default_factory=list)
    known_subclasses: Dict[str, Set[str]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Konvertuje model na slovník vhodný pre serializáciu.
        
        Returns:
            Slovník reprezentujúci model
        """
        return {
            "objects": [
                {
                    "name": obj.name,
                    "class_name": obj.class_name,
                    "attributes": obj.attributes
                }
                for obj in self.objects
            ],
            "links": [
                {
                    "source": link.source,
                    "target": link.target,
                    "link_type": link.link_type.value
                }
                for link in self.links
            ],
            "known_subclasses": {
                general_class: list(specific_classes)
                for general_class, specific_classes in self.known_subclasses.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Model':
        """
        Vytvorí model zo slovníka.
        
        Args:
            data: Slovník obsahujúci serializovaný model
            
        Returns:
            Nový model
        """
        # Vytvorím objekty
        objects = []
        if "objects" in data:
            for obj_data in data["objects"]:
                obj = Object(
                    name=obj_data["name"],
                    class_name=obj_data["class_name"],
                    attributes=obj_data.get("attributes")
                )
                objects.append(obj)
        
        # Vytvorím spojenia
        links = []
        if "links" in data:
            for link_data in data["links"]:
                # Konverzia string hodnoty link_type na enum
                link_type_value = link_data["link_type"]
                link_type = LinkType.REGULAR  # default
                
                # Nájdi príslušnú enum hodnotu
                for lt in LinkType:
                    if lt.value == link_type_value:
                        link_type = lt
                        break
                
                link = Link(
                    source=link_data["source"],
                    target=link_data["target"],
                    link_type=link_type
                )
                links.append(link)
        
        # Načítam known_subclasses
        known_subclasses = {}
        if "known_subclasses" in data:
            for general_class, specific_classes in data["known_subclasses"].items():
                known_subclasses[general_class] = set(specific_classes)
        
        return cls(objects=objects, links=links, known_subclasses=known_subclasses)
    
    def copy(self) -> 'Model':
        """
        Vytvori hlboku kopiu modelu.
        
        Returns:
            Novy model s identickymi objektmi a spojeniami
        """
        new_model = Model(
            objects=deepcopy(self.objects),
            links=deepcopy(self.links)
        )
        # Kopírujeme aj known_subclasses
        for general_class, specific_classes in self.known_subclasses.items():
            new_model.known_subclasses[general_class] = set(specific_classes)
        return new_model
    
    def __eq__(self, other):
        """
        Porovná dva modely na základe ich objektov a spojení.
        
        Args:
            other: Iný model na porovnanie
            
        Returns:
            True ak sú modely ekvivalentné (majú rovnaké objekty a spojenia), inak False
        """
        if not isinstance(other, Model):
            return False
            
        # Porovnaj počet objektov a spojení
        if len(self.objects) != len(other.objects) or len(self.links) != len(other.links):
            return False
            
        # Porovnaj objekty (nezáleží na poradí)
        self_objects = sorted(self.objects, key=lambda obj: obj.name)
        other_objects = sorted(other.objects, key=lambda obj: obj.name)
        
        for self_obj, other_obj in zip(self_objects, other_objects):
            if self_obj != other_obj:
                return False
                
        # Porovnaj spojenia (nezáleží na poradí)
        self_links = sorted(self.links, key=lambda link: (link.source, link.target, link.link_type.value))
        other_links = sorted(other.links, key=lambda link: (link.source, link.target, link.link_type.value))
        
        for self_link, other_link in zip(self_links, other_links):
            if self_link != other_link:
                return False
        
        # Porovnaj known_subclasses
        if set(self.known_subclasses.keys()) != set(other.known_subclasses.keys()):
            return False
            
        for class_name in self.known_subclasses:
            if self.known_subclasses[class_name] != other.known_subclasses[class_name]:
                return False
                
        return True
    
    def has_link(self, link: Link) -> bool:
        """
        Zisti, ci model obsahuje specificke spojenie.
        
        Args:
            link: Spojenie, ktore hladame
            
        Returns:
            True, ak spojenie existuje v modeli, inak False
        """
        return any(l.source == link.source and 
                  l.target == link.target and 
                  l.link_type == link.link_type 
                  for l in self.links)
    
    def add_link(self, link: Link):
        """
        Prida nove spojenie do modelu, ak este neexistuje.
        
        Args:
            link: Spojenie, ktore sa ma pridat
        """
        if not self.has_link(link):
            self.links.append(link)
    
    def remove_link(self, link: Link):
        """
        Odstrani spojenie z modelu.
        
        Args:
            link: Spojenie, ktore sa ma odstranit
        """
        self.links = [l for l in self.links if not (
            l.source == link.source and 
            l.target == link.target and 
            l.link_type == link.link_type
        )]
    
    def update_object_class(self, object_name, new_class):
        """
        Aktualizuje triedu daného objektu.
        
        Args:
            object_name: Názov objektu
            new_class: Nová trieda
        """
        for obj in self.objects:
            if obj.name == object_name:
                obj.class_name = new_class
                # Aktualizuj aj spojenie MUST_BE_A, ak existuje
                for link in self.links:
                    if link.source == object_name and link.link_type == LinkType.MUST_BE_A:
                        link.target = new_class
                        break
                break
    
    def get_attribute_value(self, obj_name: str, attr: str) -> Optional[AttributeValue]:
        """
        Ziska hodnotu atributu objektu.
        
        Args:
            obj_name: Nazov objektu
            attr: Nazov atributu
            
        Returns:
            Hodnota atributu alebo None, ak objekt alebo atribut neexistuje
        """
        for obj in self.objects:
            if obj.name == obj_name and obj.attributes and attr in obj.attributes:
                return obj.attributes[attr]
        return None
    
    def set_attribute_interval(self, obj_name: str, attr: str, interval: Tuple[float, float]):
        """
        Nastavi intervalovu hodnotu atributu objektu.
        
        Pouziva sa najma na definovanie rozsahu povolenych hodnot pre numericke atributy.
        
        Args:
            obj_name: Nazov objektu
            attr: Nazov atributu
            interval: Dvojica (min, max) reprezentujuca interval povolenych hodnot
        """
        for obj in self.objects:
            if obj.name == obj_name:
                if not obj.attributes:
                    obj.attributes = {}
                obj.attributes[attr] = interval
                break

    def to_formula(self) -> str:
        """
        Konvertuje model na formulu v PL1.
        
        Vráti reťazec reprezentujúci model ako formulu v predikátovej logike prvého rádu.
        Podporuje generovanie disjunkcií z množín alternatívnych komponentov a správne
        zobrazuje všetky typy atribútov.
        """
        predicates = []
        
        # Predikáty pre objekty a ich triedy
        for obj in self.objects:
            class_name = obj.class_name
            # Ak trieda má známe podtriedy, pridáme informáciu ako komentár
            if class_name in self.known_subclasses and self.known_subclasses[class_name]:
                subclasses = self.known_subclasses[class_name]
                # Vypisujeme podtriedy v zátvorke za triedou
                predicates.append(f"Ι({obj.name}, {class_name})")
            else:
                predicates.append(f"Ι({obj.name}, {class_name})")
        
        # Predikáty pre spojenia a zoskupenie MUST linkov podľa zdrojov
        must_links_by_source = {}
        
        for link in self.links:
            if link.link_type == LinkType.REGULAR:
                predicates.append(f"Π({link.source}, {link.target})")
            elif link.link_type == LinkType.MUST:
                if link.source not in must_links_by_source:
                    must_links_by_source[link.source] = []
                must_links_by_source[link.source].append(link.target)
            elif link.link_type == LinkType.MUST_NOT:
                predicates.append(f"Ν({link.source}, {link.target})")
        
        # Predikáty pre atribúty - upravená časť pre správne zobrazenie všetkých typov atribútov
        for obj in self.objects:
            if not obj.attributes:
                continue
            
            # Identifikácia allowed_X_types atribútov pre disjunkcie
            disjunction_attrs = {}
            regular_attrs = {}
            
            # Rozdelenie atribútov na disjunkcie a bežné atribúty
            for attr_name, attr_value in obj.attributes.items():
                if attr_name.startswith("allowed_") and "_types" in attr_name and isinstance(attr_value, set) and len(attr_value) > 1:
                    disjunction_attrs[attr_name] = attr_value
                else:
                    regular_attrs[attr_name] = attr_value
            
            # Spracovanie bežných atribútov
            for attr_name, attr_value in regular_attrs.items():
                # Interval (tuple) - vždy zobraziť ako interval
                if isinstance(attr_value, tuple) and len(attr_value) == 2:
                    min_val, max_val = attr_value
                    predicates.append(f"Α({obj.name}, {attr_name}, ({min_val}, {max_val}))")
                
                # Množina - zobraziť ako množinu
                elif isinstance(attr_value, set):
                    # Zjednotená množina nečíselných hodnôt
                    if all(not isinstance(v, (int, float)) for v in attr_value):
                        # Konvertujeme množinu na string s formátom {val1, val2, ...}
                        set_str = "{"
                        set_str += ", ".join(str(v) for v in attr_value)
                        set_str += "}"
                        predicates.append(f"Α({obj.name}, {attr_name}, {set_str})")
                    # Množina číselných hodnôt - zobraziť ako interval
                    elif all(isinstance(v, (int, float)) for v in attr_value):
                        if attr_value:  # Ak množina nie je prázdna
                            min_val = min(attr_value)
                            max_val = max(attr_value)
                            predicates.append(f"Α({obj.name}, {attr_name}, ({min_val}, {max_val}))")
                    # Zmiešaná množina - rozdeliť na číselné a nečíselné hodnoty
                    else:
                        numeric_vals = [v for v in attr_value if isinstance(v, (int, float))]
                        non_numeric_vals = [v for v in attr_value if not isinstance(v, (int, float))]
                        
                        if numeric_vals:
                            min_val = min(numeric_vals)
                            max_val = max(numeric_vals)
                            predicates.append(f"Α({obj.name}, {attr_name}_numeric, ({min_val}, {max_val}))")
                        
                        if non_numeric_vals:
                            set_str = "{"
                            set_str += ", ".join(str(v) for v in non_numeric_vals)
                            set_str += "}"
                            predicates.append(f"Α({obj.name}, {attr_name}_non_numeric, {set_str})")
                
                # Jednoduchá hodnota - zobraziť priamo
                else:
                    # Ak je hodnota číslo (int alebo float), zobrazíme ju ako interval (hodnota, hodnota)
                    if isinstance(attr_value, (int, float)):
                        predicates.append(f"Α({obj.name}, {attr_name}, ({attr_value}, {attr_value}))")
                    else:
                        predicates.append(f"Α({obj.name}, {attr_name}, {attr_value})")
        
        # Spracovanie disjunkcií z allowed_X_types atribútov
        for obj in self.objects:
            if not obj.attributes:
                continue
            
            for attr_name, attr_value in obj.attributes.items():
                if attr_name.startswith("allowed_") and "_types" in attr_name and isinstance(attr_value, set) and len(attr_value) > 1:
                    component_types = sorted(attr_value)
                    disjuncts = " ∨ ".join([f"Μ({obj.name}, {comp})" for comp in component_types])
                    predicates.append(f"({disjuncts})")
        
        # Spracovanie disjunkcií z MUST linkov pre rovnaké kategórie komponentov
        type_categories = {
            "Engine": ["Engine", "DieselEngine", "PetrolEngine", "HybridEngine"],
            "Transmission": ["Transmission", "AutomaticTransmission", "ManualTransmission"],
            "DriveSystem": ["DriveSystem", "XDrive", "AWD", "RWD"],
            "SUV": ["SUV", "CompactSUV", "MidSizeSUV", "FullSizeSUV"]
        }
        
        # Mapovanie komponentov na kategórie
        component_to_category = {}
        for category, components in type_categories.items():
            for comp in components:
                component_to_category[comp] = category
        
        # Pre každý zdroj spracujeme MUST linky podľa kategórií
        for source, targets in must_links_by_source.items():
            if not targets:
                continue
                
            by_category = {}
            for target in targets:
                category = component_to_category.get(target)
                if category:
                    if category not in by_category:
                        by_category[category] = []
                    by_category[category].append(target)
                else:
                    # Komponenty bez kategórie pridáme priamo
                    # Pridáme poznámku, ak target je v known_subclasses
                    if target in self.known_subclasses and self.known_subclasses[target]:
                        subclasses = ", ".join(sorted(self.known_subclasses[target]))
                        predicates.append(f"Μ({source}, {target})")
                    else:
                        predicates.append(f"Μ({source}, {target})")
            
            # Vytvorenie disjunkcií pre komponenty rovnakej kategórie
            for category, components in by_category.items():
                if len(components) > 1:
                    # Skontrolujeme, či niektorá z týchto komponentov má známe podtriedy
                    components_with_subclasses = []
                    for comp in components:
                        if comp in self.known_subclasses and self.known_subclasses[comp]:
                            components_with_subclasses.append(comp)
                    
                    # Vytvoríme disjunkciu
                    disjuncts = " ∨ ".join([f"Μ({source}, {comp})" for comp in sorted(components)])
                    predicates.append(f"({disjuncts})")
                else:
                    # Pridáme poznámku, ak komponent má známe podtriedy
                    comp = components[0]
                    if comp in self.known_subclasses and self.known_subclasses[comp]:
                        subclasses = ", ".join(sorted(self.known_subclasses[comp]))
                        predicates.append(f"Μ({source}, {comp})")
                    else:
                        predicates.append(f"Μ({source}, {comp})")
        
        # Spojenie všetkých predikátov konjunkciou
        return " ∧ ".join(predicates)

    def extract_model_rules(self) -> Dict[str, str]:
        """
        Extrahuje identifikačné pravidlá pre jednotlivé modely áut.
        
        Vráti slovník, kde kľúče sú názvy modelov a hodnoty sú
        textové reprezentácie pravidiel v logike prvého rádu.
        
        Táto metóda extrahuje pravidlá len pre modely, ktoré sú naozaj prítomné v modeli.
        """
        rules = {}
        
        # Najprv získame všetky možné špecifické modely áut (bez základnej triedy BMW)
        specific_car_models = {"Series3", "Series5", "Series7", "X5", "X7"}
        
        # Nájdeme skutočné modely áut, ktoré sú prítomné v modeli
        # a) buď priamo ako objekty
        car_models_in_objects = {obj.class_name for obj in self.objects if obj.class_name in specific_car_models}
        
        # b) alebo ako triedy v spojeniach
        car_models_in_links = set()
        for link in self.links:
            if link.source in specific_car_models:
                car_models_in_links.add(link.source)
            if link.target in specific_car_models:
                car_models_in_links.add(link.target)
        
        # Spojenie oboch množín
        car_models_present = car_models_in_objects.union(car_models_in_links)
        
        if not car_models_present:
            print("Nenašli sa žiadne špecifické modely áut v aktuálnom modeli.")
            return rules  # Prázdny slovník
            
        print(f"Špecifické modely áut prítomné v modeli: {car_models_present}")
        
        # Vygeneruj formulu z modelu
        formula_text = self.to_formula()
        
        # Vytvor slovník všetkých objektov a ich atribútov pre rýchlejší prístup
        all_objects_dict = {obj.name: obj for obj in self.objects}
        
        # Vytvor slovník komponentov podľa tried
        components_by_class = {}
        for obj in self.objects:
            if obj.class_name not in components_by_class:
                components_by_class[obj.class_name] = []
            components_by_class[obj.class_name].append(obj)
        
        # Pre každý model nájdi všetky objekty, ktoré sú s ním spojené
        model_to_components = {}
        for model_name in car_models_present:
            model_to_components[model_name] = {}
            model_objects = [obj for obj in self.objects if obj.class_name == model_name]
            
            # Pre každý objekt daného modelu nájdi spojené komponenty
            for model_obj in model_objects:
                for link in self.links:
                    if link.source == model_obj.name:
                        target_obj = all_objects_dict.get(link.target)
                        if target_obj:
                            component_class = target_obj.class_name
                            if component_class not in model_to_components[model_name]:
                                model_to_components[model_name][component_class] = []
                            model_to_components[model_name][component_class].append(target_obj)
            
            # Pridaj aj generické spojenia na úrovni tried
            for link in self.links:
                if link.source == model_name and link.link_type == LinkType.MUST:
                    # Ak máme MUST spojenie z modelu na triedu komponentu
                    component_class = link.target
                    if component_class not in model_to_components[model_name]:
                        model_to_components[model_name][component_class] = []
                        # Ak existujú objekty danej triedy, pridaj ich
                        if component_class in components_by_class:
                            model_to_components[model_name][component_class].extend(components_by_class[component_class])
        
        # Spracuj MUST (Μ) a MUST_NOT (Ν) vzťahy a atribúty (Α) pre jednotlivé modely
        import re
        
        # Pre každý nájdený model vytvoríme pravidlo
        for model_name in car_models_present:
            # Hľadáme všetky MUST (Μ) spojenia pre tento model
            must_pattern = re.compile(r'Μ\s*\(\s*' + re.escape(model_name) + r'\s*,\s*(\w+)\s*\)')
            must_relations = must_pattern.findall(formula_text)
            
            # Hľadáme všetky MUST_NOT (Ν) spojenia pre tento model
            must_not_pattern = re.compile(r'Ν\s*\(\s*' + re.escape(model_name) + r'\s*,\s*(\w+)\s*\)')
            must_not_relations = must_not_pattern.findall(formula_text)
            
            # Hľadáme atribúty pre tento model
            attr_pattern = re.compile(r'Α\s*\(\s*' + re.escape(model_name) + r'\s*,\s*(\w+)\s*,\s*(.+?)\s*\)')
            model_attributes = attr_pattern.findall(formula_text)
            
            # Vytvor množinu podmienok pre pravidlo - použijeme množinu pre elimináciu duplicít
            conditions = set()
            
            # Základné komponenty sú vždy v pravidlách
            basic_components = ["DriveSystem", "Engine", "Transmission"]
            
            # Analyzujeme MUST vzťahy - tie sú najdôležitejšie pre identifikačné pravidlá
            must_components = set(must_relations)
            
            # Pre X5 a X7 modely musíme mať XDrive
            if model_name.startswith("X"):
                if "XDrive" in must_components:
                    conditions.add(f"HAS(x, XDrive)")
                else:
                    conditions.add(f"HAS(x, XDrive)")
            
            # Pre Series modely určíme potrebný DriveSystem
            elif model_name.startswith("Series"):
                if "AWD" in must_components:
                    conditions.add(f"HAS(x, AWD)")
                elif "RWD" in must_components:
                    conditions.add(f"HAS(x, RWD)")
                elif model_name == "Series7":
                    conditions.add(f"HAS(x, AWD)")
                else:
                    conditions.add(f"HAS(x, RWD)")
            
            # Pridáme špecifické engine typy, ak sú v MUST vzťahoch
            engine_types = ["PetrolEngine", "DieselEngine", "HybridEngine"]
            model_engines = []
            
            for engine in engine_types:
                if engine in must_components:
                    model_engines.append(engine)
            
            # Ak máme konkrétne motory, pridáme ich
            if model_engines:
                if len(model_engines) == 1:
                    conditions.add(f"HAS(x, {model_engines[0]})")
                else:
                    engine_condition = " ∨ ".join([f"HAS(x, {engine})" for engine in model_engines])
                    conditions.add(f"({engine_condition})")
            else:
                # Ak nemáme špecifické motory, pridáme všeobecný Engine
                conditions.add(f"HAS(x, Engine)")
            
            # Pridáme špecifické prevodovky ak sú v MUST vzťahoch
            transmission_types = ["AutomaticTransmission", "ManualTransmission"]
            model_transmissions = []
            
            for transmission in transmission_types:
                if transmission in must_components:
                    model_transmissions.append(transmission)
            
            # Ak máme konkrétne prevodovky, pridáme ich
            if model_transmissions:
                if len(model_transmissions) == 1:
                    conditions.add(f"HAS(x, {model_transmissions[0]})")
                else:
                    transmission_condition = " ∨ ".join([f"HAS(x, {trans})" for trans in model_transmissions])
                    conditions.add(f"({transmission_condition})")
            else:
                # Ak nemáme špecifické prevodovky, pridáme všeobecný Transmission
                conditions.add(f"HAS(x, Transmission)")
            
            # Pridáme MUST_NOT podmienky
            for component in must_not_relations:
                conditions.add(f"¬HAS(x, {component})")
            
            # Pridáme atribúty modelu
            for attr_name, attr_value in model_attributes:
                # Spracovanie rôznych typov hodnôt
                if '(' in attr_value and ')' in attr_value and "," in attr_value:
                    # Interval hodnota
                    try:
                        # Extrahujeme hodnoty z intervalu
                        interval_match = re.search(r'\(\s*([\d\.]+)\s*,\s*([\d\.]+)\s*\)', attr_value)
                        if interval_match:
                            min_val = interval_match.group(1)
                            max_val = interval_match.group(2)
                            conditions.add(f"ATTR(x, {attr_name}) ∈ [{min_val}, {max_val}]")
                    except Exception as e:
                        print(f"Chyba pri spracovaní intervalu: {e}")
                elif '{' in attr_value and '}' in attr_value:
                    # Množina hodnôt
                    try:
                        # Extrahujeme hodnoty z množiny
                        set_match = re.search(r'\{\s*(.+?)\s*\}', attr_value)
                        if set_match:
                            set_values = set_match.group(1)
                            conditions.add(f"ATTR(x, {attr_name}) ∈ {{{set_values}}}")
                    except Exception as e:
                        print(f"Chyba pri spracovaní množiny: {e}")
                else:
                    # Jednoduchá hodnota
                    conditions.add(f"ATTR(x, {attr_name}) = {attr_value}")
            
            # Pridaj atribúty pre všetky komponenty spojené s týmto modelom
            components_data = model_to_components.get(model_name, {})
            for component_class, component_objects in components_data.items():
                # Zbieraj atribúty pre všetky komponenty danej triedy
                component_attributes = {}
                
                for component_obj in component_objects:
                    if component_obj.attributes:
                        for attr_name, attr_value in component_obj.attributes.items():
                            if attr_name not in component_attributes:
                                component_attributes[attr_name] = []
                            component_attributes[attr_name].append(attr_value)
                
                # Pre každý atribút vytvor pravidlo
                for attr_name, values in component_attributes.items():
                    if not values:
                        continue
                        
                    # Ak sú hodnoty intervaly, spoj ich
                    if all(isinstance(v, tuple) and len(v) == 2 for v in values):
                        min_vals = [v[0] for v in values]
                        max_vals = [v[1] for v in values]
                        min_val = min(min_vals)
                        max_val = max(max_vals)
                        conditions.add(f"∀y: [HAS(x, y) ∧ IS(y, {component_class}) → ATTR(y, {attr_name}) ∈ [{min_val}, {max_val}]]")
                    
                    # Ak sú hodnoty množiny, zlúč ich
                    elif all(isinstance(v, set) for v in values):
                        combined_set = set()
                        for value_set in values:
                            combined_set.update(value_set)
                        set_str = "{" + ", ".join([f'"{v}"' if isinstance(v, str) else str(v) for v in combined_set]) + "}"
                        conditions.add(f"∀y: [HAS(x, y) ∧ IS(y, {component_class}) → ATTR(y, {attr_name}) ∈ {set_str}]")
                    
                    # Ak sú hodnoty jednoduché a rovnaké
                    elif len(set(values)) == 1:
                        val = values[0]
                        val_str = f'"{val}"' if isinstance(val, str) else str(val)
                        conditions.add(f"∀y: [HAS(x, y) ∧ IS(y, {component_class}) → ATTR(y, {attr_name}) = {val_str}]")
                    
                    # Inak vytvor zoznam možných hodnôt
                    else:
                        # Odstráň duplicity
                        unique_values = list(set(values))
                        if len(unique_values) > 1:
                            values_str = " ∨ ".join([f"ATTR(y, {attr_name}) = {v}" for v in unique_values])
                            conditions.add(f"∀y: [HAS(x, y) ∧ IS(y, {component_class}) → ({values_str})]")
            
            # Spoj podmienky konjunkciou a vytvor pravidlo
            if conditions:
                rule_condition = " ∧ ".join(sorted(conditions))  # Zoraďujeme podmienky pre konzistentnosť
                rules[model_name] = f"∀x: [\n  {rule_condition} → IS(x, {model_name})\n]"
            else:
                # Ak nie sú žiadne podmienky, vytvor základné pravidlo
                basic_condition = " ∧ ".join([f"HAS(x, {comp})" for comp in basic_components])
                rules[model_name] = f"∀x: [\n  {basic_condition} → IS(x, {model_name})\n]"
        
        print(f"Extrahované pravidlá pre modely: {list(rules.keys())}")
        
        return rules
        
    def get_rules_for_model_type(self, model_type):
        """
        Získá strukturovaná pravidla pro konkrétní typ modelu.
        
        Args:
            model_type: Typ modelu (např. 'Series7', 'X5')
            
        Returns:
            Slovník s pravidly rozdělenými na 'must' a 'must_not'
        """
        rules = {
            "must": [],
            "must_not": []
        }
        
        # Najít všechna MUST pravidla
        for link in self.links:
            if link.source == model_type:
                if link.link_type == LinkType.MUST:
                    rules["must"].append(link.target)
                elif link.link_type == LinkType.MUST_NOT:
                    rules["must_not"].append(link.target)
        
        return rules

    def to_semantic_network(self) -> Dict[str, Any]:
        """
        Konvertuje model na sémantickú sieť vhodnú pre vizualizáciu.
        
        Vráti slovník s dvomi kľúčmi:
        - nodes: zoznam uzlov (objektov) v sieti
        - links: zoznam spojení medzi uzlami
        
        Každý uzol má atribúty:
        - id: jedinečný identifikátor uzla
        - name: názov objektu
        - class: trieda objektu
        - category: kategória uzla (BMW, Engine, Transmission, Drive, Other)
        - attributes: slovník atribútov objektu
        - value_display: textová reprezentácia hodnoty pre atribútové uzly
        """
        nodes = []
        links = []
        
        # Kategórie pre uzly
        bmw_categories = ["BMW", "Series3", "Series5", "Series7", "X5", "X7"]
        engine_categories = ["Engine", "DieselEngine", "PetrolEngine", "HybridEngine"]
        transmission_categories = ["Transmission", "AutomaticTransmission", "ManualTransmission"]
        drive_categories = ["DriveSystem", "RWD", "AWD", "XDrive"]
        
        # Pomocná funkcia na určenie kategórie uzla
        def get_node_category(obj_name: str, obj_class: str) -> str:
            if any(category in obj_class for category in bmw_categories):
                return "BMW"
            elif any(category in obj_class for category in engine_categories) or "engine" in obj_name.lower():
                return "Engine"
            elif any(category in obj_class for category in transmission_categories) or "transmission" in obj_name.lower():
                return "Transmission"
            elif any(category in obj_class for category in drive_categories) or "drive" in obj_name.lower():
                return "Drive"
            else:
                return "Other"
        
        # Sledujeme už pridané atribúty, aby sme zabránili duplikátom
        added_attributes = set()
        
        # Vytvor uzly pre objekty
        for obj in self.objects:
            category = get_node_category(obj.name, obj.class_name)
            
            node = {
                "id": obj.name,
                "name": obj.name,
                "class": obj.class_name,
                "category": category,
                "attributes": obj.attributes or {}
            }
            
            nodes.append(node)
            
            # Pridaj atribúty objektu ako samostatné uzly a vytvor spojenia na ne
            if obj.attributes:
                for attr_name, attr_value in obj.attributes.items():
                    # Vytvoríme unikátne ID pre atribút
                    attr_node_id = f"{obj.name}_{attr_name}"
                    
                    if attr_node_id not in added_attributes:
                        # Pripravíme zobrazenie hodnoty
                        value_display = ""
                        if isinstance(attr_value, set):
                            # Pre množinu hodnôt vytvoríme formátovaný reťazec
                            value_display = "{" + ", ".join(str(v) for v in attr_value) + "}"
                        elif isinstance(attr_value, tuple) and len(attr_value) == 2:
                            # Pre interval vytvoríme formátovaný reťazec
                            value_display = f"({attr_value[0]}, {attr_value[1]})"
                        else:
                            # Pre jednoduchú hodnotu použijeme priamo jej reťazcovú reprezentáciu
                            value_display = str(attr_value)
                        
                        # Pridáme uzol pre atribút
                        attr_node = {
                            "id": attr_node_id,
                            "name": attr_name,
                            "class": "Attribute",
                            "category": "Attribute",
                            "value": attr_value,
                            "value_display": value_display
                        }
                        nodes.append(attr_node)
                        added_attributes.add(attr_node_id)
                        
                        # Vytvoríme spojenie medzi objektom a atribútom
                        attr_link = {
                            "source": obj.name,
                            "target": attr_node_id,
                            "type": "HAS_ATTRIBUTE"
                        }
                        links.append(attr_link)
                        
                        # Ak hodnota atribútu je množina, pridáme každú hodnotu ako samostatný uzol
                        if isinstance(attr_value, set):
                            for idx, val in enumerate(attr_value):
                                value_node_id = f"{attr_node_id}_value_{idx}"
                                
                                # Pridáme uzol pre hodnotu
                                value_node = {
                                    "id": value_node_id,
                                    "name": str(val),
                                    "class": "Value",
                                    "category": "Value"
                                }
                                nodes.append(value_node)
                                
                                # Spojenie od atribútu k hodnote
                                value_link = {
                                    "source": attr_node_id,
                                    "target": value_node_id,
                                    "type": "VALUE"
                                }
                                links.append(value_link)
        
        # Vytvor spojenia medzi objektami
        for link in self.links:
            link_data = {
                "source": link.source,
                "target": link.target,
                "type": link.link_type.value
            }
            
            links.append(link_data)
            
        # Pridaj explicitné uzly pre triedy, ktoré sú v spojeniach, ale nie sú v zozname objektov
        class_nodes = set()
        for node in nodes:
            if node["class"] != "Attribute" and node["class"] != "Value":
                class_nodes.add(node["class"])
        
        # Kontrola tried v spojeniach
        for link in links:
            for endpoint in [link["source"], link["target"]]:
                # Ak endpoint vyzerá ako názov triedy (začína veľkým písmenom) a ešte nie je uzol
                if (endpoint[0].isupper() and 
                    not any(node["id"] == endpoint for node in nodes) and 
                    endpoint not in class_nodes):
                    
                    # Určíme kategóriu uzla
                    category = "Other"
                    if any(category in endpoint for category in bmw_categories):
                        category = "BMW"
                    elif any(category in endpoint for category in engine_categories):
                        category = "Engine"
                    elif any(category in endpoint for category in transmission_categories):
                        category = "Transmission"
                    elif any(category in endpoint for category in drive_categories):
                        category = "Drive"
                    
                    # Pridáme uzol pre triedu
                    class_node = {
                        "id": endpoint,
                        "name": endpoint,
                        "class": endpoint,
                        "category": category
                    }
                    nodes.append(class_node)
                    class_nodes.add(endpoint)
        
        return {
            "nodes": nodes,
            "links": links
        }

    def has_generic_class_link(self, source_class, target_class, link_type):
        """
        Zistí, či model obsahuje spojenie medzi danými triedami (bez ohľadu na konkrétne objekty).
        Toto je užitočné pre generické spojenia, ktoré vyjadrujú požiadavky na úrovni tried.
        
        Args:
            source_class: Zdrojová trieda (napr. "BMW")
            target_class: Cieľová trieda (napr. "Engine")
            link_type: Typ spojenia (napr. LinkType.MUST)
            
        Returns:
            True ak model obsahuje spojenie medzi triedami, inak False
        """
        # Najprv skontroluj spojenia medzi triedami priamo
        for link in self.links:
            if link.source == source_class and link.target == target_class and link.link_type == link_type:
                return True
        
        # Skontroluj, či niekto z objektov nemá spojenie na iný objekt,
        # kde zdrojový objekt je triedy source_class a cieľový objekt je triedy target_class
        sources_of_class = [obj.name for obj in self.objects if obj.class_name == source_class]
        targets_of_class = [obj.name for obj in self.objects if obj.class_name == target_class]
        
        for link in self.links:
            if (link.source in sources_of_class and link.target in targets_of_class and 
                link.link_type == link_type):
                return True
            
        return False
    
    def add_generic_class_link(self, source_class, target_class, link_type):
        """
        Pridá generické spojenie medzi triedami.
        
        Args:
            source_class: Zdrojová trieda (napr. "BMW")
            target_class: Cieľová trieda (napr. "Engine")
            link_type: Typ spojenia (napr. LinkType.MUST)
        """
        # Pridáme priame spojenie medzi triedami
        new_link = Link(source_class, target_class, link_type)
        self.add_link(new_link)
        
    def remove_duplicate_links(self):
        """
        Odstráni duplicitné spojenia z modelu.
        
        Táto metóda prechádza všetky linky a ponechá iba jedinečné spojenia,
        odstrániac akékoľvek duplicity.
        
        Returns:
            Počet odstránených duplicít
        """
        # Vytvoríme množinu pre sledovanie jedinečných spojení
        unique_links = set()
        links_to_keep = []
        removed_count = 0
        
        for link in self.links:
            # Vytvoríme kľúč pre spojenie
            link_key = (link.source, link.target, link.link_type)
            
            # Ak toto spojenie ešte nemáme v množine, pridáme ho
            if link_key not in unique_links:
                unique_links.add(link_key)
                links_to_keep.append(link)
            else:
                # Ak už existuje, toto je duplicita
                removed_count += 1
                
        # Aktualizujeme zoznam spojení len na jedinečné spojenia
        self.links = links_to_keep
        
        return removed_count

def formula_to_model(formula: Formula) -> Model:
    """
    Konvertuje formulu na model.
    
    Args:
        formula: Formula v predikátovej logike prvého rádu
        
    Returns:
        Model vytvoreny z formuly
    """
    print("\n==================== DEBUG: Starting formula_to_model ====================")
    print(f"Spracovávam formulu: {formula}")
    
    objects = []
    links = []
    attributes = {}
    
    # Pomocná funkcia na spracovanie hodnoty atribútu
    def process_attribute_value(value_str):
        print(f"DEBUG: Processing attribute value: {value_str}")
        # Ak obsahuje disjunkciu (∨), vytvoríme množinu hodnôt
        if "∨" in value_str:
            # Rozdelíme podľa symbolu disjunkcie a spracujeme každú hodnotu
            values = [val.strip() for val in value_str.split("∨")]
            result_set = set()
            
            for val in values:
                # Skúsime konvertovať na číslo
                try:
                    if "." in val:
                        result_set.add(float(val))
                    else:
                        result_set.add(int(val))
                except ValueError:
                    # Ak nie je číslo, pridáme ako reťazec
                    result_set.add(val)
            
            print(f"DEBUG: Created set attribute value: {result_set}")
            return result_set
        
        # Ak je v zátvorke a obsahuje čiarku, môže to byť interval
        elif "(" in value_str and ")" in value_str and "," in value_str:
            try:
                # Extrahujeme hodnoty z intervalu
                value_str = value_str.strip("()")
                min_val, max_val = [x.strip() for x in value_str.split(",")]
                
                # Konvertujeme na čísla
                if "." in min_val or "." in max_val:
                    result = (float(min_val), float(max_val))
                else:
                    result = (int(min_val), int(max_val))
                
                print(f"DEBUG: Created range attribute value: {result}")
                return result
            except ValueError:
                # Ak konverzia zlyhá, vrátime pôvodnú hodnotu
                print(f"DEBUG: Failed to convert range value, returning original: {value_str}")
                return value_str
        
        # Inak skúsime konvertovať na číslo
        else:
            try:
                # Skúsime konvertovať na číslo
                if "." in value_str:
                    result = float(value_str)
                else:
                    result = int(value_str)
                
                print(f"DEBUG: Converted attribute value to numeric: {result}")
                return result
            except ValueError:
                # Ak konverzia zlyhá, vrátime pôvodnú hodnotu
                print(f"DEBUG: Failed to convert to numeric, returning original: {value_str}")
                return value_str
    
    # Mapovanie predikatov na objekty a spojenia
    print(f"\nDEBUG: Processing {len(formula.predicates)} predicates")
    for predicate in formula.predicates:
        print(f"\nDEBUG: Processing predicate {predicate.name} with args {predicate.arguments}")
        if predicate.type == PredicateType.UNARY:
            # Unarny predikat reprezentuje triedu objektu
            obj_name = predicate.arguments[0]
            class_name = predicate.name
            
            print(f"DEBUG: Unary predicate -> object {obj_name} of class {class_name}")
            
            # Pridaj objekt, ak este neexistuje
            if obj_name not in [obj.name for obj in objects]:
                objects.append(Object(obj_name, class_name))
                print(f"DEBUG: Added object {obj_name} of class {class_name}")
            
            # Pridaj spojenie MUST_BE_A
            links.append(Link(obj_name, class_name, LinkType.MUST_BE_A))
            print(f"DEBUG: Added MUST_BE_A link {obj_name} -> {class_name}")
        
        elif predicate.type == PredicateType.BINARY:
            # Binarny predikat moze reprezentovat spojenie alebo atribut
            arg1 = predicate.arguments[0]
            arg2 = predicate.arguments[1]
            
            if predicate.name == "Π":  # PI - has_part
                # Spojenie HAS (REGULAR)
                links.append(Link(arg1, arg2, LinkType.REGULAR))
                print(f"DEBUG: Added REGULAR link {arg1} -> {arg2}")
            elif predicate.name == "Ι":  # IOTA - is_a
                # Spojenie IS_A (objekt je instanciou triedy)
                # Check if object already exists
                existing_obj = next((obj for obj in objects if obj.name == arg1), None)
                if existing_obj:
                    # Update class name if needed
                    if existing_obj.class_name != arg2:
                        existing_obj.class_name = arg2
                        print(f"DEBUG: Updated object {arg1} class to {arg2}")
                else:
                    # Create new object
                    objects.append(Object(arg1, arg2))
                    print(f"DEBUG: Added object {arg1} of class {arg2}")
                
                # Add MUST_BE_A link
                links.append(Link(arg1, arg2, LinkType.MUST_BE_A))
                print(f"DEBUG: Added MUST_BE_A link {arg1} -> {arg2}")
            elif predicate.name == "Μ":  # MU - must_have_part
                # Spojenie MUST
                links.append(Link(arg1, arg2, LinkType.MUST))
                print(f"DEBUG: Added MUST link {arg1} -> {arg2}")
            elif predicate.name == "Ν":  # NU - must_not_have_part
                # Spojenie MUST_NOT
                links.append(Link(arg1, arg2, LinkType.MUST_NOT))
                print(f"DEBUG: Added MUST_NOT link {arg1} -> {arg2}")
            else:
                # Atribut
                if arg1 not in attributes:
                    attributes[arg1] = {}
                
                # Pouzijeme cely nazov predikatu ako nazov atributu
                attr_name = predicate.name.lower()
                attr_value = process_attribute_value(arg2)
                attributes[arg1][attr_name] = attr_value
                print(f"DEBUG: Added attribute {attr_name}={attr_value} to object {arg1}")
        
        elif predicate.type == PredicateType.TERNARY:
            # Ternarny predikat reprezentuje atribut s nazvom
            obj_name = predicate.arguments[0]
            attr_name = predicate.arguments[1]
            attr_value_str = predicate.arguments[2]
            
            print(f"DEBUG: Ternary predicate -> attribute for {obj_name}.{attr_name} = {attr_value_str}")
            
            if obj_name not in attributes:
                attributes[obj_name] = {}
                print(f"DEBUG: Created attributes dictionary for object {obj_name}")
            
            # Spracuj hodnotu atribútu
            attr_value = process_attribute_value(attr_value_str)
            attributes[obj_name][attr_name] = attr_value
            print(f"DEBUG: Added attribute {attr_name}={attr_value} to object {obj_name}")
    
    # Pridaj atributy k objektom
    print("\nDEBUG: Attaching attributes to objects")
    for obj in objects:
        print(f"DEBUG: Processing object {obj.name} of class {obj.class_name}")
        if obj.name in attributes:
            obj.attributes = attributes[obj.name]
            print(f"DEBUG: Attached attributes {obj.attributes} to object {obj.name}")
        else:
            print(f"DEBUG: No attributes found for object {obj.name}")
    
    # Create Model
    result_model = Model(objects=objects, links=links)
    print(f"\nDEBUG: Created model with {len(objects)} objects and {len(links)} links")
    
    # Debug výpis všetkých objektov
    print("\nDEBUG: All objects in model:")
    for obj in result_model.objects:
        print(f"  Object: {obj.name}, Class: {obj.class_name}, Attributes: {obj.attributes}")
    
    print("\nDEBUG: All links in model:")
    for link in result_model.links:
        print(f"  Link: {link.source} -> {link.target} ({link.link_type})")
    
    print("====================== DEBUG: End formula_to_model ======================\n")
    return result_model

class ClassificationTree:
    """Strom klasifikácie tried pre hierarchiu pojmov."""
    
    def __init__(self):
        """Inicializácia prázdneho klasifikačného stromu."""
        self.parent_map = {}
        self.children_map = {}
    
    def add_relationship(self, child: str, parent: str):
        """
        Pridá vzťah dieťa-rodič do stromu.
        
        Args:
            child: Trieda dieťaťa
            parent: Trieda rodiča (None pre top-level triedy)
        """
        # Pridá vzťah dieťa -> rodič
        self.parent_map[child] = parent
        
        # Pridá vzťah rodič -> deti
        if parent:
            if parent not in self.children_map:
                self.children_map[parent] = []
            if child not in self.children_map[parent]:
                self.children_map[parent].append(child)
        
        # Zabezpečí, že rodič je v parent_map aj keď nemá vlastného rodiča
        if parent and parent not in self.parent_map:
            self.parent_map[parent] = None
    
    def get_parent(self, class_name: str) -> str:
        """
        Vráti rodiča danej triedy.
        
        Args:
            class_name: Názov triedy
            
        Returns:
            Názov rodičovskej triedy alebo None
        """
        return self.parent_map.get(class_name)
    
    def get_children(self, class_name: str) -> List[str]:
        """
        Vráti zoznam detí danej triedy.
        
        Args:
            class_name: Názov triedy
            
        Returns:
            Zoznam názvov tried detí
        """
        return self.children_map.get(class_name, [])
    
    def is_subclass(self, child: str, parent: str) -> bool:
        """
        Kontroluje, či `child` je podtriedou `parent`.
        
        Args:
            child: Názov triedy dieťaťa
            parent: Názov triedy rodiča
            
        Returns:
            True ak je `child` podtriedou `parent` (priamou alebo nepriamou)
        """
        # Priama kontrola
        if child == parent:
            return True
            
        # Ak child nie je v strome, nemôže byť podtriedou
        if child not in self.parent_map:
            return False
            
        # Rekurzívne prehľadávanie cez rodičov
        current_parent = self.parent_map.get(child)
        while current_parent:
            if current_parent == parent:
                return True
            current_parent = self.parent_map.get(current_parent)
            
        return False
    
    def find_common_ancestor(self, class1: str, class2: str) -> Optional[str]:
        """
        Nájde najbližšieho spoločného predka dvoch tried.
        
        Args:
            class1: Názov prvej triedy
            class2: Názov druhej triedy
            
        Returns:
            Názov najbližšieho spoločného predka alebo None
        """
        # Ak ktorákoľvek trieda nie je v strome, nemôžeme nájsť spoločného predka
        if class1 not in self.parent_map or class2 not in self.parent_map:
            # Špeciálny prípad pre motory, aj keď nie sú v clasifikačnom strome
            if (class1 in ["DieselEngine", "PetrolEngine", "HybridEngine"] and 
                class2 in ["DieselEngine", "PetrolEngine", "HybridEngine"]):
                return "Engine"
            return None
        
        # Najprv získame cestu od class1 k root
        path1 = []
        current = class1
        while current:
            path1.append(current)
            current = self.parent_map.get(current)
            
        # Teraz prejdeme cestu od class2 k root a hľadáme prvého spoločného predka
        current = class2
        while current:
            if current in path1:
                return current
            current = self.parent_map.get(current)
            
        return None

def is_valid_example(model: Model, example: Model, classification_tree: ClassificationTree) -> tuple[bool, list[str]]:
    """
    Zisti, ci priklad je platny podla modelu.
    
    Args:
        model: Model, podla ktoreho sa ma priklad vyhodnotit
        example: Priklad, ktory sa ma vyhodnotit
        classification_tree: Klasifikacny strom pre zistenie vztahov medzi triedami
        
    Returns:
        Tuple (bool, list[str]), kde prvy prvok je True, ak priklad je platny,
        inak False, a druhy prvok je zoznam dovodov neplatnosti.
    """
    is_valid = True
    differences = []
    
    print("\nDEBUG - Začiatok validácie príkladu")
    
    # Zistenie tried objektov v príklade a v modeli (pre generické pravidlá)
    example_classes = set(obj.class_name for obj in example.objects)
    model_classes = set(obj.class_name for obj in model.objects)
    
    print(f"DEBUG - Triedy objektov v príklade: {example_classes}")
    
    # Kontrola BMW objektov v príklade - hlavná časť validácie
    bmw_models = ["BMW", "Series3", "Series5", "Series7", "X5", "X7"]
    
    bmw_objects_in_example = [obj for obj in example.objects if obj.class_name in bmw_models]
    print(f"DEBUG - BMW objekty v príklade: {[obj.name for obj in bmw_objects_in_example]}")
    
    # Pre každý objekt BMW v príklade skontrolujeme pravidlá
    for example_obj in example.objects:
        if example_obj.class_name in bmw_models:
            # Identifikácia modelu BMW vozidla
            car_model = example_obj.class_name
            car_obj_name = example_obj.name
            
            print(f"\nDEBUG - Kontrola BMW modelu: {car_model}, objekt: {car_obj_name}")
            
            # 1. Kontrola prepojení s motorom (Engine)
            has_engine = False
            engine_class = None
            engine_obj = None
            
            print("DEBUG - Kontrola prepojenia s motorom:")
            for link in example.links:
                if link.source == car_obj_name:
                    # Nájdi cieľový objekt
                    target_obj = next((obj for obj in example.objects if obj.name == link.target), None)
                    if target_obj:
                        print(f"DEBUG - Prepojenie {car_obj_name} -> {target_obj.name} ({target_obj.class_name})")
                        if "Engine" in target_obj.class_name:
                            has_engine = True
                            engine_class = target_obj.class_name
                            engine_obj = target_obj
                            print(f"DEBUG - Našiel som motor: {engine_obj.name} ({engine_class})")
                            break
            
            if not has_engine:
                is_valid = False
                diff_msg = f"Chýba požadované spojenie: {car_model} → Engine"
                differences.append(diff_msg)
                print(f"DEBUG - NEPLATNÝ: {diff_msg}")
            
            # 2. Kontrola prepojení s prevodovkou (Transmission)
            has_transmission = False
            transmission_class = None
            
            print("DEBUG - Kontrola prepojenia s prevodovkou:")
            for link in example.links:
                if link.source == car_obj_name:
                    # Nájdi cieľový objekt
                    target_obj = next((obj for obj in example.objects if obj.name == link.target), None)
                    if target_obj:
                        print(f"DEBUG - Prepojenie {car_obj_name} -> {target_obj.name} ({target_obj.class_name})")
                        if "Transmission" in target_obj.class_name:
                            has_transmission = True
                            transmission_class = target_obj.class_name
                            print(f"DEBUG - Našiel som prevodovku: {target_obj.name} ({transmission_class})")
                            break
            
            if not has_transmission:
                is_valid = False
                diff_msg = f"Chýba požadované spojenie: {car_model} → Transmission"
                differences.append(diff_msg)
                print(f"DEBUG - NEPLATNÝ: {diff_msg}")
            
            # 3. Kontrola prepojení s pohonným systémom (DriveSystem)
            has_drive_system = False
            drive_system_class = None
            
            print("DEBUG - Kontrola prepojenia s pohonným systémom:")
            for link in example.links:
                if link.source == car_obj_name:
                    # Nájdi cieľový objekt
                    target_obj = next((obj for obj in example.objects if obj.name == link.target), None)
                    if target_obj:
                        print(f"DEBUG - Prepojenie {car_obj_name} -> {target_obj.name} ({target_obj.class_name})")
                        if target_obj.class_name in ["DriveSystem", "RWD", "AWD", "XDrive"]:
                            has_drive_system = True
                            drive_system_class = target_obj.class_name
                            print(f"DEBUG - Našiel som pohon: {target_obj.name} ({drive_system_class})")
                            break
            
            if not has_drive_system:
                is_valid = False
                diff_msg = f"Chýba požadované spojenie: {car_model} → DriveSystem"
                differences.append(diff_msg)
                print(f"DEBUG - NEPLATNÝ: {diff_msg}")
            
            # 4. Špecifické validácie pre jednotlivé modely
            
            # X modely musia mať XDrive
            if car_model in ["X5", "X7"] and drive_system_class != "XDrive":
                is_valid = False
                diff_msg = f"Chýba požadované spojenie: {car_model} → XDrive"
                differences.append(diff_msg)
                print(f"DEBUG - NEPLATNÝ: {diff_msg} (má {drive_system_class})")
            
            # Series7 musí mať AWD
            if car_model == "Series7" and drive_system_class != "AWD":
                is_valid = False
                diff_msg = f"Chýba požadované spojenie: {car_model} → AWD"
                differences.append(diff_msg)
                print(f"DEBUG - NEPLATNÝ: {diff_msg} (má {drive_system_class})")
            
            # X7 musí mať AutomaticTransmission
            if car_model == "X7" and transmission_class != "AutomaticTransmission":
                is_valid = False
                diff_msg = f"Chýba požadované spojenie: {car_model} → AutomaticTransmission"
                differences.append(diff_msg)
                print(f"DEBUG - NEPLATNÝ: {diff_msg} (má {transmission_class})")
            
            # Kontrola validácie spojenia Engine-Transmission
            if has_engine and has_transmission and engine_obj:
                engine_linked_to_transmission = False
                print(f"DEBUG - Kontrola prepojenia motora {engine_obj.name} s prevodovkou:")
                for link in example.links:
                    if link.source == engine_obj.name:
                        target_obj = next((obj for obj in example.objects if obj.name == link.target), None)
                        if target_obj:
                            print(f"DEBUG - Prepojenie {engine_obj.name} -> {target_obj.name} ({target_obj.class_name})")
                            if "Transmission" in target_obj.class_name:
                                engine_linked_to_transmission = True
                                print(f"DEBUG - Motor je prepojený s prevodovkou")
                                break
                
                if not engine_linked_to_transmission:
                    is_valid = False
                    diff_msg = f"Chýba požadované spojenie: {engine_class} → Transmission"
                    differences.append(diff_msg)
                    print(f"DEBUG - NEPLATNÝ: {diff_msg}")
    
    # Kontrola MUST_NOT vzťahov - stále platí
    for model_link in model.links:
        if model_link.link_type == LinkType.MUST_NOT:
            for example_link in example.links:
                if (
                    example_link.source == model_link.source
                    and example_link.target == model_link.target
                ):
                    is_valid = False
                    diff = f"Obsahuje zakázané spojenie: {model_link.source} → {model_link.target}"
                    differences.append(diff)
                    print(f"DEBUG - NEPLATNÝ: {diff}")
    
    print(f"\nDEBUG - Výsledok validácie: {'✅ PLATNÝ' if is_valid else '❌ NEPLATNÝ'}")
    print(f"DEBUG - Počet problémov: {len(differences)}")
    
    return is_valid, differences 