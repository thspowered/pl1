#!/usr/bin/env python3
import os
import sys

# Add root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pl1.backend.pl1_parser import parse_pl1_formula, Predicate, PredicateType, Formula
from pl1.backend.model import formula_to_model, Model, Link, LinkType, Object

def test_parse_formula():
    """Test parsing a PL1 formula."""
    formula_str = """
    Ι(c1, X5) ∧
    Π(c1, e1) ∧ Ι(e1, PetrolEngine) ∧
    Π(c1, t1) ∧ Ι(t1, ManualTransmission) ∧
    Π(c1, d1) ∧ Ι(d1, XDrive) ∧
    Π(e1, t1)
    """
    
    # Clean the formula
    lines = [line.strip() for line in formula_str.split('\n') if line.strip()]
    # Remove lines starting with #
    filtered_lines = [line for line in lines if not line.startswith('#')]
    # Remove trailing ∧
    cleaned_lines = []
    for line in filtered_lines:
        if line.endswith('∧'):
            line = line[:-1].strip()
        cleaned_lines.append(line)
    # Join with ∧
    clean_formula = ' ∧ '.join(cleaned_lines)
    
    print(f"Clean formula: {clean_formula}")
    
    # Parse the formula
    parsed_formula = parse_pl1_formula(clean_formula)
    print(f"Parsed formula: {parsed_formula}")
    print(f"Number of predicates: {len(parsed_formula.predicates)}")
    
    # Print all predicates
    print("\nPredicates:")
    for i, pred in enumerate(parsed_formula.predicates):
        print(f"  {i+1}. Type: {pred.type.name}, Name: {pred.name}, Args: {pred.arguments}")
    
    # Create a model from the formula
    model = formula_to_model(parsed_formula)
    
    # Print model objects
    print("\nModel Objects:")
    for obj in model.objects:
        print(f"  {obj.name}: {obj.class_name}")
        if obj.attributes:
            print(f"    Attributes: {obj.attributes}")
    
    # Print model links
    print("\nModel Links:")
    for link in model.links:
        print(f"  {link.source} -> {link.target} (type: {link.link_type.name})")

if __name__ == "__main__":
    test_parse_formula() 