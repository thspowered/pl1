from dataclasses import dataclass
from typing import List, Set, Optional, Union, Dict
from enum import Enum
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

class LinkType(Enum):
    MUST = "must"
    MUST_NOT = "must_not"
    MUST_BE_A = "must_be_a"
    REGULAR = "regular"

@dataclass
class Link:
    source: str
    target: str
    link_type: LinkType = LinkType.REGULAR

@dataclass
class Object:
    name: str
    class_name: str
    attributes: Optional[Dict] = None

@dataclass
class Model:
    objects: List[Object]
    links: List[Link]
    
    def add_link(self, link: Link):
        self.links.append(link)
        
    def remove_link(self, link: Link):
        self.links = [l for l in self.links if l != link]
        
    def has_link(self, source: str, target: str) -> bool:
        return any(l.source == source and l.target == target for l in self.links)

    def create_semantic_network(self) -> nx.DiGraph:
        """Creates a NetworkX directed graph from the model"""
        G = nx.DiGraph()
        
        # Add all objects as nodes
        for obj in self.objects:
            G.add_node(obj.name, class_name=obj.class_name)
            if obj.attributes:
                for attr, value in obj.attributes.items():
                    attr_node = f"{obj.name}_{attr}"
                    G.add_node(attr_node, value=value)
                    G.add_edge(obj.name, attr_node, type="has_attribute")
        
        # Add all links as edges
        for link in self.links:
            G.add_edge(link.source, link.target, type=link.link_type.value)
            
        return G
    
    def visualize(self):
        """Visualizes the semantic network"""
        G = self.create_semantic_network()
        
        # Create layout
        pos = nx.spring_layout(G)
        
        # Draw nodes
        nx.draw_networkx_nodes(G, pos, node_color='lightblue', 
                             node_size=1500)
        
        # Draw edges with different colors based on link type
        edge_colors = {
            'must': 'green',
            'must_not': 'red',
            'must_be_a': 'blue',
            'regular': 'gray',
            'has_attribute': 'orange'
        }
        
        for edge_type in edge_colors:
            edges = [(u, v) for (u, v, d) in G.edges(data=True) 
                    if d['type'] == edge_type]
            if edges:
                nx.draw_networkx_edges(G, pos, edgelist=edges, 
                                     edge_color=edge_colors[edge_type],
                                     arrows=True)
        
        # Draw labels
        nx.draw_networkx_labels(G, pos)
        
        # Add legend
        legend_elements = [
            Line2D([0], [0], color='green', label='Matching/Must Links'),
            Line2D([0], [0], color='red', label='Missing/Must Not Links'),
            Line2D([0], [0], color='blue', label='Must Be A Links'),
            Line2D([0], [0], color='gray', label='Regular Links'),
            Line2D([0], [0], color='orange', label='Attribute Links'),
            Line2D([0], [0], marker='o', color='lightblue', 
                  label='Object Nodes', markerfacecolor='lightblue', markersize=10),
            Line2D([0], [0], marker='s', color='lightgreen', 
                  label='Attribute Nodes', markerfacecolor='lightgreen', markersize=10)
        ]
        plt.legend(handles=legend_elements)
        
        plt.title("Semantic Network Visualization")
        plt.axis('off')
        plt.show()

class ClassificationTree:
    def __init__(self):
        self.hierarchy: Dict[str, Set[str]] = {}
        
    def add_relationship(self, parent: str, child: str):
        if parent not in self.hierarchy:
            self.hierarchy[parent] = set()
        self.hierarchy[parent].add(child)
        
    def find_common_ancestor(self, class1: str, class2: str) -> Optional[str]:
        # Implementation to find most specific common class
        # This is a simplified version - would need more robust implementation
        for parent, children in self.hierarchy.items():
            if class1 in children and class2 in children:
                return parent
        return None

class HeuristicsEngine:
    def __init__(self, classification_tree: ClassificationTree):
        self.classification_tree = classification_tree
    
    def learn_link_type(self, model: Model, example: Model, near_miss: Model, source: str, target: str) -> Optional[LinkType]:
        """Determines link type based on patterns in examples and near misses"""
        example_has_link = example.has_link(source, target)
        near_miss_has_link = near_miss.has_link(source, target)
        model_has_link = model.has_link(source, target)
        
        # If link consistently appears in good examples but never in near misses
        if example_has_link and not near_miss_has_link:
            return LinkType.MUST
        
        # If link appears in near misses but never in good examples
        if near_miss_has_link and not example_has_link:
            return LinkType.MUST_NOT
        
        # If link appears in classification hierarchy
        if (source in [obj.name for obj in model.objects] and
            target in [cls for cls in self.classification_tree.hierarchy.keys()]):
            return LinkType.MUST_BE_A
        
        # If link appears sometimes but isn't critical
        if example_has_link or model_has_link:
            return LinkType.REGULAR
        
        return None

    def update_model(self, model: Model, example: Model, near_miss: Model):
        """Updates model based on learning from examples and near misses"""
        # Collect all possible source-target pairs
        all_objects = set()
        for m in [model, example, near_miss]:
            all_objects.update([obj.name for obj in m.objects])
            all_objects.update([link.source for link in m.links])
            all_objects.update([link.target for link in m.links])
        
        # Learn from each possible connection
        for source in all_objects:
            for target in all_objects:
                if source != target:
                    learned_type = self.learn_link_type(model, example, near_miss, source, target)
                    
                    if learned_type:
                        # Remove existing link if present
                        model.remove_link(Link(source, target, LinkType.REGULAR))
                        
                        # Add new link with learned type
                        new_link = Link(source, target, learned_type)
                        if not any(l.source == source and l.target == target for l in model.links):
                            model.add_link(new_link)
        
        return model

def create_base_car_dataset():
    """Creates a base dataset defining what a 'good car' is"""
    tree = ClassificationTree()
    tree.add_relationship("Vehicle", "Car")
    
    # Define our ideal car model
    good_car = Model(
        objects=[
            Object("car", "Car", {
                "wheels": 4,
                "doors": 4,
                "safety_rating": 5,
                "engine_condition": "good",
                "mileage": 50000
            }),
            Object("engine", "Engine", {
                "horsepower": 150,
                "fuel_type": "gasoline"
            }),
            Object("transmission", "Transmission", {
                "type": "automatic"
            })
        ],
        links=[
            Link("car", "engine", LinkType.MUST),
            Link("car", "transmission", LinkType.MUST),
            Link("car", "Car", LinkType.MUST_BE_A),
            Link("car", "has_airbags", LinkType.MUST),
            Link("car", "has_abs", LinkType.MUST)
        ]
    )
    
    return {
        "classification_tree": tree,
        "ideal_car": good_car
    }

def compare_models(base_model: Model, new_example: Model) -> dict:
    """Compares a new example with the base model and returns differences"""
    differences = {
        "missing_links": [],
        "extra_links": [],
        "different_attributes": {},
        "wrong_class": None,
        "missing_components": [],  # New: track missing required components
        "matches": []
    }
    
    # Check if it's the correct class
    base_class = next((link.target for link in base_model.links 
                      if link.link_type == LinkType.MUST_BE_A), None)
    example_class = next((link.target for link in new_example.links 
                        if link.link_type == LinkType.MUST_BE_A), None)
    if base_class != example_class:
        differences["wrong_class"] = f"Expected {base_class}, got {example_class}"
    
    # Check for required components (objects)
    base_objects = {obj.name: obj.class_name for obj in base_model.objects}
    example_objects = {obj.name: obj.class_name for obj in new_example.objects}
    
    for name, class_name in base_objects.items():
        if name not in example_objects:
            differences["missing_components"].append(f"{class_name} ({name})")
    
    # Compare links
    base_links = {(l.source, l.target, l.link_type) for l in base_model.links}
    new_links = {(l.source, l.target, l.link_type) for l in new_example.links}
    
    differences["missing_links"] = [l for l in base_links if l not in new_links]
    differences["extra_links"] = [l for l in new_links if l not in base_links]
    
    # Compare attributes
    for base_obj in base_model.objects:
        for new_obj in new_example.objects:
            if base_obj.name == new_obj.name:
                if base_obj.attributes and new_obj.attributes:
                    diff_attrs = {}
                    for attr, value in base_obj.attributes.items():
                        if attr in new_obj.attributes:
                            if value != new_obj.attributes[attr]:
                                diff_attrs[attr] = {
                                    "expected": value,
                                    "actual": new_obj.attributes[attr]
                                }
                            else:
                                differences["matches"].append(
                                    f"{base_obj.name}.{attr}: {value}"
                                )
                    if diff_attrs:
                        differences["different_attributes"][base_obj.name] = diff_attrs
    
    return differences

def create_example_car(modifications: dict) -> Model:
    """Creates a new car example with specified modifications"""
    example_car = Model(
        objects=[
            Object("car", "Car", {
                "wheels": modifications.get("wheels", 4),
                "doors": modifications.get("doors", 4),
                "safety_rating": modifications.get("safety_rating", 5),
                "engine_condition": modifications.get("engine_condition", "good"),
                "mileage": modifications.get("mileage", 50000)
            }),
            Object("engine", "Engine", {
                "horsepower": modifications.get("horsepower", 150),
                "fuel_type": modifications.get("fuel_type", "gasoline")
            }),
            Object("transmission", "Transmission", {
                "type": modifications.get("transmission_type", "automatic")
            })
        ],
        links=[]
    )
    
    # Add basic links
    example_car.add_link(Link("car", "engine", LinkType.MUST))
    example_car.add_link(Link("car", "transmission", LinkType.MUST))
    example_car.add_link(Link("car", "Car", LinkType.MUST_BE_A))
    
    # Add optional links based on modifications
    if modifications.get("has_airbags", True):
        example_car.add_link(Link("car", "has_airbags", LinkType.MUST))
    if modifications.get("has_abs", True):
        example_car.add_link(Link("car", "has_abs", LinkType.MUST))
    
    return example_car

def compare_networks_visualization(model1: Model, model2: Model, differences: dict, 
                                title1: str = "Final Example", title2: str = "Exercise Network"):
    plt.close('all')  # Close all existing figures
    
    # Create subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(24, 12))
    
    def create_node_labels(G):
        """Creates detailed labels for nodes including attributes"""
        labels = {}
        for node in G.nodes():
            # Get node data
            node_data = G.nodes[node]
            if 'class_name' in node_data:
                # For objects, show class name and attributes
                attrs = node_data.get('attributes', {})
                attr_str = '\n'.join([f"{k}: {v}" for k, v in attrs.items()]) if attrs else ""
                labels[node] = f"{node}\n({node_data['class_name']})\n{attr_str}"
            elif 'value' in node_data:
                # For attribute nodes
                labels[node] = f"{node}\n= {node_data['value']}"
            else:
                labels[node] = str(node)
        return labels
    
    def draw_network(G, pos, ax, title, is_test=False):
        """Draws a single network with improved styling"""
        # Draw nodes with different colors based on type
        object_nodes = [node for node, attr in G.nodes(data=True) if 'class_name' in attr]
        attr_nodes = [node for node, attr in G.nodes(data=True) if 'value' in attr]
        
        # Draw object nodes
        nx.draw_networkx_nodes(G, pos, nodelist=object_nodes, 
                             node_color='lightblue' if not is_test else 'red',
                             node_size=3000,
                             node_shape='o',
                             ax=ax)
        
        # Draw attribute nodes
        nx.draw_networkx_nodes(G, pos, nodelist=attr_nodes,
                             node_color='lightgreen',
                             node_size=2000,
                             node_shape='s',
                             ax=ax)
        
        # Create and draw labels
        labels = create_node_labels(G)
        
        # Add requirements and errors to labels
        if not is_test:  # For Car Requirements
            for node in object_nodes:
                if node == 'car':
                    labels[node] += "\n[MUST BE TYPE: Car]"
                    labels[node] += "\n[MUST HAVE: 4 wheels]"
                    labels[node] += "\n[MUST HAVE: airbags, ABS]"
                elif node == 'engine':
                    labels[node] += "\n[REQUIRED COMPONENT]"
                elif node == 'transmission':
                    labels[node] += "\n[REQUIRED COMPONENT]"
        else:  # For Exercise Network
            for node in object_nodes:
                if "bike" in node:
                    labels[node] += "\n[WRONG TYPE: Should be Car]"
                    labels[node] += "\n[WRONG WHEELS: Has 2, needs 4]"
                    labels[node] += "\n[MISSING: Engine, Transmission]"
                    labels[node] += "\n[MISSING: Airbags, ABS]"
        
        nx.draw_networkx_labels(G, pos, labels, font_size=8, ax=ax)
        
        # Draw edges
        if not is_test:  # For Car Requirements
            # Show all required connections in blue
            required_edges = [(u, v) for (u, v, d) in G.edges(data=True) 
                            if d.get('type') in ['must', 'must_be_a']]
            attr_edges = [(u, v) for (u, v, d) in G.edges(data=True) 
                         if d.get('type') == 'has_attribute']
            
            nx.draw_networkx_edges(G, pos, edgelist=required_edges,
                                 edge_color='blue', arrows=True, ax=ax,
                                 width=2.0)
            nx.draw_networkx_edges(G, pos, edgelist=attr_edges,
                                 edge_color='orange', arrows=True, ax=ax)
            
            # Add "REQUIRED" labels
            edge_labels = {(u, v): "REQUIRED" for (u, v) in required_edges}
            nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=8, ax=ax)
        else:  # For Exercise Network
            # Show regular edges in gray
            regular_edges = [(u, v) for (u, v) in G.edges()]
            nx.draw_networkx_edges(G, pos, edgelist=regular_edges,
                                 edge_color='gray', arrows=True, ax=ax)
            
            # Show extra features in yellow
            extra_edges = [(u, v) for (u, v) in G.edges() 
                         if (u, v) in differences["extra_links"]]
            if extra_edges:
                nx.draw_networkx_edges(G, pos, edgelist=extra_edges,
                                     edge_color='yellow', width=2.0,
                                     arrows=True, ax=ax)
                # Add "NOT IN CARS" labels
                edge_labels = {(u, v): "NOT IN CARS" for (u, v) in extra_edges}
                nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=8, ax=ax)
    
    # Draw first network (Trained Model)
    G1 = model1.create_semantic_network()
    pos1 = nx.spring_layout(G1, k=2, iterations=50)
    draw_network(G1, pos1, ax1, title1)
    ax1.set_title(title1, pad=20, size=16)
    ax1.axis('off')
    
    # Draw second network (Test Example)
    G2 = model2.create_semantic_network()
    pos2 = nx.spring_layout(G2, k=2, iterations=50)
    draw_network(G2, pos2, ax2, title2, is_test=True)
    ax2.set_title(title2, pad=20, size=16)
    ax2.axis('off')
    
    # Add legend
    legend_elements = [
        Line2D([0], [0], color='green', label='Matching Links'),
        Line2D([0], [0], color='red', label='Missing Links'),
        Line2D([0], [0], color='yellow', label='Extra Links'),
        Line2D([0], [0], color='orange', label='Attribute Links'),
        Line2D([0], [0], marker='o', color='lightblue', 
              label='Object Nodes', markerfacecolor='lightblue', markersize=10),
        Line2D([0], [0], marker='s', color='lightgreen', 
              label='Attribute Nodes', markerfacecolor='lightgreen', markersize=10)
    ]
    fig.legend(handles=legend_elements, loc='center right', 
              bbox_to_anchor=(0.98, 0.5))
    
    plt.tight_layout()
    plt.show()

def main():
    # Create training dataset
    dataset = create_base_car_dataset()
    base_model = dataset["ideal_car"]
    
    # Create heuristics engine
    engine = HeuristicsEngine(dataset["classification_tree"])
    
    # Training examples - good cars
    good_examples = [
        create_example_car({
            "wheels": 4,
            "safety_rating": 5,
            "has_airbags": True,
            "has_abs": True
        }),  # Perfect car
        create_example_car({
            "horsepower": 200,
            "safety_rating": 4,
            "has_airbags": True,
            "has_abs": True
        })  # Powerful but safe car
    ]
    
    # Near misses - not good cars
    near_misses = [
        create_example_car({
            "wheels": 3,
            "safety_rating": 2,
            "has_airbags": False,
            "has_abs": False
        }),  # Unsafe car
        create_example_car({
            "engine_condition": "poor",
            "mileage": 200000,
            "safety_rating": 3,
            "has_abs": False
        })  # Very old car
    ]
    
    # Learning phase - train the model
    learned_model = base_model
    for good_example in good_examples:
        for near_miss in near_misses:
            learned_model = engine.update_model(learned_model, good_example, near_miss)
    
    # Create test example - Bicycle
    test_example = Model(
        objects=[
            Object("bike", "Bicycle", {
                "wheels": 2,
                "pedals": True,
                "safety_rating": 2,
            }),
            Object("frame", "Frame", {
                "material": "aluminum"
            }),
            Object("handlebars", "Controls", {
                "type": "manual"
            })
        ],
        links=[
            Link("bike", "frame", LinkType.MUST),
            Link("bike", "handlebars", LinkType.MUST),
            Link("bike", "has_pedals", LinkType.MUST),
            Link("bike", "Bicycle", LinkType.MUST_BE_A)
        ]
    )
    
    # Compare the test example with learned model
    print("\nAnalyzing Exercise Network...")
    differences = compare_models(learned_model, test_example)
    
    print("\nWhy this is not a car:")
    if differences["wrong_class"]:
        print(f"1. Wrong vehicle type: {differences['wrong_class']}")
    
    if differences["missing_components"]:
        print("\n2. Missing required car components:")
        for component in differences["missing_components"]:
            print(f"   - {component}")
    
    if differences["missing_links"]:
        print("\n3. Missing required features:")
        for link in differences["missing_links"]:
            print(f"   - {link[0]} must have {link[1]}")
    
    if differences["different_attributes"]:
        print("\n4. Incorrect specifications:")
        for obj, attrs in differences["different_attributes"].items():
            for attr, values in attrs.items():
                print(f"   - {obj} {attr}: got {values['actual']}, "
                      f"should be {values['expected']}")
    
    if differences["extra_links"]:
        print("\n5. Extra features not found in cars:")
        for link in differences["extra_links"]:
            print(f"   - {link[0]} has {link[1]}")
    
    # Visualize comparison
    compare_networks_visualization(learned_model, test_example, differences,
                                "Car Requirements", "Exercise Network")

if __name__ == "__main__":
    main()