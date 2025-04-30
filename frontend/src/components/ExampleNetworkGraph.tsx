import React, { useRef, useState, useEffect } from 'react';
import { Network, Data, Options, Edge, Node } from 'vis-network';
import { DataSet } from 'vis-data';
import { ComparisonResult, NetworkNode as BaseNetworkNode, NetworkLink as BaseNetworkLink } from '../types';
import './NetworkGraph.css';

interface ExampleNetworkGraphProps {
  comparisonResult: ComparisonResult;
  formula: string;
  showLayeredVisualization?: boolean;
  viewType?: 'model' | 'example' | 'combined'; // Add combined view type option
}

// Use a completely separate interface for visualization needs instead of extending BaseNetworkNode
interface NetworkNode {
  id: string;
  name: string;
  class?: string;
  class_name?: string;
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
  if (status === 'missingInExample') return '#000000'; // Black - missing element in user example
  
  switch (status) {
    case 'valid': return '#4CAF50'; // Green - valid element
    case 'invalid': return '#FF9800'; // Orange - invalid element (wrong value)
    case 'missing': return '#F44336'; // Red - missing required element
    case 'extra': return '#2196F3'; // Blue - excess element (shouldn't be there)
    default: return '#999999'; // Gray - neutral element
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
  
  // Zabezpečí, že kontajner sa pripojil k DOM
  useEffect(() => {
    // Oneskoríme inicializáciu, aby sa kontajner mohol vyrenderiť
    const timer = setTimeout(() => {
      setIsReady(true);
    }, 300);
    
    return () => clearTimeout(timer);
  }, []);
  
  useEffect(() => {
    if (!containerRef.current || !isReady) return;
    
    console.log("ComparisonResult:", comparisonResult);
    console.log("ViewType:", viewType);
    
    // Check if validation shows this example is invalid
    const isExampleValid = comparisonResult.is_valid === true;
    console.log("Is example valid:", isExampleValid);
    
    // Log validation count information
    const violationCount = (comparisonResult.violations || []).length;
    const satisfiedCount = (comparisonResult.satisfied_rules || []).length;
    console.log(`Validation stats: ${violationCount} violations, ${satisfiedCount} satisfied rules`);
    
    // Cleanup any existing network instance first to prevent DOM conflicts
    if (network) {
      console.log("Cleaning up existing network instance");
      network.destroy();
      setNetwork(null);
    }
    
    // Create a local variable for the network instance that we'll create
    let networkInstance: Network | null = null;
    
    try {
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
          console.log("Component violations:", comparisonResult.categorized_violations.component_violations);
        }
        
        if (comparisonResult.categorized_violations.must_violations) {
          missingElements = [...missingElements, ...comparisonResult.categorized_violations.must_violations];
          console.log("Must violations:", comparisonResult.categorized_violations.must_violations);
        }
        
        if (comparisonResult.categorized_violations.must_not_violations) {
          extraElements = [...extraElements, ...comparisonResult.categorized_violations.must_not_violations];
          console.log("Must not violations:", comparisonResult.categorized_violations.must_not_violations);
        }
      }
      
      // Collect key components
      const keyComponents = [
        'motor', 'engine', 'dieselovymotor', 'dieselengine', 'automatickaprevodovka', 
        'manualtransmission', 'automatictransmission', 'pohon', 'wheels', 'kolesá',
        'xdrive', 'awd', 'rwd'
      ];
      
      // Flag to ensure we mark at least one component as invalid if validation fails
      let hasMarkedInvalidComponent = false;
      
      // Key components that are mentioned in violations
      const componentMatches: { [key: string]: boolean } = {};
      
      // Pre-process violations to identify mentioned components
      if (comparisonResult.violations) {
        comparisonResult.violations.forEach(violation => {
          const lowerViolation = violation.toLowerCase();
          keyComponents.forEach(comp => {
            if (lowerViolation.includes(comp)) {
              componentMatches[comp] = true;
            }
          });
        });
      }
      
      console.log("Component matches in violations:", componentMatches);
      
      // Update node statuses based on violations
      processedNodes = processedNodes.map((node: NetworkNode) => {
        const nodeNameLC = node.name.toLowerCase();
        const nodeClassLC = (node.class_name || '').toLowerCase();
        
        // First check - Direct check for specific violations
        const isNodeMentionedInViolation = (comparisonResult.violations || []).some(violation => {
          const lowerViolation = violation.toLowerCase();
          // Check for direct mentions of this node
          return lowerViolation.includes(nodeNameLC) || 
                (node.class_name && lowerViolation.includes(nodeClassLC));
        });
        
        // Second check - Check if this is a key component that's missing
        const keyComponents = ['motor', 'engine', 'prevodovka', 'transmission', 'pohon', 'xdrive'];
        const isKeyComponent = keyComponents.some(comp => 
          nodeNameLC.includes(comp.toLowerCase()) || nodeClassLC.includes(comp.toLowerCase())
        );
        
        // Check specifically for attribute violations which often include "A(v, attribute, value)" format
        // This is for matching specific attribute violations like sedadla, velkost, navigacia
        if (comparisonResult.violations?.length > 0) {
          // Pattern to match A(variable, attribute_name, value)
          const attrPattern = /A\s*\(\s*([^,]+),\s*([^,]+),\s*([^)]+)\s*\)/i;
          
          for (const violation of comparisonResult.violations) {
            // Special handling for attribute violations in format "Chýbajúci predikát...A(v, sedadla, kozene)"
            if (violation.includes('A(')) {
              
              // Extract the attribute name from the violation
              const match = violation.match(attrPattern);
              if (match) {
                const varName = match[1].trim();
                const attrName = match[2].trim();
                const attrValue = match[3].trim();
                
                // Map variable names to component names
                const componentMap: {[key: string]: string} = {
                  'p': 'AutomatickaPrevodovka',
                  'v': 'Vybava',
                  'k': 'Kolesa',
                  'e': 'Motor',
                  'd': 'Pohon',
                  'r': 'ModelovaRada'
                };
                
                // If this node represents the component related to the missing attribute
                if ((varName in componentMap && node.name === componentMap[varName]) || 
                    (node.name.toLowerCase() === attrName.toLowerCase()) ||
                    (node.id.toLowerCase().includes(attrName.toLowerCase()))) {
                  
                  console.log(`Marking node ${node.name} as missing due to attribute violation: ${violation}`);
                  return { ...node, status: 'missing', size: 40, color: '#F44336', shape: 'diamond' };
                }
                
                // Specific check for current violation: A(p, rychlosti, 8)
                if (varName === 'p' && attrName === 'rychlosti' && 
                    (node.name === 'AutomatickaPrevodovka' || node.id.includes('Prevodovka'))) {
                  console.log(`Marking AutomatickaPrevodovka node as missing due to rychlosti attribute violation`);
                  return { ...node, status: 'missing', size: 40, color: '#F44336', shape: 'diamond' };
                }
              }
            }
          }
        }
        
        // Special check for component violations
        if (comparisonResult.categorized_violations?.component_violations) {
          for (const violation of comparisonResult.categorized_violations.component_violations) {
            // For component violations, be very specific
            if ((isKeyComponent && violation.toLowerCase().includes(nodeNameLC)) ||
                (nodeNameLC === 'pohon' && violation.toLowerCase().includes('pohon')) ||
                (nodeNameLC === 'motor' && violation.toLowerCase().includes('motor')) ||
                (nodeNameLC === 'prevodovka' && violation.toLowerCase().includes('prevodovk'))) {
              
              console.log(`Marking node ${node.name} as missing due to component violation: ${violation}`);
              return { ...node, status: 'missing', size: 40, color: '#F44336', shape: 'diamond' };
            }
          }
        }
        
        // For attribute violations, only mark the specific attribute nodes
        if (node.category === 'Value' || node.category === 'Attribute') {
          const attrViolations = comparisonResult.categorized_violations?.attribute_violations || [];
          
          // For values, extract attribute name and value
          const parts = node.id.split('_');
          if (parts.length > 1) {
            const value = parts[parts.length - 1];
            const attributeName = parts.length > 2 ? parts[parts.length - 2] : '';
            
            // Check for violations mentioning this value or attribute
            const isInAttributeViolations = attrViolations.some(violation => {
              const lowerViolation = violation.toLowerCase();
              return (attributeName && lowerViolation.includes(attributeName.toLowerCase())) ||
                     (value && lowerViolation.includes(value));
            });
            
            if (isInAttributeViolations) {
              console.log(`Found attribute violation for ${node.id} (${attributeName}=${value})`);
              return {
                ...node,
                status: 'invalid',
                size: 38,
                color: '#FF9800',
                shape: node.category === 'Value' ? 'hexagon' : 'diamond',
                group: node.category === 'Value' ? 'InvalidValue' : 'invalid'
              };
            }
          }
        }
        
        // Only mark nodes as missing if they're directly mentioned in violations
        if (isNodeMentionedInViolation && isKeyComponent) {
          console.log(`Node ${node.name} is mentioned in a violation and is a key component`);
          return { ...node, status: 'missing', size: 40, color: '#F44336', shape: 'diamond' };
        }
        
        // If the example is invalid but we haven't found specific violations, 
        // mark a single key component as invalid
        if (!isExampleValid && !hasMarkedInvalidComponent && isKeyComponent) {
          // Only do this for one specific type of component per category to avoid marking too many
          if ((nodeNameLC === 'motor' || nodeNameLC === 'pohon' || nodeNameLC === 'prevodovka') &&
              (comparisonResult.categorized_violations?.component_violations?.length ||
               comparisonResult.categorized_violations?.must_violations?.length)) {
            console.log(`Marking ${node.name} as invalid - validation failed and no specific component identified`);
            hasMarkedInvalidComponent = true;
            return {
              ...node,
              status: 'missing',
              size: 40,
              color: '#F44336',
              shape: 'diamond'
            };
          }
        }
        
        // Default - mark as valid
        return { ...node, status: 'valid', size: 30 };
      });
      
      // Update link statuses based on viewType
      processedLinks = processedLinks.map((link: NetworkLink) => {
        // Check if link connects nodes involved in violations
        const sourceNode = processedNodes.find((n: NetworkNode) => n.id === link.source);
        const targetNode = processedNodes.find((n: NetworkNode) => n.id === link.target);
        
        // If one of the nodes is marked as missing/invalid, mark the link accordingly
        if (sourceNode?.status === 'missing' || targetNode?.status === 'missing') {
          return { ...link, status: 'missing', width: 4 };
        }
        
        if (sourceNode?.status === 'invalid' || targetNode?.status === 'invalid') {
          return { ...link, status: 'invalid', width: 3 };
        }
        
        if (sourceNode?.status === 'extra' || targetNode?.status === 'extra') {
          return { ...link, status: 'extra', width: 3 };
        }
        
        return { ...link, status: 'valid', width: 2 };
      });
      
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
          
          // Collect all attribute violations in a structured way for easier checking
          const attributeViolations: Array<{varName: string, attrName: string, attrValue: string}> = [];
          for (const violation of comparisonResult.violations || []) {
            const attrMatch = violation.match(/A\s*\(\s*([^,]+),\s*([^,]+),\s*([^)]+)\s*\)/i);
            if (attrMatch) {
              const varName = attrMatch[1].trim();
              const attrName = attrMatch[2].trim();
              const attrValue = attrMatch[3].trim();
              attributeViolations.push({ varName, attrName, attrValue });
            }
          }
          
          console.log("All extracted attribute violations:", attributeViolations);
          
          // If this is a Value related to a missing/violated attribute, mark it
          const isMissingAttribute = attributeViolations.some(v => 
            (attributeName === v.attrName) || 
            (value === v.attrValue) ||
            (node.id.includes(v.attrName)) ||
            (node.id.includes(v.attrValue.replace(/[\[\]{}]/g, ''))) // Handle special chars in values
          );
          
          if (isMissingAttribute) {
            console.log(`Found value node related to missing attribute: ${node.id}`);
            return {
              ...node,
              status: 'missing', 
              size: 40,
              shape: 'diamond',
              color: '#F44336',
              group: 'MissingInExample' 
            };
          }
          
          // Check for specific known invalid values (original logic kept for compatibility)
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
      
      // Create the data model - always use the combined view
      const allNodes = [...processedNodes];  // Create a copy to add missing components
      
      // If the example is invalid, find at least one component to mark as invalid
      if (!isExampleValid && missingElements.length === 0) {
        // Check if we have attribute violations - if so, don't mark key components as invalid
        const hasAttributeViolations = 
          (comparisonResult.categorized_violations?.attribute_violations?.length || 0) > 0 ||
          comparisonResult.violations?.some(v => v.includes('A('));
        
        // Only mark a component if we have no attribute violations and no other specific violations
        if (!hasAttributeViolations) {
          // If there are no specific violations but the example is invalid,
          // mark a key component as invalid to show there's a problem
          console.log("Example is invalid but no specific violations found. Marking a key component.");
          
          // Common key components to look for
          const keyComponents = ['Motor', 'Engine', 'Prevodovka', 'Transmission', 'Pohon', 'Drive', 'Kolesá', 'Wheels'];
          
          // Find a node matching a key component to mark as invalid
          const componentNode = allNodes.find(node => {
            const nodeName = node.name.toLowerCase();
            const nodeClass = (node.class || '').toLowerCase();
            return keyComponents.some(comp => 
              nodeName.includes(comp.toLowerCase()) || nodeClass.includes(comp.toLowerCase())
            );
          });
          
          // Mark the component as invalid if found
          if (componentNode) {
            console.log(`Marking component ${componentNode.name} as invalid due to validation failure`);
            componentNode.status = 'missing';
            componentNode.color = '#F44336';
            componentNode.size = 40;
          }
        } else {
          console.log("Not marking key components as invalid because attribute violations were found");
        }
      }
      
      // For the combined view, add missing components
      console.log("Adding missing components to view");
      
      // Get all missing components
      const missingComponents = comparisonResult.categorized_violations?.component_violations 
        ? extractComponentsFromViolations(comparisonResult.categorized_violations.component_violations)
        : [];
      
      console.log("Missing components from violations:", missingComponents);
      
      // Check for missing attributes and add them as missing nodes
      const missingAttributes: Array<{name: string, value: string, parent: string}> = [];
      
      // Check for the specific missing attribute violations
      const specificViolations = comparisonResult.violations || [];
      // Match any A(x, attr, value) pattern in violations
      for (const violation of specificViolations) {
        const attrMatch = violation.match(/A\s*\(\s*([^,]+),\s*([^,]+),\s*([^)]+)\s*\)/i);
        if (attrMatch) {
          const varName = attrMatch[1].trim();
          const attrName = attrMatch[2].trim();
          const attrValue = attrMatch[3].trim();
          console.log(`Found attribute violation: A(${varName}, ${attrName}, ${attrValue})`);
          
          // Map the variable to its component type
          let parentComponent = '';
          if (varName === 'p') parentComponent = 'AutomatickaPrevodovka';
          else if (varName === 'v') parentComponent = 'Vybava';
          else if (varName === 'k') parentComponent = 'Kolesa';
          else if (varName === 'e') parentComponent = 'Motor';
          else if (varName === 'd') parentComponent = 'Pohon';
          else if (varName === 'r') parentComponent = 'ModelovaRada';
          else parentComponent = varName; // Default to variable name if mapping not found
          
          missingAttributes.push({ name: attrName, value: attrValue, parent: parentComponent });
        }
      }
      
      console.log("Missing attributes from violations:", missingAttributes);
      
      // Create visual nodes for the missing attributes if we have any
      if (missingAttributes.length > 0) {
        // Find or create parent nodes for the attributes
        for (const attr of missingAttributes) {
          // Find parent component, or add it if it doesn't exist
          let parentNode = allNodes.find(n => n.name.toLowerCase() === attr.parent.toLowerCase());
          if (!parentNode) {
            console.log(`Adding missing parent node for attribute: ${attr.parent}`);
            parentNode = {
              id: attr.parent,
              name: attr.parent,
              class: attr.parent,
              category: 'Component',
              status: 'missing' as any,
              size: 40
            };
            allNodes.push(parentNode);
          }
          
          // Create attribute node
          const attrNodeId = `${attr.parent}_${attr.name}`;
          console.log(`Adding missing attribute node: ${attrNodeId}`);
          
          // Add the attribute node
          allNodes.push({
            id: attrNodeId,
            name: attr.name,
            class: 'Attribute',
            category: 'MissingInExample',
            status: 'missingInExample' as any,
            size: 40
          });
          
          // Add connection from parent to attribute
          processedLinks.push({
            source: attr.parent,
            target: attrNodeId,
            type: 'HAS_ATTRIBUTE',
            status: 'missingInExample' as any,
            width: 4
          });
          
          // Add value node
          const valueNodeId = `${attrNodeId}_${attr.value}`;
          console.log(`Adding missing value node: ${valueNodeId}`);
          
          // Add the value node
          allNodes.push({
            id: valueNodeId,
            name: attr.value,
            class: 'Value',
            category: 'MissingInExample',
            status: 'missingInExample' as any,
            size: 40
          });
          
          // Add connection from attribute to value
          processedLinks.push({
            source: attrNodeId,
            target: valueNodeId,
            type: 'VALUE',
            status: 'missingInExample' as any,
            width: 4
          });
        }
      }
      
      // Add regular missing components
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
        const opacity = (node.status === 'missing' || node.category === 'MissingComponent' || 
                          node.status === 'invalid' || node.status === 'extra') 
          ? 1.0  // Full opacity for special nodes
          : 1.0;  // Full opacity for all nodes now
        
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
      const visEdges = processedLinks.map((link: NetworkLink) => {
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
        
        // Define network options
        const options = {
          nodes: {
            shape: 'dot',
            size: 35,
            font: {
              size: 14,
              color: '#FFFFFF',
              face: 'arial',
              strokeWidth: 3,
              strokeColor: '#000000',
              bold: {
                color: '#FFFFFF',
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
              gravitationalConstant: -15000,
              centralGravity: 0.3,
              springLength: 250,
              springConstant: 0.05,
              damping: 0.09,
              avoidOverlap: 1.0
            },
            stabilization: {
              enabled: true,
              iterations: 1000,
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
        networkInstance = new Network(container, data, options as any);
        
        // Add basic event handlers
        networkInstance.once('stabilizationIterationsDone', function() {
          console.log('Network stabilized');
          networkInstance?.fit();
        });
        
        // Save reference to network
        setNetwork(networkInstance);
        setError(null);
      }
    } catch (e) {
      console.error('Error creating network visualization:', e);
      setError(`Error creating network visualization: ${(e as Error).message}`);
    }
    
    // Cleanup function for useEffect
    return () => {
      console.log("Cleaning up network instance");
      if (networkInstance) {
        try {
          networkInstance.destroy();
        } catch (e) {
          console.error("Error destroying network:", e);
        }
      }
    };
  }, [comparisonResult, formula, isReady, viewType]);
  
  // Pridáme legendu s vysvetlením farieb
  const renderLegend = () => {
    return (
      <div className="network-legend" style={{
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        padding: '12px 16px',
        borderRadius: '8px',
        boxShadow: '0 4px 15px rgba(0, 0, 0, 0.3)',
        border: '1px solid rgba(255, 255, 255, 0.15)',
        position: 'absolute',
        top: '10px',
        right: '10px',
        zIndex: 1000
      }}>
        <div className="legend-title" style={{ fontSize: '15px', marginBottom: '10px', color: '#90caf9' }}>Legenda:</div>
        <div className="legend-item" style={{ marginBottom: '8px' }}>
          <span className="legend-color" style={{ display: 'inline-block', backgroundColor: getStatusColor('valid'), width: '18px', height: '18px', marginRight: '10px', borderRadius: '3px' }}></span>
          <span style={{ fontSize: '14px' }}>Splnená požiadavka</span>
        </div>
        <div className="legend-item" style={{ marginBottom: '8px' }}>
          <span className="legend-color" style={{ display: 'inline-block', backgroundColor: getStatusColor('invalid'), width: '18px', height: '18px', marginRight: '10px', borderRadius: '3px' }}></span>
          <span style={{ fontSize: '14px' }}>Nesprávna hodnota</span>
        </div>
        <div className="legend-item" style={{ marginBottom: '8px' }}>
          <span className="legend-color" style={{ display: 'inline-block', backgroundColor: getStatusColor('missing'), width: '18px', height: '18px', marginRight: '10px', borderRadius: '3px' }}></span>
          <span style={{ fontSize: '14px' }}>Porušená požiadavka</span>
        </div>
        <div className="legend-item" style={{ marginBottom: '8px' }}>
          <span className="legend-color" style={{ display: 'inline-block', backgroundColor: getStatusColor('extra'), width: '18px', height: '18px', marginRight: '10px', borderRadius: '3px' }}></span>
          <span style={{ fontSize: '14px' }}>Nadbytočný prvok</span>
        </div>
        <div className="legend-item" style={{ marginBottom: '8px' }}>
          <span className="legend-color" style={{ display: 'inline-block', backgroundColor: '#000000', width: '18px', height: '18px', marginRight: '10px', borderRadius: '3px' }}></span>
          <span style={{ fontSize: '14px' }}>Chýbajúci v príklade</span>
        </div>
      </div>
    );
  };
  
  // Add this to the render function, just before the closing return statement
  const networkStyle: React.CSSProperties = {
    height: '100%',
    minHeight: '700px',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '8px',
    background: 'rgba(17, 24, 39, 0.7)',
    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)',
    position: 'relative' // Add relative positioning for legend
  };
  
  // Render network graph with legend and loading state
  return (
    <div className="network-container" style={{ height: '100%' }}>
      {error && (
        <div className="network-error" style={{ 
          color: '#f44336', 
          padding: '10px', 
          backgroundColor: 'rgba(244, 67, 54, 0.1)', 
          borderRadius: '4px', 
          marginBottom: '10px' 
        }}>
          Error: {error}
        </div>
      )}
      
      <div 
        ref={containerRef} 
        className="network-vis-container"
        style={networkStyle}
      >
        {!error && !isReady && (
          <div className="network-loading" style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            padding: '20px',
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            borderRadius: '8px',
            color: 'white'
          }}>
            Načítavam vizualizáciu...
          </div>
        )}
        
        {!error && isReady && renderLegend()}
      </div>
    </div>
  );
};

export default ExampleNetworkGraph;