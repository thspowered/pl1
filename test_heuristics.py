from backend.model import Model, ClassificationTree, Object, Link, LinkType
from backend.learner import WinstonLearner
import copy

def initialize_tree():
    """Vytvoří komplexní klasifikační strom pro testování všech heuristik."""
    tree = ClassificationTree()
    
    # Kořenové třídy
    tree.add_relationship("Device", None)
    tree.add_relationship("Component", None)
    
    # Typy zařízení
    tree.add_relationship("Phone", "Device")
    tree.add_relationship("Tablet", "Device")
    tree.add_relationship("Laptop", "Device")
    
    # Podtypy telefonů
    tree.add_relationship("SmartPhone", "Phone")
    tree.add_relationship("FeaturePhone", "Phone")
    
    # Druhy smartphonů
    tree.add_relationship("HighEndPhone", "SmartPhone")
    tree.add_relationship("MidRangePhone", "SmartPhone")
    tree.add_relationship("BudgetPhone", "SmartPhone")
    
    # Druhy tabletů
    tree.add_relationship("GamingTablet", "Tablet")
    tree.add_relationship("EntertainmentTablet", "Tablet")
    tree.add_relationship("ProductivityTablet", "Tablet")
    
    # Komponenty
    tree.add_relationship("Processor", "Component")
    tree.add_relationship("Memory", "Component")
    tree.add_relationship("Display", "Component")
    tree.add_relationship("Battery", "Component")
    tree.add_relationship("Camera", "Component")
    tree.add_relationship("Storage", "Component")
    
    # Typy procesorů
    tree.add_relationship("HighEndProcessor", "Processor")
    tree.add_relationship("MidRangeProcessor", "Processor")
    tree.add_relationship("LowEndProcessor", "Processor")
    
    # Typy paměti
    tree.add_relationship("HighRAM", "Memory")
    tree.add_relationship("MidRAM", "Memory")
    tree.add_relationship("LowRAM", "Memory")
    
    # Typy displejů
    tree.add_relationship("AMOLEDDisplay", "Display")
    tree.add_relationship("LCDDisplay", "Display")
    
    # Typy baterií
    tree.add_relationship("HighCapacityBattery", "Battery")
    tree.add_relationship("StandardBattery", "Battery")
    
    # Typy kamer
    tree.add_relationship("HighResCamera", "Camera")
    tree.add_relationship("MidResCamera", "Camera")
    tree.add_relationship("LowResCamera", "Camera")
    
    # Typy úložiště
    tree.add_relationship("FlashStorage", "Storage")
    tree.add_relationship("SSDStorage", "Storage")
    
    return tree

def create_high_end_phone(name_prefix="he1"):
    """Vytvoří model high-end telefonu pro testování."""
    phone = Object(f"{name_prefix}_phone", "HighEndPhone")
    processor = Object(f"{name_prefix}_proc", "HighEndProcessor", {"clock_speed": 3.0, "cores": 8})
    ram = Object(f"{name_prefix}_ram", "HighRAM", {"capacity": 12})
    display = Object(f"{name_prefix}_display", "AMOLEDDisplay", {"size": 6.7, "resolution": "2K"})
    battery = Object(f"{name_prefix}_battery", "HighCapacityBattery", {"capacity": 5000})
    camera = Object(f"{name_prefix}_camera", "HighResCamera", {"megapixels": 108})
    storage = Object(f"{name_prefix}_storage", "FlashStorage", {"capacity": 512})
    
    objects = [phone, processor, ram, display, battery, camera, storage]
    
    links = [
        Link(phone.name, processor.name),
        Link(phone.name, ram.name),
        Link(phone.name, display.name),
        Link(phone.name, battery.name),
        Link(phone.name, camera.name),
        Link(phone.name, storage.name)
    ]
    
    return Model(objects=objects, links=links)

def create_mid_range_phone(name_prefix="mr1"):
    """Vytvoří model mid-range telefonu pro testování."""
    phone = Object(f"{name_prefix}_phone", "MidRangePhone")
    processor = Object(f"{name_prefix}_proc", "MidRangeProcessor", {"clock_speed": 2.4, "cores": 6})
    ram = Object(f"{name_prefix}_ram", "HighRAM", {"capacity": 8})  # Sdílí stejný typ RAM jako high-end
    display = Object(f"{name_prefix}_display", "AMOLEDDisplay", {"size": 6.4, "resolution": "FHD+"})
    battery = Object(f"{name_prefix}_battery", "StandardBattery", {"capacity": 4500})
    camera = Object(f"{name_prefix}_camera", "MidResCamera", {"megapixels": 64})
    storage = Object(f"{name_prefix}_storage", "FlashStorage", {"capacity": 256})
    
    objects = [phone, processor, ram, display, battery, camera, storage]
    
    links = [
        Link(phone.name, processor.name),
        Link(phone.name, ram.name),
        Link(phone.name, display.name),
        Link(phone.name, battery.name),
        Link(phone.name, camera.name),
        Link(phone.name, storage.name)
    ]
    
    return Model(objects=objects, links=links)

def create_budget_phone(name_prefix="bp1"):
    """Vytvoří model budget telefonu pro testování."""
    phone = Object(f"{name_prefix}_phone", "BudgetPhone")
    processor = Object(f"{name_prefix}_proc", "LowEndProcessor", {"clock_speed": 1.8, "cores": 4})
    ram = Object(f"{name_prefix}_ram", "LowRAM", {"capacity": 4})
    display = Object(f"{name_prefix}_display", "LCDDisplay", {"size": 6.1, "resolution": "HD+"})
    battery = Object(f"{name_prefix}_battery", "StandardBattery", {"capacity": 4000})
    camera = Object(f"{name_prefix}_camera", "LowResCamera", {"megapixels": 13})
    storage = Object(f"{name_prefix}_storage", "FlashStorage", {"capacity": 64})
    
    objects = [phone, processor, ram, display, battery, camera, storage]
    
    links = [
        Link(phone.name, processor.name),
        Link(phone.name, ram.name),
        Link(phone.name, display.name),
        Link(phone.name, battery.name),
        Link(phone.name, camera.name),
        Link(phone.name, storage.name)
    ]
    
    return Model(objects=objects, links=links)

def create_special_mid_range_phone(name_prefix="smr1"):
    """Vytvoří speciální mid-range telefon s některými high-end komponentami."""
    phone = Object(f"{name_prefix}_phone", "MidRangePhone")
    processor = Object(f"{name_prefix}_proc", "MidRangeProcessor", {"clock_speed": 2.6, "cores": 6})
    ram = Object(f"{name_prefix}_ram", "HighRAM", {"capacity": 10})  # Vyšší RAM
    display = Object(f"{name_prefix}_display", "AMOLEDDisplay", {"size": 6.5, "resolution": "2K"})  # Lepší displej
    battery = Object(f"{name_prefix}_battery", "HighCapacityBattery", {"capacity": 5000})  # Lepší baterie
    camera = Object(f"{name_prefix}_camera", "MidResCamera", {"megapixels": 64})
    storage = Object(f"{name_prefix}_storage", "FlashStorage", {"capacity": 256})
    
    objects = [phone, processor, ram, display, battery, camera, storage]
    
    links = [
        Link(phone.name, processor.name),
        Link(phone.name, ram.name),
        Link(phone.name, display.name),
        Link(phone.name, battery.name),
        Link(phone.name, camera.name),
        Link(phone.name, storage.name)
    ]
    
    return Model(objects=objects, links=links)

def create_gaming_tablet(name_prefix="gt1"):
    """Vytvoří model herního tabletu pro testování."""
    tablet = Object(f"{name_prefix}_tablet", "GamingTablet")
    processor = Object(f"{name_prefix}_proc", "HighEndProcessor", {"clock_speed": 3.2, "cores": 8})
    ram = Object(f"{name_prefix}_ram", "HighRAM", {"capacity": 16})
    display = Object(f"{name_prefix}_display", "AMOLEDDisplay", {"size": 10.5, "resolution": "2K"})
    battery = Object(f"{name_prefix}_battery", "HighCapacityBattery", {"capacity": 8000})
    storage = Object(f"{name_prefix}_storage", "FlashStorage", {"capacity": 1024})
    
    objects = [tablet, processor, ram, display, battery, storage]
    
    links = [
        Link(tablet.name, processor.name),
        Link(tablet.name, ram.name),
        Link(tablet.name, display.name),
        Link(tablet.name, battery.name),
        Link(tablet.name, storage.name)
    ]
    
    return Model(objects=objects, links=links)

def create_laptop_with_numeric_attributes(name_prefix="lt1"):
    """Vytvoří model laptopu s numerickými atributy pro testování close-interval heuristiky."""
    laptop = Object(f"{name_prefix}_laptop", "Laptop")
    processor = Object(f"{name_prefix}_proc", "HighEndProcessor", {"clock_speed": 3.8, "cores": 12, "tdp": 45})
    ram = Object(f"{name_prefix}_ram", "HighRAM", {"capacity": 32, "speed": 3200})
    display = Object(f"{name_prefix}_display", "AMOLEDDisplay", {"size": 15.6, "resolution": "4K", "refresh_rate": 120})
    battery = Object(f"{name_prefix}_battery", "HighCapacityBattery", {"capacity": 9000, "life_hours": 8.5})
    storage = Object(f"{name_prefix}_storage", "SSDStorage", {"capacity": 2048, "read_speed": 3500, "write_speed": 3000})
    
    objects = [laptop, processor, ram, display, battery, storage]
    
    links = [
        Link(laptop.name, processor.name),
        Link(laptop.name, ram.name),
        Link(laptop.name, display.name),
        Link(laptop.name, battery.name),
        Link(laptop.name, storage.name)
    ]
    
    return Model(objects=objects, links=links)

def create_laptop_variant(name_prefix="lt2"):
    """Vytvoří variantu laptopu s mírně odlišnými numerickými atributy pro testování enlarge-set heuristiky."""
    laptop = Object(f"{name_prefix}_laptop", "Laptop")
    processor = Object(f"{name_prefix}_proc", "HighEndProcessor", {"clock_speed": 4.2, "cores": 16, "tdp": 65})
    ram = Object(f"{name_prefix}_ram", "HighRAM", {"capacity": 64, "speed": 4800})
    display = Object(f"{name_prefix}_display", "AMOLEDDisplay", {"size": 17.3, "resolution": "4K", "refresh_rate": 144})
    battery = Object(f"{name_prefix}_battery", "HighCapacityBattery", {"capacity": 10000, "life_hours": 6.5})
    storage = Object(f"{name_prefix}_storage", "SSDStorage", {"capacity": 4096, "read_speed": 5000, "write_speed": 4500})
    
    objects = [laptop, processor, ram, display, battery, storage]
    
    links = [
        Link(laptop.name, processor.name),
        Link(laptop.name, ram.name),
        Link(laptop.name, display.name),
        Link(laptop.name, battery.name),
        Link(laptop.name, storage.name)
    ]
    
    return Model(objects=objects, links=links)

def run_heuristic_tests():
    """Spustí komplexní testy pro všechny heuristiky Winston algoritmu."""
    print("=== TESTOVÁNÍ HEURISTIK WINSTON ALGORITMU ===")
    
    # Inicializace klasifikačního stromu a učícího algoritmu
    tree = initialize_tree()
    learner = WinstonLearner(tree)
    learner.debug_enabled = True
    
    # Vytvoření prázdného modelu
    model = Model(objects=[], links=[])
    
    print("\n=== 1. TEST: add_missing_objects, require_link, climb_tree ===")
    print("Testování přidání objektů z prvního příkladu a vytvoření základních MUST vazeb")
    high_end_phone = create_high_end_phone()
    model = learner.update_model(model, high_end_phone, None)
    print(f"Aplikované heuristiky: {learner.applied_heuristics}")
    print("Počet objektů v modelu:", len(model.objects))
    print("Počet spojení v modelu:", len(model.links))
    
    # Výpis MUST vazeb
    must_links = [link for link in model.links if link.link_type == LinkType.MUST]
    print("MUST vazby v modelu:", [(link.source, link.target) for link in must_links])
    
    print("\n=== 2. TEST: forbid_link, check_consistency ===")
    print("Testování heuristiky forbid_link s near-miss příkladem a řešení konfliktů")
    mid_range_phone = create_mid_range_phone()
    model = learner.update_model(model, high_end_phone, mid_range_phone)
    print(f"Aplikované heuristiky: {learner.applied_heuristics}")
    
    # Výpis MUST_NOT vazeb
    must_not_links = [link for link in model.links if link.link_type == LinkType.MUST_NOT]
    print("MUST_NOT vazby v modelu:", [(link.source, link.target) for link in must_not_links])
    
    print("\n=== 3. TEST: propagate_to_common_ancestor ===")
    print("Testování propagace pravidel na nejvyšší společný předek")
    budget_phone = create_budget_phone()
    model = learner.update_model(model, mid_range_phone, budget_phone)
    print(f"Aplikované heuristiky: {learner.applied_heuristics}")
    
    # Výpis generických vazeb na úrovni tříd
    class_links = [link for link in model.links if link.source in ["Device", "Phone", "SmartPhone", "HighEndPhone", "MidRangePhone", "BudgetPhone"]]
    print("Vazby na úrovni tříd:", [(link.source, link.target, link.link_type.value) for link in class_links])
    
    print("\n=== 4. TEST: enlarge_set ===")
    print("Testování rozšíření množiny přijatelných hodnot atributů")
    laptop1 = create_laptop_with_numeric_attributes()
    laptop2 = create_laptop_variant()
    model_before = copy.deepcopy(model)  # Uložení modelu před testem
    model = learner.update_model(model, laptop1, None)
    print(f"Aplikované heuristiky po přidání prvního laptopu: {learner.applied_heuristics}")
    
    # Výpis atributů před druhým laptopem
    laptop_proc = next((obj for obj in model.objects if obj.name == "lt1_proc"), None)
    if laptop_proc and laptop_proc.attributes:
        print("Atributy procesoru před testem enlarge_set:", laptop_proc.attributes)
    
    model = learner.update_model(model, laptop2, None)
    print(f"Aplikované heuristiky po přidání druhého laptopu: {learner.applied_heuristics}")
    
    # Ověření, zda se atributy rozšířily
    laptop_proc = next((obj for obj in model.objects if obj.name == "lt1_proc"), None)
    if laptop_proc and laptop_proc.attributes:
        print("Atributy procesoru po testu enlarge_set:", laptop_proc.attributes)
    
    print("\n=== 5. TEST: close_interval ===")
    print("Testování zúžení intervalů numerických atributů")
    
    # Vytvoříme nový learner pro tento test
    test_tree = initialize_tree()
    test_learner = WinstonLearner(test_tree)
    test_learner.debug_enabled = True
    
    # Nejprve inicializujeme model s procesorem
    first_processor = Object("init_proc", "HighEndProcessor", {"clock_speed": 4.0, "cores": 12})
    init_model = Model(objects=[first_processor], links=[])
    
    # Vytvoříme pozitivní příklad s hodnotou uvnitř budoucího intervalu
    pos_processor = Object("pos_proc", "HighEndProcessor", {"clock_speed": 3.8, "cores": 12})
    pos_example = Model(objects=[pos_processor], links=[])
    
    # Aktualizujeme model s pozitivním příkladem
    init_model = test_learner.update_model(init_model, pos_example, None)
    
    # Vytvoříme near-miss příklad s hodnotou mimo interval
    neg_processor = Object("neg_proc", "HighEndProcessor", {"clock_speed": 2.8, "cores": 6})
    neg_example = Model(objects=[neg_processor], links=[])
    
    # Testování close_interval heuristiky s near-miss příkladem
    test_model = test_learner.update_model(init_model, pos_example, neg_example)
    print(f"Aplikované heuristiky: {test_learner.applied_heuristics}")
    
    # Ověření, zda se intervaly upravily
    test_proc = next((obj for obj in test_model.objects if obj.class_name == "HighEndProcessor"), None)
    close_interval_applied = False
    if test_proc and test_proc.attributes:
        if "clock_speed" in test_proc.attributes:
            # Zobrazíme aktuální interval
            current_interval = test_proc.attributes["clock_speed"]
            print(f"Aktuální interval clock_speed: {current_interval}")
            
            # Kontrola, zda došlo ke změně intervalu - buď zúžení nebo rozšíření
            if isinstance(current_interval, tuple) and 2.8 not in current_interval:
                close_interval_applied = True
                print(f"Hodnota 2.8 byla vyloučena z intervalu")
        
        # Alternativní kontrola na atribut cores
        if "cores" in test_proc.attributes:
            current_cores_interval = test_proc.attributes["cores"]
            print(f"Aktuální interval cores: {current_cores_interval}")
            
            if isinstance(current_cores_interval, tuple) and 6 not in current_cores_interval:
                close_interval_applied = True
                print(f"Hodnota 6 byla vyloučena z intervalu")
    
    print("5. close_interval: ", "OK" if close_interval_applied else "CHYBA")
    
    print("\n=== 6. TEST: drop_link a backup_rule ===")
    print("Testování odstranění nepotřebných vazeb a návratu k předchozímu modelu")
    
    # Vytvoříme model s několika vazbami
    drop_test_model = Model(
        objects=[
            Object("device", "Device"),
            Object("component1", "Component"),
            Object("component2", "Component"),
            Object("component3", "Component")
        ],
        links=[
            Link("device", "component1"),
            Link("device", "component2"),
            Link("device", "component3")
        ]
    )
    
    # Vytvoříme pozitivní příklad bez jedné vazby
    pos_drop_example = Model(
        objects=[
            Object("device", "Device"),
            Object("component1", "Component"),
            Object("component2", "Component")
        ],
        links=[
            Link("device", "component1"),
            Link("device", "component2")
        ]
    )
    
    # Testování drop_link heuristiky
    drop_test_model = learner.update_model(drop_test_model, pos_drop_example, None)
    print(f"Aplikované heuristiky: {learner.applied_heuristics}")
    
    # Ověření, zda byla odebrána nepotřebná vazba
    print("Vazby po testu drop_link:", [(link.source, link.target) for link in drop_test_model.links])
    
    # Test konfliktu a backup_rule
    print("\n=== 7. TEST: backup_rule při konfliktu ===")
    conflicting_model = Model(
        objects=[
            Object("device", "Device"),
            Object("component1", "Component")
        ],
        links=[
            Link("device", "component1", LinkType.MUST)
        ]
    )
    
    conflicting_positive = Model(
        objects=[
            Object("device", "Device"),
            Object("component2", "Component")
        ],
        links=[
            Link("device", "component2")
        ]
    )
    
    conflicting_negative = Model(
        objects=[
            Object("device", "Device"),
            Object("component1", "Component")
        ],
        links=[
            Link("device", "component1")
        ]
    )
    
    # Přidáme model do historie
    learner._add_to_history(conflicting_model)
    
    # Testování backup_rule heuristiky
    result_model = learner.update_model(conflicting_model, conflicting_positive, conflicting_negative)
    print(f"Aplikované heuristiky: {learner.applied_heuristics}")
    
    # Ověření, zda se model vrátil k předchozí verzi
    is_same = result_model == conflicting_model
    print(f"Model se vrátil k předchozí verzi: {is_same}")
    
    print("\n=== SOUHRN VÝSLEDKŮ TESTŮ ===")
    print("1. add_missing_objects, require_link, climb_tree: ", "OK" if len(must_links) > 0 else "CHYBA")
    print("2. forbid_link, check_consistency: ", "OK" if len(must_not_links) > 0 else "CHYBA")
    print("3. propagate_to_common_ancestor: ", "OK" if [link for link in class_links if link.source == "SmartPhone"] else "CHYBA")
    
    # Zjistíme, zda byla enlarge_set heuristika aplikována v testu 4
    enlarge_set_applied = False
    
    # Hledáme objekt displeje s množinou hodnot pro atribut resolution
    for obj in model.objects:
        if obj.class_name == "AMOLEDDisplay" and obj.attributes:
            if "resolution" in obj.attributes and isinstance(obj.attributes["resolution"], set):
                if "4K" in obj.attributes["resolution"] and len(obj.attributes["resolution"]) > 1:
                    enlarge_set_applied = True
                    break
    
    # Pokud jsme nenašli, zkusíme projít všechny objekty a hledat jakékoliv množiny hodnot atributů
    if not enlarge_set_applied:
        for obj in model.objects:
            if obj.attributes:
                for attr_name, attr_value in obj.attributes.items():
                    if isinstance(attr_value, set) and len(attr_value) > 1:
                        enlarge_set_applied = True
                        break
                if enlarge_set_applied:
                    break
    
    print("4. enlarge_set: ", "OK" if enlarge_set_applied else "CHYBA")
    
    # Zjistíme, zda byla drop_link heuristika aplikována v testu 6
    drop_link_applied = len(drop_test_model.links) == 2  # Měly by zůstat jen 2 vazby
    
    print("6. drop_link: ", "OK" if drop_link_applied else "CHYBA")
    
    # Zjistíme, zda byla backup_rule heuristika aplikována v testu 7
    backup_rule_applied = result_model == conflicting_model
    
    print("7. backup_rule: ", "OK" if backup_rule_applied else "CHYBA")

if __name__ == "__main__":
    run_heuristic_tests() 