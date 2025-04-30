from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union
import traceback
import json
import os
from datetime import datetime
import random
from contextlib import asynccontextmanager

from backend.model import Model, Link, LinkType, Object, ClassificationTree, formula_to_model, is_valid_example
from backend.pl1_parser import parse_pl1_formula, parse_pl1_dataset, Formula, Predicate
from backend.learner import WinstonLearner
from backend.example_validator import compare_example

app = FastAPI(title="PL1 Learning System")

# Povolenie CORS pre frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # V produkcii by malo byť obmedzené na konkrétne domény
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Globálne premenné pre uloženie stavu aplikácie
current_model = Model(objects=[], links=[])
classification_tree = ClassificationTree()
learner = WinstonLearner(classification_tree)
dataset_examples = []  # Zoznam všetkých príkladov v datasete
training_history = []  # História trénovania (použité príklady)
model_history = []  # Historie stavů modelu pro navigaci vpřed/zpět
model_visualization_history = []  # História vizualizácií modelu
current_history_index = -1  # Aktuální index v historii modelu
MAX_HISTORY_SIZE = 30  # Maximálny počet krokov v histórií

# Dátové modely pre API
class PL1Example(BaseModel):
    formula: str
    is_positive: Optional[bool] = True
    name: Optional[str] = None
    validate_attributes: Optional[bool] = True

class TrainingRequest(BaseModel):
    example_ids: List[int]
    retrain_mode: str = "incremental"  # "incremental" alebo "full"
    batch_size: int = 5  # Počet príkladov v jednej dávke
    retrain_all: bool = False  # Označuje, či sa trénujú všetky príklady v datasete

class TrainingResult(BaseModel):
    success: bool
    message: str
    model_state: Optional[Dict[str, Any]] = None
    steps: List[str] = []
    batch_count: Optional[int] = None
    processed_examples: Optional[int] = None
    error: Optional[str] = None
    training_mode: str = "batch"  # "batch" alebo "single" alebo "retrained"
    model_formula: Optional[str] = None
    model_rules: Optional[Dict[str, Any]] = None
    model_hypothesis: Optional[str] = None
    model_visualization: Optional[Dict[str, Any]] = None

class ComparisonResult(BaseModel):
    is_valid: bool
    explanation: str
    symbolic_differences: List[str]

class ModelVisualization(BaseModel):
    nodes: List[Dict[str, Any]]
    links: List[Dict[str, Any]]

# Pomocné funkcie
def initialize_classification_tree():
    """Inicializuje klasifikačný strom so základnými triedami."""
    global classification_tree
    
    # Vytvoríme nový strom
    classification_tree = ClassificationTree()
    print(f"Inicializujem klasifikačný strom...")
    
    # Motory
    classification_tree.add_relationship("Motor", None)
    classification_tree.add_relationship("DieselovyMotor", "Motor")
    classification_tree.add_relationship("BenzinovyMotor", "Motor")
    classification_tree.add_relationship("HybridnyMotor", "Motor")
    
    # Prevodovky
    classification_tree.add_relationship("Prevodovka", None)
    classification_tree.add_relationship("AutomatickaPrevodovka", "Prevodovka")
    classification_tree.add_relationship("ManualnaPrevodovka", "Prevodovka")
    
    # Pohony
    classification_tree.add_relationship("Pohon", None)
    classification_tree.add_relationship("RWD", "Pohon")  # Rear-wheel drive
    classification_tree.add_relationship("AWD", "Pohon")  # All-wheel drive
    classification_tree.add_relationship("XDrive", "AWD")       # BMW xDrive je typ AWD

    # Vybava
    classification_tree.add_relationship("Vybava", None)
    classification_tree.add_relationship("Basic", "Vybava")
    classification_tree.add_relationship("Sport", "Vybava")
    classification_tree.add_relationship("Lux", "Vybava")

 
    
    print(f"Klasifikačný strom inicializovaný, obsahuje {len(classification_tree.parent_map)} vzťahov rodič-dieťa")
    
    # Vypíšeme obsah stromu pre debugovanie
    for child, parent in classification_tree.parent_map.items():
        print(f"  {child} -> {parent or 'ROOT'}")

def generate_model_visualization(model: Model):
    """
    Generuje vizualizaci modelu pro frontend.
    
    Args:
        model: Model k vizualizaci
        
    Returns:
        Slovník obsahující vizualizaci modelu
    """
    if not model:
        return {"nodes": [], "links": []}
        
    try:
        return model.to_semantic_network()
    except Exception as e:
        print(f"Error generating model visualization: {str(e)}")
        traceback.print_exc()
        return {"nodes": [], "links": [], "error": str(e)}

def generate_difference_visualization(model_a, model_b, model_type_differences):
    """
    Generuje vizualizaci rozdílů mezi dvěma modely ve formátu sémantické sítě.
    
    Args:
        model_a: První model
        model_b: Druhý model
        model_type_differences: Slovník s rozdíly v pravidlech pro každý typ modelu
        
    Returns:
        Slovník s uzly a spojeními pro vizualizaci rozdílů
    """
    if not model_a or not model_b:
        return None
        
    nodes = []
    links = []
    
    # Kategórie pre uzly (stejné jako v Model.to_semantic_network)
    bmw_categories = ["BMW", "Series3", "Series5", "Series7", "X5", "X7"]
    engine_categories = ["Engine", "DieselEngine", "PetrolEngine", "HybridEngine"]
    transmission_categories = ["Transmission", "AutomaticTransmission", "ManualTransmission"]
    drive_categories = ["DriveSystem", "RWD", "AWD", "XDrive"]
    
    # Pomocná funkce na určenie kategórie uzla
    def get_node_category(obj_name, class_name):
        if any(category in class_name for category in bmw_categories):
            return "BMW"
        elif any(category in class_name for category in engine_categories) or "engine" in obj_name.lower():
            return "Engine"
        elif any(category in class_name for category in transmission_categories) or "transmission" in obj_name.lower():
            return "Transmission"
        elif any(category in class_name for category in drive_categories) or "drive" in obj_name.lower():
            return "Drive"
        else:
            return "Other"
    
    # Vytvoříme slovníky objektů podle jména pro rychlejší přístup
    objects_a = {obj.name: obj for obj in model_a.objects}
    objects_b = {obj.name: obj for obj in model_b.objects}
    
    # Vytvoříme slovníky spojení podle zdroje a cíle pro rychlejší porovnání
    links_a = {(link.source, link.target, link.link_type.value): link for link in model_a.links}
    links_b = {(link.source, link.target, link.link_type.value): link for link in model_b.links}
    
    # Přidáme třídy, které jsou uvedeny v links, ale chybí v objects
    for link_key in links_a.keys():
        source, target, _ = link_key
        # Přidáme chybějící třídy jako uzly
        if source not in objects_a and source not in objects_b:
            if any(cat in source for cat in bmw_categories + engine_categories + transmission_categories + drive_categories):
                class_name = source
                objects_a[source] = Object(name=source, class_name=class_name)
        if target not in objects_a and target not in objects_b:
            if any(cat in target for cat in bmw_categories + engine_categories + transmission_categories + drive_categories):
                class_name = target
                objects_a[source] = Object(name=target, class_name=class_name)
    
    for link_key in links_b.keys():
        source, target, _ = link_key
        # Přidáme chybějící třídy jako uzly
        if source not in objects_a and source not in objects_b:
            if any(cat in source for cat in bmw_categories + engine_categories + transmission_categories + drive_categories):
                class_name = source
                objects_b[source] = Object(name=source, class_name=class_name)
        if target not in objects_a and target not in objects_b:
            if any(cat in target for cat in bmw_categories + engine_categories + transmission_categories + drive_categories):
                class_name = target
                objects_b[source] = Object(name=target, class_name=class_name)
    
    # Zpracování objektů z obou modelů a přidání do vizualizace
    all_object_names = set(objects_a.keys()) | set(objects_b.keys())
    
    print(f"Total objects for visualization: {len(all_object_names)}")
    
    # Sledujeme již přidané atributy, abychom zabránili duplikátům
    added_attributes = set()
    
    for obj_name in all_object_names:
        # Určíme, zda je objekt v modelu A, B nebo v obou
        status = "common" if obj_name in objects_a and obj_name in objects_b else \
                "only_in_a" if obj_name in objects_a else "only_in_b"
        
        # Vezmeme objekt z příslušného modelu pro získání informací
        obj = objects_a.get(obj_name) if obj_name in objects_a else objects_b.get(obj_name)
        
        # Kontrola null hodnoty
        if not obj:
            print(f"Warning: NULL object found: {obj_name}")
            continue
        
        # Určíme kategorii objektu
        category = get_node_category(obj.name, obj.class_name)
        
        # Vytvoříme uzel
        node = {
            "id": obj.name,
            "name": obj.name,
            "class": obj.class_name,
            "category": category,
            "attributes": obj.attributes or {},
            "status": status  # Přidáme status pro vizualizaci
        }
        
        nodes.append(node)
        
        # Přidáme atributy objektu jako samostatné uzly a vytvoříme spojení na ně
        if hasattr(obj, 'attributes') and obj.attributes:
            for attr_name, attr_value in obj.attributes.items():
                # Vytvoříme unikátní ID pro atribut
                attr_node_id = f"{obj.name}_{attr_name}"
                
                if attr_node_id not in added_attributes:
                    # Přidáme uzel pro atribut
                    attr_node = {
                        "id": attr_node_id,
                        "name": attr_name,
                        "class": "Attribute",
                        "category": "Attribute",
                        "value": attr_value,
                        "status": status  # Atributy mají stejný status jako jejich objekt
                    }
                    nodes.append(attr_node)
                    added_attributes.add(attr_node_id)
                    
                    # Vytvoříme spojení mezi objektem a atributem
                    link_data = {
                        "source": obj.name,
                        "target": attr_node_id,
                        "type": "HAS_ATTRIBUTE",
                        "status": status
                    }
                    links.append(link_data)
                    
                    # Pokud hodnota atributu je seznam nebo množina, přidáme každou hodnotu jako samostatný uzel
                    if isinstance(attr_value, (list, set)) or (isinstance(attr_value, dict) and attr_value.get('type') == 'set'):
                        values = attr_value if isinstance(attr_value, (list, set)) else attr_value.get('values', [])
                        for idx, val in enumerate(values):
                            value_node_id = f"{attr_node_id}_value_{idx}"
                            
                            # Přidáme uzel pro hodnotu
                            value_node = {
                                "id": value_node_id,
                                "name": str(val),
                                "class": "Value",
                                "category": "Value",
                                "status": status
                            }
                            nodes.append(value_node)
                            
                            # Spojení od atributu k hodnotě
                            value_link = {
                                "source": attr_node_id,
                                "target": value_node_id,
                                "type": "VALUE",
                                "status": status
                            }
                            links.append(value_link)
                    else:
                        # Pro jednoduché hodnoty přidáme hodnotu přímo do uzlu atributu
                        attr_node["value_display"] = str(attr_value)
    
    # Přidáme všechny třídy jako uzly
    for class_name in bmw_categories + engine_categories + transmission_categories + drive_categories:
        # Pokud už třída existuje jako uzel, přeskočíme ji
        if any(node["name"] == class_name for node in nodes):
            continue
        
        # Určíme kategorii třídy
        category = get_node_category(class_name, class_name)
        
        # Určíme status třídy (třídy existují v obou modelech)
        status = "common"
        
        # Vytvoříme uzel pro třídu
        node = {
            "id": class_name,
            "name": class_name,
            "class": class_name,
            "category": category,
            "attributes": {},
            "status": status
        }
        
        nodes.append(node)
    
    # Zpracování spojení z obou modelů
    all_link_keys = set(links_a.keys()) | set(links_b.keys())
    
    print(f"Total links for visualization: {len(all_link_keys)}")
    
    for link_key in all_link_keys:
        source, target, link_type = link_key
        
        # Určíme, zda je spojení v modelu A, B nebo v obou
        status = "common" if link_key in links_a and link_key in links_b else \
                "only_in_a" if link_key in links_a else "only_in_b"
        
        # Vytvoříme spojení
        link_data = {
            "source": source,
            "target": target,
            "type": link_type,
            "status": status  # Přidáme status pro vizualizaci
        }
        
        links.append(link_data)
    
    print(f"Generated visualization with {len(nodes)} nodes and {len(links)} links")
    
    return {
        "nodes": nodes,
        "links": links
    }

def get_timestamp():
    """
    Vráti aktuálny časový údaj vo formáte vhodnom pre identifikáciu snímok histórie.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Inicializácia aplikácie
@app.on_event("startup")
async def startup_event():
    """
    Inicializácia aplikácie pri spustení.
    
    Inicializuje klasifikačný strom a ďalšie globálne premenné.
    """
    global learner, classification_tree, tracker, current_model, training_history, saved_models, dataset_examples
    
    # Inicializácia prázdnych kolekcií
    current_model = None
    training_history = []
    saved_models = []
    dataset_examples = []
    
    # Inicializácia klasifikačného stromu
    initialize_classification_tree()
    
    # Vytvoríme tracker pre sledovanie aplikácie heuristík
    tracker = HeuristicTracker()
    
    # Inicializujeme learner s klasifikačným stromom
    learner = WinstonLearner(classification_tree)
    
    # Vytvoríme proxy objekt, ktorý sleduje aplikáciu heuristík
    learner = track_winston_learner(learner, tracker)
    
    print(f"Aplikácia bola inicializovaná.")

# API endpointy
@app.get("/")
async def root():
    """Základný endpoint pre kontrolu, či API beží."""
    return {"message": "PL1 Learning System API is running"}

@app.post("/api/upload-dataset")
async def upload_dataset(examples: List[PL1Example]):
    """Nahrá dataset príkladov vo formáte PL1."""
    global dataset_examples
    
    try:
        # Zachováme informácie o použitých príkladoch
        used_examples = {ex["id"]: ex.get("used_in_training", False) for ex in dataset_examples}
        
        # Vytvoríme nový dataset s novými príkladmi
        new_dataset = []
        
        print(f"Received {len(examples)} examples for upload")
        
        # Spracuj každý príklad
        for i, example in enumerate(examples):
            try:
                print(f"Processing example {i+1}: {example.name}")
                print(f"Formula: {example.formula}")
                print(f"Is positive: {example.is_positive}")
                
                # Skontroluj, či formula nie je prázdna
                if not example.formula or not example.formula.strip():
                    return JSONResponse(
                        status_code=400,
                        content={"success": False, "message": f"Príklad {i+1} má prázdnu formulu"}
                    )
                
                # Parsuj formulu
                try:
                    formula = parse_pl1_formula(example.formula)
                    
                    # Vytvor model z formuly
                    model = formula_to_model(formula)
                    
                    # Zisti, či príklad už existuje v datasete a použitie z použitých príkladov
                    is_used = used_examples.get(i, False)
                    
                    # Pridaj do datasetu
                    new_dataset.append({
                        "id": i,
                        "formula": example.formula,
                        "parsed_formula": formula,
                        "model": model.to_dict(),  # Ulož model ako slovník
                        "is_positive": example.is_positive,
                        "name": example.name or f"Example {i+1}",
                        "used_in_training": is_used
                    })
                    print(f"Example {i+1} processed successfully")
                except Exception as parse_error:
                    print(f"Error parsing example {i+1}: {str(parse_error)}")
                    traceback.print_exc()
                    return JSONResponse(
                        status_code=400,
                        content={"success": False, "message": f"Chyba pri parsovaní príkladu {i+1}: {str(parse_error)}"}
                    )
            except Exception as e:
                print(f"Unexpected error processing example {i+1}: {str(e)}")
                traceback.print_exc()
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": f"Neočakávaná chyba pri spracovaní príkladu {i+1}: {str(e)}"}
                )
        
        # Aktualizuj globálny dataset
        dataset_examples = new_dataset
        
        return {"success": True, "message": f"Dataset s {len(examples)} príkladmi bol úspešne nahraný."}
    
    except Exception as e:
        print(f"Unexpected error in upload_dataset: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chyba pri nahrávaní datasetu: {str(e)}")

@app.get("/api/dataset")
async def get_dataset():
    """Vráti všetky príklady v datasete."""
    global dataset_examples, training_history
    
    examples_to_return = []
    
    # Zlep výpis pre debugging
    print(f"GET /api/dataset: {len(dataset_examples)} examples available")
    used_count = sum(1 for ex in dataset_examples if ex.get("used_in_training", False))
    print(f"Currently marked as used: {used_count} examples")
    
    # Zbierame všetky ID z tréningovej histórie
    used_example_ids = set()
    
    for entry in training_history:
        if "example_id" in entry:
            used_example_ids.add(entry["example_id"])
            print(f"Found example_id in history: {entry['example_id']}")
        if "negative_ids" in entry and isinstance(entry["negative_ids"], list):
            for neg_id in entry["negative_ids"]:
                used_example_ids.add(neg_id)
                print(f"Found negative_id in history: {neg_id}")
    
    print(f"Total IDs found in training history: {len(used_example_ids)}")
    
    # Vytvor zoznam príkladov pre odpoveď
    for example in dataset_examples:
        # Skontrolujeme známy stav aj históriu
        is_used = example["used_in_training"] or example["id"] in used_example_ids
        
        examples_to_return.append({
            "id": example["id"],
            "formula": example["formula"],
            "is_positive": example["is_positive"],
            "name": example["name"],
            "used_in_training": is_used
        })
        
        # Aktualizujeme stav v globálnych dátach
        if is_used and not example["used_in_training"]:
            print(f"Updating example {example['id']} as used based on history")
            example["used_in_training"] = True
    
    return {"examples": examples_to_return}

# Trieda pre evidenciu použitých heuristík
class HeuristicTracker:
    def __init__(self):
        self.heuristics = []
    
    def add_heuristic(self, name, description, example_id=None, details=None):
        self.heuristics.append({
            "name": name,
            "description": description,
            "example_id": example_id,
            "details": details or {}
        })
    
    def get_all(self):
        return self.heuristics

def track_winston_learner(original_learner, tracker):
    """
    Vytvorí proxy objekt, ktorý zachytáva a zaznamenáva heuristiky aplikované v learnerovi.
    """
    global classification_tree
    
    class WinstonLearnerProxy:
        def __init__(self, original_learner, tracker):
            self.original_learner = original_learner
            self.tracker = tracker
            self.last_applied_heuristic = None
            self.classification_tree = classification_tree
            self.debug_enabled = True
            self.applied_heuristics = []
            
            # Kontrola, či klasifikačný strom obsahuje údaje
            parent_relations = len(self.classification_tree.parent_map)
            print(f"[WinstonLearnerProxy] Klasifikačný strom obsahuje {parent_relations} vzťahov rodič-dieťa.")
        
            # Vypíšeme niekoľko vzťahov pre kontrolu
            count = 0
            for child, parent in self.classification_tree.parent_map.items():
                print(f"[WinstonLearnerProxy] Vzťah: {child} -> {parent or 'ROOT'}")
                count += 1
                if count >= 5:  # Obmedzíme výpis len na niekoľko prvých vzťahov
                    print(f"[WinstonLearnerProxy] ... a ďalších {parent_relations - count} vzťahov.")
                    break
        
        def _debug_log(self, message):
            """Debugovacie logovanie pre sledovanie priebehu algoritmu."""
            print(f"[WinstonLearnerProxy] {message}")
            
        def _similar_formulas(self, formula1, formula2):
            """
            Compares two formulas for similarity, ignoring whitespace and order differences.
            """
            # Remove whitespace and normalize
            f1 = ''.join(formula1.split())
            f2 = ''.join(formula2.split())
            
            # If identical after whitespace removal, return True
            if f1 == f2:
                return True
                
            # For more complex comparison, we could split by ∧ and check predicate by predicate
            # but this simple check should catch many cases
            return False
        
        def update_model(self, current_model, example, example_type, example_id=None):
            """
            Aktualizuje model podľa dodaného príkladu.
            
            Args:
                current_model: Aktuálny model
                example: Príklad na spracovanie
                example_type: Typ príkladu ("first_positive", "positive", "negative")
                example_id: ID príkladu (voliteľný parameter)
                
            Returns:
                Aktualizovaný model
            """
            self._debug_log(f"Volám update_model s typom príkladu: {example_type}, example_id: {example_id}")
            
            # Ak sme dostali example_id ako parameter, použijeme ho
            # a nebudeme hľadať príklad podľa formuly
            if example_id is None:
                # Toto je pôvodná logika pre hľadanie príkladu podľa formuly
                # Skúsime nájsť príklad v dataset_examples podľa formuly
                if hasattr(example, 'to_formula'):
                    example_formula = example.to_formula()
                    print(f"\nDEBUG: Looking for matching example with formula: {example_formula[:50]}...")
                    print(f"DEBUG: Dataset examples count: {len(dataset_examples)}")
                    
                    # Print first 5 formulas from dataset for comparison
                    for i, ex in enumerate(dataset_examples[:5]):
                        print(f"DEBUG: Dataset example {i} formula: {ex['formula'][:50]}...")
                    
                    matching_example = next((e for e in dataset_examples if e["formula"] == example_formula), None)
                    
                    if matching_example:
                        example_id = matching_example["id"]
                        self._debug_log(f"Našiel som príklad s ID: {example_id} podľa formuly")
                    else:
                        print("DEBUG: No matching example found by exact formula comparison")
                        
                        # Try a more flexible match
                        for e in dataset_examples:
                            if self._similar_formulas(e["formula"], example_formula):
                                example_id = e["id"]
                                print(f"DEBUG: Found similar formula match with ID: {example_id}")
                                break
            
            # Zavolať originálnu metódu
            if example_type == "first_positive":
                # Pre prvý pozitívny príklad použijeme len _add_missing_objects
                self.original_learner.applied_heuristics = []
                result = self.original_learner._add_missing_objects(current_model.copy(), example)
            elif example_type == "positive":
                # Pre pozitívny príklad použijeme GENERALIZE heuristiky
                result = current_model.copy()
                
                # Resetujeme heuristiky pre tento príklad
                self.original_learner.applied_heuristics = []
                
                # Volanie jednotlivých metód
                result = self.original_learner._check_consistency(result, example)
                result = self.original_learner._apply_climb_tree(result, example)
                result = self.original_learner._apply_close_interval(result, example)
                result = self.original_learner._apply_enlarge_set(result, example)
                result = self.original_learner._apply_drop_link(result, example)
            elif example_type == "negative":
                # Pre negatívny príklad použijeme SPECIALIZE heuristiky
                result = current_model.copy()
                
                # Resetujeme heuristiky pre tento príklad
                self.original_learner.applied_heuristics = []
                
                # Volanie jednotlivých metód
                result = self.original_learner._apply_require_link(result, example)
                result = self.original_learner._apply_forbid_link(result, example)
            else:
                # Neočakávaný typ príkladu
                raise ValueError(f"Neplatný typ príkladu: {example_type}")
            
            # Získame aplikované heuristiky
            self.applied_heuristics = self.original_learner.applied_heuristics
            
            # Logujeme aplikované heuristiky
            if self.applied_heuristics:
                self.last_applied_heuristic = self.applied_heuristics[-1]
                
                # Mapovanie názvov heuristík na užívateľsky zrozumiteľné popisky
                heuristic_descriptions = {
                    "require_link": "Heuristika REQUIRE-LINK - Identifikácia spojení, ktoré musia byť prítomné",
                    "forbid_link": "Heuristika FORBID-LINK - Identifikácia spojení, ktoré nesmú byť prítomné",
                    "drop_link": "Heuristika DROP-LINK - Eliminácia nepotrebných spojení",
                    "climb_tree": "Heuristika CLIMB-TREE - Generalizácia hľadaním spoločných predkov",
                    "enlarge_set": "Heuristika ENLARGE-SET - Vytváranie zjednotení pre funkčne ekvivalentné komponenty",
                    "close_interval": "Heuristika CLOSE-INTERVAL - Spracovanie numerických atribútov zúžením intervalov",
                    "add_object": "Heuristika ADD-OBJECT - Pridanie nového objektu do modelu",
                    "add_link": "Heuristika ADD-LINK - Pridanie nového spojenia do modelu"
                }
                
                # Základné informácie o zmene
                details = {
                    "changes_made": len(result.links) - len(current_model.links)
                }
                
                # Logujeme počet objektov, ak sú k dispozícii
                if hasattr(example, 'objects'):
                    details["example_objects"] = len(example.objects)
                
                # Pre každú aplikovanú heuristiku pridáme záznam (bez duplicít)
                processed_heuristics = set()
                for heuristic_name in self.applied_heuristics:
                    if heuristic_name in processed_heuristics:
                        continue
                    processed_heuristics.add(heuristic_name)
                    self._debug_log(f"Pridávam heuristiku {heuristic_name} pre príklad {example_id}")
                    self.tracker.add_heuristic(
                        heuristic_name,
                        heuristic_descriptions.get(heuristic_name, f"Heuristika {heuristic_name.upper()}"),
                        example_id=example_id,
                        details=details
                    )
            
            # Odstránenie duplicitných spojení pred vrátením modelu
            removed_count = result.remove_duplicate_links()
            if removed_count > 0:
                self._debug_log(f"Odstránených {removed_count} duplicitných spojení z výsledného modelu")
            
            return result
        
        # Delegujeme všetky ostatné metódy na originálny learner
        def __getattr__(self, name):
            return getattr(self.original_learner, name)
    
    return WinstonLearnerProxy(original_learner, tracker)

@app.post("/api/train")
async def train_model(training_request: TrainingRequest):
    """
    Trénuje model na základě vybraného príkladu alebo viacerých príkladov (batch).
    
    Príklady sú spracované INKREMENTÁLNE - postupne jeden po druhom v poradí ich ID.
    Každý príklad je spracovaný PRÁVE RAZ pri danom trénovacom behu, bez opätovného prehodnocovania 
    predchádzajúcich príkladov (čo zodpovedá pôvodnému Winstonovmu algoritmu).
    
    Ak príklad už bol použitý na trénovanie, je preskočený (pokiaľ nie je nastavené retrain_all=True).
    Heuristiky pre príklady zostávajú zachované aj po opätovnom trénovaní.
    
    Args:
        training_request: Požiadavka na trénovanie obsahujúca ID príkladov, ktoré sa majú použiť,
                         alebo nastavenie pre dávkové spracovanie
        
    Returns:
        Výsledok trénovania s informáciami o priebehu
    """
    try:
        global learner, current_model, dataset_examples, tracker
        
        # Poznámka: Už nevymazávame heuristiky pre príklady, ktoré sa trénujú
        # aby ostala zachovaná história aplikovaných heuristík
        
        # Overenie, či máme inicializované potrebné premenné
        if learner is None:
            return TrainingResult(
                success=False,
                message="Chyba: Learner nie je inicializovaný",
                error="Learner nie je inicializovaný"
            )
            
        if dataset_examples is None or len(dataset_examples) == 0:
            return TrainingResult(
                success=False,
                message="Chyba: Dataset neobsahuje žiadne príklady",
                error="Prázdny dataset"
            )
        
        # Ak máme špecifické ID príkladov, použijeme len tie
        if training_request.example_ids and len(training_request.example_ids) > 0:
            # Zoraďujeme príklady podľa ID - toto zabezpečí spracovanie v poradí, ako boli definované v datasete
            examples_to_process = sorted(
                [ex for ex in dataset_examples if ex["id"] in training_request.example_ids],
                key=lambda x: x["id"]
            )
            if not examples_to_process:
                return TrainingResult(
                    success=False,
                    message="Žiadny z vybraných príkladov nebol nájdený",
                    error="Neplatné ID príkladov"
                )
        else:
            # Inak vezmeme všetky nepoužité príklady, zoradené podľa ID
            examples_to_process = sorted(
                [ex for ex in dataset_examples if not ex.get("used_in_training", False)],
                key=lambda x: x["id"]
            )
            if not examples_to_process:
                return TrainingResult(
                    success=False,
                    message="Všetky príklady už boli použité na trénovanie",
                    error="Niet k dispozícii žiadne nepoužité príklady"
                )
        
        # Trénovacie kroky
        steps = []
        processed_count = 0
        batch_count = 0
        
        # Potrebujeme nájsť prvý pozitívny príklad, ak ešte nemáme inicializovaný model
        if current_model is None or not hasattr(current_model, 'objects') or len(current_model.objects) == 0:
            # Nájdeme prvý pozitívny príklad na inicializáciu modelu
            first_positive = next((ex for ex in examples_to_process if ex.get("is_positive", True)), None)
            
            if not first_positive:
                return TrainingResult(
                    success=False,
                    message="Na inicializáciu modelu je potrebný aspoň jeden pozitívny príklad",
                    error="Chýba pozitívny príklad na inicializáciu"
                )
                
            # Presunieme prvý pozitívny príklad na začiatok zoznamu
            examples_to_process.remove(first_positive)
            examples_to_process.insert(0, first_positive)
        
        # Postupne spracujeme všetky príklady v poradí ich ID
        for example in examples_to_process:
            example_id = example["id"]
            
            # Preskočiť príklady, ktoré už boli použité na trénovanie
            # (toto zabezpečí, že príklady sa budú trénovať len raz, bez opätovného prehodnocovania)
            if example.get("used_in_training", False) and not training_request.retrain_all:
                print(f"Preskakujem príklad {example_id}, pretože už bol použitý na trénovanie")
                continue
                
            # Spracuj formulu a vytvor model
            try:
                formula_str = example.get("formula")
                is_positive = example.get("is_positive", True)
                
                if not isinstance(formula_str, str):
                    steps.append(f"Chyba pri spracovaní príkladu {example_id}: formula nie je reťazec")
                    continue
                
                # Sparsujeme formulu a vytvoríme model
                formula = parse_pl1_formula(formula_str)
                
                # Teraz vždy použijeme rovnaký spôsob tvorby modelu bez ohľadu na to, 
                # či je to prvý pozitívny príklad alebo nie
                example_model = formula_to_model(formula)
                
                print(f"\nSpracovávam príklad {example_id} (pozitívny: {is_positive})")
                print(f"Príklad obsahuje {len(example_model.objects)} objektov a {len(example_model.links)} spojení")
                
            except Exception as e:
                steps.append(f"Chyba pri spracovaní príkladu {example_id}: {str(e)}")
                continue
                
            # Aktualizácia modelu na základe typu príkladu
            if current_model is None or not hasattr(current_model, 'objects') or len(current_model.objects) == 0:
                # Prvotná inicializácia modelu pri prvom príklade
                if not is_positive:
                    steps.append(f"Preskakujem negatívny príklad {example_id} - prvý príklad musí byť pozitívny")
                    continue
                    
                print(f"Inicializujem model s prvým príkladom (ID: {example_id})")
                
                # Vytvoríme nový prázdny model a použijeme ho na inicializáciu
                empty_model = Model(objects=[], links=[])
                current_model = learner.update_model(empty_model, example_model, "first_positive", example_id=example_id)
                
                # Odstránenie duplicitných spojení
                removed_duplicates = current_model.remove_duplicate_links()
                if removed_duplicates > 0:
                    print(f"Odstránených {removed_duplicates} duplicitných spojení")
                
                # Debug výpis aktualizovaného modelu
                print(f"Aktualizovaný model po inicializácii: {len(current_model.objects)} objektov a {len(current_model.links)} spojení")
                for obj in current_model.objects:
                    print(f"  Objekt: {obj.name} ({obj.class_name})")
                    
                step_message = f"Model inicializovaný s príkladom {example_id}"
            elif is_positive:
                # Spracovanie pozitívneho príkladu
                print(f"Aktualizujem model s pozitívnym príkladom {example_id}")
                current_model = learner.update_model(current_model, example_model, "positive", example_id=example_id)
                
                # Odstránenie duplicitných spojení
                removed_duplicates = current_model.remove_duplicate_links()
                if removed_duplicates > 0:
                    print(f"Odstránených {removed_duplicates} duplicitných spojení")
                
                print(f"Aktualizovaný model: {len(current_model.objects)} objektov a {len(current_model.links)} spojení")
                step_message = f"Model aktualizovaný s pozitívnym príkladom {example_id}"
            else:
                # Spracovanie negatívneho príkladu
                print(f"Aktualizujem model s negatívnym príkladom {example_id}")
                current_model = learner.update_model(current_model, example_model, "negative", example_id=example_id)
                
                # Odstránenie duplicitných spojení
                removed_duplicates = current_model.remove_duplicate_links()
                if removed_duplicates > 0:
                    print(f"Odstránených {removed_duplicates} duplicitných spojení")
                
                print(f"Aktualizovaný model: {len(current_model.objects)} objektov a {len(current_model.links)} spojení")
                step_message = f"Model aktualizovaný s negatívnym príkladom {example_id}"
                
            # Označíme príklad ako použitý
            example["used_in_training"] = True
            print(f"Príklad {example_id} označený ako použitý")
                    
            steps.append(step_message)
            processed_count += 1
            
            # Ak sme dosiahli batch_size, aktualizujeme históriu
            if processed_count % training_request.batch_size == 0:
                batch_count += 1
                
                # Aktualizujeme vizualizáciu a históriu po každej dávke
                visualization = generate_model_visualization(current_model)
                save_model_to_history(
                    current_model,
                    visualization,
                    steps[-training_request.batch_size:],
                    training_request.batch_size
                )
        
        # Získanie formuly a pravidiel modelu pre frontend
        model_formula = current_model.to_formula()
        model_rules = current_model.extract_model_rules() if hasattr(current_model, 'extract_model_rules') else {}
        
        # Vytvorenie vizualizácie modelu
        visualization = generate_model_visualization(current_model)
        
        # Uloženie stavu modelu do histórie pre zvyšné príklady
        remaining_examples = processed_count % training_request.batch_size
        if remaining_examples > 0:
            save_model_to_history(
                current_model,
                visualization,
                steps[-remaining_examples:],
                remaining_examples
            )
            batch_count += 1
        
        print(f"Trénovanie úspešné, spracovaných {processed_count} príkladov, hypotéza: {model_formula}")
        
        # Zapíšeme aktuálnu hypotézu
        model_hypothesis = current_model.to_formula() if current_model else ""
        
        # Debug print pre kontrolu heuristík
        print(f"\n--- DEBUG HEURISTIKY ---")
        print(f"Počet heuristík v trackeri: {len(tracker.heuristics)}")
        for h in tracker.heuristics:
            print(f" - {h.get('name')}: {h.get('description')} pre príklad {h.get('example_id')}")
        print(f"------------------------\n")
        
        print(f"Inkrementálne trénovanie dokončené - každý príklad bol spracovaný iba raz v poradí ID")
        print(f"Celkový počet spracovaných príkladov: {processed_count}")
        
        return TrainingResult(
            success=True,
            message=f"Model úspešne natrénovaný s {processed_count} príkladmi",
            model_state=current_model.to_dict(),
            steps=steps,
            batch_count=batch_count,
            processed_examples=processed_count,
            training_mode="batch",
            model_formula=model_formula,  # Hypotéza pre frontend
            model_visualization=visualization, # Vizualizácia pre frontend
            model_hypothesis=model_hypothesis,  # Pridaná natrénovaná formula
            model_rules=model_rules  # Pridané extrahované pravidlá 
        )
        
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"Chyba pri trénovaní: {str(e)}")
        print(tb)
        
        return TrainingResult(
            success=False,
            message=f"Neočakávaná chyba pri trénovaní: {str(e)}",
            error=str(e),
            steps=[]
        )

@app.post("/api/compare")
async def compare_example_endpoint(example: PL1Example):
    """
    Validuje PL1 příklad proti aktuálnímu modelu se zaměřením na konkrétní model auta.
    
    Args:
        example: PL1 příklad k validaci
        
    Returns:
        Výsledek validace s konkrétními vysvětleními pro daný model auta
    """
    global current_model
    
    if not example:
        raise HTTPException(status_code=400, detail="Chybí příklad k validaci")
    
    if not current_model or not current_model.objects:
        raise HTTPException(status_code=400, detail="Model není natrénován")
    
    try:
        # Validace příkladu s parametrom validate_attributes
        validate_attrs = example.validate_attributes if example.validate_attributes is not None else True
        result = compare_example(current_model, example.formula, validate_attrs)
        
        # Přidáme formuli modelu pro frontend
        model_formula = current_model.to_formula() if current_model else ""
        
        return {
            "is_valid": result["is_valid"],
            "model_type": result["model_type"],
            "violations": result["violations"],
            "satisfied_rules": result["satisfied_rules"],
            "formula": result["formula"],
            "validate_attributes": result.get("validate_attributes", validate_attrs),
            "allowed_alternatives": result.get("allowed_alternatives", {}),
            "categorized_violations": result.get("categorized_violations", {}),
            "highlighted_formula": result.get("highlighted_formula", {
                "highlighted_formula": model_formula,
                "tokens": []
            }),
            "model_formula": model_formula
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chyba při validaci příkladu: {str(e)}")

@app.get("/api/model")
async def get_model():
    """Vráti aktuálne naučený model vo formáte vhodnom pre vizualizáciu."""
    global current_model
    
    try:
        print(f"GET /api/model: Model má {len(current_model.objects)} objektov a {len(current_model.links)} spojení")
        
        if len(current_model.objects) == 0:
            print("GET /api/model: Model je prázdny, vraciam chybu")
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Model ešte nebol natrénovaný."}
            )
        
        # Vytvor vizualizáciu modelu
        visualization = generate_model_visualization(current_model)
        print(f"GET /api/model: Vytvorená vizualizácia s {len(visualization.get('nodes', []))} uzlami a {len(visualization.get('links', []))} spojeniami")
        
        # Konvertuj model späť do PL1 formuly
        pl1_representation = current_model.to_formula()
        print(f"GET /api/model: Hypotéza: {pl1_representation}")
        
        # Extrahuj identifikačné pravidlá pre modely áut
        model_rules = current_model.extract_model_rules() if hasattr(current_model, 'extract_model_rules') else {}
        
        # Dodatočné informácie o modeli
        model_info = {
            "object_count": len(current_model.objects),
            "link_count": len(current_model.links),
            "objects": [{"name": obj.name, "class": obj.class_name} for obj in current_model.objects]
        }
        
        return {
            "success": True,
            "visualization": visualization,
            "pl1_representation": pl1_representation,
            "model_rules": model_rules,
            "model_info": model_info
        }
    
    except Exception as e:
        print(f"GET /api/model: Chyba: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chyba pri získavaní modelu: {str(e)}")

@app.get("/api/training-history")
async def get_training_history():
    """Vráti históriu trénovania modelu."""
    global dataset_examples, training_history
    
    # Filter len pre aktuálne záznamy histórie
    current_history = [entry for entry in training_history if entry.get("current", True)]
    
    history_with_details = []
    
    for entry in current_history:
        # Získaj typ akcie (kompatibilita s oboma formátmi)
        action_type = entry.get("action") or entry.get("step", "unknown")
        
        # Nájdi detaily príkladu
        example = next((e for e in dataset_examples if e["id"] == entry.get("example_id")), None)
        near_misses = []
        
        # Získaj buď jeden "near_miss" alebo viacero "near_miss_ids"
        if "near_miss_id" in entry:
            near_miss = next((e for e in dataset_examples if e["id"] == entry.get("near_miss_id")), None)
            if near_miss:
                near_misses.append(near_miss)
        elif "near_miss_ids" in entry:
            for near_miss_id in entry.get("near_miss_ids", []):
                near_miss = next((e for e in dataset_examples if e["id"] == near_miss_id), None)
                if near_miss:
                    near_misses.append(near_miss)
        
        history_entry = {
            "step": action_type,  # Jednotný kľúč "step" pre frontend
            "timestamp": entry.get("timestamp", ""),
            "example": {
                "id": example["id"],
                "name": example["name"],
                "is_positive": example["is_positive"]
            } if example else None
        }
        
        # Pridaj informácie o negative príkladoch
        if near_misses:
                history_entry["near_misses"] = [
                    {
                        "id": nm["id"],
                        "name": nm["name"],
                        "is_positive": nm["is_positive"]
                } for nm in near_misses
            ]
        
        history_with_details.append(history_entry)
    
    return {"history": history_with_details}

@app.post("/api/model/reset")
async def reset_model():
    """Resetuje naučený model a históriu trénovania."""
    global current_model, training_history, model_history, current_history_index, dataset_examples, tracker
    
    # Resetujeme model
    current_model = Model(objects=[], links=[])
    
    # Kompletně vymažeme historii tréninku místo pouhého označení jako neaktuální
    training_history = []
    
    # Resetujeme příznaky used_in_training ve všech příkladech
    for example in dataset_examples:
        example["used_in_training"] = False
    
    # Vymažeme historii modelu
    model_history = []
    current_history_index = -1
    
    # Resetujeme log heuristík
    if tracker:
        tracker.heuristics = []
    
    return {"success": True, "message": "Model, historie a log heuristik byly úplně resetovány."}



@app.get("/api/model-history")
async def get_model_history():
    """Vráti históriu stavov modelu pre navigáciu späť/vpred."""
    
    global model_history, current_history_index
    
    history_entries = []
    # Zozbieraj informácie o všetkých záznamoch v histórii
    for i, entry in enumerate(model_history):
        entry_info = {
            "index": i,
            "timestamp": entry.get("timestamp", ""),
            "used_examples_count": entry.get("used_examples_count", 0),
            "training_steps": len(entry.get("training_steps", [])) if entry.get("training_steps") else 0
        }
        history_entries.append(entry_info)
    
    return {
        "success": True,
        "current_index": current_history_index,
        "history_entries": history_entries,
        "total_entries": len(model_history)
    }
@app.post("/api/model/history/step_back")
async def step_back_in_history():
    """Krok zpět v historii modelu."""
    global current_model, model_history, current_history_index, dataset_examples
    
    # Kontrola, zda můžeme jít zpět
    if current_history_index <= 0 or len(model_history) == 0:
        return {
            "success": False,
            "message": "Nelze jít zpět - jsme na začátku historie nebo historie je prázdná.",
            "current_index": current_history_index
        }
    
    # Posun zpět v historii
    current_history_index -= 1
    
    # Obnovení modelu z historie
    history_entry = model_history[current_history_index]
    if history_entry.get("model_state"):
        current_model = Model.from_dict(history_entry["model_state"])
    
    # Obnovení informací o použitých příkladech
    used_example_ids = history_entry.get("used_example_ids", [])
    
    # Resetování příznaků used_in_training pro všechny příklady
    for example in dataset_examples:
        example["used_in_training"] = example["id"] in used_example_ids
    
    # Získání vizualizace pro frontend
    visualization = generate_model_visualization(current_model)
    
    # Získaní trénovanej formuly
    model_hypothesis = current_model.to_formula() if current_model else None

    # Extrahuj identifikačné pravidlá pre modely áut
    model_rules = current_model.extract_model_rules() if current_model else {}
    
    return {
        "success": True,
        "message": f"Model obnoven na stav z historie (index {current_history_index}).",
        "current_index": current_history_index,
        "model_visualization": visualization,
        "training_steps": history_entry.get("training_steps", []),
        "used_examples_count": history_entry.get("used_examples_count", 0),
        "used_example_ids": used_example_ids,  # Pridaný zoznam ID použitých príkladov
        "model_hypothesis": model_hypothesis,  # Pridaná natrénovaná formula
        "model_rules": model_rules,  # Pridané extrahované pravidlá 
        "model_updated": True  # Signalizácia, že model bol aktualizovaný
    }

@app.post("/api/model/history/step_forward")
async def step_forward_in_history():
    """Krok vpřed v historii modelu."""
    global current_model, model_history, current_history_index, dataset_examples
    
    # Kontrola, zda můžeme jít vpřed
    if current_history_index >= len(model_history) - 1:
        return {
            "success": False,
            "message": "Nelze jít vpřed - jsme na konci historie.",
            "current_index": current_history_index
        }
    
    # Posun vpřed v historii
    current_history_index += 1
    
    # Obnovení modelu z historie
    history_entry = model_history[current_history_index]
    if history_entry.get("model_state"):
        current_model = Model.from_dict(history_entry["model_state"])
    
    # Obnovení informací o použitých příkladech
    used_example_ids = history_entry.get("used_example_ids", [])
    
    # Resetování příznaků used_in_training pro všechny příklady
    for example in dataset_examples:
        example["used_in_training"] = example["id"] in used_example_ids
    
    # Získání vizualizace pro frontend
    visualization = generate_model_visualization(current_model)
    
    # Získaní trénovanej formuly
    model_hypothesis = current_model.to_formula() if current_model else None
    
    # Extrahuj identifikačné pravidlá pre modely áut
    model_rules = current_model.extract_model_rules() if current_model else {}
    
    return {
        "success": True,
        "message": f"Model posunutý na stav z histórie (index {current_history_index}).",
        "current_index": current_history_index,
        "model_visualization": visualization,
        "training_steps": history_entry.get("training_steps", []),
        "used_examples_count": history_entry.get("used_examples_count", 0),
        "used_example_ids": used_example_ids,  # Pridaný zoznam ID použitých príkladov
        "model_hypothesis": model_hypothesis,  # Pridaná natrénovaná formula
        "model_rules": model_rules,  # Pridané extrahované pravidlá 
        "model_updated": True  # Signalizácia, že model bol aktualizovaný
    }


@app.get("/api/model-status")
async def get_model_status():
    """Vráti informácie o aktuálnom stave modelu a trénovania"""
    global current_model, dataset_examples, training_history
    
    # Počty príkladov
    used_examples = sum(1 for example in dataset_examples if example.get("used_in_training", False))
    total_positive = sum(1 for example in dataset_examples if example.get("is_positive", True))
    total_negative = sum(1 for example in dataset_examples if not example.get("is_positive", True))
    positive_used = sum(1 for example in dataset_examples if example.get("used_in_training", False) and example.get("is_positive", True))
    negative_used = sum(1 for example in dataset_examples if example.get("used_in_training", False) and not example.get("is_positive", True))
    
    # Mód trénovania
    training_mode = "none"
    
    # Kontrola či model existuje
    if current_model is None:
        print("Model status: Model nie je inicializovaný")
        # Vrátime predvolené hodnoty pre neinicializovaný model
        return {
            "object_count": 0,
            "link_count": 0,
            "total_examples": len(dataset_examples),
            "used_examples": used_examples,
            "positive_examples": {
                "used": positive_used,
                "total": total_positive
            },
            "negative_examples": {
                "used": negative_used,
                "total": total_negative
            },
            "training_mode": training_mode,
            "training_steps": len(training_history),
            "current_hypothesis": "",
            "has_model": False
        }
    
    if len(current_model.objects) > 0:
        training_mode = "single"  # Používame len jeden mód - sekvenčné trénovanie
    
    # Počet krokov trénovania
    training_steps = len(training_history)
    
    # Hypotéza modelu
    pl1_representation = ""
    if len(current_model.objects) > 0:
        pl1_representation = current_model.to_formula()
    
    print(f"Model status: {len(current_model.objects)} objects, {len(current_model.links)} links")
    print(f"Examples: {used_examples}/{len(dataset_examples)} used total")
    print(f"Positive: {positive_used}/{total_positive}, Negative: {negative_used}/{total_negative}")
    print(f"Current hypothesis: {pl1_representation}")
        
    return {
        "object_count": len(current_model.objects),
        "link_count": len(current_model.links),
        "total_examples": len(dataset_examples),
        "used_examples": used_examples,
        "positive_examples": {
            "used": positive_used,
            "total": total_positive
        },
        "negative_examples": {
            "used": negative_used,
            "total": total_negative
        },
        "training_mode": training_mode,
        "training_steps": training_steps,
        "current_hypothesis": pl1_representation,
        "has_model": len(current_model.objects) > 0
    }

@app.post("/api/analyze-example")
async def analyze_example(example_id: int):
    """Analyzuje konkrétny príklad a poskytne detailné informácie o jeho štruktúre."""
    global dataset_examples, classification_tree
    
    try:
        # Nájdi príklad v datasete
        example = next((e for e in dataset_examples if e["id"] == example_id), None)
        if not example:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": f"Príklad s ID {example_id} nebol nájdený."}
            )
        
        # Konvertuj formulu na model
        print(f"Analyzing example {example_id}: {example['name']}")
        print(f"Formula: {example['formula']}")
        
        try:
            model = formula_to_model(example["parsed_formula"])
            
            # Zozbieraj detailné informácie o modeli
            objects_info = []
            for obj in model.objects:
                # Získaj informácie o nadtriedach
                superclasses = []
                current_class = obj.class_name
                while current_class:
                    parent = classification_tree.get_parent(current_class)
                    if parent and parent != current_class:
                        superclasses.append(parent)
                        current_class = parent
                    else:
                        break
                
                objects_info.append({
                    "name": obj.name,
                    "class": obj.class_name,
                    "superclasses": superclasses,
                    "attributes": obj.attributes if hasattr(obj, "attributes") and obj.attributes else {}
                })
            
            # Informácie o spojeniach
            links_info = []
            for link in model.links:
                links_info.append({
                    "source": link.source,
                    "target": link.target,
                    "type": str(link.link_type)
                })
            
            # Analýza chýbajúcich kľúčových komponentov
            key_components_analysis = {}
            
            # Často potrebné komponenty v autách, ktoré môžu chýbať v negatívnych príkladoch
            common_car_components = ["motor", "prevodovka", "kolesá", "karoséria", "volant", "sedadlá"]
            
            # Kontrola, či príklad obsahuje tieto komponenty
            existing_components = [obj.name.lower() for obj in model.objects]
            for component in common_car_components:
                component_found = any(component in obj_name for obj_name in existing_components)
                key_components_analysis[component] = component_found
            
            return {
                "success": True,
                "example_id": example_id,
                "name": example["name"],
                "is_positive": example["is_positive"],
                "formula": example["formula"],
                "model_info": {
                    "object_count": len(model.objects),
                    "link_count": len(model.links),
                    "objects": objects_info,
                    "links": links_info,
                    "key_components_analysis": key_components_analysis
                }
            }
        except Exception as model_error:
            print(f"Error analyzing example: {str(model_error)}")
            traceback.print_exc()
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": f"Chyba pri analýze príkladu: {str(model_error)}",
                    "example_id": example_id,
                    "name": example["name"],
                    "formula": example["formula"]
                }
            )
    except Exception as e:
        print(f"Error accessing example: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Chyba pri prístupe k príkladu: {str(e)}"}
        )

# Funkcia pre uloženie stavu modelu do historie
def save_model_to_history(model_state, visualization=None, steps=None, examples_count=0):
    """
    Uloží aktuálny stav modelu do histórie pre neskoršie použitie.
    
    Args:
        model_state: Model alebo jeho slovníková reprezentácia
        visualization: Vizualizácia modelu pre frontend
        steps: Kroky trénovania (popis akcií)
        examples_count: Počet spracovaných príkladov
    """
    global model_history, current_history_index, dataset_examples, MAX_HISTORY_SIZE
    
    # Pokud jsme se vrátili zpět a pak děláme novou změnu, odstraníme historii vpřed
    if current_history_index < len(model_history) - 1:
        model_history = model_history[:current_history_index+1]
    
    # Získáme seznam ID příkladů, které jsou aktuálně označeny jako použité
    used_example_ids = [example["id"] for example in dataset_examples if example.get("used_in_training", False)]
    
    # Kontrola, či model_state je už slovník alebo ho treba konvertovať
    model_state_dict = model_state
    if hasattr(model_state, 'to_dict') and callable(getattr(model_state, 'to_dict')):
        model_state_dict = model_state.to_dict()
    
    # Ak nemáme vizualizáciu, vytvoríme ju
    if visualization is None and model_state is not None:
        if isinstance(model_state, dict):
            model_obj = Model.from_dict(model_state)
            visualization = generate_model_visualization(model_obj)
        else:
            visualization = generate_model_visualization(model_state)
    
    # Získanie aktuálnej hypotézy
    hypothesis = None
    if model_state is not None:
        if isinstance(model_state, dict):
            model_obj = Model.from_dict(model_state)
            hypothesis = model_obj.to_formula()
        elif hasattr(model_state, 'to_formula'):
            hypothesis = model_state.to_formula()
    
    print(f"Ukladám model do histórie: {len(model_state_dict.get('objects', []))} objektov, {len(model_state_dict.get('links', []))} spojení")
    if hypothesis:
        print(f"Hypotéza: {hypothesis}")
    
    # Uložíme aktuální stav modelu včetně seznamu použitých příkladů
    model_history.append({
        "model_state": model_state_dict,
        "model_visualization": visualization,
        "training_steps": steps,
        "used_examples_count": examples_count,
        "used_example_ids": used_example_ids,  # Ukládáme i ID použitých příkladů
        "timestamp": datetime.now().isoformat(),
        "hypothesis": hypothesis  # Pridáme aj hypotézu
    })
    
    # Obmedzíme veľkosť histórie
    if len(model_history) > MAX_HISTORY_SIZE:
        # Odstraníme najstarší záznam a upravíme current_history_index
        model_history.pop(0)
        current_history_index = max(0, current_history_index - 1)
    else:
        # Aktualizujeme index
        current_history_index = len(model_history) - 1
    
    print(f"Saved model to history at index {current_history_index} with {len(used_example_ids)} used examples (history size: {len(model_history)}/{MAX_HISTORY_SIZE})")
    return current_history_index

# Nový endpoint pre získanie informácií o modeli a histórii
@app.get("/api/model/info")
async def model_info():
    """Vráti informácie o modeli a histórii pre frontend."""
    
    global model_history, current_history_index
    
    # Vytvorenie rovnakej odpovede ako v prípade /api/model-history
    history_entries = []
    for i, entry in enumerate(model_history):
        entry_info = {
            "index": i,
            "timestamp": entry.get("timestamp", ""),
            "used_examples_count": entry.get("used_examples_count", 0),
            "training_steps": len(entry.get("training_steps", [])) if entry.get("training_steps") else 0
        }
        history_entries.append(entry_info)
    
    # Vrátime históriu v očakávanom formáte
    return {
        "success": True,
        "history": {
            "current_index": current_history_index,
            "total_entries": len(model_history),
            "entries": history_entries
        }
    }

# Seznam uložených modelů/hypotéz
saved_models = []

@app.post("/api/save-model")
async def save_current_model(model_data: dict):
    """Uloží aktuální model pod zadaným názvem."""
    global current_model, saved_models
    
    if not current_model or not current_model.objects:
        raise HTTPException(status_code=400, detail="Model není natrénován")
    
    name = model_data.get("name", f"Model {len(saved_models) + 1}")
    
    # Uložení modelu
    saved_model = {
        "id": len(saved_models) + 1,
        "name": name,
        "timestamp": datetime.now().isoformat(),
        "model_state": current_model.to_dict(),
        "pl1_representation": current_model.to_formula()
    }
    
    saved_models.append(saved_model)
    
    return {
        "success": True,
        "message": f"Model byl úspěšně uložen jako '{name}'",
        "model_id": saved_model["id"]
    }

@app.get("/api/saved-models")
async def get_saved_models():
    """Vrátí seznam uložených modelů."""
    global saved_models
    
    # Vrátíme zjednodušenou verzi bez velkých dat
    models_info = [
        {
            "id": model["id"],
            "name": model["name"],
            "timestamp": model["timestamp"]
        }
        for model in saved_models
    ]
    
    return {
        "success": True,
        "models": models_info
    }

@app.get("/api/saved-model/{model_id}")
async def get_saved_model(model_id: int):
    """Vrátí konkrétní uložený model."""
    global saved_models
    
    model = next((m for m in saved_models if m["id"] == model_id), None)
    
    if not model:
        raise HTTPException(status_code=404, detail=f"Model s ID {model_id} nebyl nalezen")
    
    return {
        "success": True,
        "model": model
    }

class CompareModelsRequest(BaseModel):
    model_a_type: str  # "current" nebo "saved"
    model_a_id: Optional[int] = None  # ID uloženého modelu, pokud model_a_type == "saved"
    model_b_type: str  # "current" nebo "saved"
    model_b_id: Optional[int] = None  # ID uloženého modelu, pokud model_b_type == "saved"

def is_model_trained():
    """Zkontroluje, zda je aktuální model natrénován."""
    global current_model
    return current_model is not None and len(current_model.objects) > 0 and len(current_model.links) > 0

@app.post("/api/compare-models")
async def compare_models(request: CompareModelsRequest):
    """Porovná dva modely na základě požadavku."""
    try:
        # Získání prvního modelu (model_a)
        model_a = None
        model_a_name = None
        if request.model_a_type == "current":
            if not is_model_trained():
                raise HTTPException(status_code=400, detail="Aktuální model není natrénován")
            model_a = current_model
            model_a_name = "Aktuální model"
        elif request.model_a_type == "saved":
            if not request.model_a_id:
                raise HTTPException(status_code=400, detail="Model ID je povinný pro uložený model")
            
            # Use the saved_models list instead of database
            saved_model = next((m for m in saved_models if m["id"] == request.model_a_id), None)
            if not saved_model:
                raise HTTPException(status_code=404, detail="Uložený model nebyl nalezen")
            
            model_a_name = saved_model["name"]
            model_a = Model.from_dict(saved_model["model_state"])
        else:
            raise HTTPException(status_code=400, detail="Neplatný typ modelu A")
        
        # Získání druhého modelu (model_b)
        model_b = None
        model_b_name = None
        if request.model_b_type == "current":
            if not is_model_trained():
                raise HTTPException(status_code=400, detail="Aktuální model není natrénován")
            model_b = current_model
            model_b_name = "Aktuální model"
        elif request.model_b_type == "saved":
            if not request.model_b_id:
                raise HTTPException(status_code=400, detail="Model ID je povinný pro uložený model")
            
            # Use the saved_models list instead of database
            saved_model = next((m for m in saved_models if m["id"] == request.model_b_id), None)
            if not saved_model:
                raise HTTPException(status_code=404, detail="Uložený model nebyl nalezen")
            
            model_b_name = saved_model["name"]
            model_b = Model.from_dict(saved_model["model_state"])
        else:
            raise HTTPException(status_code=400, detail="Neplatný typ modelu B")
        
        # Porovnání modelů
        # Získáme rozdíly objektů
        a_objects = set(obj.name for obj in model_a.objects)
        b_objects = set(obj.name for obj in model_b.objects)
        
        # Porovnání spojení (links)
        a_links = set((link.source, link.link_type, link.target) for link in model_a.links)
        b_links = set((link.source, link.link_type, link.target) for link in model_b.links)
        
        # Formátování výsledků
        result = {
            "success": True,
            "model_a": {
                "name": model_a_name,
                "type": request.model_a_type,
                "id": request.model_a_id if request.model_a_type == "saved" else None,
                "pl1_representation": model_a.to_formula() if model_a else ""
            },
            "model_b": {
                "name": model_b_name,
                "type": request.model_b_type,
                "id": request.model_b_id if request.model_b_type == "saved" else None,
                "pl1_representation": model_b.to_formula() if model_b else ""
            },
            "differences": {
                "objects": {
                    "only_in_a": list(a_objects - b_objects),
                    "only_in_b": list(b_objects - a_objects),
                    "common": list(a_objects & b_objects)
                },
                "links": {
                    "only_in_a": [f"{source} -{link_type}-> {target}" for source, link_type, target in (a_links - b_links)],
                    "only_in_b": [f"{source} -{link_type}-> {target}" for source, link_type, target in (b_links - a_links)],
                    "count_a": len(a_links),
                    "count_b": len(b_links),
                    "common_count": len(a_links & b_links)
                },
                "model_types": {}
            }
        }
        
        # Získáme typy modelů aut z obou modelů
        car_models = set()
        known_car_models = {"BMW", "Series3", "Series5", "Series7", "X5", "X7"}
        
        # Hledáme typy modelů aut v objektech obou modelů
        for obj in model_a.objects:
            if obj.class_name in known_car_models:
                car_models.add(obj.class_name)
                
        for obj in model_b.objects:
            if obj.class_name in known_car_models:
                car_models.add(obj.class_name)
        
        # Pravidla pro jednotlivé typy modelů
        model_type_differences = {}
        
        for car_model in car_models:
            # Získáme pravidla pro daný model
            rules_a = model_a.get_rules_for_model_type(car_model)
            rules_b = model_b.get_rules_for_model_type(car_model)
            
            # Rozdíly mezi pravidly
            model_type_differences[car_model] = {
                "only_in_a": {
                    "must": list(set(rules_a.get("must", [])) - set(rules_b.get("must", []))),
                    "must_not": list(set(rules_a.get("must_not", [])) - set(rules_b.get("must_not", [])))
                },
                "only_in_b": {
                    "must": list(set(rules_b.get("must", [])) - set(rules_a.get("must", []))),
                    "must_not": list(set(rules_b.get("must_not", [])) - set(rules_a.get("must_not", [])))
                },
                "different": {}
            }
        
        result["differences"]["model_types"] = model_type_differences
        
        # Vytvoříme vizualizaci rozdílů
        visualization = generate_difference_visualization(model_a, model_b, model_type_differences)
        result["visualization"] = visualization
        
        # Přidáme statistiky o vizualizaci
        if visualization and "nodes" in visualization and "links" in visualization:
            result["visualization_stats"] = {
                "node_count": len(visualization["nodes"]),
                "link_count": len(visualization["links"]),
                "nodes_only_in_a": len([n for n in visualization["nodes"] if n.get("status") == "only_in_a"]),
                "nodes_only_in_b": len([n for n in visualization["nodes"] if n.get("status") == "only_in_b"]),
                "nodes_common": len([n for n in visualization["nodes"] if n.get("status") == "common"]),
                "links_only_in_a": len([l for l in visualization["links"] if l.get("status") == "only_in_a"]),
                "links_only_in_b": len([l for l in visualization["links"] if l.get("status") == "only_in_b"]),
                "links_common": len([l for l in visualization["links"] if l.get("status") == "common"])
            }
        
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error in compare_models: {str(e)}")
        traceback.print_exc()  # Výpis traceback pro podrobnější informace
        raise HTTPException(status_code=500, detail=f"Chyba při porovnávání modelů: {str(e)}")

@app.get("/api/heuristics/history")
async def get_heuristics_history():
    """
    Vráti históriu heuristík aplikovaných na jednotlivé príklady.
    Zobrazí všetky príklady, ktoré boli použité na trénovanie, vrátane tých z predošlých behov.
    Filtruje ADD-LINK a ADD-OBJECT heuristiky, ktoré sa používajú pri inicializácii.
    """
    global tracker, dataset_examples, training_history
    
    # Získanie všetkých heuristík z trackera
    all_heuristics = tracker.get_all()
    
    # Vytvoríme štruktúru, ktorá mapuje ID príkladu na zoznam jedinečných heuristík
    example_heuristics = {}
    
    # Najprv spracujeme, ktoré príklady majú heuristiky a zoradíme ich podľa času (posledný tréning)
    heuristics_by_example = {}
    
    for heuristic in all_heuristics:
        example_id = heuristic.get("example_id")
        if example_id is not None:
            if example_id not in heuristics_by_example:
                heuristics_by_example[example_id] = []
            
            # Pridáme heuristiku do zoznamu pre daný príklad
            heuristics_by_example[example_id].append(heuristic)
    
    # Nájdeme ID prvého príkladu, ktorý bol použitý na inicializáciu (ak existuje)
    first_example_id = None
    if len(training_history) > 0 and "examples" in training_history[0]:
        for example in training_history[0]["examples"]:
            if example.get("is_positive", True):
                first_example_id = example.get("id")
                break
    
    # Pre každý príklad, vytvoríme list heuristík (vrátane duplicít)
    for example_id, heuristics in heuristics_by_example.items():
        # Nájdeme príklad
        example = next((e for e in dataset_examples if e["id"] == example_id), None)
        if example:
            # Inicializujeme záznam pre príklad
            example_heuristics[example_id] = {
                "id": example_id,
                "name": example.get("name", f"Príklad {example_id}"),
                "is_positive": example.get("is_positive", True),
                "heuristics": []
            }
            
            # Ak je to prvý príklad (inicializácia), pridáme špeciálnu heuristiku "initialization"
            if example_id == first_example_id:
                example_heuristics[example_id]["heuristics"].append({
                    "name": "initialization",
                    "description": "Inicializácia modelu prvým pozitívnym príkladom",
                    "details": {}
                })
            
            # Pridáme všetky heuristiky pre príklad, okrem ADD-LINK a ADD-OBJECT
            for heuristic in heuristics:
                heuristic_name = heuristic["name"]
                # Preskočiť ADD-LINK a ADD-OBJECT heuristiky
                if heuristic_name in ["add_link", "add_object"]:
                    continue
                    
                # Pridáme heuristiku (vrátane duplicít)
                example_heuristics[example_id]["heuristics"].append({
                    "name": heuristic_name,
                    "description": heuristic["description"],
                    "details": heuristic.get("details", {})
                })
    
    # Teraz pridáme aj trénované príklady, ktoré možno nemajú heuristiky
    for example in dataset_examples:
        if example.get("used_in_training", False) and example["id"] not in example_heuristics:
            example_id = example["id"]
            
            # Ak je to prvý príklad (inicializácia), pridáme špeciálnu heuristiku "initialization"
            is_first_example = (example_id == first_example_id)
            
            example_heuristics[example_id] = {
                "id": example_id,
                "name": example.get("name", f"Príklad {example_id}"),
                "is_positive": example.get("is_positive", True),
                "heuristics": [] if not is_first_example else [
                    {
                        "name": "initialization",
                        "description": "Inicializácia modelu prvým pozitívnym príkladom",
                        "details": {}
                    }
                ]
            }
    
    # Prekonvertujeme slovník na zoznam a zoradíme podľa ID príkladu
    result = list(example_heuristics.values())
    result.sort(key=lambda x: x["id"])
    
    return {"examples": result}

# Spustenie aplikácie (pre lokálny vývoj)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 