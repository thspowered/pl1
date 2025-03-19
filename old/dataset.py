from models import ClassificationTree
from pl1 import parse_pl1_input

def create_training_dataset():
    """Vytvorí trénovací dataset s BMW automobilmi v PL1 formáte"""
    
    # Vytvor klasifikačný strom pre BMW automobily
    tree = ClassificationTree()
    tree.add_relationship("Vehicle", "Car")
    tree.add_relationship("Car", "BMW")
    tree.add_relationship("BMW", "Sedan")
    tree.add_relationship("BMW", "SUV")
    tree.add_relationship("BMW", "Coupe")
    tree.add_relationship("BMW", "Touring")
    tree.add_relationship("Vehicle", "Non_BMW")  # Pre near-miss príklady
    
    # BMW modelové rady
    tree.add_relationship("Sedan", "Series3")
    tree.add_relationship("Sedan", "Series5")
    tree.add_relationship("Sedan", "Series7")
    tree.add_relationship("SUV", "X3")
    tree.add_relationship("SUV", "X5")
    tree.add_relationship("SUV", "X7")
    tree.add_relationship("Coupe", "Series4")
    tree.add_relationship("Coupe", "Series8")
    
    # Dobré príklady BMW áut v PL1 formáte
    good_examples_pl1 = """
    # BMW 3 Series - Sedan s benzínovým motorom
    IS_A(bmw_320i, Series3).
    ATTRIBUTE(bmw_320i, model_type, 3_series).
    ATTRIBUTE(bmw_320i, body_type, sedan).
    HAS(bmw_320i, engine_20i).
    HAS(bmw_320i, transmission_auto).
    HAS(bmw_320i, rwd_drive).
    ATTRIBUTE(bmw_320i, trim_level, sport_line).
    ATTRIBUTE(engine_20i, displacement, 2.0).
    ATTRIBUTE(engine_20i, fuel_type, petrol).
    ATTRIBUTE(engine_20i, power_kw, 135).
    ATTRIBUTE(transmission_auto, type, steptronic).
    ATTRIBUTE(rwd_drive, drive_type, rear_wheel).
    
    # BMW 5 Series - Sedan s dieselovým motorom a xDrive
    IS_A(bmw_530d, Series5).
    ATTRIBUTE(bmw_530d, model_type, 5_series).
    ATTRIBUTE(bmw_530d, body_type, sedan).
    HAS(bmw_530d, engine_30d).
    HAS(bmw_530d, transmission_auto).
    HAS(bmw_530d, xdrive_system).
    ATTRIBUTE(bmw_530d, trim_level, luxury_line).
    ATTRIBUTE(engine_30d, displacement, 3.0).
    ATTRIBUTE(engine_30d, fuel_type, diesel).
    ATTRIBUTE(engine_30d, power_kw, 195).
    ATTRIBUTE(transmission_auto, type, steptronic).
    ATTRIBUTE(xdrive_system, drive_type, all_wheel).
    
    # BMW X5 - SUV s benzínovým motorom
    IS_A(bmw_x5_40i, X5).
    ATTRIBUTE(bmw_x5_40i, model_type, x5).
    ATTRIBUTE(bmw_x5_40i, body_type, suv).
    HAS(bmw_x5_40i, engine_40i).
    HAS(bmw_x5_40i, transmission_auto).
    HAS(bmw_x5_40i, xdrive_system).
    ATTRIBUTE(bmw_x5_40i, trim_level, m_sport).
    ATTRIBUTE(engine_40i, displacement, 3.0).
    ATTRIBUTE(engine_40i, fuel_type, petrol).
    ATTRIBUTE(engine_40i, power_kw, 250).
    ATTRIBUTE(transmission_auto, type, steptronic).
    ATTRIBUTE(xdrive_system, drive_type, all_wheel).
    
    # BMW 4 Series - Kupé s benzínovým motorom
    IS_A(bmw_430i, Series4).
    ATTRIBUTE(bmw_430i, model_type, 4_series).
    ATTRIBUTE(bmw_430i, body_type, coupe).
    HAS(bmw_430i, engine_30i).
    HAS(bmw_430i, transmission_manual).
    HAS(bmw_430i, rwd_drive).
    ATTRIBUTE(bmw_430i, trim_level, m_sport).
    ATTRIBUTE(engine_30i, displacement, 2.0).
    ATTRIBUTE(engine_30i, fuel_type, petrol).
    ATTRIBUTE(engine_30i, power_kw, 180).
    ATTRIBUTE(transmission_manual, type, manual).
    ATTRIBUTE(rwd_drive, drive_type, rear_wheel).
    
    # BMW 5 Touring - Kombi s dieselovým motorom
    IS_A(bmw_520d_touring, Touring).
    ATTRIBUTE(bmw_520d_touring, model_type, 5_series).
    ATTRIBUTE(bmw_520d_touring, body_type, wagon).
    HAS(bmw_520d_touring, engine_20d).
    HAS(bmw_520d_touring, transmission_auto).
    HAS(bmw_520d_touring, rwd_drive).
    ATTRIBUTE(bmw_520d_touring, trim_level, business).
    ATTRIBUTE(engine_20d, displacement, 2.0).
    ATTRIBUTE(engine_20d, fuel_type, diesel).
    ATTRIBUTE(engine_20d, power_kw, 140).
    ATTRIBUTE(transmission_auto, type, steptronic).
    ATTRIBUTE(rwd_drive, drive_type, rear_wheel).
    
    # BMW 8 Series - Kupé s high-performance motorom
    IS_A(bmw_m850i, Series8).
    ATTRIBUTE(bmw_m850i, model_type, 8_series).
    ATTRIBUTE(bmw_m850i, body_type, coupe).
    HAS(bmw_m850i, engine_v8).
    HAS(bmw_m850i, transmission_auto).
    HAS(bmw_m850i, xdrive_system).
    ATTRIBUTE(bmw_m850i, trim_level, m_performance).
    ATTRIBUTE(engine_v8, displacement, 4.4).
    ATTRIBUTE(engine_v8, fuel_type, petrol).
    ATTRIBUTE(engine_v8, power_kw, 390).
    ATTRIBUTE(transmission_auto, type, sport_automatic).
    ATTRIBUTE(xdrive_system, drive_type, all_wheel).
    
    # BMW X7 - Veľké SUV s dieselovým motorom
    IS_A(bmw_x7_m50d, X7).
    ATTRIBUTE(bmw_x7_m50d, model_type, x7).
    ATTRIBUTE(bmw_x7_m50d, body_type, suv).
    HAS(bmw_x7_m50d, engine_quad_turbo).
    HAS(bmw_x7_m50d, transmission_auto).
    HAS(bmw_x7_m50d, xdrive_system).
    ATTRIBUTE(bmw_x7_m50d, trim_level, m_performance).
    ATTRIBUTE(engine_quad_turbo, displacement, 3.0).
    ATTRIBUTE(engine_quad_turbo, fuel_type, diesel).
    ATTRIBUTE(engine_quad_turbo, power_kw, 294).
    ATTRIBUTE(transmission_auto, type, sport_automatic).
    ATTRIBUTE(xdrive_system, drive_type, all_wheel).
    """
    
    # Zlé príklady v PL1 formáte - každý príklad obsahuje iba jednu kľúčovú odlišnosť
    near_misses_pl1 = """
    # Near miss 1: BMW 3 Series s výbavou Mercedes (nesprávny branding)
    # - Všetko je ako u správneho BMW, ale je označené ako Non_BMW (iba jedna zmena)
    IS_A(almost_bmw_3, Non_BMW).
    ATTRIBUTE(almost_bmw_3, model_type, 3_series).
    ATTRIBUTE(almost_bmw_3, body_type, sedan).
    HAS(almost_bmw_3, engine_20i).
    HAS(almost_bmw_3, transmission_auto).
    HAS(almost_bmw_3, rwd_drive).
    ATTRIBUTE(almost_bmw_3, trim_level, sport_line).
    ATTRIBUTE(engine_20i, displacement, 2.0).
    ATTRIBUTE(engine_20i, fuel_type, petrol).
    ATTRIBUTE(engine_20i, power_kw, 135).
    ATTRIBUTE(transmission_auto, type, steptronic).
    ATTRIBUTE(rwd_drive, drive_type, rear_wheel).
    
    # Near miss 2: BMW bez motora (neplatné BMW)
    # - Jediný problém: chýba motor
    IS_A(invalid_bmw_3, Series3).
    ATTRIBUTE(invalid_bmw_3, model_type, 3_series).
    ATTRIBUTE(invalid_bmw_3, body_type, sedan).
    # Chýba motor!
    HAS(invalid_bmw_3, transmission_auto).
    HAS(invalid_bmw_3, rwd_drive).
    ATTRIBUTE(invalid_bmw_3, trim_level, base).
    ATTRIBUTE(transmission_auto, type, steptronic).
    ATTRIBUTE(rwd_drive, drive_type, rear_wheel).
    
    # Near miss 3: BMW X5 bez xDrive (nesprávny pohon)
    # - Jediný problém: X5 musí mať xDrive, ale má zadný pohon
    IS_A(invalid_bmw_x5, X5).
    ATTRIBUTE(invalid_bmw_x5, model_type, x5).
    ATTRIBUTE(invalid_bmw_x5, body_type, suv).
    HAS(invalid_bmw_x5, engine_40i).
    HAS(invalid_bmw_x5, transmission_auto).
    HAS(invalid_bmw_x5, rwd_drive).  # X5 musí mať xDrive, nie zadný pohon
    ATTRIBUTE(invalid_bmw_x5, trim_level, base).
    ATTRIBUTE(engine_40i, displacement, 3.0).
    ATTRIBUTE(engine_40i, fuel_type, petrol).
    ATTRIBUTE(engine_40i, power_kw, 250).
    ATTRIBUTE(transmission_auto, type, steptronic).
    ATTRIBUTE(rwd_drive, drive_type, rear_wheel).
    
    # Near miss 4: BMW so zlým výkonom pre danú sériu
    # - Jediný problém: Séria 7 s príliš malým motorom a slabým výkonom
    IS_A(invalid_bmw_750i, Series7).
    ATTRIBUTE(invalid_bmw_750i, model_type, 7_series).
    ATTRIBUTE(invalid_bmw_750i, body_type, sedan).
    HAS(invalid_bmw_750i, engine_small).
    HAS(invalid_bmw_750i, transmission_auto).
    HAS(invalid_bmw_750i, xdrive_system).
    ATTRIBUTE(invalid_bmw_750i, trim_level, luxury_line).
    ATTRIBUTE(engine_small, displacement, 1.5). # Príliš malý motor pre 7 Series
    ATTRIBUTE(engine_small, fuel_type, petrol).
    ATTRIBUTE(engine_small, power_kw, 85).  # Príliš slabý výkon pre 7 Series
    ATTRIBUTE(transmission_auto, type, steptronic).
    ATTRIBUTE(xdrive_system, drive_type, all_wheel).
    """
    
    # Konvertuj PL1 text na množinu predikátov
    good_examples = [parse_pl1_input(good_examples_pl1)]
    near_misses = [parse_pl1_input(near_misses_pl1)]
    
    return {
        "classification_tree": tree,
        "good_examples": good_examples,
        "near_misses": near_misses
    } 