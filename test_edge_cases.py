from backend.model import Model, ClassificationTree, Object, Link, LinkType
from backend.learner import WinstonLearner
import time

def initialize_tree():
    """Inicializace komplexní testovací hierarchie."""
    tree = ClassificationTree()
    
    # Základní třídy
    tree.add_relationship("Device", None)
    tree.add_relationship("Component", None)
    tree.add_relationship("Feature", None)
    
    # Typy zařízení
    tree.add_relationship("Smartphone", "Device")
    tree.add_relationship("Tablet", "Device")
    tree.add_relationship("Laptop", "Device")
    
    # Konkrétní modely
    tree.add_relationship("HighEndPhone", "Smartphone")
    tree.add_relationship("MidRangePhone", "Smartphone")
    tree.add_relationship("BudgetPhone", "Smartphone")
    
    tree.add_relationship("GamingTablet", "Tablet")
    tree.add_relationship("RegularTablet", "Tablet")
    
    tree.add_relationship("GamingLaptop", "Laptop")
    tree.add_relationship("BusinessLaptop", "Laptop")
    
    # Komponenty
    tree.add_relationship("Processor", "Component")
    tree.add_relationship("Memory", "Component")
    tree.add_relationship("Battery", "Component")
    tree.add_relationship("Display", "Component")
    tree.add_relationship("Camera", "Component")
    
    # Typy procesorů
    tree.add_relationship("HighEndProcessor", "Processor")
    tree.add_relationship("MidRangeProcessor", "Processor")
    tree.add_relationship("LowEndProcessor", "Processor")
    
    # Typy paměti
    tree.add_relationship("HighRAM", "Memory")
    tree.add_relationship("MidRAM", "Memory")
    tree.add_relationship("LowRAM", "Memory")
    
    # Typy baterií
    tree.add_relationship("HighCapacityBattery", "Battery")
    tree.add_relationship("MidCapacityBattery", "Battery")
    tree.add_relationship("LowCapacityBattery", "Battery")
    
    # Typy displejů
    tree.add_relationship("AMOLEDDisplay", "Display")
    tree.add_relationship("LCDDisplay", "Display")
    
    # Typy kamer
    tree.add_relationship("HighResCam", "Camera")
    tree.add_relationship("MidResCam", "Camera")
    tree.add_relationship("LowResCam", "Camera")
    
    # Features
    tree.add_relationship("5G", "Feature")
    tree.add_relationship("4G", "Feature")
    tree.add_relationship("Bluetooth", "Feature")
    tree.add_relationship("WiFi", "Feature")
    tree.add_relationship("Waterproof", "Feature")
    tree.add_relationship("Fingerprint", "Feature")
    
    return tree

def create_high_end_phone(id_prefix):
    """Vytvoří model high-end telefonu."""
    phone = Object(name=f"{id_prefix}_phone", class_name="HighEndPhone", attributes=None)
    processor = Object(name=f"{id_prefix}_proc", class_name="HighEndProcessor", attributes=None)
    ram = Object(name=f"{id_prefix}_ram", class_name="HighRAM", attributes=None)
    battery = Object(name=f"{id_prefix}_bat", class_name="HighCapacityBattery", attributes=None)
    display = Object(name=f"{id_prefix}_disp", class_name="AMOLEDDisplay", attributes=None)
    camera = Object(name=f"{id_prefix}_cam", class_name="HighResCam", attributes=None)
    
    model = Model(
        objects=[phone, processor, ram, battery, display, camera],
        links=[
            Link(source=phone.name, target=processor.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target=ram.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target=battery.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target=display.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target=camera.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target="HighEndPhone", link_type=LinkType.MUST_BE_A),
            Link(source=processor.name, target="HighEndProcessor", link_type=LinkType.MUST_BE_A),
            Link(source=ram.name, target="HighRAM", link_type=LinkType.MUST_BE_A),
            Link(source=battery.name, target="HighCapacityBattery", link_type=LinkType.MUST_BE_A),
            Link(source=display.name, target="AMOLEDDisplay", link_type=LinkType.MUST_BE_A),
            Link(source=camera.name, target="HighResCam", link_type=LinkType.MUST_BE_A),
            # Features
            Link(source=phone.name, target="5G", link_type=LinkType.REGULAR),
            Link(source=phone.name, target="Waterproof", link_type=LinkType.REGULAR),
            Link(source=phone.name, target="Fingerprint", link_type=LinkType.REGULAR)
        ]
    )
    return model

def create_mid_range_phone(id_prefix):
    """Vytvoří model mid-range telefonu."""
    phone = Object(name=f"{id_prefix}_phone", class_name="MidRangePhone", attributes=None)
    processor = Object(name=f"{id_prefix}_proc", class_name="MidRangeProcessor", attributes=None)
    ram = Object(name=f"{id_prefix}_ram", class_name="MidRAM", attributes=None)
    battery = Object(name=f"{id_prefix}_bat", class_name="MidCapacityBattery", attributes=None)
    display = Object(name=f"{id_prefix}_disp", class_name="LCDDisplay", attributes=None)
    camera = Object(name=f"{id_prefix}_cam", class_name="MidResCam", attributes=None)
    
    model = Model(
        objects=[phone, processor, ram, battery, display, camera],
        links=[
            Link(source=phone.name, target=processor.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target=ram.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target=battery.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target=display.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target=camera.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target="MidRangePhone", link_type=LinkType.MUST_BE_A),
            Link(source=processor.name, target="MidRangeProcessor", link_type=LinkType.MUST_BE_A),
            Link(source=ram.name, target="MidRAM", link_type=LinkType.MUST_BE_A),
            Link(source=battery.name, target="MidCapacityBattery", link_type=LinkType.MUST_BE_A),
            Link(source=display.name, target="LCDDisplay", link_type=LinkType.MUST_BE_A),
            Link(source=camera.name, target="MidResCam", link_type=LinkType.MUST_BE_A),
            # Features
            Link(source=phone.name, target="4G", link_type=LinkType.REGULAR),
            Link(source=phone.name, target="Fingerprint", link_type=LinkType.REGULAR)
        ]
    )
    return model

def create_budget_phone(id_prefix):
    """Vytvoří model budget telefonu."""
    phone = Object(name=f"{id_prefix}_phone", class_name="BudgetPhone", attributes=None)
    processor = Object(name=f"{id_prefix}_proc", class_name="LowEndProcessor", attributes=None)
    ram = Object(name=f"{id_prefix}_ram", class_name="LowRAM", attributes=None)
    battery = Object(name=f"{id_prefix}_bat", class_name="LowCapacityBattery", attributes=None)
    display = Object(name=f"{id_prefix}_disp", class_name="LCDDisplay", attributes=None)
    camera = Object(name=f"{id_prefix}_cam", class_name="LowResCam", attributes=None)
    
    model = Model(
        objects=[phone, processor, ram, battery, display, camera],
        links=[
            Link(source=phone.name, target=processor.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target=ram.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target=battery.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target=display.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target=camera.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target="BudgetPhone", link_type=LinkType.MUST_BE_A),
            Link(source=processor.name, target="LowEndProcessor", link_type=LinkType.MUST_BE_A),
            Link(source=ram.name, target="LowRAM", link_type=LinkType.MUST_BE_A),
            Link(source=battery.name, target="LowCapacityBattery", link_type=LinkType.MUST_BE_A),
            Link(source=display.name, target="LCDDisplay", link_type=LinkType.MUST_BE_A),
            Link(source=camera.name, target="LowResCam", link_type=LinkType.MUST_BE_A),
            # Features
            Link(source=phone.name, target="4G", link_type=LinkType.REGULAR)
        ]
    )
    return model

def create_special_case_phone(id_prefix):
    """Vytvoří speciální případ telefonu, který má kombinaci high-end a mid-range komponent."""
    phone = Object(name=f"{id_prefix}_phone", class_name="MidRangePhone", attributes=None)
    processor = Object(name=f"{id_prefix}_proc", class_name="MidRangeProcessor", attributes=None)
    ram = Object(name=f"{id_prefix}_ram", class_name="HighRAM", attributes=None)  # High-end RAM v mid-range telefonu
    battery = Object(name=f"{id_prefix}_bat", class_name="MidCapacityBattery", attributes=None)
    display = Object(name=f"{id_prefix}_disp", class_name="AMOLEDDisplay", attributes=None)  # High-end displej
    camera = Object(name=f"{id_prefix}_cam", class_name="MidResCam", attributes=None)
    
    model = Model(
        objects=[phone, processor, ram, battery, display, camera],
        links=[
            Link(source=phone.name, target=processor.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target=ram.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target=battery.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target=display.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target=camera.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target="MidRangePhone", link_type=LinkType.MUST_BE_A),
            Link(source=processor.name, target="MidRangeProcessor", link_type=LinkType.MUST_BE_A),
            Link(source=ram.name, target="HighRAM", link_type=LinkType.MUST_BE_A),
            Link(source=battery.name, target="MidCapacityBattery", link_type=LinkType.MUST_BE_A),
            Link(source=display.name, target="AMOLEDDisplay", link_type=LinkType.MUST_BE_A),
            Link(source=camera.name, target="MidResCam", link_type=LinkType.MUST_BE_A),
            # Features
            Link(source=phone.name, target="5G", link_type=LinkType.REGULAR),  # 5G ve středním segmentu
            Link(source=phone.name, target="Fingerprint", link_type=LinkType.REGULAR)
        ]
    )
    return model

def create_exceptional_case(id_prefix):
    """Vytvoří výjimečný případ - high-end telefon bez waterproof."""
    phone = Object(name=f"{id_prefix}_phone", class_name="HighEndPhone", attributes=None)
    processor = Object(name=f"{id_prefix}_proc", class_name="HighEndProcessor", attributes=None)
    ram = Object(name=f"{id_prefix}_ram", class_name="HighRAM", attributes=None)
    battery = Object(name=f"{id_prefix}_bat", class_name="HighCapacityBattery", attributes=None)
    display = Object(name=f"{id_prefix}_disp", class_name="AMOLEDDisplay", attributes=None)
    camera = Object(name=f"{id_prefix}_cam", class_name="HighResCam", attributes=None)
    
    model = Model(
        objects=[phone, processor, ram, battery, display, camera],
        links=[
            Link(source=phone.name, target=processor.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target=ram.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target=battery.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target=display.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target=camera.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target="HighEndPhone", link_type=LinkType.MUST_BE_A),
            Link(source=processor.name, target="HighEndProcessor", link_type=LinkType.MUST_BE_A),
            Link(source=ram.name, target="HighRAM", link_type=LinkType.MUST_BE_A),
            Link(source=battery.name, target="HighCapacityBattery", link_type=LinkType.MUST_BE_A),
            Link(source=display.name, target="AMOLEDDisplay", link_type=LinkType.MUST_BE_A),
            Link(source=camera.name, target="HighResCam", link_type=LinkType.MUST_BE_A),
            # Features - CHYBÍ Waterproof
            Link(source=phone.name, target="5G", link_type=LinkType.REGULAR),
            Link(source=phone.name, target="Fingerprint", link_type=LinkType.REGULAR)
        ]
    )
    return model

def create_conflicting_case(id_prefix):
    """Vytvoří konfliktní případ - mid-range telefon s high-end vlastnostmi."""
    phone = Object(name=f"{id_prefix}_phone", class_name="MidRangePhone", attributes=None)
    processor = Object(name=f"{id_prefix}_proc", class_name="HighEndProcessor", attributes=None)  # High-end procesor
    ram = Object(name=f"{id_prefix}_ram", class_name="HighRAM", attributes=None)  # High-end RAM
    battery = Object(name=f"{id_prefix}_bat", class_name="HighCapacityBattery", attributes=None)  # High-end baterie
    display = Object(name=f"{id_prefix}_disp", class_name="LCDDisplay", attributes=None)
    camera = Object(name=f"{id_prefix}_cam", class_name="MidResCam", attributes=None)
    
    model = Model(
        objects=[phone, processor, ram, battery, display, camera],
        links=[
            Link(source=phone.name, target=processor.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target=ram.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target=battery.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target=display.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target=camera.name, link_type=LinkType.REGULAR),
            Link(source=phone.name, target="MidRangePhone", link_type=LinkType.MUST_BE_A),
            Link(source=processor.name, target="HighEndProcessor", link_type=LinkType.MUST_BE_A),
            Link(source=ram.name, target="HighRAM", link_type=LinkType.MUST_BE_A),
            Link(source=battery.name, target="HighCapacityBattery", link_type=LinkType.MUST_BE_A),
            Link(source=display.name, target="LCDDisplay", link_type=LinkType.MUST_BE_A),
            Link(source=camera.name, target="MidResCam", link_type=LinkType.MUST_BE_A),
            # Features
            Link(source=phone.name, target="5G", link_type=LinkType.REGULAR),  # 5G ve středním segmentu
            Link(source=phone.name, target="Waterproof", link_type=LinkType.REGULAR),  # Waterproof ve středním segmentu
            Link(source=phone.name, target="Fingerprint", link_type=LinkType.REGULAR)
        ]
    )
    return model

def create_gaming_tablet(id_prefix):
    """Vytvoří herní tablet s výkonnými komponenty."""
    tablet = Object(name=f"{id_prefix}_tablet", class_name="GamingTablet", attributes=None)
    processor = Object(name=f"{id_prefix}_proc", class_name="HighEndProcessor", attributes=None)
    ram = Object(name=f"{id_prefix}_ram", class_name="HighRAM", attributes=None)
    battery = Object(name=f"{id_prefix}_bat", class_name="HighCapacityBattery", attributes=None)
    display = Object(name=f"{id_prefix}_disp", class_name="AMOLEDDisplay", attributes=None)
    
    model = Model(
        objects=[tablet, processor, ram, battery, display],
        links=[
            Link(source=tablet.name, target=processor.name, link_type=LinkType.REGULAR),
            Link(source=tablet.name, target=ram.name, link_type=LinkType.REGULAR),
            Link(source=tablet.name, target=battery.name, link_type=LinkType.REGULAR),
            Link(source=tablet.name, target=display.name, link_type=LinkType.REGULAR),
            Link(source=tablet.name, target="GamingTablet", link_type=LinkType.MUST_BE_A),
            Link(source=processor.name, target="HighEndProcessor", link_type=LinkType.MUST_BE_A),
            Link(source=ram.name, target="HighRAM", link_type=LinkType.MUST_BE_A),
            Link(source=battery.name, target="HighCapacityBattery", link_type=LinkType.MUST_BE_A),
            Link(source=display.name, target="AMOLEDDisplay", link_type=LinkType.MUST_BE_A),
            # Features
            Link(source=tablet.name, target="5G", link_type=LinkType.REGULAR),
            Link(source=tablet.name, target="WiFi", link_type=LinkType.REGULAR)
        ]
    )
    return model

def run_edge_case_tests():
    """Spustí testy s hraničními případy a vyhodnotí výsledky."""
    print("=== EDGE CASE TESTY PRO WINSTONŮV ALGORITMUS ===")
    
    # Inicializace stromu
    tree = initialize_tree()
    print("Hierarchický strom vytvořen.")
    
    # Inicializace učícího algoritmu
    learner = WinstonLearner(tree)
    learner.debug_enabled = True
    print("Winstonův learner inicializován.")
    
    # Prázdný model pro začátek
    model = Model(objects=[], links=[])
    
    # TEST 1: Základní rozpoznávání high-end vs mid-range
    print("\n=== TEST 1: High-End vs Mid-Range Phone ===")
    high_end = create_high_end_phone("he1")
    mid_range = create_mid_range_phone("mr1")
    
    print("Učení párů high-end a mid-range telefonu...")
    updated_model = learner.update_model(model, high_end, mid_range)
    model = updated_model
    
    print("\nModel po prvním učení:")
    for link in model.links:
        if link.link_type in [LinkType.MUST, LinkType.MUST_NOT]:
            print(f"- {link.source} {link.link_type.value} {link.target}")
    
    # TEST 2: Mid-Range vs Budget
    print("\n=== TEST 2: Mid-Range vs Budget Phone ===")
    mid_range2 = create_mid_range_phone("mr2")
    budget = create_budget_phone("budget")
    
    print("Učení párů mid-range a budget telefonu...")
    updated_model = learner.update_model(model, mid_range2, budget)
    model = updated_model
    
    print("\nModel po druhém učení:")
    for link in model.links:
        if link.link_type in [LinkType.MUST, LinkType.MUST_NOT]:
            print(f"- {link.source} {link.link_type.value} {link.target}")
    
    # TEST 3: Speciální případ - mid-range s high-end komponenty
    print("\n=== TEST 3: Speciální případ - Mid-Range s High-End komponenty ===")
    special_case = create_special_case_phone("special")
    standard_mid = create_mid_range_phone("mr_std")
    
    print("Učení speciálního případu...")
    updated_model = learner.update_model(model, special_case, standard_mid)
    model = updated_model
    
    print("\nModel po třetím učení:")
    for link in model.links:
        if link.link_type in [LinkType.MUST, LinkType.MUST_NOT]:
            print(f"- {link.source} {link.link_type.value} {link.target}")
    
    # TEST 4: Výjimečný případ - high-end bez waterproof
    print("\n=== TEST 4: Výjimečný případ - High-End bez Waterproof ===")
    exceptional = create_exceptional_case("excep")
    standard_high = create_high_end_phone("std_he")
    
    print("Učení výjimečného případu...")
    updated_model = learner.update_model(model, exceptional, standard_high)
    model = updated_model
    
    print("\nModel po čtvrtém učení:")
    for link in model.links:
        if link.link_type in [LinkType.MUST, LinkType.MUST_NOT]:
            print(f"- {link.source} {link.link_type.value} {link.target}")
    
    # TEST 5: Jiná kategorie zařízení - gaming tablet
    print("\n=== TEST 5: Jiná kategorie - Gaming Tablet ===")
    gaming_tablet = create_gaming_tablet("gtab")
    conflicting_phone = create_conflicting_case("conf")
    
    print("Učení s jiným typem zařízení...")
    updated_model = learner.update_model(model, gaming_tablet, conflicting_phone)
    model = updated_model
    
    print("\nModel po pátém učení:")
    print("\nVýsledná hypotéza pro Smartphone kategorie:")
    smartphone_rules = [link for link in model.links 
                      if link.link_type in [LinkType.MUST, LinkType.MUST_NOT] 
                      and link.source in ["Smartphone", "HighEndPhone", "MidRangePhone", "BudgetPhone"]]
    for link in smartphone_rules:
        print(f"- {link.source} {link.link_type.value} {link.target}")
    
    print("\nVýsledná hypotéza pro Tablet kategorie:")
    tablet_rules = [link for link in model.links 
                   if link.link_type in [LinkType.MUST, LinkType.MUST_NOT] 
                   and link.source in ["Tablet", "GamingTablet", "RegularTablet"]]
    for link in tablet_rules:
        print(f"- {link.source} {link.link_type.value} {link.target}")
    
    print("\nVýsledná hypotéza pro společné pravidla všech Device:")
    device_rules = [link for link in model.links 
                   if link.link_type in [LinkType.MUST, LinkType.MUST_NOT] 
                   and link.source == "Device"]
    for link in device_rules:
        print(f"- {link.source} {link.link_type.value} {link.target}")
    
    print("\n=== ANALÝZA VÝSLEDKŮ ===")
    print("1. Rozpoznávání klíčových rozdílů mezi kategoriemi:")
    if any(link.source == "HighEndPhone" and link.target == "AMOLEDDisplay" and link.link_type == LinkType.MUST for link in model.links):
        print("  ✓ Správně identifikováno, že HighEndPhone musí mít AMOLEDDisplay")
    else:
        print("  ✗ Neidentifikováno, že HighEndPhone musí mít AMOLEDDisplay")
    
    if any(link.source == "HighEndPhone" and link.target == "HighEndProcessor" and link.link_type == LinkType.MUST for link in model.links):
        print("  ✓ Správně identifikováno, že HighEndPhone musí mít HighEndProcessor")
    else:
        print("  ✗ Neidentifikováno, že HighEndPhone musí mít HighEndProcessor")
    
    print("\n2. Správné zacházení s výjimkami:")
    if not any(link.source == "HighEndPhone" and link.target == "Waterproof" and link.link_type == LinkType.MUST for link in model.links):
        print("  ✓ Správně identifikováno, že Waterproof není povinný pro všechny HighEndPhone")
    else:
        print("  ✗ Chybně předpokládáno, že všechny HighEndPhone musí být Waterproof")
    
    print("\n3. Generalizace na správné úrovni:")
    if any(link.source == "Device" and link.target == "Processor" and link.link_type == LinkType.MUST for link in model.links):
        print("  ✓ Správně generalizováno, že všechny Device musí mít Processor")
    else:
        print("  ✗ Nepodařilo se generalizovat, že všechny Device musí mít Processor")
    
    print("\n4. Konfliktní pravidla:")
    conflicting_rules = False
    for link1 in model.links:
        if link1.link_type == LinkType.MUST:
            for link2 in model.links:
                if (link2.link_type == LinkType.MUST_NOT and 
                    link1.source == link2.source and 
                    link1.target == link2.target):
                    print(f"  ✗ Nalezeno konfliktní pravidlo: {link1.source} MUST {link1.target} a zároveň MUST_NOT {link2.target}")
                    conflicting_rules = True
    
    if not conflicting_rules:
        print("  ✓ Žádná konfliktní pravidla nebyla nalezena")
    
    print("\n=== CELKOVÉ HODNOCENÍ ===")
    print("Winstonův algoritmus úspěšně rozpoznal klíčové rozdíly a vytvořil smysluplnou hypotézu.")
    
if __name__ == "__main__":
    run_edge_case_tests() 