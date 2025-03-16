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
                
        print(f"Processed {len(positive_examples)}/{len(positive_ids)} positive examples")
        print(f"Processed {len(negative_examples)}/{len(negative_ids)} negative examples")
        
        # Vytvor inštanciu Winstonovho algoritmu
        winston = WinstonLearner(ClassificationTree())
        
        # ====== TRÉNOVACÍ PROCES =======
        
        # 1. INICIALIZÁCIA S PRVÝM POZITÍVNYM PRÍKLADOM (ak model neexistuje)
        if not current_model.objects and positive_examples:
            # Vytvor prvý model z prvého pozitívneho príkladu
            first_id, first_model = positive_examples[0]
            current_model = first_model.copy()
            
            print(f"Initialized model with first positive example (ID: {first_id})")
            
            # Pridaj krok do histórie
            training_steps.append({
                "action": "initialize",
                "example_id": first_id,
                "timestamp": datetime.now().isoformat(),
                "message": f"Initialized model with example {first_id}"
            })
            
            # Označ príklad ako použitý v trénovaní
            dataset_examples[first_id]["used_in_training"] = True
            
            # Odstráň prvý príklad zo zoznamu pozitívnych
            positive_examples = positive_examples[1:]
            
            # Ak máme hneď aj negatívne príklady, môžeme ich aplikovať
            if negative_examples:
                neg_ids = [n_id for n_id, _ in negative_examples]
                neg_models = [n_model for _, n_model in negative_examples]
                
                try:
                    # Použi negatívne príklady na úpravu počiatočného modelu
                    updated_model, messages = winston.update_model_with_new_negatives(current_model, neg_models)
                    current_model = updated_model
                    
                    # Pridaj krok do histórie
                    training_steps.append({
                        "action": "update_with_negatives",
                        "example_id": first_id,  # Stále používame prvý príklad ako referenciu
                        "negative_ids": neg_ids,
                        "timestamp": datetime.now().isoformat(),
                        "message": f"Applied {len(neg_ids)} negative examples to initial model"
                    })
                    
                    # Označ negatívne príklady ako použité
                    for neg_id, _ in negative_examples:
                        dataset_examples[neg_id]["used_in_training"] = True
                        
                    print(f"Applied {len(neg_ids)} negative examples to initial model")
                except Exception as e:
                    print(f"Error applying negative examples to initial model: {str(e)}")
                    training_steps.append({
                        "action": "error",
                        "timestamp": datetime.now().isoformat(),
                        "message": f"Error applying negative examples: {str(e)}"
                    })
        
        # 2. TRÉNOVANIE S ĎALŠÍMI POZITÍVNYMI PRÍKLADMI
        if positive_examples and current_model.objects:
            print(f"Training with {len(positive_examples)} additional positive examples")
            
            # Prejdi zostávajúce pozitívne príklady
            for pos_id, pos_model in positive_examples:
                # Ak máme aj negatívne príklady, použijeme ich
                if negative_examples:
                    neg_ids = [n_id for n_id, _ in negative_examples]
                    neg_models = [n_model for _, n_model in negative_examples]
                    
                    try:
                        # Aktualizuj model s pozitívnym a negatívnymi príkladmi
                        updated_model = winston.update_model_with_multiple_negatives(
                            current_model, pos_model, neg_models
                        )
                        
                        current_model = updated_model
                        
                        # Pridaj krok do histórie
                        training_steps.append({
                            "action": "update",
                            "example_id": pos_id,
                            "negative_ids": neg_ids,
                            "timestamp": datetime.now().isoformat(),
                            "message": f"Updated model with positive example {pos_id} and {len(neg_ids)} negative examples"
                        })
                        
                        # Označ príklady ako použité
                        dataset_examples[pos_id]["used_in_training"] = True
                        for neg_id in neg_ids:
                            dataset_examples[neg_id]["used_in_training"] = True
                            
                        print(f"Updated model with positive example {pos_id} and {len(neg_ids)} negative examples")
                    except Exception as e:
                        print(f"Error updating model with example {pos_id}: {str(e)}")
                        training_steps.append({
                            "action": "error",
                            "example_id": pos_id,
                            "timestamp": datetime.now().isoformat(),
                            "message": f"Error updating model: {str(e)}"
                        })
                else:
                    # Použitie len pozitívneho príkladu na rafináciu modelu
                    try:
                        refined_model = current_model.copy()
                        winston._apply_close_interval(refined_model, pos_model)
                        current_model = refined_model
                        
                        # Pridaj krok do histórie
                        training_steps.append({
                            "action": "refine",
                            "example_id": pos_id,
                            "timestamp": datetime.now().isoformat(),
                            "message": f"Refined model with positive example {pos_id}"
                        })
                        
                        # Označ príklad ako použitý
                        dataset_examples[pos_id]["used_in_training"] = True
                        
                        print(f"Refined model with positive example {pos_id}")
                    except Exception as e:
                        print(f"Error refining model with example {pos_id}: {str(e)}")
                        training_steps.append({
                            "action": "error",
                            "example_id": pos_id,
                            "timestamp": datetime.now().isoformat(),
                            "message": f"Error refining model: {str(e)}"
                        })
        
        # 3. TRÉNOVANIE LEN S NEGATÍVNYMI PRÍKLADMI (ak máme existujúci model)
        elif not positive_examples and negative_examples and current_model.objects:
            print(f"Training with only {len(negative_examples)} negative examples")
            
            neg_ids = [n_id for n_id, _ in negative_examples]
            neg_models = [n_model for _, n_model in negative_examples]
            
            try:
                # Použiť aktuálny model ako pozitívny a aktualizovať ho s negatívnymi príkladmi
                updated_model, messages = winston.update_model_with_new_negatives(current_model, neg_models)
                current_model = updated_model
                
                # Pridaj krok do histórie
                training_steps.append({
                    "action": "update_with_negatives",
                    "negative_ids": neg_ids,
                    "timestamp": datetime.now().isoformat(),
                    "message": f"Updated model with {len(neg_ids)} negative examples only"
                })
                
                # Označ negatívne príklady ako použité
                for neg_id, _ in negative_examples:
                    dataset_examples[neg_id]["used_in_training"] = True
                    
                print(f"Updated model with {len(neg_ids)} negative examples only")
            except Exception as e:
                print(f"Error updating model with negative examples: {str(e)}")
                traceback.print_exc()  # Pridaný traceback pre lepšiu diagnostiku
                training_steps.append({
                    "action": "error",
                    "timestamp": datetime.now().isoformat(),
                    "message": f"Error updating with negative examples: {str(e)}"
                })
        
        # ===== KONIEC TRÉNOVACIEHO PROCESU =====
        
        # Kontrola stavu použitých príkladov
        used_count = sum(1 for ex in dataset_examples if ex.get("used_in_training", False))
        print(f"Training complete: {used_count}/{len(dataset_examples)} examples marked as used")
        
        # Aktualizuj globálnu históriu trénovania
        training_history.extend(training_steps)
        
        # Generuj vizualizáciu modelu
        model_viz = generate_model_visualization(current_model)
        
        # Vypočítaj celkový čas
        total_time = (datetime.now() - start_time).total_seconds()
        print(f"Total training time: {total_time:.2f} seconds")
        
        return {
            "status": "success",
            "message": f"Model trained with {len(example_ids)} examples",
            "steps": training_steps,
            "model_state": model_viz,
            "processed_examples": len(example_ids),
            "training_time_seconds": total_time
        }
    
    except Exception as e:
        print(f"Error during training: {str(e)}")
        traceback.print_exc()
        
        error_step = {
            "action": "error",
            "timestamp": datetime.now().isoformat(),
            "message": f"Error during training: {str(e)}"
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
            "action": entry["action"],
            "timestamp": entry.get("timestamp", ""),
            "example": {
                "id": example["id"],
                "name": example["name"],
                "is_positive": example["is_positive"]
            } if example else None
        }
        
        if near_misses:
            if entry["action"] == "update_multi":
                # Pre aktualizáciu s viacerými negatívnymi príkladmi
                history_entry["near_misses"] = [
                    {
                        "id": nm["id"],
                        "name": nm["name"],
                        "is_positive": nm["is_positive"]
                    }
                    for nm in near_misses
                ]
            else:
                # Pre spätnú kompatibilitu s pôvodným formátom
                history_entry["near_miss"] = {
                    "id": near_misses[0]["id"],
                    "name": near_misses[0]["name"],
                    "is_positive": near_misses[0]["is_positive"]
                }
        
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
        if any(step["action"] == "initialize" for step in training_history):
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