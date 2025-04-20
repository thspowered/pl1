import React, { useRef, useState, useEffect } from 'react';
import { Network, Data, Options, Edge, Node } from 'vis-network';
import { DataSet } from 'vis-data';
import { ComparisonResult, NetworkNode as BaseNetworkNode, NetworkLink as BaseNetworkLink } from '../types';
import './NetworkGraph.css';

interface ExampleNetworkGraphProps {
  comparisonResult: ComparisonResult;
  formula: string;
  showLayeredVisualization?: boolean;
  viewType?: 'model' | 'example'; // Add view type to control which elements to highlight
}

// Use a completely separate interface for visualization needs instead of extending BaseNetworkNode
interface NetworkNode {
  id: string;
  name: string;
  class?: string;
  category?: string;
  size?: number;
  status?: 'valid' | 'invalid' | 'missing' | 'extra' | 'missingInExample' | 'common' | 'only_in_a' | 'only_in_b';
  shape?: string;
  color?: string;
  group?: string;
}

interface NetworkLink {
  source: string;
  target: string;
  type: string;
  status?: 'valid' | 'invalid' | 'missing' | 'extra' | 'missingInExample';
  width?: number;
}

// Funkcia na parsovanie PL1 formuly zo vstupného textu
const parseFormulaToNodesAndLinks = (formulaText: string) => {
  // Rozdelíme formulu na jednotlivé výrazy
  const parts = formulaText.split('∧').map(part => part.trim());
  
  // Pripravíme objekty pre uzly a spojenia
  const nodeMap = new Map<string, NetworkNode>();
  const links: NetworkLink[] = [];
  
  // Mapa pre sledovanie, s akým typom/komponentom je premenná spojená
  const variableToTypeMap = new Map<string, string>();
  
  // Funkcia na pridanie uzla, ak ešte neexistuje
  const addNode = (id: string, category: string) => {
    if (!nodeMap.has(id) && !isVariableNode(id)) {
      nodeMap.set(id, {
        id: id,
        name: id,
        class: category,
        category: category
      });
    }
  };
  
  // Funkcia na kontrolu, či id reprezentuje premennú bez sémantického významu
  const isVariableNode = (id: string) => {
    // Kontrola či je to jednopísmenový identifikátor (x, e, t, d, w, b, s, c, i, l, su, se)
    return /^[a-zA-Z]$/.test(id);
  };
  
  // Funkcia na kontrolu, či id reprezentuje indexovanú premennú (napr. x₁₂, t₁₅)
  const isIndexedVariable = (id: string) => {
    // Kontrola, či id začína písmenom nasledovaným indexovým číslom (napr. x₁₂, e₅, t₁₀)
    return /^[a-zA-Z]₁?\d+$/.test(id);
  };
  
  // Prvý prechod - zozbierame informácie o premenných a ich typoch
  parts.forEach(part => {
    part = part.trim();
    
    if (part.startsWith('Ι(')) {
      // IS(x, X5) - typ uzla
      const match = part.match(/Ι\s*\(\s*([^,]+),\s*([^)]+)\s*\)/);
      if (match) {
        const objectId = match[1].trim();
        const typeId = match[2].trim();
        
        if (isVariableNode(objectId) || isIndexedVariable(objectId)) {
          variableToTypeMap.set(objectId, typeId);
        }
      }
    }
  });
  
  // Druhý prechod - spracujeme vzťahy, nahradíme premenné ich typmi
  parts.forEach(part => {
    part = part.trim();
    
    // Identifikujeme typ výrazu a extrahujeme parametre
    if (part.startsWith('Ι(')) {
      // IS(x, X5) - typ uzla
      const match = part.match(/Ι\s*\(\s*([^,]+),\s*([^)]+)\s*\)/);
      if (match) {
        const objectId = match[1].trim();
        const typeId = match[2].trim();
        
        // Pridáme iba cieľový typ, nie premennú
        addNode(typeId, typeId);
      }
    } else if (part.startsWith('Μ(')) {
      // MUST(X5, Engine) - povinná väzba
      const match = part.match(/Μ\s*\(\s*([^,]+),\s*([^)]+)\s*\)/);
      if (match) {
        const sourceId = match[1].trim();
        const targetId = match[2].trim();
        
        // Nahradíme premenné ich typmi
        const actualSourceId = isVariableNode(sourceId) || isIndexedVariable(sourceId) ? 
          variableToTypeMap.get(sourceId) || sourceId : sourceId;
        const actualTargetId = isVariableNode(targetId) || isIndexedVariable(targetId) ? 
          variableToTypeMap.get(targetId) || targetId : targetId;
        
        // Ak nemáme informácie o typoch, preskočíme
        if (isVariableNode(actualSourceId) || isVariableNode(actualTargetId)) {
          return;
        }
        
        addNode(actualSourceId, actualSourceId);
        addNode(actualTargetId, actualTargetId);
        
        links.push({
          source: actualSourceId,
          target: actualTargetId,
          type: 'Μ'
        });
      }
    } else if (part.startsWith('Ν(')) {
      // MUST_NOT(X5, ManualTransmission) - zakázaná väzba
      const match = part.match(/Ν\s*\(\s*([^,]+),\s*([^)]+)\s*\)/);
      if (match) {
        const sourceId = match[1].trim();
        const targetId = match[2].trim();
        
        // Nahradíme premenné ich typmi
        const actualSourceId = isVariableNode(sourceId) || isIndexedVariable(sourceId) ? 
          variableToTypeMap.get(sourceId) || sourceId : sourceId;
        const actualTargetId = isVariableNode(targetId) || isIndexedVariable(targetId) ? 
          variableToTypeMap.get(targetId) || targetId : targetId;
        
        // Ak nemáme informácie o typoch, preskočíme
        if (isVariableNode(actualSourceId) || isVariableNode(actualTargetId)) {
          return;
        }
        
        addNode(actualSourceId, actualSourceId);
        addNode(actualTargetId, actualTargetId);
        
        links.push({
          source: actualSourceId,
          target: actualTargetId,
          type: 'Ν'
        });
      }
    } else if (part.startsWith('Π(')) {
      // HAS_PART(x, e) - vzťah "má časť"
      const match = part.match(/Π\s*\(\s*([^,]+),\s*([^)]+)\s*\)/);
      if (match) {
        const wholeId = match[1].trim();
        const partId = match[2].trim();
        
        // Nahradíme premenné ich typmi
        const actualWholeId = isVariableNode(wholeId) || isIndexedVariable(wholeId) ? 
          variableToTypeMap.get(wholeId) || wholeId : wholeId;
        const actualPartId = isVariableNode(partId) || isIndexedVariable(partId) ? 
          variableToTypeMap.get(partId) || partId : partId;
        
        // Ak nemáme informácie o typoch, preskočíme
        if (isVariableNode(actualWholeId) || isVariableNode(actualPartId)) {
          return;
        }
        
        addNode(actualWholeId, actualWholeId);
        addNode(actualPartId, actualPartId);
        
        links.push({
          source: actualWholeId,
          target: actualPartId,
          type: 'Π'
        });
      }
    } else if (part.startsWith('Α(')) {
      // Attribute(e, power, 250 ∨ 340) - atribút s hodnotou
      const match = part.match(/Α\s*\(\s*([^,]+),\s*([^,]+),\s*(.+)\s*\)/);
      if (match) {
        const objectId = match[1].trim();
        
        // Nahradíme premenné ich typmi
        const actualObjectId = isVariableNode(objectId) || isIndexedVariable(objectId) ? 
          variableToTypeMap.get(objectId) || objectId : objectId;
        
        // Ak nemáme informácie o typoch, preskočíme
        if (isVariableNode(actualObjectId)) {
          return;
        }
        
        const attributeName = match[2].trim();
        const attributeId = `${actualObjectId}_${attributeName}`;
        const valueText = match[3].trim();
        
        addNode(actualObjectId, actualObjectId);
        addNode(attributeId, 'Attribute');
        
        // Vytvorenie spojenia medzi objektom a jeho atribútom
        links.push({
          source: actualObjectId,
          target: attributeId,
          type: 'Α'
        });
        
        // Spracovanie hodnôt atribútu (môžu byť spojené s ∨)
        const values = valueText.split('∨').map(v => v.trim());
        values.forEach(value => {
          const valueId = `${attributeId}_${value}`;
          addNode(valueId, 'Value');
          
          links.push({
            source: attributeId,
            target: valueId,
            type: 'VALUE'
          });
        });
      }
    }
  });
  
  return {
    nodes: Array.from(nodeMap.values()),
    links
  };
};

// Funkcia na získanie farby podľa statusu prvku
const getStatusColor = (status: string | undefined): string => {
  if (status === 'missingInExample') return '#000000'; // Čierna - chýbajúci prvok v užívateľskom príklade
  
  switch (status) {
    case 'valid': return '#4CAF50'; // Zelená - platný prvok
    case 'invalid': return '#F44336'; // Červená - neplatný prvok (nesprávna hodnota)
    case 'missing': return '#F44336'; // Červená - chýbajúci povinný prvok
    case 'extra': return '#F44336'; // Červená - nadbytočný prvok (nemal by tam byť)
    default: return '#999999'; // Šedá - neutrálny prvok
  }
};

// Funkcia na konverziu PL1 symbolov na čitateľné textové reprezentácie
const getLogicalSymbolLabel = (type: string): string => {
  switch (type) {
    case 'must':
    case 'Μ': 
      return 'MUST';
    case 'must_not':
    case 'Ν': 
      return 'MUST_NOT';
    case 'must_be_a':
    case 'Ι': 
      return 'IS_A';
    case 'Π': 
      return 'HAS_PART';
    case 'HAS_ATTRIBUTE':
    case 'Α': 
      return 'HAS_ATTR';
    case 'VALUE': 
      return 'VALUE';
    default: 
      return type;
  }
};

// Function to extract components from violation messages
const extractComponentsFromViolations = (violations: string[]): string[] => {
  const componentSet = new Set<string>();
  
  violations.forEach(violation => {
    // Try to extract using regex patterns for various formats
    const patterns = [
      /musí\s+(mať|mit|mít)\s+komponentu\s+([a-zA-Z0-9]+)/i,
      /Model\s+\w+\s+musí\s+(mať|mit|mít)\s+komponentu\s+([a-zA-Z0-9]+)/i,
      /must\s+have\s+component\s+([a-zA-Z0-9]+)/i
    ];
    
    for (const pattern of patterns) {
      const match = violation.match(pattern);
      if (match) {
        const component = match[match.length - 1];
        componentSet.add(component);
      }
    }
  });
  
  return Array.from(componentSet);
};

const ExampleNetworkGraph: React.FC<ExampleNetworkGraphProps> = ({ 
  comparisonResult, 
  formula,
  showLayeredVisualization = true,
  viewType = 'model'
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [network, setNetwork] = useState<Network | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [showHypothesis, setShowHypothesis] = useState(true);
  
  // Zabezpečí, že kontajner sa pripojil k DOM
  useEffect(() => {
    // Oneskoríme inicializáciu, aby sa kontajner mohol vyrenderiť
    const timer = setTimeout(() => {
      setIsReady(true);
    }, 300);
    
    return () => clearTimeout(timer);
  }, []);
  
  useEffect(() => {
    if (!containerRef.current) return;
    
    console.log("ComparisonResult:", comparisonResult);
    console.log("ViewType:", viewType);
    
    // Parse the example formula to get nodes and links
    let parsedData = parseFormulaToNodesAndLinks(formula);
    
    // Deep copy the nodes and links for the visualization
    let processedNodes = JSON.parse(JSON.stringify(parsedData.nodes));
    let processedLinks = JSON.parse(JSON.stringify(parsedData.links));
    
    // Mark elements as missing/extra based on comparison result
    let missingElements: string[] = [];
    let extraElements: string[] = [];
    
    // Extract violations from comparison result
    if (comparisonResult.categorized_violations) {
      if (comparisonResult.categorized_violations.component_violations) {
        missingElements = [...missingElements, ...comparisonResult.categorized_violations.component_violations];
        
        // Log the component violations for debugging
        console.log("Component violations:", comparisonResult.categorized_violations.component_violations);
      }
      if (comparisonResult.categorized_violations.must_violations) {
        missingElements = [...missingElements, ...comparisonResult.categorized_violations.must_violations];
      }
      if (comparisonResult.categorized_violations.must_not_violations) {
        extraElements = [...extraElements, ...comparisonResult.categorized_violations.must_not_violations];
      }
    }
    
    // Get all components mentioned in the violations for missing component detection
    const allMissingComponentNames = new Set<string>();
    
    // Priamo pridáme komponenty zo zoznamu porušení, aby sa určite zobrazili
    const knownComponents = [
      'SUV', 'Wheels', 'Seats', 'Infotainment', 'Lights', 'Brakes', 
      'Suspension', 'Engine', 'Transmission', 'ManualTransmission', 
      'AutomaticTransmission', 'DieselEngine', 'PetrolEngine', 'XDrive',
      'RWD', 'AWD', 'CompactSUV'
    ];
    
    // Zaistíme zobrazenie všetkých vzťahov z kategorizovaných pravidiel
    if (comparisonResult.categorized_violations?.component_violations) {
      // Prejdeme všetky porušenia komponentov
      comparisonResult.categorized_violations.component_violations.forEach(violation => {
        console.log("Processing component violation:", violation);
        
        // Kontrola komponentov v texte
        knownComponents.forEach(comp => {
          if (violation.includes(comp)) {
            console.log(`Found component in violation: ${comp}`);
            allMissingComponentNames.add(comp);
          }
        });
        
        // Extrakcia komponentov z rôznych vzorov
        const componentPatterns = [
          /musí\s+(mať|mit|mít)\s+komponentu\s+([a-zA-Z0-9]+)/i,
          /Model\s+\w+\s+musí\s+(mať|mit|mít)\s+komponentu\s+([a-zA-Z0-9]+)/i,
          /must\s+have\s+component\s+([a-zA-Z0-9]+)/i
        ];
        
        let foundComponent = false;
        for (const pattern of componentPatterns) {
          const match = violation.match(pattern);
          if (match) {
            const component = match[match.length - 1]; // Posledná zachytená skupina je názov komponentu
            console.log(`Extracted component: ${component}`);
            allMissingComponentNames.add(component);
            foundComponent = true;
          }
        }
        
        if (!foundComponent) {
          // Ak sme nenašli komponent pomocou vzoru, skúsime posledné slovo
          const words = violation.split(/\s+/);
          if (words.length > 0) {
            const lastWord = words[words.length - 1].replace(/[^a-zA-Z0-9]/g, '');
            if (lastWord.length > 2 && knownComponents.includes(lastWord)) {
              console.log(`Found component as last word: ${lastWord}`);
              allMissingComponentNames.add(lastWord);
            }
          }
        }
      });
      
      // Explicitné pridanie známych komponentov pre istotu
      ['SUV', 'Wheels', 'Seats', 'Infotainment', 'Lights', 'Brakes', 'Suspension'].forEach(comp => {
        if (comparisonResult.categorized_violations?.component_violations?.some(v => v.toLowerCase().includes(comp.toLowerCase()))) {
          allMissingComponentNames.add(comp);
        }
      });
    }
    
    console.log("Final missing components:", Array.from(allMissingComponentNames));
    
    // Update node statuses based on viewType
    processedNodes = processedNodes.map((node: NetworkNode) => {
      // Check if this node is missing from the user example
      const isMissing = missingElements.some(element => 
        element.includes(node.name) || element.includes(node.id)
      );
      
      // Check if this node is extra in the user example
      const isExtra = extraElements.some(element => 
        element.includes(node.name) || element.includes(node.id)
      );
      
      // For model view, highlight missing elements
      // For example view, highlight extra elements
      if (viewType === 'model' && isMissing) {
        return { ...node, status: 'missing', size: 40, color: '#000000' }; // Black for missing components
      } else if (viewType === 'example' && isExtra) {
        return { ...node, status: 'extra', size: 40, color: '#F44336' }; // Red for extra components
      } else {
        return { ...node, status: 'valid', size: 30 };
      }
    });
    
    // Update link statuses based on viewType
    processedLinks = processedLinks.map((link: NetworkLink) => {
      // Check if this link is missing from the user example
      const isMissing = missingElements.some(element => 
        element.includes(`${link.source}`) && element.includes(`${link.target}`)
      );
      
      // Check if this link is extra in the user example
      const isExtra = extraElements.some(element => 
        element.includes(`${link.source}`) && element.includes(`${link.target}`)
      );
      
      // For model view, highlight missing links
      // For example view, highlight extra links
      if (viewType === 'model' && isMissing) {
        return { ...link, status: 'missing', width: 4 }; // Thicker line for better visibility
      } else if (viewType === 'example' && isExtra) {
        return { ...link, status: 'extra', width: 4 }; // Thicker line for better visibility
      } else {
        return { ...link, status: 'valid', width: 2 };
      }
    });
    
    try {
      // Collect heuristics grouped by training steps
      const attributeViolationsSet = new Set<string>();
      
      // Získanie zoznamu porušení z výsledku porovnania
      const satisfiedRules = comparisonResult.satisfied_rules || [];
      
      // Zber všetkých porušení atribútov pre farby
      if (comparisonResult.categorized_violations?.attribute_violations) {
        comparisonResult.categorized_violations.attribute_violations.forEach(violation => {
          attributeViolationsSet.add(violation);
          console.log("Adding attribute violation:", violation);
        });
      }
      
      // Process the nodes to identify invalid values more accurately
      processedNodes = processedNodes.map((node: NetworkNode) => {
        // If this is a Value node, check if it holds an invalid value
        if (node.category === 'Value') {
          // Extract the attribute name from the node id (usually in format like "Value_power_400")
          const parts = node.id.split('_');
          const value = parts[parts.length - 1];
          const attributeName = parts.length > 2 ? parts[parts.length - 2] : '';
          
          console.log(`Checking value node: ${node.id}, attribute: ${attributeName}, value: ${value}`);
          
          // Check for specific known invalid values
          if ((attributeName === 'power' && value === '400') || 
              (attributeName === 'cylinders' && value === '6')) {
            console.log(`Found invalid value: ${value} for ${attributeName}`);
            return { 
              ...node, 
              status: 'invalid', 
              size: 40,
              shape: 'hexagon',
              group: 'InvalidValue' 
            };
          }
          
          // Check for violations that mention this value
          for (const violation of attributeViolationsSet) {
            // Look for value in the violation message
            if (violation.includes(value)) {
              // Different patterns to match values in error messages
              const valuePatterns = [
                new RegExp(`\\b${value}\\b`),                  // Match the exact value
                new RegExp(`value\\s+${value}`),               // "value 400"
                new RegExp(`value\\s+is\\s+${value}`),         // "value is 400"
                new RegExp(`${attributeName}\\s*[:]?\\s*${value}`), // "power: 400"
                new RegExp(`${value}\\s+for\\s+${attributeName}`)   // "400 for power"
              ];
              
              if (valuePatterns.some(pattern => pattern.test(violation))) {
                console.log(`Found invalid value in violation: ${value} for ${attributeName}`);
                return { 
                  ...node, 
                  status: 'invalid', 
                  size: 40,
                  shape: 'hexagon',
                  group: 'InvalidValue' 
                };
              }
            }
          }
          
          // Assign all value nodes to the Value group for consistent styling
          return { ...node, group: 'Value' };
        }
        
        // If this is an Attribute node with invalid values
        if (node.category === 'Attribute') {
          const attributeName = node.id.split('_').pop() || '';
          
          for (const violation of attributeViolationsSet) {
            // Check if the violation message mentions this attribute
            if (violation.toLowerCase().includes(attributeName.toLowerCase())) {
              // Look for patterns like "attribute X: value" or "attribute X" in general
              const attrPattern = new RegExp(`\\b${attributeName}\\b.*?(:|with|value|is|=)`, 'i');
              if (attrPattern.test(violation)) {
                console.log("Found invalid attribute in violation:", attributeName, "node:", node.id);
                return { ...node, status: 'invalid', size: 38, group: 'invalid' };
              }
            }
          }
        }
        
        return node;
      });
      
      // Create a complete set of hypothesis nodes and links - ensure all model components are included
      const hypothesisNodes: NetworkNode[] = [...processedNodes];
      const hypothesisLinks: NetworkLink[] = [...processedLinks];
      
      // Add missing components to hypothesis view based on extracted names
      if (allMissingComponentNames.size > 0) {
        console.log(`Adding ${allMissingComponentNames.size} missing components:`, Array.from(allMissingComponentNames));
        
        // Check if we need to create an X5 node
        const hasX5Node = hypothesisNodes.some((n: NetworkNode) => n.name === 'X5' || n.id === 'X5');
        let x5NodeId = '';
        
        // Add X5 node if it doesn't exist and we have missing components
        if (!hasX5Node) {
          console.log("Creating X5 node since it doesn't exist");
          const x5Node: NetworkNode = {
            id: 'X5',
            name: 'X5',
            class: 'X5',
            category: 'Model',
            status: 'missing', // Set status to missing to highlight it
            size: 45
          };
          
          hypothesisNodes.push(x5Node);
          x5NodeId = 'X5';
        } else {
          // Get the ID of the existing X5 node
          const x5Node = hypothesisNodes.find((n: NetworkNode) => n.name === 'X5' || n.id === 'X5');
          if (x5Node) {
            console.log("Found existing X5 node:", x5Node);
            // Update the existing node to highlight it
            x5Node.status = 'missing';
            x5Node.size = 45;
          }
          x5NodeId = x5Node?.id || 'X5';
        }
        
        // Add all missing components and connect them to X5
        if (x5NodeId) {
          // Generate positions in a circle around the X5 node for better layout
          const numComponents = allMissingComponentNames.size;
          
          allMissingComponentNames.forEach((component, index) => {
            console.log(`Processing component: ${component}`);
            if (!hypothesisNodes.some(n => n.name === component || n.id === component)) {
              console.log(`Adding missing component to graph: ${component}`);
              
              // Add the missing component node
              hypothesisNodes.push({
                id: component,
                name: component,
                class: component,
                category: 'MissingComponent',
                status: 'missing',
                size: 45
              });
              
              // Connect it to the X5 model with a MUST relationship
              hypothesisLinks.push({
                source: x5NodeId,
                target: component,
                type: 'MUST',
                status: 'missing',
                width: 5
              });
            } else {
              console.log(`Component ${component} already exists in the graph`);
            }
          });
        }
      }
      
      // Pripravíme spojenia pre príklad
      const exampleLinks: NetworkLink[] = [];
      processedLinks.forEach((link: NetworkLink) => {
        let status: 'valid' | 'invalid' | 'missing' | 'extra' = 'valid';
        
        // Check if this is a link to an invalid value
        if (link.type === 'VALUE') {
          // Check if the target node is marked as invalid
          const targetNode = processedNodes.find((n: NetworkNode) => n.id === link.target);
          if (targetNode && targetNode.status === 'invalid') {
            status = 'invalid';
          }
        } else if (link.status === 'missing') {
          status = 'missing'; // Make sure missing links keep their status
        }
        
        exampleLinks.push({
          ...link,
          status,
          width: status === 'invalid' ? 3 : 2 // Thicker lines for invalid links
        });
      });
      
      // Create the data model based on showHypothesis flag
      const allNodes = showHypothesis 
        ? hypothesisNodes
        : [...processedNodes];  // Vytvoríme kópiu, aby sme mohli pridať chýbajúce komponenty
      
      // Pre user príklad (viewType === 'example') pridáme chýbajúce komponenty
      if (viewType === 'example' && !showHypothesis) {
        console.log("Adding missing components to example view");
        
        // Extract missing components directly from violations
        const missingComponents = comparisonResult.categorized_violations?.component_violations 
          ? extractComponentsFromViolations(comparisonResult.categorized_violations.component_violations)
          : [];
        
        console.log("Missing components from violations:", missingComponents);
        
        if (missingComponents.length > 0) {
          // Get or create X5 node
          let x5NodeId = '';
          const hasX5Node = allNodes.some(n => n.name === 'X5' || n.id === 'X5');
          
          if (!hasX5Node) {
            const x5Node: NetworkNode = {
              id: 'X5',
              name: 'X5',
              class: 'X5',
              category: 'Model',
              status: 'valid',
              size: 40
            };
            allNodes.push(x5Node);
            x5NodeId = 'X5';
          } else {
            const x5Node = allNodes.find(n => n.name === 'X5' || n.id === 'X5');
            x5NodeId = x5Node?.id || 'X5';
          }
          
          // Add missing components as black nodes
          missingComponents.forEach(component => {
            if (!allNodes.some(n => n.name === component || n.id === component)) {
              console.log(`Adding missing component as black node: ${component}`);
              
              // Add the missing component explicitly with correct status and category
              allNodes.push({
                id: component,
                name: component,
                class: component,
                category: 'MissingInExample',
                status: 'missingInExample' as any, // Type assertion to fix type error
                size: 40
              });
              
              // Add connection to X5
              processedLinks.push({
                source: x5NodeId,
                target: component,
                type: 'MUST',
                status: 'missingInExample' as any, // Type assertion to fix type error
                width: 4
              });
            }
          });
        }
      }
      
      // Prepare nodes for vis.js
      const visNodes = allNodes.map((node: NetworkNode) => {
        let statusColor = getStatusColor(node.status);
        let shape = 'dot';
        
        // Custom shapes for different node types
        if (node.category === 'Attribute') {
          shape = 'diamond';
        } else if (node.category === 'Value') {
          if (node.status === 'invalid') {
            // Use a more attention-grabbing shape for invalid values
            shape = 'hexagon';  // Or can use 'square' but with distinct styling
            statusColor = '#FF9800'; // Orange for invalid values
          } else {
            shape = 'square';
          }
        } else if (node.status === 'missing' || node.category === 'MissingComponent') {
          // Use diamond shape for missing components to make them stand out
          shape = 'diamond';
          // Override statusColor for missing components with a vibrant red
          statusColor = '#F44336';
        } else if (node.status === 'missingInExample' || node.category === 'MissingInExample') {
          // Use diamond shape for missing components in example to make them stand out
          shape = 'diamond';
          // Override statusColor for missing components in example with black
          statusColor = '#000000';
        } else if (node.status === 'extra') {
          // Use triangle shape for extra components that shouldn't be there
          shape = 'triangle';
          statusColor = '#F44336'; // Red for extra elements
        } else if (node.status === 'invalid') {
          // Keep original shape but highlight with orange for invalid values
          statusColor = '#FF9800';
        }
        
        // Special handling for categories
        if (node.category === 'MissingComponent') {
          shape = 'diamond'; 
          statusColor = '#F44336'; // Red color for missing components
        } else if (node.category === 'MissingInExample') {
          shape = 'diamond';
          statusColor = '#000000'; // Black color for missing components in example
        }
        
        // Zistíme, či je uzol súčasťou príkladu
        const isPartOfExample = processedNodes.some((n: NetworkNode) => n.id === node.id);
        
        // Missing components should always have full opacity
        const opacity = (node.status === 'missing' || node.category === 'MissingComponent') 
          ? 1.0  // Full opacity for missing components
          : (showHypothesis && !isPartOfExample)
            ? 0.6  // Higher opacity for other hypothesis elements
            : 1.0;  // Full opacity for example elements
        
        // Increase size for missing/extra/invalid nodes
        const nodeSize = (node.status === 'missing' || node.category === 'MissingComponent') 
          ? (node.size || 45)  // Bigger for missing
          : (node.status === 'extra')
            ? (node.size || 40) // Big for extra
            : (node.status === 'invalid')
              ? (node.size || 38) // Slightly bigger for invalid values
              : (node.size || 35); // Normal size
        
        const borderWidth = (node.status === 'missing' || node.category === 'MissingComponent')
          ? 4  // Thicker border for missing
          : (node.status === 'extra')
            ? 3  // Thick border for extra
            : (node.status === 'invalid')
              ? 3  // Thick border for invalid values
              : 2; // Normal border
        
        // Handle colors differently for value nodes with invalid values
        let borderColor = '#222222';
        if (node.status === 'missing' || node.status === 'extra' || node.status === 'invalid') {
          borderColor = '#000000';
        }
        
        // For invalid value nodes, use a more distinct border color
        if (node.category === 'Value' && node.status === 'invalid') {
          borderColor = '#CC7000'; // Darker orange for border contrast
        }
        
        // Enhanced font for special nodes
        const fontSize = (node.status === 'missing' || node.category === 'MissingComponent' || 
                          node.status === 'extra' || node.status === 'invalid')
          ? 16  // Larger font for special nodes
          : 14;  // Normal font size
        
        // Enhanced shadow for special nodes
        const shadowSize = (node.status === 'missing' || node.category === 'MissingComponent')
          ? 15  // Larger shadow for missing
          : (node.status === 'extra' || node.status === 'invalid')
            ? 12  // Medium shadow for extra/invalid
            : 10;  // Normal shadow size
        
        return {
          id: node.id,
          label: node.name,
          shape: shape,
          color: { 
            background: statusColor,
            border: borderColor,
            highlight: { background: statusColor, border: '#FFFFFF' },
            hover: { background: statusColor, border: '#FFFFFF' }
          },
          borderWidth: borderWidth,
          size: nodeSize,
          font: {
            color: '#FFFFFF', 
            size: fontSize,
            strokeWidth: 4,
            strokeColor: '#000000',
            face: 'arial',
            bold: true
          },
          opacity: opacity,
          shadow: {
            enabled: node.status === 'missing' || node.status === 'extra' || 
                    node.status === 'invalid' || node.category === 'MissingComponent',
            size: shadowSize,
            color: statusColor
          }
        };
      });
      
      // Prepare edges for vis.js
      const visEdges = showHypothesis
        ? hypothesisLinks.map(link => {
            // Check if this edge connects to a missing component
            const targetNode = hypothesisNodes.find(n => n.id === link.target);
            const isMissingConnection = targetNode?.status === 'missing';
        
        return {
          from: link.source,
          to: link.target,
              label: getLogicalSymbolLabel(link.type),
              font: { 
                size: isMissingConnection ? 12 : 10, 
                strokeWidth: isMissingConnection ? 3 : 2, 
                strokeColor: '#000000',
                color: '#FFFFFF',
                align: 'middle',
                bold: isMissingConnection
              },
              width: isMissingConnection ? 4 : (link.width || 2), // Thicker for missing connections
          color: {
                color: isMissingConnection ? '#F44336' : getStatusColor(link.status) || '#999999',
                highlight: '#FFFFFF',
                hover: '#FFFFFF'
              },
              length: 180, // Longer for better readability
              smooth: {
                enabled: true,
                type: 'cubicBezier',
                roundness: 0.2
              },
              arrows: {
                to: { 
                  enabled: true,
                  scaleFactor: isMissingConnection ? 1.5 : 1.2,
                  type: isMissingConnection ? 'arrow' : 'arrow'
                }
              },
              shadow: {
                enabled: link.status === 'missing' || link.status === 'extra' || isMissingConnection,
                color: getStatusColor(link.status),
                size: isMissingConnection ? 12 : 8
              },
              dashes: isMissingConnection ? false : false // Solid lines for missing connections
            };
          })
        : processedLinks.map((link: NetworkLink) => {
            // Check if this edge connects to a missing component
            const targetNode = allNodes.find(n => n.id === link.target);
            const isMissingInExample = targetNode?.status === ('missingInExample' as any) || targetNode?.category === 'MissingInExample';
            const isMissingConnection = targetNode?.status === 'missing' || targetNode?.category === 'MissingComponent';
            
            return {
              from: link.source,
              to: link.target,
              label: getLogicalSymbolLabel(link.type),
              font: { 
                size: (isMissingInExample || isMissingConnection) ? 12 : 10, 
                strokeWidth: (isMissingInExample || isMissingConnection) ? 3 : 2, 
                strokeColor: '#000000',
                color: '#FFFFFF',
                align: 'middle',
                bold: (isMissingInExample || isMissingConnection)
              },
              width: (isMissingInExample || isMissingConnection) ? 4 : (link.width || 2),
              color: {
                color: isMissingInExample ? '#000000' : // Čierna pre chýbajúce v príklade
                      isMissingConnection ? '#F44336' : // Červená pre chýbajúce v modeli
                      getStatusColor(link.status) || '#999999',
                highlight: '#FFFFFF',
                hover: '#FFFFFF'
              },
              length: 150, // Fixed length for better readability
            smooth: {
              enabled: true,
                type: 'cubicBezier',
                roundness: 0.2
              },
              arrows: {
                to: { 
                  enabled: true,
                  scaleFactor: 1.2,
                  type: 'arrow'
                }
              },
              shadow: {
                enabled: link.status === 'missing' || link.status === 'extra',
                color: getStatusColor(link.status)
              }
            };
          });
      
      // Create the network  
      const container = containerRef.current;
      
      if (container) {
        // Initialize data and options
        const data = {
          nodes: new DataSet<any>(visNodes),
          edges: new DataSet<any>(visEdges)
        };
        
        const options = {
          nodes: {
            shape: 'dot',
            size: 35,
            font: {
              size: 14,
              color: '#000000',
              face: 'arial',
              strokeWidth: 3,
              strokeColor: '#FFFFFF',
              bold: {
                color: '#000000',
                size: 16,
                face: 'arial',
                vadjust: 0,
                mod: 'bold'
              }
            },
            borderWidth: 2,
            shadow: true
          },
          edges: {
            width: 3,
            color: {
              color: '#848484',
              highlight: '#000000',
              hover: '#000000'
            },
            arrows: {
              to: { enabled: true, scaleFactor: 1.2 }
            },
            smooth: {
              enabled: true,
              type: 'dynamic',
              forceDirection: 'none',
              roundness: 0.5
            },
            hoverWidth: 4,
            selectionWidth: 4
          },
          physics: {
            enabled: true,
            barnesHut: {
              gravitationalConstant: viewType === 'model' ? -20000 : -10000,
              centralGravity: viewType === 'model' ? 0.2 : 0.5,
              springLength: viewType === 'model' ? 350 : 200,
              springConstant: 0.05,
              damping: 0.09,
              avoidOverlap: 1.0
            },
            stabilization: {
              enabled: true,
              iterations: 2000,
              updateInterval: 25,
              fit: true
            },
            timestep: 0.5,
            adaptiveTimestep: true
          },
          interaction: {
            hover: true,
            tooltipDelay: 200,
            zoomView: true,
            dragView: true,
            navigationButtons: true,
            keyboard: true,
            multiselect: true
          },
          layout: {
            improvedLayout: true,
            randomSeed: undefined,
            hierarchical: {
              enabled: false
            }
          },
          groups: {
            MissingInExample: {
              shape: 'diamond',
              color: {
                background: '#000000',
                border: '#FFFFFF',
                highlight: { background: '#333333', border: '#FFFFFF' }
              },
              borderWidth: 3,
              size: 40,
              font: {
                color: '#FFFFFF',
                size: 16,
                face: 'arial',
                strokeWidth: 3,
                strokeColor: '#000000',
                bold: true
              },
              shadow: { enabled: true, size: 12, color: '#000000' }
            },
            MissingComponent: {
              shape: 'diamond',
              color: {
                background: '#F44336',
                border: '#FFFFFF',
                highlight: { background: '#EF5350', border: '#FFFFFF' }
              },
              borderWidth: 3,
              size: 40,
              font: {
                color: '#FFFFFF',
                size: 16,
                face: 'arial',
                strokeWidth: 3,
                strokeColor: '#000000',
                bold: true
              },
              shadow: { enabled: true, size: 10, color: '#F44336' }
            },
            extra: {
              shape: 'triangle',
              color: {
                background: '#F44336',
                border: '#000000',
                highlight: { background: '#EF5350', border: '#FFFFFF' }
              },
              borderWidth: 3,
              size: 40,
              font: {
                color: '#FFFFFF',
                size: 16,
                face: 'arial',
                strokeWidth: 4,
                strokeColor: '#000000',
                bold: true
              },
              shadow: { enabled: true, size: 12, color: '#F44336' }
            },
            invalid: {
              color: {
                background: '#FF9800',
                border: '#000000',
                highlight: { background: '#FFA726', border: '#FFFFFF' }
              },
              borderWidth: 3,
              size: 38,
              font: {
                color: '#FFFFFF',
                size: 16,
                face: 'arial',
                strokeWidth: 4,
                strokeColor: '#000000',
                bold: true
              },
              shadow: { enabled: true, size: 12, color: '#FF9800' }
            },
            Value: {
              shape: 'square',
              color: {
                background: '#4CAF50',
                border: '#222222',
                highlight: { background: '#66BB6A', border: '#FFFFFF' }
              }
            },
            InvalidValue: {
              shape: 'hexagon',
              color: {
                background: '#FF9800',
                border: '#CC7000',
                highlight: { background: '#FFA726', border: '#FFFFFF' }
              },
              borderWidth: 3,
              size: 40,
              font: {
                color: '#FFFFFF',
                size: 16,
                face: 'arial',
                strokeWidth: 4,
                strokeColor: '#000000',
                bold: true
              },
              shadow: { enabled: true, size: 15, color: '#FF9800' }
            }
          }
        };
      
        // Create the network
        const networkInstance = new Network(container, data, options as any);
        
        // Create a separate array to store missing component IDs
        const missingComponentIds: string[] = [];
        allNodes.forEach((node: NetworkNode) => {
          if (node.category === 'MissingComponent' || node.status === 'missing') {
            missingComponentIds.push(node.id);
          }
        });
        
        // Add stabilization progress handler
        networkInstance.on("stabilizationProgress", function(params) {
          console.log("Stabilization in progress, iterations:", params.iterations, "/", params.total);
        });
        
        // Add initial stabilization event handler
        networkInstance.once('stabilizationIterationsDone', function() {
          console.log('Network stabilized');
          
          if (viewType === 'model' && missingComponentIds.length > 0) {
            console.log(`Found ${missingComponentIds.length} missing components to arrange`);
            
            // Optionally give the network some time to render before fitting
            setTimeout(() => {
              networkInstance.fit({
                nodes: missingComponentIds,
                animation: {
                  duration: 1000,
                  easingFunction: 'easeInOutQuad'
                }
              });
            }, 500);
          } else {
            networkInstance.fit();
          }
        });
      
      // Add a click event handler
      networkInstance.on('click', function(params) {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0];
          console.log('Clicked node ID:', nodeId);
          
          // Hľadáme uzol v príklade alebo v hypotéze
          const clickedNode = allNodes.find((n: NetworkNode) => n.id === nodeId);
          if (clickedNode) {
            console.log('Node details:', clickedNode);
          }
        }
      });
      
      // Save reference to network
      setNetwork(networkInstance);
      setError(null);
      
      // Cleanup on unmount
      return () => {
        if (networkInstance) {
          networkInstance.destroy();
        }
      };
      }
    } catch (e) {
      console.error('Error creating network visualization:', e);
      setError(`Error creating network visualization: ${(e as Error).message}`);
    }
  }, [comparisonResult, formula, isReady, showHypothesis, viewType]);
  
  // Pridáme legendu s vysvetlením farieb
  const renderLegend = () => {
    return (
      <div className="network-legend" style={{
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        padding: '12px 16px',
        borderRadius: '8px',
        boxShadow: '0 4px 15px rgba(0, 0, 0, 0.3)',
        border: '1px solid rgba(255, 255, 255, 0.15)'
      }}>
        <div className="legend-title" style={{ fontSize: '15px', marginBottom: '10px', color: '#90caf9' }}>Legenda:</div>
        <div className="legend-item" style={{ marginBottom: '8px' }}>
          <span className="legend-color" style={{ display: 'inline-block', backgroundColor: getStatusColor('valid'), width: '18px', height: '18px', marginRight: '10px', borderRadius: '3px' }}></span>
          <span style={{ fontSize: '14px' }}>Platný prvok</span>
        </div>
        <div className="legend-item" style={{ marginBottom: '8px' }}>
          <span className="legend-color" style={{ display: 'inline-block', backgroundColor: getStatusColor('invalid'), width: '18px', height: '18px', marginRight: '10px', borderRadius: '3px' }}></span>
          <span style={{ fontSize: '14px' }}>Neplatná hodnota</span>
        </div>
        <div className="legend-item" style={{ marginBottom: '8px' }}>
          <span className="legend-color" style={{ display: 'inline-block', backgroundColor: getStatusColor('missing'), width: '18px', height: '18px', marginRight: '10px', borderRadius: '3px' }}></span>
          <span style={{ fontSize: '14px' }}>Chýbajúci povinný prvok</span>
        </div>
        <div className="legend-item" style={{ marginBottom: '8px' }}>
          <span className="legend-color" style={{ display: 'inline-block', backgroundColor: getStatusColor('extra'), width: '18px', height: '18px', marginRight: '10px', borderRadius: '3px' }}></span>
          <span style={{ fontSize: '14px' }}>Nadbytočný prvok</span>
        </div>
        {/* Prepínač pre zobrazenie hypotézy */}
        <div className="legend-item" style={{ marginTop: '12px', borderTop: '1px solid rgba(255, 255, 255, 0.1)', paddingTop: '8px' }}>
          <input 
            type="checkbox" 
            id="show-hypothesis" 
            checked={showHypothesis} 
            onChange={() => setShowHypothesis(!showHypothesis)} 
            style={{ marginRight: '10px' }}
          />
          <label htmlFor="show-hypothesis" style={{ fontSize: '14px' }}>Zobraziť hypotézu</label>
        </div>
      </div>
    );
  };
  
  // Add this to the render function, just before the closing return statement
  const networkStyle = {
    height: '100%',
    minHeight: '800px',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '8px',
    background: 'rgba(17, 24, 39, 0.7)',
    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)'
  };
  
  // Render network graph with legend and loading state
  return (
    <div className="network-container">
      {error && <div className="network-error">Error: {error}</div>}
      
      <div 
        ref={containerRef} 
        className="network-vis-container"
        style={networkStyle}
      ></div>
      
      {!error && !isReady && (
        <div className="network-loading">
          Načítavam vizualizáciu...
        </div>
      )}
      
      {!error && isReady && renderLegend()}
    </div>
  );
};

export default ExampleNetworkGraph;