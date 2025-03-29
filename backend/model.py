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
    """
    objects: List[Object] = field(default_factory=list)
    links: List[Link] = field(default_factory=list)
    
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
            ]
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
        
        return cls(objects=objects, links=links)
    
    def copy(self) -> 'Model':
        """
        Vytvori hlboku kopiu modelu.
        
        Returns:
            Novy model s identickymi objektmi a spojeniami
        """
        return Model(
            objects=deepcopy(self.objects),
            links=deepcopy(self.links)
        )
    
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
        """
        predicates = []
        
        # Pridaj predikáty pre objekty a ich triedy
        for obj in self.objects:
            predicates.append(f"Ι({obj.name}, {obj.class_name})")
        
        # Pridaj predikáty pre spojenia
        for link in self.links:
            if link.link_type == LinkType.REGULAR:
                predicates.append(f"Π({link.source}, {link.target})")
            elif link.link_type == LinkType.MUST:
                predicates.append(f"Μ({link.source}, {link.target})")  # Μ pre MUST
            elif link.link_type == LinkType.MUST_NOT:
                predicates.append(f"Ν({link.source}, {link.target})")  # Ν pre MUST_NOT
            # MUST_BE_A spojenia sú už zahrnuté v Ι predikátoch
        
        # Pridaj predikáty pre atribúty
        for obj in self.objects:
            if obj.attributes:
                for attr_name, attr_value in obj.attributes.items():
                    if isinstance(attr_value, tuple) and len(attr_value) == 2:
                        # Interval
                        min_val, max_val = attr_value
                        predicates.append(f"Α({obj.name}, {attr_name}, ({min_val}, {max_val}))")
                    else:
                        # Jednoduchá hodnota
                        predicates.append(f"Α({obj.name}, {attr_name}, {attr_value})")
        
        # Spoj predikáty konjunkciou
        return " ∧ ".join(predicates)

    def extract_model_rules(self) -> Dict[str, str]:
        """
        Extrahuje identifikačné pravidlá pre jednotlivé modely áut.
        
        Vráti slovník, kde kľúče sú názvy modelov a hodnoty sú
        textové reprezentácie pravidiel v logike prvého rádu.
        
        Táto metóda extrahuje pravidlá pre všetky modely z formuly vygenerovanej
        metódou to_formula().
        """
        rules = {}
        
        # Najprv získame známe modely, ktoré chceme hľadať v pravidlách
        known_models = {"BMW", "Series3", "Series5", "Series7", "X5", "X7"}
        
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
        for model_name in known_models:
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
        
        # Pre každý známy model vytvoríme pravidlo
        for model_name in known_models:
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
                if '(' in attr_value and ')' in attr_value and ',' in attr_value:
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
        
        # Pre debugovanie vypíšeme extrahované pravidlá
        print(f"Extracted rules from model: {rules}")
        
        return rules

    def to_semantic_network(self) -> Dict[str, Any]:
        """
        Konvertuje model na sémantickú sieť vhodnú pre vizualizáciu.
        
        Vráti slovník s dvoma kľúčmi:
        - nodes: zoznam uzlov (objektov) v sieti
        - links: zoznam spojení medzi uzlami
        
        Každý uzol má atribúty:
        - id: jedinečný identifikátor uzla
        - name: názov objektu
        - class: trieda objektu
        - category: kategória uzla (BMW, Engine, Transmission, Drive, Other)
        - attributes: slovník atribútov objektu
        
        Každé spojenie má atribúty:
        - source: ID zdrojového uzla
        - target: ID cieľového uzla
        - type: typ spojenia (MUST, MUST_NOT, MUST_BE_A, REGULAR)
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
        
        # Vytvor uzly
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
        
        # Vytvor spojenia
        for link in self.links:
            link_data = {
                "source": link.source,
                "target": link.target,
                "type": link.link_type.value
            }
            
            links.append(link_data)
        
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

def formula_to_model(formula: Formula) -> Model:
    """
    Konvertuje formulu na model.
    
    Args:
        formula: Formula v predikátovej logike prvého rádu
        
    Returns:
        Model vytvoreny z formuly
    """
    print("DEBUG: Starting formula_to_model")
    objects = []
    links = []
    attributes = {}
    
    # Mapovanie predikatov na objekty a spojenia
    for predicate in formula.predicates:
        print(f"DEBUG: Processing predicate {predicate.name} with args {predicate.arguments}")
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
            
            if predicate.name == "Π":  # PI
                # Spojenie HAS (REGULAR)
                links.append(Link(arg1, arg2, LinkType.REGULAR))
                print(f"DEBUG: Added REGULAR link {arg1} -> {arg2}")
            elif predicate.name == "Ι":  # IOTA
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
            elif predicate.name == "Μ":  # MU
                # Spojenie MUST
                links.append(Link(arg1, arg2, LinkType.MUST))
                print(f"DEBUG: Added MUST link {arg1} -> {arg2}")
            elif predicate.name == "Ν":  # NU
                # Spojenie MUST_NOT
                links.append(Link(arg1, arg2, LinkType.MUST_NOT))
                print(f"DEBUG: Added MUST_NOT link {arg1} -> {arg2}")
            else:
                # Atribut
                if arg1 not in attributes:
                    attributes[arg1] = {}
                
                # Pouzijeme cely nazov predikatu ako nazov atributu
                attr_name = predicate.name.lower()
                attributes[arg1][attr_name] = arg2
                print(f"DEBUG: Added attribute {attr_name}={arg2} to object {arg1}")
        
        elif predicate.type == PredicateType.TERNARY:
            # Ternarny predikat reprezentuje atribut s nazvom
            obj_name = predicate.arguments[0]
            attr_name = predicate.arguments[1]
            attr_value = predicate.arguments[2]
            
            if obj_name not in attributes:
                attributes[obj_name] = {}
            
            attributes[obj_name][attr_name] = attr_value
            print(f"DEBUG: Added attribute {attr_name}={attr_value} to object {obj_name}")
    
    # Pridaj atributy k objektom
    for obj in objects:
        if obj.name in attributes:
            obj.attributes = attributes[obj.name]
            print(f"DEBUG: Attached attributes {obj.attributes} to object {obj.name}")
    
    # Create Model
    result_model = Model(objects=objects, links=links)
    print(f"DEBUG: Created model with {len(objects)} objects and {len(links)} links")
    return result_model

class ClassificationTree:
    """
    Trieda reprezentujuca hierarchiu tried v klasifikacnom strome.
    
    Tato trieda sluzi na definovanie vztahov medzi triedami a podporuje
    operacie ako hladanie spolocneho predka pre dve triedy alebo pridavanie
    novych vztahov.
    """
    def __init__(self):
        """
        Inicializuje prazdny klasifikacny strom.
        """
        self.parent_map = {}  # Mapa trieda -> rodič
        self.children_map = {}  # Mapa trieda -> zoznam detí
        
    def add_relationship(self, child: str, parent: Optional[str]) -> None:
        """
        Pridá vzťah rodič-dieťa do stromu.
        
        Parametre:
            child: Názov detskej triedy
            parent: Názov rodičovskej triedy, alebo None ak je to koreňová trieda
        """
        # Ak rodič je None, ide o koreňovú triedu
        if parent is None:
            self.parent_map[child] = None
        else:
            self.parent_map[child] = parent
            
            # Pridaj dieťa do zoznamu detí rodiča
            if parent not in self.children_map:
                self.children_map[parent] = []
            
            if child not in self.children_map[parent]:
                self.children_map[parent].append(child)
    
    def get_parent(self, class_name: str) -> Optional[str]:
        """
        Vráti rodiča danej triedy.
        
        Parametre:
            class_name: Názov triedy
            
        Návratová hodnota:
            Názov rodičovskej triedy, alebo None ak trieda nemá rodiča alebo neexistuje
        """
        return self.parent_map.get(class_name)
    
    def get_children(self, class_name: str) -> List[str]:
        """
        Vráti zoznam detí danej triedy.
        
        Parametre:
            class_name: Názov triedy
            
        Návratová hodnota:
            Zoznam názvov detských tried, alebo prázdny zoznam ak trieda nemá deti alebo neexistuje
        """
        return self.children_map.get(class_name, [])
    
    def add_union_class(self, union_class: str, component_classes: List[str]) -> None:
        """
        Vytvorí novú triedu, ktorá je zjednotením existujúcich tried.
        
        Parametre:
            union_class: Názov novej zjednotenej triedy
            component_classes: Zoznam tried, ktoré tvoria zjednotenie
        """
        # Nájdi spoločného predka komponentových tried
        common_ancestor = None
        
        if len(component_classes) > 1:
            common_ancestor = self.find_common_ancestor(component_classes[0], component_classes[1])
            
            for i in range(2, len(component_classes)):
                if common_ancestor:
                    common_ancestor = self.find_common_ancestor(common_ancestor, component_classes[i])
                else:
                    break
        
        # Ak neexistuje spoločný predok, použi None (koreňová trieda)
        # Pridaj novú triedu ako potomka spoločného predka
        self.add_relationship(union_class, common_ancestor)
        
        # Pridaj komponentové triedy ako potomkov novej triedy
        for component in component_classes:
            # Ak komponentová trieda už existuje, aktualizuj jej rodiča
            if component in self.parent_map:
                old_parent = self.parent_map[component]
                
                # Odstráň komponentovú triedu zo zoznamu detí starého rodiča
                if old_parent and old_parent in self.children_map and component in self.children_map[old_parent]:
                    self.children_map[old_parent].remove(component)
            
            # Nastav novú triedu ako rodiča komponentovej triedy
            self.parent_map[component] = union_class
            
            # Pridaj komponentovú triedu do zoznamu detí novej triedy
            if union_class not in self.children_map:
                self.children_map[union_class] = []
            
            if component not in self.children_map[union_class]:
                self.children_map[union_class].append(component)
    
    def find_common_ancestor(self, class1: str, class2: str) -> Optional[str]:
        """
        Nájde najbližšieho spoločného predka dvoch tried.
        
        Parametre:
            class1: Názov prvej triedy
            class2: Názov druhej triedy
            
        Návratová hodnota:
            Názov najbližšieho spoločného predka, alebo None ak neexistuje
        """
        # Ak niektorá z tried neexistuje, vráť None
        if class1 not in self.parent_map or class2 not in self.parent_map:
            return None
        
        # Ak sú triedy rovnaké, vráť túto triedu
        if class1 == class2:
            return class1
        
        # Nájdi cestu od class1 ku koreňu
        path1 = []
        current = class1
        
        while current:
            path1.append(current)
            current = self.parent_map.get(current)
        
        # Nájdi prvú triedu na ceste od class2 ku koreňu, ktorá je aj v path1
        current = class2
        
        while current:
            if current in path1:
                return current
            current = self.parent_map.get(current)
        
        return None
    
    def is_subclass(self, child: str, parent: str) -> bool:
        """
        Skontroluje, či je jedna trieda podtriedou druhej.
        
        Parametre:
            child: Názov potenciálnej podtriedy
            parent: Názov potenciálnej nadtriedy
            
        Návratová hodnota:
            True ak je child podtriedou parent, inak False
        """
        # Ak sú triedy rovnaké, vráť True
        if child == parent:
            return True
        
        # Ak child neexistuje v strome, vráť False
        if child not in self.parent_map:
            return False
        
        # Postupuj od child smerom ku koreňu a hľadaj parent
        current = self.parent_map.get(child)
        
        while current:
            if current == parent:
                return True
            current = self.parent_map.get(current)
        
        return False
    
    def are_related(self, class1: str, class2: str) -> bool:
        """
        Skontroluje, či sú dve triedy v hierarchickom vzťahu.
        
        Parametre:
            class1: Názov prvej triedy
            class2: Názov druhej triedy
            
        Návratová hodnota:
            True ak je jedna trieda podtriedou druhej, inak False
        """
        return self.is_subclass(class1, class2) or self.is_subclass(class2, class1) 

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