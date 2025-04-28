import React, { useRef, useState, useEffect } from 'react';
import { Network } from 'vis-network';
import { SigmaNetworkProps, NetworkNode, NetworkLink } from '../types';
import './NetworkGraph.css';

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
      return 'HAS_ATTRIBUTE';
    case 'VALUE': 
      return 'VALUE';
    default: 
      return type;
  }
};

// Funkcia na kontrolu, či id reprezentuje premennú bez sémantického významu
const isVariableNode = (id: string) => {
  // Kontrola či je to jednopísmenový identifikátor (x, e, t, d, w, b, s, c, i, l, su, se)
  return /^[a-zA-Z]$/.test(id);
};

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
  const addNode = (id: string, category: string, displayName?: string) => {
    if (!nodeMap.has(id) && !isVariableNode(id)) {
      nodeMap.set(id, {
        id: id,
        name: displayName || id,  // Ak je zadaný displayName, použijeme ho, inak id
        class: category,
        category: category
      });
    }
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
        
        if (isVariableNode(objectId)) {
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
        
        // Ak jedna z hodnôt je indexovaná premenná, preskočíme
        if (isIndexedVariable(objectId) && isIndexedVariable(typeId)) {
          return;
        }
        
        // Pridáme iba cieľový typ, nie premennú
        addNode(typeId, typeId);
      }
    } else if (part.startsWith('Μ(')) {
      // MUST(X5, Engine) - povinná väzba
      const match = part.match(/Μ\s*\(\s*([^,]+),\s*([^)]+)\s*\)/);
      if (match) {
        const sourceId = match[1].trim();
        const targetId = match[2].trim();
        
        // Ak oba prvky sú indexované premenné alebo jednopísmenové premenné, preskočíme
        if ((isIndexedVariable(sourceId) && isIndexedVariable(targetId)) || 
            (isVariableNode(sourceId) && isVariableNode(targetId))) {
          return;
        }
        
        // Nahradíme premenné ich typmi
        const actualSourceId = isVariableNode(sourceId) ? variableToTypeMap.get(sourceId) || sourceId : sourceId;
        const actualTargetId = isVariableNode(targetId) ? variableToTypeMap.get(targetId) || targetId : targetId;
        
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
        
        // Ak oba prvky sú indexované premenné, preskočíme
        if (isIndexedVariable(sourceId) && isIndexedVariable(targetId)) {
          return;
        }
        
        // Nahradíme premenné ich typmi
        const actualSourceId = isVariableNode(sourceId) ? variableToTypeMap.get(sourceId) || sourceId : sourceId;
        const actualTargetId = isVariableNode(targetId) ? variableToTypeMap.get(targetId) || targetId : targetId;
        
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
        
        // Ak oba prvky sú indexované premenné, preskočíme
        if (isIndexedVariable(wholeId) && isIndexedVariable(partId)) {
          return;
        }
        
        // Nahradíme premenné ich typmi
        const actualWholeId = isVariableNode(wholeId) ? variableToTypeMap.get(wholeId) || wholeId : wholeId;
        const actualPartId = isVariableNode(partId) ? variableToTypeMap.get(partId) || partId : partId;
        
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
        
        // Preskočíme, ak objekt je indexovaná premenná
        if (isIndexedVariable(objectId)) {
          return;
        }
        
        // Nahradíme premenné ich typmi
        const actualObjectId = isVariableNode(objectId) ? variableToTypeMap.get(objectId) || objectId : objectId;
        
        // Ak nemáme informácie o typoch, preskočíme
        if (isVariableNode(actualObjectId)) {
          return;
        }
        
        const attributeName = match[2].trim();
        const attributeId = `${actualObjectId}_${attributeName}`;
        const valueText = match[3].trim();
        
        addNode(actualObjectId, actualObjectId);
        // Zobrazíme názov atribútu
        addNode(attributeId, 'Attribute', attributeName);
        
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
          // Zobrazíme konkrétnu hodnotu
          addNode(valueId, 'Value', value);
          
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

// NetworkGraph component using vis-network for better visualization
const NetworkGraph = ({ nodes: providedNodes, links: providedLinks, showDifferences, modelA, modelB, formula }: SigmaNetworkProps & { formula?: string }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [network, setNetwork] = useState<Network | null>(null);
  
  useEffect(() => {
    // Ensure container exists
    if (!containerRef.current) {
      setError('Container reference is not available');
      return;
    }

    try {
      let nodes = providedNodes;
      let links = providedLinks;
      
      // Priorita: 1. formula parameter, 2. data-formula atribút, 3. pôvodné nodes a links
      if (formula) {
        // Ak je formula parameter, parsujeme ho priamo
        console.log('Using formula from prop:', formula.substring(0, 100) + '...');
        const parsedData = parseFormulaToNodesAndLinks(formula);
        nodes = parsedData.nodes;
        links = parsedData.links;
      } else {
        // Inak skúsime nájsť formulu v DOM
        const formulaElement = document.querySelector('.formula-container') || 
                               document.querySelector('[data-formula]');
        
        if (formulaElement && formulaElement.textContent) {
          const formulaText = formulaElement.textContent.trim();
          console.log('Found formula in DOM:', formulaText.substring(0, 100) + '...');
          const parsedData = parseFormulaToNodesAndLinks(formulaText);
          nodes = parsedData.nodes;
          links = parsedData.links;
        } else if (providedNodes && providedLinks) {
          console.log('Using provided graph data - nodes:', providedNodes.length, 'links:', providedLinks.length);
        } else {
          console.log('No formula or provided data found');
        }
      }
      
      // Vypíšme, či máme nejaké dáta
      if (!nodes || nodes.length === 0) {
        console.warn('No nodes to display');
        setError('Nie sú k dispozícii žiadne dáta na zobrazenie sémantickej siete.');
        return;
      }
      
      // Clean up any existing network
      if (network) {
        network.destroy();
      }
      
      // Prepare nodes for vis.js
      const visNodes = nodes.map(node => {
        // Základné farbenie podľa kategórie
        let color = '#999999';
        let shape = 'dot';
        let size = 15;
        
        if (node.category) {
          switch (node.category) {
            case 'BMW': color = '#5D8AA8'; size = 25; break;
            case 'X5': color = '#4169E1'; size = 25; break;
            case 'Engine': 
            case 'DieselovyMotor': 
            case 'BenzinovyMotor': 
            case 'PetrolEngine': 
              color = '#DC143C'; size = 20; break;
            case 'Transmission': 
            case 'AutomatickaPrevodovka': 
            case 'ManualnaPrevodovka': 
            case 'AutomaticTransmission': 
            case 'ManualTransmission': 
              color = '#CD5C5C'; size = 20; break;
            case 'Drive': 
            case 'DriveSystem': 
            case 'Pohon': 
            case 'XDrive': 
            case 'AWD': 
            case 'RWD': 
              color = '#FF6347'; size = 20; break;
            case 'SUV': 
            case 'CompactSUV': 
            case 'Car': 
            case 'Auto': 
            case 'Vehicle': 
              color = '#4682B4'; size = 20; break;
            case 'ModelovaRada': color = '#5D8AA8'; size = 20; break;
            case 'Farba': color = '#8A2BE2'; size = 20; break;
            case 'Vybava': color = '#2E8B57'; size = 20; break;
            case 'Kolesa': color = '#B8860B'; size = 20; break;
            case 'Component': color = '#A0522D'; size = 18; break;
            case 'Attribute': color = '#9370DB'; shape = 'diamond'; size = 15; break;
            case 'Value': color = '#FFD700'; shape = 'square'; size = 12; break;
            case 'Object': color = '#808080'; size = 18; break;
            default: color = '#999999';
          }
        }
        
        // Extrahujeme názvy atribútov a hodnôt z ID
        let displayLabel = node.category;
        
        // Špeciálne spracovanie pre atribúty
        if (node.category === 'Attribute') {
          // Extrahujeme názov atribútu z ID (format: object_attributeName)
          const parts = node.id.split('_');
          if (parts.length >= 2) {
            // Použijeme druhú časť ako názov atribútu
            displayLabel = parts[1];
          }
        }
        
        // Špeciálne spracovanie pre hodnoty
        if (node.category === 'Value') {
          // Extrahujeme hodnotu z ID (format: attribute_value)
          const parts = node.id.split('_');
          if (parts.length >= 3) {
            // Použijeme poslednú časť ako hodnotu
            displayLabel = parts[parts.length - 1];
          }
        }
        
        // Preferujeme zobrazovať kategóriu (triedu) namiesto názvu objektu (identifikátora)
        // Ak kategória nie je dostupná, použijeme názov
        return {
          id: node.id,
          label: displayLabel,
          color: { 
            background: color,
            border: '#ffffff' 
          },
          shape: shape,
          size: size,
          font: {
            size: 14,
            color: '#ffffff',
            face: 'arial',
            background: 'rgba(0, 0, 0, 0.5)'
          }
        };
      });
      
      // Prepare edges for vis.js
      const visEdges = links.map((link, index) => {
        // Farebné kódovanie podľa typu
        let color = '#999999';
        let width = 1.5;
        let dashes: boolean | number[] = false;
        let label = '';
        
        switch (link.type) {
          case 'must':
          case 'Μ':
            color = '#00BB00';
            width = 2;
            label = 'MUST';
            break;
          case 'must_not':
          case 'Ν':
            color = '#DD0000';
            width = 2;
            dashes = [5, 5] as number[];
            label = 'MUST_NOT';
            break;
          case 'must_be_a':
          case 'Ι':
            color = '#0000DD';
            width = 2;
            label = 'IS_A';
            break;
          case 'Π':
            color = '#8A2BE2';
            width = 2;
            label = 'HAS_PART';
            break;
          case 'HAS_ATTRIBUTE':
          case 'Α':
            color = '#9370DB';
            width = 2;
            label = 'HAS_ATTR';
            break;
          case 'VALUE':
            color = '#FFD700';
            width = 1.5;
            label = 'VALUE';
            break;
          default:
            color = '#777777';
            width = 1.5;
            label = link.type || '';
        }
        
        return {
          id: `e${index}`,
          from: link.source,
          to: link.target,
          color: color,
          width: width,
          dashes: dashes,
          arrows: 'to',
          title: label, // Tooltip
          label: label,
          font: { 
            size: 12, 
            color: color,
            background: 'white'
          },
          smooth: {
            enabled: true,
            type: 'dynamic',
            roundness: 0.5
          }
        };
      });
      
      // Create network data
      const data = {
        nodes: visNodes,
        edges: visEdges
      };
      
      // Network options
      const options = {
        physics: {
          enabled: true,
          stabilization: {
            iterations: 200
          },
          barnesHut: {
            gravitationalConstant: -2000,
            centralGravity: 0.1,
            springLength: 150,
            springConstant: 0.05
          }
        },
        layout: {
          improvedLayout: true
        },
        interaction: {
          navigationButtons: true,
          keyboard: true,
          multiselect: true,
          hover: true
        },
        edges: {
          smooth: {
            enabled: true,
            type: 'dynamic',
            roundness: 0.5
          }
        }
      };
      
      // Create the network
      const networkInstance = new Network(containerRef.current, data, options);
      
      // Add a click event handler
      networkInstance.on('click', function(params) {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0];
          console.log('Clicked node ID:', nodeId);
          
          const clickedNode = nodes.find(n => n.id === nodeId);
          if (clickedNode) {
            console.log('Node details:', clickedNode);
          }
        }
      });
      
      // Fit to view all elements after stabilization
      networkInstance.once('stabilizationIterationsDone', function() {
        console.log('Network stabilized');
        networkInstance.fit();
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
    } catch (e) {
      console.error('Error creating network visualization:', e);
      setError(`Error creating network visualization: ${(e as Error).message}`);
    }
  }, [providedNodes, providedLinks, showDifferences, formula]);
  
  // Display error message
  if (error) {
    return <div className="network-error">Error: {error}</div>;
  }
  
  // Render network graph
  return (
    <div className="network-container">
      <div 
        ref={containerRef} 
        style={{ width: "100%", height: "800px" }} 
      />
    </div>
  );
};

export default NetworkGraph; 