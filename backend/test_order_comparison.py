#!/usr/bin/env python3
"""
Test script to compare the effect of example order on Winston's algorithm.
This script processes two datasets with identical examples but in different order,
and then compares the resulting models.
"""

import os
import sys
import json
from pprint import pprint

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pl1.backend.model import Model, Link, LinkType, Object, ClassificationTree, formula_to_model
from pl1.backend.learner import WinstonLearner
from pl1.backend.pl1_parser import parse_pl1_dataset

def read_pl1_file(filename):
    """Read a PL1 file and return its contents"""
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

def process_dataset(dataset_content, dataset_name=""):
    """Process a dataset and return the learned model"""
    print(f"\n=== Processing dataset: {dataset_name} ===")
    
    # Parse the dataset
    formulas = parse_pl1_dataset(dataset_content)
    print(f"Number of formulas parsed: {len(formulas)}")
    
    # Create a classification tree for BMW cars
    tree = ClassificationTree()
    tree.add_relationship("BMW", None)  # BMW is the root
    tree.add_relationship("X5", "BMW")
    tree.add_relationship("X7", "BMW")
    tree.add_relationship("Series3", "BMW")
    tree.add_relationship("Series5", "BMW")
    tree.add_relationship("Series7", "BMW")
    tree.add_relationship("Engine", None)
    tree.add_relationship("PetrolEngine", "Engine")
    tree.add_relationship("DieselEngine", "Engine") 
    tree.add_relationship("HybridEngine", "Engine")
    tree.add_relationship("Transmission", None)
    tree.add_relationship("AutomaticTransmission", "Transmission")
    tree.add_relationship("ManualTransmission", "Transmission")
    tree.add_relationship("DriveSystem", None)
    tree.add_relationship("RWD", "DriveSystem")
    tree.add_relationship("AWD", "DriveSystem")
    tree.add_relationship("XDrive", "DriveSystem")
    
    # Initialize models and learner
    current_model = Model()  # Start with an empty model
    learner = WinstonLearner(classification_tree=tree)
    
    # Separate positive and negative examples 
    positive_examples = []
    negative_examples = []
    
    # First, convert all formulas to models and categorize them
    for i, formula in enumerate(formulas):
        formula_str = str(formula)
        formula_model = formula_to_model(formula)
        
        if "Ν" in formula_str:  # Check if it's a negative example
            print(f"Formula {i+1}: Negative example")
            negative_examples.append(formula_model)
        else:
            print(f"Formula {i+1}: Positive example")
            positive_examples.append(formula_model)
    
    # Now process positive examples one by one
    for i, positive_example in enumerate(positive_examples):
        print(f"\nProcessing positive example {i+1}/{len(positive_examples)}...")
        
        # Find corresponding negative example if available
        near_miss = None
        if i < len(negative_examples):
            near_miss = negative_examples[i]
            print(f"  Using near miss example {i+1}")
        
        # Update the model with this example and its near miss
        current_model = learner.update_model(current_model, positive_example, near_miss)
        print(f"  Model updated - now has {len(current_model.objects)} objects and {len(current_model.links)} links")
    
    # Return the final model and learner for further analysis
    return current_model, learner

def analyze_model_differences(model1, model2, name1="Model 1", name2="Model 2"):
    """Analyze and print differences between two models"""
    print("\n=== Model Differences Analysis ===")
    
    # Count model elements
    print(f"{name1}: {len(model1.objects)} objects, {len(model1.links)} links")
    print(f"{name2}: {len(model2.objects)} objects, {len(model2.links)} links")
    
    # Extract identification rules
    rules1 = model1.extract_model_rules()
    rules2 = model2.extract_model_rules()
    
    # Compare rule presence
    models = set(rules1.keys()) | set(rules2.keys())
    for model_name in sorted(models):
        if model_name in rules1 and model_name in rules2:
            # Both have rules for this model
            rule1 = rules1[model_name]
            rule2 = rules2[model_name]
            if rule1 == rule2:
                print(f"\n{model_name}: Rules are identical")
            else:
                print(f"\n{model_name}: Rules differ:")
                print(f"  {name1} rule:")
                print(f"    {rule1}")
                print(f"  {name2} rule:")
                print(f"    {rule2}")
        elif model_name in rules1:
            print(f"\n{model_name}: Only in {name1}")
            print(f"  {rules1[model_name]}")
        else:
            print(f"\n{model_name}: Only in {name2}")
            print(f"  {rules2[model_name]}")
    
    # Compare MUST links (important structural elements)
    must_links1 = {(link.source, link.target) for link in model1.links if link.link_type == LinkType.MUST}
    must_links2 = {(link.source, link.target) for link in model2.links if link.link_type == LinkType.MUST}
    
    print("\nMUST links comparison:")
    links_only_in_1 = must_links1 - must_links2
    links_only_in_2 = must_links2 - must_links1
    
    if links_only_in_1:
        print(f"MUST links only in {name1}:")
        for source, target in links_only_in_1:
            print(f"  {source} -> {target}")
    
    if links_only_in_2:
        print(f"MUST links only in {name2}:")
        for source, target in links_only_in_2:
            print(f"  {source} -> {target}")
    
    if not links_only_in_1 and not links_only_in_2:
        print("  MUST links are identical between models")
    
    # Compare MUST_NOT links
    must_not_links1 = {(link.source, link.target) for link in model1.links if link.link_type == LinkType.MUST_NOT}
    must_not_links2 = {(link.source, link.target) for link in model2.links if link.link_type == LinkType.MUST_NOT}
    
    print("\nMUST_NOT links comparison:")
    links_only_in_1 = must_not_links1 - must_not_links2
    links_only_in_2 = must_not_links2 - must_not_links1
    
    if links_only_in_1:
        print(f"MUST_NOT links only in {name1}:")
        for source, target in links_only_in_1:
            print(f"  {source} -> {target}")
    
    if links_only_in_2:
        print(f"MUST_NOT links only in {name2}:")
        for source, target in links_only_in_2:
            print(f"  {source} -> {target}")
    
    if not links_only_in_1 and not links_only_in_2:
        print("  MUST_NOT links are identical between models")
        
    return rules1, rules2

def main():
    """Main function"""
    # File paths
    dataset1_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'test_order_1.pl1')
    dataset2_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'test_order_2.pl1')
    
    # Read datasets
    dataset1_content = read_pl1_file(dataset1_path)
    dataset2_content = read_pl1_file(dataset2_path)
    
    # Process datasets
    model1, learner1 = process_dataset(dataset1_content, "X5-first order")
    model2, learner2 = process_dataset(dataset2_content, "Series3-first order")
    
    # Analyze differences
    rules1, rules2 = analyze_model_differences(model1, model2, "X5-first", "Series3-first")
    
    # Save the results
    results_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'results')
    os.makedirs(results_dir, exist_ok=True)
    
    # Use custom JSON encoding for sets
    class SetEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, set):
                return list(obj)
            return super().default(obj)
    
    with open(os.path.join(results_dir, 'model_x5_first.json'), 'w') as f:
        json.dump(model1.to_dict(), f, indent=2, cls=SetEncoder)
    
    with open(os.path.join(results_dir, 'model_series3_first.json'), 'w') as f:
        json.dump(model2.to_dict(), f, indent=2, cls=SetEncoder)
    
    with open(os.path.join(results_dir, 'rules_x5_first.json'), 'w') as f:
        json.dump(rules1, f, indent=2)
    
    with open(os.path.join(results_dir, 'rules_series3_first.json'), 'w') as f:
        json.dump(rules2, f, indent=2)
    
    print("\nResults saved to:", results_dir)
    print("Test completed.")

if __name__ == "__main__":
    main() 