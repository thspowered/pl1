from dataclasses import dataclass
from typing import List, Set, Optional, Union, Dict, Tuple, Any
from enum import Enum
import networkx as nx
from copy import deepcopy
from pl1 import Predicate, PredicateType, Hypothesis

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

@dataclass
class Model:
    """
    Trieda reprezentujuca model zlozeny z objektov a spojeni.
    
    Tato trieda je jadrom reprezentacie modelov BMW automobilov. Obsahuje zoznam
    objektov (auto a jeho komponenty) a spojeni medzi nimi, ktore vyjadruju
    vztahy a poziadavky na platny model BMW.
    
    Atributy:
        objects: Zoznam objektov v modeli
        links: Zoznam spojeni medzi objektmi
    """
    objects: List[Object]
    links: List[Link]
    
    def copy(self) -> 'Model':
        """
        Vytvori hlboku kopiu modelu.
        
        Returns:
            Novy model s identickymi objektmi a spojeniami
        """
        return Model(
            objects=[deepcopy(obj) for obj in self.objects],
            links=[deepcopy(link) for link in self.links]
        )
    
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
    
    def update_object_class(self, obj_name: str, new_class: str):
        """
        Aktualizuje triedu objektu.
        
        Args:
            obj_name: Nazov objektu, ktoreho triedu chceme zmenit
            new_class: Nova trieda pre objekt
        """
        for obj in self.objects:
            if obj.name == obj_name:
                obj.class_name = new_class
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

    def create_semantic_network(self) -> nx.DiGraph:
        """
        Vytvori orientovany graf reprezentujuci semanticku siet modelu.
        
        Tato metoda konvertuje model na graf v kniznici NetworkX, kde uzly
        su objekty a hrany su spojenia medzi nimi. Atributy objektov su
        reprezentovane ako samostatne uzly spojene s objektmi.
        
        Returns:
            DiGraph: Orientovany graf reprezentujuci model
        """
        G = nx.DiGraph()
        
        # Pridaj vsetky objekty ako uzly
        for obj in self.objects:
            G.add_node(obj.name, class_name=obj.class_name)
            if obj.attributes:
                for attr, value in obj.attributes.items():
                    attr_node = f"{obj.name}_{attr}"
                    G.add_node(attr_node, value=value)
                    G.add_edge(obj.name, attr_node, type="has_attribute")
        
        # Pridaj vsetky spojenia ako hrany
        for link in self.links:
            G.add_edge(link.source, link.target, type=link.link_type.value)
            
        return G

    def to_pl1(self) -> Hypothesis:
        """
        Konvertuje model na PL1 hypotezu.
        
        Tato metoda transformuje model na mnozinu predikatov v PL1 formate,
        kde objekty a ich triedy su reprezentovane IS_A predikatmi,
        komponenty su reprezentovane HAS predikatmi a atributy su
        reprezentovane ATTRIBUTE predikatmi.
        
        Returns:
            Hypothesis: PL1 hypoteza reprezentujuca model
        """
        predicates = set()
        
        # Konvertuj objekty a ich triedy
        for obj in self.objects:
            # Pridaj IS_A predikat len pre ne-komponentove objekty
            if not (obj.name == obj.class_name):
                predicates.add(Predicate(
                    type=PredicateType.IS_A,
                    arguments=[obj.name, obj.class_name]
                ))
            
            # Konvertuj atributy pre VSETKY objekty (vratane komponentov)
            if obj.attributes:
                for attr, value in obj.attributes.items():
                    predicates.add(Predicate(
                        type=PredicateType.ATTRIBUTE,
                        arguments=[obj.name, attr, str(value)]
                    ))
        
        # Konvertuj spojenia
        for link in self.links:
            if link.link_type == LinkType.MUST:
                predicates.add(Predicate(
                    type=PredicateType.HAS,
                    arguments=[link.source, link.target]
                ))
            elif link.link_type == LinkType.MUST_BE_A:
                predicates.add(Predicate(
                    type=PredicateType.IS_A,
                    arguments=[link.source, link.target]
                ))
        
        return Hypothesis(predicates)

class ClassificationTree:
    """
    Trieda reprezentujuca hierarchiu tried v klasifikacnom strome.
    
    Tato trieda sluzi na definovanie vztahov medzi triedami (napr. BMW je typ auta,
    Sedan je typ BMW, atd.) a podporuje operacie ako hladanie spolocneho predka
    pre dve triedy alebo pridavanie novych vztahov.
    """
    def __init__(self):
        """
        Inicializuje prazdny klasifikacny strom.
        """
        self.hierarchy: Dict[str, Set[str]] = {}
        
    def add_relationship(self, parent: str, child: str):
        """
        Prida vztah rodic-dieta do stromu.
        
        Args:
            parent: Nazov rodicovskej triedy
            child: Nazov detskej triedy
        """
        if parent not in self.hierarchy:
            self.hierarchy[parent] = set()
        self.hierarchy[parent].add(child)
    
    def find_common_ancestor(self, class1: str, class2: str) -> Optional[str]:
        """
        Najde spolocneho predka dvoch tried.
        
        Args:
            class1: Prva trieda
            class2: Druha trieda
            
        Returns:
            Nazov spolocneho predka alebo None, ak neexistuje
        """
        for parent, children in self.hierarchy.items():
            if class1 in children and class2 in children:
                return parent
        return None
    
    def are_related(self, class1: str, class2: str) -> bool:
        """
        Zisti, ci su dve triedy pribuzne (maju spolocneho predka).
        
        Args:
            class1: Prva trieda
            class2: Druha trieda
            
        Returns:
            True, ak triedy maju spolocneho predka, inak False
        """
        return bool(self.find_common_ancestor(class1, class2))

    def add_union_class(self, new_class: str, component_classes: List[str]):
        """
        Prida novu triedu, ktora je zjednotenim existujucich tried.
        
        Tato metoda vytvara nove triedy, ktore zastresuju viacero existujucich
        tried - pouziva sa najma pri vytvarani abstraktnych kategorii pre
        funkcne podobne komponenty (napr. EquivalentEngine pre rozne typy motorov).
        
        Args:
            new_class: Nazov novej zjednocujucej triedy
            component_classes: Zoznam tried, ktore nova trieda zdruzuje
        """
        self.hierarchy[new_class] = set(component_classes) 