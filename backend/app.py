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

# Dátové modely pre API
class PL1Example(BaseModel):
    formula: str
    is_positive: bool
    name: Optional[str] = None

class TrainingRequest(BaseModel):
    example_ids: List[int]
    retrain_mode: str = "incremental"  # "incremental" alebo "full"
    batch_size: int = 5  # Počet príkladov v jednej dávke

class TrainingResult(BaseModel):
    success: bool
    message: str
    model_state: Optional[Dict[str, Any]] = None
    steps: List[str] = []
    batch_count: Optional[int] = None
    processed_examples: Optional[int] = None
    error: Optional[str] = None
    training_mode: str = "batch"  # "batch" alebo "single" alebo "retrained"

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
    
    # Základné triedy pre BMW príklady
    classification_tree.add_relationship("Vehicle", None)  # Koreňová trieda
    
    # Triedy BMW
    classification_tree.add_relationship("BMW", "Vehicle")
    classification_tree.add_relationship("Series3", "BMW")
    classification_tree.add_relationship("Series5", "BMW")
    classification_tree.add_relationship("Series7", "BMW")
    classification_tree.add_relationship("X5", "BMW")
    classification_tree.add_relationship("X7", "BMW")
    
    # Komponenty
    classification_tree.add_relationship("Component", None)
    
    # Motory
    classification_tree.add_relationship("Engine", "Component")
    classification_tree.add_relationship("DieselEngine", "Engine")
    classification_tree.add_relationship("PetrolEngine", "Engine")
    classification_tree.add_relationship("HybridEngine", "Engine")
    
    # Prevodovky
    classification_tree.add_relationship("Transmission", "Component")
    classification_tree.add_relationship("AutomaticTransmission", "Transmission")
    classification_tree.add_relationship("ManualTransmission", "Transmission")
    
    # Pohony
    classification_tree.add_relationship("DriveSystem", "Component")
    classification_tree.add_relationship("RWD", "DriveSystem")  # Rear-wheel drive
    classification_tree.add_relationship("AWD", "DriveSystem")  # All-wheel drive
    classification_tree.add_relationship("XDrive", "AWD")       # BMW xDrive je typ AWD
    
    print(f"Klasifikačný strom inicializovaný, obsahuje {len(classification_tree.parent_map)} vzťahov rodič-dieťa")
    
    # Vypíšeme obsah stromu pre debugovanie
    for child, parent in classification_tree.parent_map.items():
        print(f"  {child} -> {parent or 'ROOT'}")

def formula_to_model(formula: Formula) -> Model:
    """Konvertuje PL1 formulu na model."""
    objects = []
    links = []
    object_classes = {}
    
    # Kontrola prázdnej formuly
    if not formula or not formula.get_all_predicates():
        print("Warning: Empty formula or no predicates found")
        return Model(objects=[], links=[])
    
    # Extrahuj všetky predikáty z formuly
    predicates = formula.get_all_predicates()
    print(f"Processing {len(predicates)} predicates")
    
    # Najprv spracuj predikáty typu "Ι" (is_a) na identifikáciu objektov a ich tried
    for predicate in predicates:
        if predicate.name == "Ι" and len(predicate.arguments) == 2:
            obj_name = predicate.arguments[0]
            class_name = predicate.arguments[1]
            object_classes[obj_name] = class_name
    
    # Vytvor objekty
    for obj_name, class_name in object_classes.items():
        objects.append(Object(name=obj_name, class_name=class_name))
    
    # Spracuj ostatné predikáty na vytvorenie spojení a atribútov
    for predicate in predicates:
        if predicate.name == "Π" and len(predicate.arguments) == 2:  # has_part
            source = predicate.arguments[0]
            target = predicate.arguments[1]
            
            # Skontroluj, či objekty existujú
            if source not in object_classes or target not in object_classes:
                print(f"Warning: Missing object definition for link {source} -> {target}")
                continue
            
            links.append(Link(source=source, target=target, link_type=LinkType.REGULAR))
        
        elif predicate.name == "Μ" and len(predicate.arguments) == 2:  # must_have_part
            source = predicate.arguments[0]
            target = predicate.arguments[1]
            
            # Skontroluj, či objekty existujú
            if source not in object_classes or target not in object_classes:
                print(f"Warning: Missing object definition for link {source} -> {target}")
                continue
            
            links.append(Link(source=source, target=target, link_type=LinkType.MUST))
        
        elif predicate.name == "Ν" and len(predicate.arguments) == 2:  # must_not_have_part
            source = predicate.arguments[0]
            target = predicate.arguments[1]
            
            # Skontroluj, či objekty existujú
            if source not in object_classes or target not in object_classes:
                print(f"Warning: Missing object definition for link {source} -> {target}")
                continue
            
            links.append(Link(source=source, target=target, link_type=LinkType.MUST_NOT))
        
        elif predicate.name == "Α" and len(predicate.arguments) >= 3:  # has_attribute
            obj_name = predicate.arguments[0]
            attr_name = predicate.arguments[1]
            attr_value = predicate.arguments[2]
            
            # Skontroluj, či objekt existuje
            if obj_name not in object_classes:
                print(f"Warning: Missing object definition for attribute {obj_name}.{attr_name}")
                continue
            
            # Nájdi objekt a pridaj mu atribút
            for obj in objects:
                if obj.name == obj_name:
                    if not obj.attributes:
                        obj.attributes = {}
                    
                    # Konvertuj hodnotu na správny typ
                    try:
                        # Skús konvertovať na číslo
                        if isinstance(attr_value, str) and attr_value.replace('.', '', 1).isdigit():
                            if '.' in attr_value:
                                attr_value = float(attr_value)
                            else:
                                attr_value = int(attr_value)
                    except:
                        # Ak konverzia zlyhá, ponechaj ako string
                        pass
                    
                    obj.attributes[attr_name] = attr_value
                    break
    
    # Pridaj MUST_BE_A spojenia pre triedy objektov
    for obj in objects:
        links.append(Link(source=obj.name, target=obj.class_name, link_type=LinkType.MUST_BE_A))
    
    return Model(objects=objects, links=links)

def generate_model_visualization(model: Model):
    """
    Generuje vizualizáciu modelu ako sémantickú sieť.
    
    Táto funkcia konvertuje model na formát vhodný pre vizualizáciu
    ako sémantická sieť (uzly a hrany).
    
    Parametre:
        model: Model, ktorý sa má vizualizovať
        
    Návratová hodnota:
        Dictionary obsahujúci uzly a hrany pre vizualizáciu
    """
    if not model:
        return {"nodes": [], "edges": []}
        
    try:
        return model.to_semantic_network()
    except Exception as e:
        print(f"Error generating model visualization: {str(e)}")
        traceback.print_exc()
        return {"nodes": [], "edges": [], "error": str(e)}

def get_timestamp():
    """Vráti aktuálny časový údaj vo formáte ISO 8601."""
    return datetime.now().isoformat()

# Inicializácia aplikácie
@app.on_event("startup")
async def startup_event():
    """Inicializuje aplikáciu pri štarte."""
    initialize_classification_tree()
    print("Aplikácia bola inicializovaná.")

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
        # Vyčisti existujúci dataset
        dataset_examples = []
        
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
                    
                    # Pridaj do datasetu
                    dataset_examples.append({
                        "id": i,
                        "formula": example.formula,
                        "parsed_formula": formula,
                        "model": model.to_dict(),  # Ulož model ako slovník
                        "is_positive": example.is_positive,
                        "name": example.name or f"Example {i+1}",
                        "used_in_training": False
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

# Presmerovanie logu Winston Learnera do trackera
def track_winston_learner(original_learner, tracker):
    """
    Vytvorí proxy objekt, ktorý zachytáva a zaznamenáva heuristiky aplikované v learnerovi.
    """
    class WinstonLearnerProxy(WinstonLearner):
        def __init__(self, original_learner, tracker):
            self.original_learner = original_learner
            self.tracker = tracker
            self.last_applied_heuristic = None
            self.classification_tree = original_learner.classification_tree
            self.debug_enabled = True  # Zapneme debugovanie pre lepšiu diagnostiku
            
            # Kontrola, či klasifikačný strom obsahuje údaje
            parent_relations = len(self.classification_tree.parent_map)
            print(f"[WinstonLearnerProxy] Klasifikačný strom obsahuje {parent_relations} vzťahov rodič-dieťa.")
        
        def update_model(self, current_model, good_example, near_miss):
            result = self.original_learner.update_model(current_model, good_example, near_miss)
            self.last_applied_heuristic = self.original_learner.applied_heuristics[-1] if self.original_learner.applied_heuristics else None
            
            if self.last_applied_heuristic:
                # Mapovanie názvov heuristík na užívateľsky zrozumiteľné popisky
                heuristic_descriptions = {
                    "require_link": "Heuristika REQUIRE-LINK - Identifikácia spojení, ktoré musia byť prítomné",
                    "forbid_link": "Heuristika FORBID-LINK - Identifikácia spojení, ktoré nesmú byť prítomné",
                    "drop_link": "Heuristika DROP-LINK - Eliminácia nepotrebných spojení",
                    "climb_tree": "Heuristika CLIMB-TREE - Generalizácia hľadaním spoločných predkov",
                    "enlarge_set": "Heuristika ENLARGE-SET - Vytváranie zjednotení pre funkčne ekvivalentné komponenty",
                    "close_interval": "Heuristika CLOSE-INTERVAL - Spracovanie numerických atribútov zúžením intervalov"
                }
                
                self.tracker.add_heuristic(
                    self.last_applied_heuristic,
                    heuristic_descriptions.get(self.last_applied_heuristic, f"Heuristika {self.last_applied_heuristic.upper()}"),
                    details={
                        "good_objects": len(good_example.objects),
                        "near_miss_objects": len(near_miss.objects),
                        "changes_made": len(result.links) - len(current_model.links)
                    }
                )
            return result
        
        def _apply_require_link(self, model, good, near_miss):
            return self.original_learner._apply_require_link(model, good, near_miss)
        
        def _apply_forbid_link(self, model, good, near_miss):
            return self.original_learner._apply_forbid_link(model, good, near_miss)
        
        def _apply_drop_link(self, model, good, near_miss):
            return self.original_learner._apply_drop_link(model, good, near_miss)
        
        def _apply_climb_tree(self, model, good, near_miss):
            return self.original_learner._apply_climb_tree(model, good, near_miss)
        
        def _apply_enlarge_set(self, model, good, near_miss):
            return self.original_learner._apply_enlarge_set(model, good, near_miss)
        
        def _apply_close_interval(self, model, good, near_miss=None):
            # Ak bol dodaný near_miss parameter, použijeme ho, inak voláme bez neho
            if near_miss is not None:
                return self.original_learner._apply_close_interval(model, good, near_miss)
            else:
                # Pre spätnú kompatibilitu poskytneme prázdny model ako near_miss
                empty_model = Model(objects=[], links=[])
                return self.original_learner._apply_close_interval(model, good, empty_model)
    
    return WinstonLearnerProxy(original_learner, tracker)

@app.post("/api/train")
async def train_model(training_request: TrainingRequest):
    """
    Trénovanie modelu s pozitívnymi a negatívnymi príkladmi.
    Implementuje zjednodušenú verziu Winstonovho algoritmu.
    """
    global current_model
    global dataset_examples
    global training_history
    
    # Inicializuj nový zoznam krokov trénovania
    training_steps = []
    start_time = datetime.now()
    
    try:
        # Získaj údaje zo žiadosti
        example_ids = training_request.example_ids
        retrain_mode = training_request.retrain_mode
        
        print(f"Training request: {len(example_ids)} examples, retrain_mode={retrain_mode}")
        
        # Ak je retrain_mode, vynuluj model a históriu
        if retrain_mode:
            current_model = Model()
            training_history.clear()
            print("Retrain mode: Initialized empty model and cleared training history")
            
            # Pridaj krok inicializácie
            training_steps.append({
                "step": "initialize",
                "description": "Inicializácia nového prázdneho modelu (režim pretrénovania).",
                "heuristics": []
            })
        
        # Rozdeľ príklady na pozitívne a negatívne
        positive_ids = []
        negative_ids = []
        
        for eid in example_ids:
            if eid < len(dataset_examples):
                if dataset_examples[eid]["is_positive"]:
                    positive_ids.append(eid)
                else:
                    negative_ids.append(eid)
                    
        print(f"Positive examples: {len(positive_ids)}, Negative examples: {len(negative_ids)}")
        
        # Získaj modely pre príklady
        positive_examples = []
        negative_examples = []
        
        # Vytvor modely pre pozitívne príklady
        for example_id in positive_ids:
            example = dataset_examples[example_id]
            try:
                if "model" in example and example["model"]:
                    # Načítaj existujúci model
                    example_model = Model.from_dict(example["model"])
                else:
                    # Vytvor nový model z formuly
                    formula = example["parsed_formula"]
                    example_model = formula_to_model(formula)
                    example["model"] = example_model.to_dict()
                
                # Pridaj tuple (id, model) do zoznamu
                positive_examples.append((example_id, example_model))
                print(f"Added positive example {example_id}: {len(example_model.objects)} objects")
            except Exception as e:
                print(f"Error processing positive example {example_id}: {str(e)}")
                
        # Vytvor modely pre negatívne príklady
        for example_id in negative_ids:
            example = dataset_examples[example_id]
            try:
                if "model" in example and example["model"]:
                    # Načítaj existujúci model
                    example_model = Model.from_dict(example["model"])
                else:
                    # Vytvor nový model z formuly
                    formula = example["parsed_formula"]
                    example_model = formula_to_model(formula)
                    example["model"] = example_model.to_dict()
                
                # Pridaj tuple (id, model) do zoznamu
                negative_examples.append((example_id, example_model))
                print(f"Added negative example {example_id}: {len(example_model.objects)} objects")
            except Exception as e:
                print(f"Error processing negative example {example_id}: {str(e)}")
                
        # Priprav learner
        local_learner = WinstonLearner(classification_tree)
        local_learner.debug_enabled = True  # Zapneme debugovanie pre lepšiu diagnostiku
        
        # KROK 1: Inicializácia modelu (ak ešte nebol inicializovaný alebo je režim pretrénovania)
        if not current_model.objects or retrain_mode:
            if positive_examples:
                print("Initializing model with positive example")
                
                # Vyber prvý pozitívny príklad pre inicializáciu
                example_id, example_model = positive_examples[0]
                example_name = dataset_examples[example_id]["name"]
                
                # Nastav aktuálny model na kópiu prvého pozitívneho príkladu
                current_model = example_model.copy()
                
                # Pridaj záznam do histórie trénovania
                training_history.append({
                        "action": "initialize",
                    "example_id": example_id,
                    "timestamp": datetime.now().isoformat(),
                    "current": True
                    })
                
                # Pridaj krok inicializácie do zoznamu krokov
                training_steps.append({
                        "step": "initialize",
                    "description": f"Inicializácia modelu s pozitívnym príkladom '{example_name}'.",
                    "example_name": example_name,
                        "is_positive": True,
                    "heuristics": []
                })
                
                print(f"Model initialized with positive example {example_id}, model has {len(current_model.objects)} objects")
            else:
                # Nie je k dispozícii žiadny pozitívny príklad pre inicializáciu
                return {
                    "success": False,
                    "message": "Nie je k dispozícii žiadny pozitívny príklad pre inicializáciu modelu."
                }
                
        # KROK 2: Aktualizácia modelu s ďalšími príkladmi
        
        # Režim trénovania s jedným pozitívnym a viacerými negatívnymi príkladmi
        used_examples = []  # Sledovanie všetkých použitých príkladov
        
        # Ak ešte neboli použité negatívne príklady, pokúsime sa aplikovať všetky dostupné
        if negative_examples:
            # Existuje aspoň jeden negatívny príklad
            update_step_description = "Aktualizácia modelu s "
            
            if len(positive_examples) <= 1 and current_model.objects:
                # Použitie aktuálneho modelu ako pozitívneho príkladu s negatívnymi príkladmi
                print(f"Updating model with {len(negative_examples)} negative examples only")
                
                negative_example_ids = [ne[0] for ne in negative_examples]
                negative_example_models = [ne[1] for ne in negative_examples]
                negative_names = [dataset_examples[ne_id]["name"] for ne_id in negative_example_ids]
                
                # Vytvor nový tracker pre tento krok
                step_tracker = HeuristicTracker()
                step_learner = track_winston_learner(local_learner, step_tracker)
                
                # UPRAVENÉ: Namiesto update_model_with_new_negatives použijeme postupné spracovanie
                # Podľa Winstonovho prístupu, potrebujeme vždy pár (pozitívny + negatívny)
                # Použijeme prvý pozitívny príklad ako referenčný pre všetky negatívne
                first_positive_id, first_positive_model = positive_examples[0]
                first_positive_name = dataset_examples[first_positive_id]["name"]
                
                # Postupné párovanie prvého pozitívneho príkladu s každým negatívnym
                applied_heuristics = []
                used_negative_examples = []
                
                for neg_idx, (neg_id, neg_model) in enumerate(negative_examples):
                    # Vytvor nový tracker pre tento konkrétny pár
                    pair_tracker = HeuristicTracker()
                    pair_learner = track_winston_learner(local_learner, pair_tracker)
                    
                    # Aktualizuj model s jedným pozitívnym a jedným negatívnym príkladom
                    updated_model = pair_learner.update_model(
                        current_model.copy(), first_positive_model, neg_model
                    )
                    
                    # Ak sa model zmenil, uloží zmeny
                    if pair_learner.last_applied_heuristic:
                        current_model = updated_model
                        applied_heuristics.extend(pair_tracker.get_all())
                        used_negative_examples.append(neg_id)
                        
                        print(f"  Applied heuristic '{pair_learner.last_applied_heuristic}' with negative example {neg_id}")
                
                # Pridaj záznamy do histórie trénovania
                for neg_id in used_negative_examples:
                    training_history.append({
                        "action": "update_incremental",
                        "example_id": first_positive_id,
                        "near_miss_id": neg_id,
                        "timestamp": datetime.now().isoformat(),
                        "current": True
                    })
                    used_examples.append(neg_id)
                
                # Pridaj krok aktualizácie do zoznamu krokov
                update_step_description += f"{len(negative_examples)} negatívnymi príkladmi"
                
                negative_examples_text = ", ".join([f"'{name}'" for name in negative_names])
                
                training_steps.append({
                    "step": "update_multi",
                    "description": update_step_description + f" ({negative_examples_text}).",
                    "negative_examples": negative_names,
                    "heuristics": step_tracker.get_all()  # Použij heuristiky z tohto kroku
                })
                
                print(f"Model updated with negative examples, model has {len(current_model.objects)} objects and {len(current_model.links)} links")
                
            else:
                # Máme viac pozitívnych príkladov, použijeme prvý na ďalšie trénovanie
                print(f"Updating model with {len(positive_examples) - 1} positive examples and {len(negative_examples)} negative examples")
                
                # Použij len zostávajúce pozitívne príklady (bez prvého, ktorý už bol použitý na inicializáciu)
                remaining_positive = positive_examples[1:] if positive_examples and not retrain_mode else positive_examples
                
                for pos_id, pos_model in remaining_positive:
                    pos_example_name = dataset_examples[pos_id]["name"]
                    
                    # Vytvor nový tracker pre tento krok pozitívneho príkladu
                    pos_step_tracker = HeuristicTracker()
                    pos_step_learner = track_winston_learner(local_learner, pos_step_tracker)
                    
                    # Párovanie pozitívneho príkladu s každým negatívnym príkladom postupne (inkrementálne)
                    # Toto je v súlade s Winstonovým algoritmom, kde sa model aktualizuje postupne
                    # jedným pozitívnym a jedným negatívnym príkladom naraz
                    applied_heuristics = []
                    used_negative_examples = []
                    
                    for neg_idx, (neg_id, neg_model) in enumerate(negative_examples):
                        # Vytvor nový tracker pre tento konkrétny pár
                        pair_tracker = HeuristicTracker()
                        pair_learner = track_winston_learner(local_learner, pair_tracker)
                        
                        # Aktualizuj model s jedným pozitívnym a jedným negatívnym príkladom
                        updated_model = pair_learner.update_model(
                            current_model.copy(), pos_model, neg_model
                        )
                        
                        # Ak sa model zmenil, uloží zmeny
                        if pair_learner.last_applied_heuristic:
                            current_model = updated_model
                            applied_heuristics.extend(pair_tracker.get_all())
                            used_negative_examples.append(neg_id)
                            
                            print(f"  Applied heuristic '{pair_learner.last_applied_heuristic}' with negative example {neg_id}")
                    
                    # Pridaj záznam do histórie trénovania
                    training_history.append({
                        "action": "update_incremental",
                        "example_id": pos_id,
                        "near_miss_ids": used_negative_examples,
                        "timestamp": datetime.now().isoformat(),
                        "current": True
                    })
                    
                    used_examples.append(pos_id)
                    used_examples.extend(used_negative_examples)
                    
                    # Pridaj krok aktualizácie do zoznamu krokov
                    training_steps.append({
                        "step": "update_incremental",
                        "description": f"Inkrementálna aktualizácia modelu s pozitívnym príkladom '{pos_example_name}' a {len(used_negative_examples)} negatívnymi príkladmi.",
                        "example_name": pos_example_name,
                        "is_positive": True,
                        "negative_examples": [dataset_examples[neg_id]["name"] for neg_id in used_negative_examples],
                        "heuristics": applied_heuristics  # Použij zozbierané heuristiky
                    })
                    
                    print(f"Model updated with positive example {pos_id} and negative examples, model has {len(current_model.objects)} objects")
                
                # Ak nemáme žiadne zostávajúce pozitívne príklady, použijeme len negatívne
                if not remaining_positive and negative_examples:
                    print(f"Updating model with just {len(negative_examples)} negative examples")
                    
                    negative_example_ids = [ne[0] for ne in negative_examples]
                    
                    # UPRAVENÉ: Winston nemá koncept práce len s negatívnymi príkladmi
                    # Podľa pôvodného algoritmu, potrebujeme vždy pár (pozitívny + negatívny)
                    # Preto použijeme posledný pozitívny príklad ako referenčný pre všetky negatívne
                    if positive_examples:
                        last_positive_id, last_positive_model = positive_examples[-1]
                        last_positive_name = dataset_examples[last_positive_id]["name"]
                        
                        # Vytvor nový tracker pre túto aktualizáciu
                        step_tracker = HeuristicTracker()
                        step_learner = track_winston_learner(local_learner, step_tracker)
                        
                        # Postupné párovanie posledného pozitívneho príkladu s každým negatívnym
                        applied_heuristics = []
                        used_negative_examples = []
                        
                        for neg_idx, (neg_id, neg_model) in enumerate(negative_examples):
                            # Vytvor nový tracker pre tento konkrétny pár
                            pair_tracker = HeuristicTracker()
                            pair_learner = track_winston_learner(local_learner, pair_tracker)
                            
                            # Aktualizuj model s jedným pozitívnym a jedným negatívnym príkladom
                            updated_model = pair_learner.update_model(
                                current_model.copy(), last_positive_model, neg_model
                            )
                            
                            # Ak sa model zmenil, uloží zmeny
                            if pair_learner.last_applied_heuristic:
                                current_model = updated_model
                                applied_heuristics.extend(pair_tracker.get_all())
                                used_negative_examples.append(neg_id)
                                
                                print(f"  Applied heuristic '{pair_learner.last_applied_heuristic}' with negative example {neg_id}")
                        
                        # Pridaj záznamy do histórie trénovania
                        for neg_id in used_negative_examples:
                            training_history.append({
                                "action": "update_incremental",
                                "example_id": last_positive_id,
                                "near_miss_id": neg_id,
                                "timestamp": datetime.now().isoformat(),
                                "current": True
                            })
                            
                            if neg_id not in used_examples:
                                used_examples.append(neg_id)
                        
                        # Pridaj krok aktualizácie do zoznamu krokov
                        update_step_description = f"Inkrementálna aktualizácia modelu s posledným pozitívnym príkladom '{last_positive_name}' a {len(used_negative_examples)} negatívnymi príkladmi."
                        
                        negative_names = [dataset_examples[ne_id]["name"] for ne_id in used_negative_examples]
                        negative_examples_text = ", ".join([f"'{name}'" for name in negative_names])
                        
                        training_steps.append({
                            "step": "update_incremental",
                            "description": update_step_description + f" ({negative_examples_text}).",
                            "example_name": last_positive_name,
                            "is_positive": True,
                            "negative_examples": negative_names,
                            "heuristics": applied_heuristics  # Použij zozbierané heuristiky
                        })
                        
                        print(f"Model updated using last positive example with negative examples, model has {len(current_model.objects)} objects and {len(current_model.links)} links")
                    else:
                        # Nemáme žiadny pozitívny príklad, nemôžeme pokračovať s Winstonovým prístupom
                        print("No positive examples available, cannot apply Winston's algorithm with only negative examples")
                else:
                    # Nie sú k dispozícii žiadne negatívne príklady, skúsime aspoň aktualizovať model s ďalšími pozitívnymi
                    print("No negative examples available, updating model with remaining positive examples only")
                    
                    # Použij zvyšné pozitívne príklady (bez prvého, ktorý už bol použitý na inicializáciu)
                    remaining_positive = positive_examples[1:] if positive_examples and not retrain_mode else positive_examples
                    
                    for pos_id, pos_model in remaining_positive:
                        pos_example_name = dataset_examples[pos_id]["name"]
                        
                        # Vytvor nový tracker pre tento krok
                        step_tracker = HeuristicTracker()
                        step_learner = track_winston_learner(local_learner, step_tracker)
                        
                        # UPRAVENÉ: V pôvodnom Winstonovom algoritme nemôžeme pracovať len s pozitívnym príkladom
                        # Skutočný Winston potrebuje párový negatívny príklad
                        # Môžeme ale použiť aspoň close_interval, ktorá funguje aj bez negatívneho príkladu
                        updated_model = current_model.copy()
                        
                        # Aplikuj aspoň close_interval heuristiku, ktorá závisí len od pozitívneho príkladu
                        step_learner._apply_close_interval(updated_model, pos_model)
                        
                        # Aktualizuj aktuálny model
                        current_model = updated_model
                        
                        # Pridaj záznam do histórie trénovania
                        training_history.append({
                            "action": "update_close_interval",
                            "example_id": pos_id,
                            "timestamp": datetime.now().isoformat(),
                            "current": True
                        })
                        
                        used_examples.append(pos_id)
                        
                        # Pridaj krok aktualizácie do zoznamu krokov
                        training_steps.append({
                            "step": "update",
                            "description": f"Obmedzená aktualizácia modelu s pozitívnym príkladom '{pos_example_name}' (bez negatívnych príkladov).",
                            "example_name": pos_example_name,
                            "is_positive": True,
                            "heuristics": step_tracker.get_all()  # Použij heuristiky z tohto kroku
                        })
                        
                        print(f"Applied close_interval heuristic with positive example {pos_id}, model has {len(current_model.objects)} objects")
                
        # Zjednoť zoznam použitých príkladov (odstráň duplicity)
        all_used_example_ids = list(set(used_examples))
        used_count = len(all_used_example_ids)
        
        # Vypočítaj celkový čas trénovania
        total_time = (datetime.now() - start_time).total_seconds()
        print(f"Total training time: {total_time:.2f} seconds")
        
        # KROK 5: Príprava odpovede
        training_time = (datetime.now() - start_time).total_seconds()
        print(f"Training completed in {training_time:.2f} seconds")
        
        # Priprav vizualizáciu modelu
        model_visualization = current_model.to_semantic_network()
        
        # Vytvor textovú reprezentáciu hypotézy
        model_hypothesis = current_model.to_formula()
        
        # Aktualizuj informácie o použitých príkladoch
        for example_id in example_ids:
            if example_id < len(dataset_examples):
                dataset_examples[example_id]["used_in_training"] = True
        
        # Finálna odpoveď s výsledkami
        return {
            "success": True,
            "message": f"Model bol úspešne natrénovaný s {len(example_ids)} príkladmi.",
            "model_updated": True,
            "model_visualization": model_visualization,
            "model_hypothesis": model_hypothesis,
            "training_steps": training_steps,
            "used_examples_count": len(example_ids),
            "total_examples_count": len(dataset_examples)
        }
    
    except Exception as e:
        print(f"Error during training: {str(e)}")
        traceback.print_exc()
        
        error_step = {
            "step": "error",
            "description": f"Error during training: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
        training_steps.append(error_step)
        
        return {"status": "error", "message": str(e), "steps": training_steps}

@app.post("/api/compare")
async def compare_example(example: PL1Example):
    """Porovná príklad s naučeným modelom a vráti výsledok."""
    global current_model, classification_tree
    
    try:
        if not current_model.objects:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Model ešte nebol natrénovaný."}
            )
        
        # Parsuj formulu a vytvor model z príkladu
        formula = parse_pl1_formula(example.formula)
        example_model = formula_to_model(formula)
        
        # Porovnaj s naučeným modelom použitím funkcie is_valid_example
        is_valid, symbolic_differences = is_valid_example(current_model, example_model, classification_tree)
        
        # Vytvor vysvetlenie
        explanation = "Príklad je platný podľa naučeného modelu." if is_valid else "Príklad nie je platný podľa naučeného modelu z nasledujúcich dôvodov:"
        
        return ComparisonResult(
            is_valid=is_valid,
            explanation=explanation,
            symbolic_differences=symbolic_differences
        )
    
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chyba pri porovnávaní príkladu: {str(e)}")

@app.get("/api/model")
async def get_model():
    """Vráti aktuálne naučený model vo formáte vhodnom pre vizualizáciu."""
    global current_model
    
    try:
        if not current_model.objects:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Model ešte nebol natrénovaný."}
            )
        
        # Vytvor vizualizáciu modelu
        visualization = current_model.to_semantic_network()
        
        # Konvertuj model späť do PL1 formuly
        pl1_representation = current_model.to_formula()
        
        return {
            "visualization": visualization,
            "pl1_representation": pl1_representation
        }
    
    except Exception as e:
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

@app.post("/api/reset")
async def reset_model():
    """Resetuje naučený model a históriu trénovania."""
    global current_model, training_history
    
    current_model = Model(objects=[], links=[])
    # Namiesto úplného vymazania histórie označíme všetky záznamy ako neaktuálne
    for entry in training_history:
        entry["current"] = False
    
    return {"success": True, "message": "Model bol resetovaný a história označená ako neaktuálna."}

@app.get("/api/model-status")
async def get_model_status():
    """Získa aktuálny stav modelu a trénovania."""
    global current_model
    global dataset_examples
    global training_history
    
    # Vypočítaj počet použitých príkladov celkom
    used_examples = sum(1 for example in dataset_examples if example.get("used_in_training", False))
    
    # Vypočítaj počet použitých pozitívnych a negatívnych príkladov
    positive_used = sum(1 for example in dataset_examples 
                      if example.get("is_positive", False) and example.get("used_in_training", False))
    negative_used = sum(1 for example in dataset_examples 
                      if not example.get("is_positive", True) and example.get("used_in_training", False))
    
    # Celkový počet príkladov podľa typu
    total_positive = sum(1 for example in dataset_examples if example.get("is_positive", False))
    total_negative = sum(1 for example in dataset_examples if not example.get("is_positive", True))
    
    # Určí trénovací režim
    training_mode = "none"
    if current_model.objects:
        # Kontrola, či je v histórii inicializačný krok (kompatibilita s oboma formátmi)
        has_initialize_step = False
        for step in training_history:
            # Skontrolujeme rôzne možné kľúče
            action_value = step.get("action") or step.get("step")
            if action_value == "initialize":
                has_initialize_step = True
                break
        
        if has_initialize_step:
            training_mode = "initialized"
        if len(training_history) > 1:
            training_mode = "incremental"
    
    # Počet krokov trénovania
    batch_count = len(training_history)
    
    print(f"Model status: {len(current_model.objects)} objects, {len(current_model.links)} links")
    print(f"Examples: {used_examples}/{len(dataset_examples)} used total")
    print(f"Positive: {positive_used}/{total_positive}, Negative: {negative_used}/{total_negative}")
        
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
        "training_steps": batch_count
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

# Spustenie aplikácie (pre lokálny vývoj)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 