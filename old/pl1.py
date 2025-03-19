from __future__ import annotations
from dataclasses import dataclass
from typing import List, Set, Dict, Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from models import Model

class PredicateType(Enum):
    """
    Enum reprezentujúci typy predikátov v jazyku PL1.
    PL1 je podmnožina predikatovej logiky prvého rádu, ktorú používame na popis objektov, ich tried a atribútov.
    """
    IS_A = "is_a"        # Predikát určujúci triedu objektu, napr. IS_A(bmw_x5, X5)
    HAS = "has"          # Predikát určujúci komponent, ktorý objekt obsahuje, napr. HAS(bmw_x5, engine_40i)
    ATTRIBUTE = "attribute"  # Predikát určujúci hodnotu atribútu, napr. ATTRIBUTE(engine_40i, power_kw, 250)

@dataclass(frozen=True)  # frozen=True robí triedu nemeniteľnou a hashovateľnou
class Predicate:
    """
    Trieda reprezentujúca jeden predikát v jazyku PL1.
    Predikáty sú základné stavebné bloky PL1 a popisujú vlastnosti objektov.
    """
    type: PredicateType         # Typ predikátu
    arguments: tuple            # Argumenty predikátu (tuple, lebo zoznamy nie sú hashovateľné)
    
    def __init__(self, type: PredicateType, arguments: List[str]):
        """
        Inicializuje predikát so zadaným typom a argumentmi.
        
        Args:
            type: Typ predikátu (IS_A, HAS, ATTRIBUTE)
            arguments: Zoznam argumentov predikátu (konvertujú sa na tuple)
        """
        object.__setattr__(self, 'type', type)
        object.__setattr__(self, 'arguments', tuple(arguments))  # Konverzia na tuple pre hashovateľnosť
    
    def __str__(self) -> str:
        """
        Prevádza predikát na čitateľný textový reťazec.
        
        Returns:
            Reťazec reprezentujúci predikát, napr. "is_a(bmw_x5, X5)"
        """
        if self.type == PredicateType.IS_A:
            return f"is_a({self.arguments[0]}, {self.arguments[1]})"
        elif self.type == PredicateType.HAS:
            return f"has({self.arguments[0]}, {self.arguments[1]})"
        elif self.type == PredicateType.ATTRIBUTE:
            return f"attribute({self.arguments[0]}, {self.arguments[1]}, {self.arguments[2]})"
        return f"{self.type}({', '.join(self.arguments)})"

    def __eq__(self, other):
        """
        Porovnáva dva predikáty na základe ich sémantickej ekvivalencie.
        
        Porovnanie zohľadňuje typ predikátu a jeho argumenty, s normalizáciou pre objekty 'car' a 'test_car'.
        
        Args:
            other: Iný predikát na porovnanie
            
        Returns:
            True ak sú predikáty sémanticky ekvivalentné, inak False
        """
        if not isinstance(other, Predicate):
            return False
        # Porovnaj typ predikátu
        if self.type != other.type:
            return False
            
        # Pre IS_A porovnaj len triedu (druhý argument)
        if self.type == PredicateType.IS_A:
            return self.arguments[1] == other.arguments[1]
            
        # Pre HAS porovnaj len komponent (druhý argument)
        elif self.type == PredicateType.HAS:
            return self.arguments[1] == other.arguments[1]
            
        # Pre ATTRIBUTE porovnaj všetky argumenty
        elif self.type == PredicateType.ATTRIBUTE:
            # Normalizuj názvy objektov (car/test_car -> car)
            obj1 = 'car' if self.arguments[0] == 'car' or self.arguments[0].startswith('test_') else self.arguments[0]
            obj2 = 'car' if other.arguments[0] == 'car' or other.arguments[0].startswith('test_') else other.arguments[0]
            
            # Porovnaj všetky argumenty
            return (obj1 == obj2 and 
                    self.arguments[1] == other.arguments[1] and 
                    self.arguments[2] == other.arguments[2])
                        
        return False

@dataclass
class Hypothesis:
    """
    Trieda reprezentujúca hypotézu - množinu predikátov, ktoré popisujú objekt alebo model.
    Hypotézy používame na reprezentáciu modelov BMW automobilov a ich komponentov.
    """
    predicates: Set[Predicate]  # Množina predikátov tvoriacich hypotézu
    
    def __str__(self) -> str:
        """
        Prevádza hypotézu na čitateľný textový reťazec.
        
        Returns:
            Reťazec reprezentujúci hypotézu ako konjunkciu predikátov
        """
        return " ∧ ".join(str(p) for p in self.predicates)
    
    def to_model(self) -> Model:
        """
        Konvertuje PL1 hypotézu na sémantický sieťový model.
        
        Táto metóda transformuje množinu predikátov na model zložený z objektov, spojení a atribútov.
        
        Returns:
            Model vytvorený z predikátov hypotézy
        """
        from models import Model, Object, Link, LinkType
        
        objects = []
        links = []
        attributes = {}
        
        # Najprv spracujeme IS_A a HAS predikáty
        for pred in self.predicates:
            if pred.type == PredicateType.IS_A:
                obj_name, class_name = pred.arguments
                if obj_name not in [obj.name for obj in objects]:
                    objects.append(Object(obj_name, class_name))
                links.append(Link(obj_name, class_name, LinkType.MUST_BE_A))
            
            elif pred.type == PredicateType.HAS:
                obj_name, component = pred.arguments
                links.append(Link(obj_name, component, LinkType.MUST))
                # Pridáme aj komponent ako objekt ak ešte neexistuje
                if component not in [obj.name for obj in objects]:
                    objects.append(Object(component, component))
            
            elif pred.type == PredicateType.ATTRIBUTE:
                obj_name, attr_name, value = pred.arguments
                if obj_name not in attributes:
                    attributes[obj_name] = {}
                attributes[obj_name][attr_name] = value
        
        # Pridáme atribúty k objektom
        for obj in objects:
            if obj.name in attributes:
                obj.attributes = attributes[obj.name]
        
        return Model(objects=objects, links=links)

def compare_hypotheses(h1: Hypothesis, h2: Hypothesis) -> Dict[str, Set[Predicate]]:
    """
    Porovnáva dve hypotézy pomocou Winstonovho prístupu.
    
    Táto funkcia je jadrom validačného procesu, ktorý porovnáva naučený model (h1) 
    s testovaným príkladom (h2) na zistenie, či je testovaný príklad platný.
    
    Args:
        h1: Prvá hypotéza (naučený model)
        h2: Druhá hypotéza (testovaný príklad)
        
    Returns:
        Slovník obsahujúci:
        - "common": množina spoločných predikátov
        - "must": množina predikátov, ktoré sú v h1, ale chýbajú v h2
        - "must_not": množina predikátov, ktoré sú v h2, ale nemali by tam byť
    """
    # Získaj typy objektov z predikátov
    h1_object_types = {}  # objekt -> trieda
    h2_object_types = {}  # objekt -> trieda
    
    for p in h1.predicates:
        if p.type == PredicateType.IS_A:
            obj_name, class_name = p.arguments
            h1_object_types[obj_name] = class_name
    
    for p in h2.predicates:
        if p.type == PredicateType.IS_A:
            obj_name, class_name = p.arguments
            h2_object_types[obj_name] = class_name
    
    # Identifikuj hlavný objekt v testovanom príklade
    main_test_object = None
    main_test_class = None
    
    for obj, cls in h2_object_types.items():
        # Prvý objekt s triedou z hierarchie Vehicle/Car považujeme za hlavný
        if cls in ["Car", "SUV", "Sedan", "SportsCar", "Vehicle"]:
            main_test_object = obj
            main_test_class = cls
            break
    
    # Nájdi relevantné objekty v naučenom modeli s rovnakou triedou
    relevant_model_objects = []
    
    for obj, cls in h1_object_types.items():
        if cls == main_test_class:
            relevant_model_objects.append(obj)
    
    # Ak nie sú nájdené objekty s presne rovnakou triedou, skúsime hľadať podobné triedy v hierarchii
    if not relevant_model_objects and main_test_class:
        for obj, cls in h1_object_types.items():
            if main_test_class in cls or cls in main_test_class:
                relevant_model_objects.append(obj)
        
        # Ak stále nie sú, použi všetky objekty typu Car
        if not relevant_model_objects:
            for obj, cls in h1_object_types.items():
                if cls in ["Car", "SUV", "Sedan", "SportsCar", "Vehicle"]:
                    relevant_model_objects.append(obj)
    
    # Vytvor mapovanie komponentov na ich atribúty, aby bolo možné porovnať funkčnú ekvivalenciu
    h1_components = {}  # Komponenty z naučeného modelu (meno -> atribúty)
    h2_components = {}  # Komponenty z testovaného príkladu (meno -> atribúty)
    
    # Najprv identifikuj všetky komponenty z HAS predikátov
    h1_has_relations = []
    h2_has_relations = []
    
    for p in h1.predicates:
        if p.type == PredicateType.HAS and p.arguments[0] in relevant_model_objects:
            component = p.arguments[1]
            h1_components[component] = {}
            h1_has_relations.append((p.arguments[0], component))
    
    for p in h2.predicates:
        if p.type == PredicateType.HAS and p.arguments[0] == main_test_object:
            component = p.arguments[1]
            h2_components[component] = {}
            h2_has_relations.append((p.arguments[0], component))

    # Potom pridaj atribúty ku komponentom
    for p in h1.predicates:
        if p.type == PredicateType.ATTRIBUTE and p.arguments[0] in h1_components:
            component = p.arguments[0]
            attr_name = p.arguments[1]
            attr_value = p.arguments[2]
            h1_components[component][attr_name] = attr_value
    
    for p in h2.predicates:
        if p.type == PredicateType.ATTRIBUTE and p.arguments[0] in h2_components:
            component = p.arguments[0]
            attr_name = p.arguments[1]
            attr_value = p.arguments[2]
            h2_components[component][attr_name] = attr_value
    
    # Vytvor mapovania medzi funkčne ekvivalentnými komponentami
    component_mappings = {}  # Meno komponentu v h2 -> meno komponentu v h1
    
    for h2_comp, h2_attrs in h2_components.items():
        for h1_comp, h1_attrs in h1_components.items():
            if not h2_attrs or not h1_attrs:  # Preskočiť komponenty bez atribútov
                continue
                
            # Porovnaj atribúty na zistenie funkčnej ekvivalencie
            matches = True
            match_score = 0  # Čím viac atribútov sa zhoduje, tým vyššie skóre
            
            # Porovnanie atribútov h1_comp s h2_comp
            for attr, val1 in h1_attrs.items():
                if attr not in h2_attrs:
                    continue  # Ak h2 nemá tento atribút, pokračuj s ďalším
                
                val2 = h2_attrs[attr]
                
                # Numerické porovnanie s toleranciou
                if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                    tolerance = 0.2 * max(abs(float(val1)), abs(float(val2)))
                    if abs(float(val1) - float(val2)) <= tolerance:
                        match_score += 1
                    else:
                        matches = False
                        break
                # Textové porovnanie
                elif str(val1).lower() == str(val2).lower():
                    match_score += 1
                else:
                    matches = False
                    break
            
            if matches and match_score > 0:
                # Ak je to zhoda a ešte nemáme mapovanie alebo máme lepšiu zhodu
                if h2_comp not in component_mappings or match_score > component_mappings[h2_comp][1]:
                    component_mappings[h2_comp] = (h1_comp, match_score)
    
    # Normalizuj predikáty - zachovaj pôvodné pre debugging
    h1_normalized = set()
    h2_normalized = set()
    
    h1_original_to_normalized = {}  # mapovanie pôvodných na normalizované predikáty
    h2_original_to_normalized = {}
    
    # Normalizácia pre h1 (naučený model)
    for p in h1.predicates:
        norm_pred = None
        
        if p.type == PredicateType.IS_A:
            obj_name, class_name = p.arguments
            # Konvertuj len relevantné objekty na 'car'
            if obj_name in relevant_model_objects or not relevant_model_objects:
                norm_pred = Predicate(p.type, ['car', class_name])
                h1_original_to_normalized[str(p)] = norm_pred
        
        elif p.type == PredicateType.HAS:
            obj_name, component = p.arguments
            # Konvertuj len relevantné objekty na 'car'
            if obj_name in relevant_model_objects or not relevant_model_objects:
                norm_pred = Predicate(p.type, ['car', component])
                h1_original_to_normalized[str(p)] = norm_pred
        
        elif p.type == PredicateType.ATTRIBUTE:
            obj_name, attr_name, attr_value = p.arguments
            # Pre atribúty relevantných objektov
            if obj_name in relevant_model_objects:
                norm_pred = Predicate(p.type, ['car', attr_name, attr_value])
                h1_original_to_normalized[str(p)] = norm_pred
            # Pre atribúty komponentov, ktoré majú hlavný objekt
            elif any(hasattr_p.type == PredicateType.HAS and 
                     hasattr_p.arguments[0] in relevant_model_objects and 
                     hasattr_p.arguments[1] == obj_name 
                     for hasattr_p in h1.predicates):
                norm_pred = Predicate(p.type, [obj_name, attr_name, attr_value])
                h1_original_to_normalized[str(p)] = norm_pred
        
        if norm_pred:
            h1_normalized.add(norm_pred)
    
    # Normalizácia pre h2 (testovaný príklad)
    for p in h2.predicates:
        norm_pred = None
        
        if p.type == PredicateType.IS_A:
            obj_name, class_name = p.arguments
            # Ak je to hlavný objekt, konvertuj na 'car'
            if obj_name == main_test_object:
                norm_pred = Predicate(p.type, ['car', class_name])
                h2_original_to_normalized[str(p)] = norm_pred
        
        elif p.type == PredicateType.HAS:
            obj_name, component = p.arguments
            # Ak je to hlavný objekt, konvertuj na 'car'
            if obj_name == main_test_object:
                # Ak máme mapovanie komponentu, použi mapovaný názov
                if component in component_mappings:
                    mapped_component = component_mappings[component][0]
                    norm_pred = Predicate(p.type, ['car', mapped_component])
                else:
                    norm_pred = Predicate(p.type, ['car', component])
                h2_original_to_normalized[str(p)] = norm_pred
        
        elif p.type == PredicateType.ATTRIBUTE:
            try:
                obj_name, attr_name, attr_value = p.arguments
                
                # Pre atribúty hlavného objektu
                if obj_name == main_test_object:
                    # Odstráň prípadné nečakané znaky na konci hodnoty
                    clean_value = attr_value.rstrip('.)]}') if isinstance(attr_value, str) else attr_value
                    norm_pred = Predicate(p.type, ['car', attr_name, clean_value])
                    h2_original_to_normalized[str(p)] = norm_pred
                
                # Pre atribúty komponentov hlavného objektu
                elif any(hasattr_p.type == PredicateType.HAS and 
                         hasattr_p.arguments[0] == main_test_object and 
                         hasattr_p.arguments[1] == obj_name 
                         for hasattr_p in h2.predicates):
                    
                    # Ak máme mapovanie pre tento komponent, použi mapované meno komponentu
                    if obj_name in component_mappings:
                        mapped_component = component_mappings[obj_name][0]
                        # Odstráň prípadné nečakané znaky na konci hodnoty
                        clean_value = attr_value.rstrip('.)]}') if isinstance(attr_value, str) else attr_value
                        norm_pred = Predicate(p.type, [mapped_component, attr_name, clean_value])
                    else:
                        # Odstráň prípadné nečakané znaky na konci hodnoty
                        clean_value = attr_value.rstrip('.)]}') if isinstance(attr_value, str) else attr_value
                        norm_pred = Predicate(p.type, [obj_name, attr_name, clean_value])
                    
                    h2_original_to_normalized[str(p)] = norm_pred
                    
            except Exception as e:
                # Skús opraviť problémové predikáty
                if len(p.arguments) >= 3:
                    obj_name, attr_name = p.arguments[0], p.arguments[1]
                    attr_value = str(p.arguments[2]).rstrip('.)]}')
                    
                    if obj_name == main_test_object:
                        norm_pred = Predicate(p.type, ['car', attr_name, attr_value])
                        h2_original_to_normalized[str(p)] = norm_pred
                    elif any(hasattr_p.type == PredicateType.HAS and 
                             hasattr_p.arguments[0] == main_test_object and 
                             hasattr_p.arguments[1] == obj_name 
                             for hasattr_p in h2.predicates):
                        
                        if obj_name in component_mappings:
                            mapped_component = component_mappings[obj_name][0]
                            norm_pred = Predicate(p.type, [mapped_component, attr_name, attr_value])
                        else:
                            norm_pred = Predicate(p.type, [obj_name, attr_name, attr_value])
                        
                        h2_original_to_normalized[str(p)] = norm_pred
        
        if norm_pred:
            h2_normalized.add(norm_pred)
    
    # Špeciálne porovnanie číselných atribútov - tolerancia pre číselné hodnoty
    numeric_attr_matches = set()
    
    for p1 in h1_normalized:
        if p1.type == PredicateType.ATTRIBUTE and len(p1.arguments) >= 3:
            obj1, attr1, val1 = p1.arguments
            
            # Skús konvertovať na číslo
            try:
                num_val1 = float(val1)
                
                # Hľadaj zodpovedajúci atribút v h2
                for p2 in h2_normalized:
                    if (p2.type == PredicateType.ATTRIBUTE and 
                        len(p2.arguments) >= 3 and 
                        p2.arguments[0] == obj1 and 
                        p2.arguments[1] == attr1):
                        
                        # Skús konvertovať na číslo
                        try:
                            num_val2 = float(p2.arguments[2])
                            
                            # Test na podobnosť čísel (tolerancia 20%)
                            tolerance = 0.2 * max(abs(num_val1), abs(num_val2))
                            if abs(num_val1 - num_val2) <= tolerance:
                                numeric_attr_matches.add(p1)
                                numeric_attr_matches.add(p2)
                        except (ValueError, TypeError):
                            pass
            except (ValueError, TypeError):
                pass
    
    # Prispôsob spoločné predikáty na základe nájdených numerických zhôd
    common = (h1_normalized & h2_normalized) | numeric_attr_matches
    
    # Nájdi rozdiely - potenciálne MUST a MUST_NOT predikáty
    must_predicates = h1_normalized - h2_normalized - numeric_attr_matches
    must_not_predicates = h2_normalized - h1_normalized - numeric_attr_matches
    
    return {
        "common": common,
        "must": must_predicates,
        "must_not": must_not_predicates
    }

def parse_pl1_input(text: str) -> Set[Predicate]:
    """
    Parsuje PL1 textový vstup do množiny predikátov.
    
    Táto funkcia spracováva textový vstup v jazyku PL1 a vytvára z neho množinu predikátov.
    Podporuje komentáre (# alebo //), spracovanie argumentov a konverziu číselných hodnôt.
    
    Args:
        text: Textový vstup v jazyku PL1
        
    Returns:
        Množina predikátov vytvorených z PL1 vstupu
    """
    predicates = set()
    
    for line in text.strip().split('\n'):
        # Odstráň komentáre - všetko za // alebo #
        if '//' in line:
            line = line[:line.index('//')]
        if '#' in line:
            line = line[:line.index('#')]
            
        line = line.strip().rstrip('.').rstrip(')')  # Odstráň bodku a prípadnú zátvorku na konci
        if not line:
            continue
            
        # Parse predicate type and arguments
        if '(' not in line:
            continue
            
        try:
            pred_type, args_str = line.split('(', 1)
            pred_type = pred_type.strip()
            
            # Skontroluj, či je to platný typ predikátu
            try:
                pred_type_enum = PredicateType(pred_type.lower())
            except ValueError:
                continue
                
            # Očisti argumenty a odstráň prípadnú zátvorku na konci
            args_str = args_str.rstrip(')')
            
            # Rozdeľ argumenty
            args = []
            # Spracuj argumenty jeden po druhom, rešpektujúc čiarky v reťazcoch 
            current_arg = ""
            in_quotes = False
            
            for char in args_str + ',':  # Pridaj čiarku na koniec, aby sa spracoval aj posledný argument
                if char == ',' and not in_quotes:
                    # Odstráň komentáre z argumentu
                    arg = current_arg.strip()
                    if '//' in arg:
                        arg = arg[:arg.index('//')].strip()
                    if '#' in arg:
                        arg = arg[:arg.index('#')].strip()
                    args.append(arg)
                    current_arg = ""
                elif char == '"' or char == "'":
                    in_quotes = not in_quotes
                    current_arg += char
                else:
                    current_arg += char
            
            # Odstráň prázdne argumenty
            args = [arg.strip() for arg in args if arg.strip()]
            
            # Konvertuj číselné hodnoty, ak je to možné
            for i, arg in enumerate(args):
                # Ak je atribút a posledný argument, skús konvertovať na číslo
                if pred_type_enum == PredicateType.ATTRIBUTE and i == 2:
                    try:
                        # Odstráň nežiaduce znaky z konca
                        clean_arg = arg.rstrip('.])}"\'')
                        
                        # Skús konvertovať na float alebo int
                        if '.' in clean_arg:
                            args[i] = float(clean_arg)
                        else:
                            args[i] = int(clean_arg)
                    except (ValueError, TypeError):
                        # Ak konverzia zlyhá, použi pôvodný očistený argument
                        args[i] = clean_arg
            
            # Vytvor predikát
            if pred_type_enum == PredicateType.IS_A:
                if len(args) >= 2:
                    predicates.add(Predicate(pred_type_enum, [args[0], args[1]]))
            elif pred_type_enum == PredicateType.HAS:
                if len(args) >= 2:
                    predicates.add(Predicate(pred_type_enum, [args[0], args[1]]))
            elif pred_type_enum == PredicateType.ATTRIBUTE:
                if len(args) >= 3:
                    predicates.add(Predicate(pred_type_enum, [args[0], args[1], args[2]]))
        except Exception:
            # Ignoruj chyby pri parsovaní
            pass
    
    return predicates