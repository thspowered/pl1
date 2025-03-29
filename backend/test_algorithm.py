#!/usr/bin/env python3
import requests
import json
import time
from pprint import pprint
from pl1.backend.model import Model, Link, LinkType, Object, ClassificationTree
from pl1.backend.learner import WinstonLearner
from pl1.backend.pl1_parser import parse_pl1_formula

# Základné nastavenia
BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}

def make_request(method, endpoint, data=None):
    """Vykoná HTTP požiadavku na API a vráti odpoveď."""
    url = f"{BASE_URL}{endpoint}"
    if method.lower() == "get":
        response = requests.get(url, headers=HEADERS)
    elif method.lower() == "post":
        response = requests.post(url, headers=HEADERS, json=data)
    else:
        raise ValueError(f"Nepodporovaná HTTP metóda: {method}")
    
    return response

def reset_model():
    """Reset modelu pre nový test."""
    response = requests.post(f"{BASE_URL}/api/reset")
    return response.json()

def upload_dataset(examples):
    """Upload datasetu do API."""
    response = requests.post(
        f"{BASE_URL}/api/upload-dataset",
        json=examples
    )
    return response.json()

def train_model(example_ids):
    """Trénovanie modelu pomocou vybraných príkladov."""
    response = requests.post(
        f"{BASE_URL}/api/train",
        json={"example_ids": example_ids}
    )
    return response.json()

def get_model():
    """Získanie aktuálneho natrénovaného modelu."""
    response = requests.get(f"{BASE_URL}/api/model")
    return response.json()

def compare_example(formula):
    """Porovnanie príkladu s modelom."""
    response = requests.post(
        f"{BASE_URL}/api/compare",
        json={"formula": formula}
    )
    return response.json()

def analyze_example(example_id):
    """Analýza príkladu podľa ID."""
    response = requests.get(f"{BASE_URL}/api/analyze_example/{example_id}")
    return response.json()

# Definícia základných príkladov
positive_example = """
Ι(bmw1, BMW)
Ι(engine1, Engine)
Ι(transmission1, Transmission)
Ι(wheel1, Wheel)
Ι(wheel2, Wheel)
Ι(wheel3, Wheel)
Ι(wheel4, Wheel)
Π(bmw1, engine1)
Π(bmw1, transmission1)
Π(bmw1, wheel1)
Π(bmw1, wheel2)
Π(bmw1, wheel3)
Π(bmw1, wheel4)
"""

# Negatívny príklad bez motora
negative_example_no_engine = """
Ι(car1, BMW)
Ι(transmission1, Transmission)
Ι(wheel1, Wheel)
Ι(wheel2, Wheel)
Ι(wheel3, Wheel)
Ι(wheel4, Wheel)
Π(car1, transmission1)
Π(car1, wheel1)
Π(car1, wheel2)
Π(car1, wheel3)
Π(car1, wheel4)
"""

# Negatívny príklad bez prevodovky
negative_example_no_transmission = """
Ι(car2, BMW)
Ι(engine2, Engine)
Ι(wheel5, Wheel)
Ι(wheel6, Wheel)
Ι(wheel7, Wheel)
Ι(wheel8, Wheel)
Π(car2, engine2)
Π(car2, wheel5)
Π(car2, wheel6)
Π(car2, wheel7)
Π(car2, wheel8)
"""

# Úplne iný pozitívny príklad pre testovanie generalizácie
different_positive_example = """
Ι(bmw2, BMW)
Ι(engine3, Engine)
Ι(transmission3, Transmission)
Ι(wheel9, Wheel)
Ι(wheel10, Wheel)
Ι(wheel11, Wheel)
Ι(wheel12, Wheel)
Π(bmw2, engine3)
Π(bmw2, transmission3)
Π(bmw2, wheel9)
Π(bmw2, wheel10)
Π(bmw2, wheel11)
Π(bmw2, wheel12)
"""

# Test case 1: Testovanie, či model správne identifikuje motor a prevodovku ako povinné
def test_required_components():
    """Testuje, či model správne rozpozná chýbajúce kľúčové komponenty."""
    print("\n--- TEST CASE 1: Vyžaduje motor a prevodovku ---")
    
    # Reset modelu
    print("Resetujem model...")
    reset_model()
    
    # Upload datasetu
    print("Uploading dataset...")
    dataset_response = upload_dataset([
        {"id": 1, "formula": positive_example, "is_positive": True},
        {"id": 2, "formula": negative_example_no_engine, "is_positive": False},
        {"id": 3, "formula": negative_example_no_transmission, "is_positive": False}
    ])
    print(f"Dataset uploaded: {dataset_response.get('success', False)}")
    
    # Trénovanie modelu
    print("Training model...")
    train_response = train_model([1, 2, 3])
    print(f"Training completed: {train_response.get('message', 'No message')}")
    
    # Zobrazenie modelu
    model = get_model()
    print("\nNatrénovaný model:")
    print(json.dumps(model, indent=2, ensure_ascii=False))
    
    # Testované príklady
    test_examples = [
        {"formula": negative_example_no_engine, "expected": False, "desc": "Príklad bez motora"},
        {"formula": negative_example_no_transmission, "expected": False, "desc": "Príklad bez prevodovky"},
        {"formula": positive_example, "expected": True, "desc": "Pozitívny príklad s motorom a prevodovkou"},
        {"formula": different_positive_example, "expected": True, "desc": "Iný pozitívny príklad s motorom a prevodovkou"}
    ]
    
    # Testovanie príkladov proti modelu
    success = True
    for i, example in enumerate(test_examples):
        print(f"\nTestujem príklad {i+1}: {example['desc']}")
        result = compare_example(example['formula'])
        print(f"Očakávaný výsledok: {example['expected']}, Aktuálny výsledok: {result['is_valid']}")
        
        if example['expected'] != result['is_valid']:
            success = False
            print("❌ TEST ZLYHAL!")
            print(f"Dôvod: {result.get('explanation', '')}")
            for diff in result.get('symbolic_differences', []):
                print(f"  - {diff}")
        else:
            print("✓ TEST USPEŠNÝ")
    
    return success

# Test case 2: Overenie, či model správne identifikuje BMW auto bez motora ako neplatné
def test_missing_engine_in_bmw():
    """Testuje, či model správne rozpozná BMW bez motora ako neplatné."""
    print("\n--- TEST CASE 2: BMW auto bez motora by malo byť neplatné ---")
    
    # Tento test používa už existujúci model, netreba resetovať
    
    # Vytvor a otestuj príklad BMW auta bez motora
    test_example = """
    Ι(my_bmw, BMW)
    Ι(transmission_x, Transmission)
    Ι(wheel_a, Wheel)
    Ι(wheel_b, Wheel)
    Ι(wheel_c, Wheel)
    Ι(wheel_d, Wheel)
    Π(my_bmw, transmission_x)
    Π(my_bmw, wheel_a)
    Π(my_bmw, wheel_b)
    Π(my_bmw, wheel_c)
    Π(my_bmw, wheel_d)
    """
    
    print("Testovanie BMW auta bez motora...")
    result = compare_example(test_example)
    print(f"Očakávaný výsledok: False, Aktuálny výsledok: {result['is_valid']}")
    
    success = not result['is_valid']  # Očakávame, že výsledok bude False
    
    if success:
        print("✓ TEST USPEŠNÝ - Model správne identifikoval chýbajúci motor")
        print(f"Explanation: {result.get('explanation', '')}")
        for diff in result.get('symbolic_differences', []):
            print(f"  - {diff}")
    else:
        print("❌ TEST ZLYHAL - Model neidentifikoval chýbajúci motor ako problém")
    
    return success

def test_generalization():
    """Testuje, či model správne generalizuje na iné objekty tej istej triedy."""
    print("\n--- TEST CASE 3: Generalizácia na nové príklady ---")
    
    # Nový príklad s iným BMW, ale s požadovanými súčasťami
    new_valid_example = """
    Ι(car_x5, BMW_X5)
    Ι(engine_turbo, TurboEngine)
    Ι(transmission_auto, AutomaticTransmission)
    Ι(wheel_front_left, AlloyWheel)
    Ι(wheel_front_right, AlloyWheel)
    Ι(wheel_back_left, AlloyWheel)
    Ι(wheel_back_right, AlloyWheel)
    Π(car_x5, engine_turbo)
    Π(car_x5, transmission_auto)
    Π(car_x5, wheel_front_left)
    Π(car_x5, wheel_front_right)
    Π(car_x5, wheel_back_left)
    Π(car_x5, wheel_back_right)
    """
    
    # Nový príklad s iným BMW bez motora
    new_invalid_example = """
    Ι(car_x3, BMW_X3)
    Ι(trans_manual, ManualTransmission)
    Ι(wheel_standard_1, StandardWheel)
    Ι(wheel_standard_2, StandardWheel)
    Ι(wheel_standard_3, StandardWheel)
    Ι(wheel_standard_4, StandardWheel)
    Π(car_x3, trans_manual)
    Π(car_x3, wheel_standard_1)
    Π(car_x3, wheel_standard_2)
    Π(car_x3, wheel_standard_3)
    Π(car_x3, wheel_standard_4)
    """
    
    # Upload expanded classification tree
    classification_tree = """
    Car(Thing)
    BMW(Car)
    BMW_X5(BMW)
    BMW_X3(BMW)
    
    Component(Thing)
    Engine(Component)
    TurboEngine(Engine)
    
    Transmission(Component)
    AutomaticTransmission(Transmission)
    ManualTransmission(Transmission)
    
    Wheel(Component)
    AlloyWheel(Wheel)
    StandardWheel(Wheel)
    """
    
    # Nahratie rozšíreného klasifikačného stromu
    tree_response = requests.post(f"{BASE_URL}/api/classification_tree", 
                                 json={"tree": classification_tree})
    print(f"Classification tree updated: {tree_response.json()['success']}")
    
    # Testovanie príkladov
    print("\nTestovanie platného príkladu BMW_X5 s motorom a prevodovkou:")
    valid_result = compare_example(new_valid_example)
    print(f"Očakávaný výsledok: True, Aktuálny výsledok: {valid_result['is_valid']}")
    
    print("\nTestovanie neplatného príkladu BMW_X3 bez motora:")
    invalid_result = compare_example(new_invalid_example)
    print(f"Očakávaný výsledok: False, Aktuálny výsledok: {invalid_result['is_valid']}")
    
    success = valid_result['is_valid'] and not invalid_result['is_valid']
    
    if success:
        print("✓ TEST USPEŠNÝ - Model správne generalizoval pravidlá na nové triedy")
        print("\nPre neplatný príklad:")
        for diff in invalid_result.get('symbolic_differences', []):
            print(f"  - {diff}")
    else:
        print("❌ TEST ZLYHAL - Model nesprávne generalizoval")
        if valid_result['is_valid'] == False:
            print("  - Platný príklad bol nesprávne označený ako neplatný")
            for diff in valid_result.get('symbolic_differences', []):
                print(f"    - {diff}")
        if invalid_result['is_valid'] == True:
            print("  - Neplatný príklad bez motora bol nesprávne označený ako platný")
    
    return success

def main():
    """Hlavná funkcia pre spustenie testov."""
    print("=== TESTOVANIE WINSTONOVHO ALGORITMU ===")
    print("Testovací skript pre overenie implementácie Winstonovho algoritmu")
    print("s negatívnymi príkladmi, ktorým chýbajú kľúčové komponenty.")
    
    # Kontrola, či server beží
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print(f"Server beží na {BASE_URL}")
        else:
            print(f"Server beží, ale vracal kód {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"CHYBA: Server na {BASE_URL} nie je dostupný. Spustite ho a skúste znova.")
        return
    
    # Spustenie testovacích prípadov
    test1_result = test_required_components()
    test2_result = test_missing_engine_in_bmw()
    test3_result = test_generalization()

    print("\n===== VÝSLEDKY TESTOVANIA =====")
    print(f"Test 1 (Vyžaduje motor a prevodovku): {'✓ USPEŠNÝ' if test1_result else '❌ ZLYHAL'}")
    print(f"Test 2 (BMW bez motora): {'✓ USPEŠNÝ' if test2_result else '❌ ZLYHAL'}")
    print(f"Test 3 (Generalizácia): {'✓ USPEŠNÝ' if test3_result else '❌ ZLYHAL'}")

    overall = test1_result and test2_result and test3_result
    print(f"\nCelkový výsledok: {'✓ VŠETKY TESTY PREŠLI' if overall else '❌ NIEKTORÉ TESTY ZLYHALI'}")

if __name__ == "__main__":
    main() 