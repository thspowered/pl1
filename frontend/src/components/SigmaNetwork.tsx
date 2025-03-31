import React, { useRef, useState, useCallback, useEffect } from 'react';
import { Box, Typography, Paper } from '@mui/material';
import Graph from 'graphology';
import Sigma from 'sigma';
import { circular } from 'graphology-layout';
import { SigmaNetworkProps, NetworkNode, NetworkLink } from '../types';
import './SigmaNetwork.css';

// Interface for the InfoPanel component props
interface InfoPanelProps {
  hoveredNode: string | null;
  nodes: NetworkNode[];
  links: NetworkLink[];
}

// SigmaNetwork component that displays the semantic network visualization
const SigmaNetwork = ({ nodes, links, showDifferences, modelA, modelB }: SigmaNetworkProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const graphRef = useRef<Graph | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  
  // Pomocná funkcia pre čistenie Sigma inštancie
  const cleanupSigma = useCallback(() => {
    try {
      if (sigmaRef.current) {
        sigmaRef.current.kill();
        sigmaRef.current = null;
      }
    } catch (e) {
      console.error('Error cleaning up Sigma instance:', e);
    }
  }, []);
  
  // Funkcia pre generovanie lepších farieb pre rôzne typy uzlov a hrán
  const getColorForType = useCallback((type: string, category: string, status?: string) => {
    // Ak zobrazujeme rozdiely a máme status, použijeme farby pre rozdiely
    if (showDifferences && status) {
      if (status === 'only_in_a') {
        return '#4a90e2'; // Modrá pre model A
      } else if (status === 'only_in_b') {
        return '#9c27b0'; // Fialová pre model B
      }
    }
    
    // Inak použijeme štandardné farby podľa kategórie
    // Použijeme rôzne farby pre rôzne kategórie
    const colors: Record<string, Record<string, string>> = {
      class: {
        BMW: '#5D8AA8',
        Series3: '#4682B4',
        Series5: '#0067A5',
        Series7: '#0047AB',
        X5: '#00008B',
        X7: '#191970',
        default: '#6495ED'
      },
      component: {
        DieselEngine: '#CD5C5C',
        PetrolEngine: '#DC143C',
        AutomaticTransmission: '#B22222',
        ManualTransmission: '#8B0000',
        RWD: '#E9967A',
        XDrive: '#FF6347',
        AWD: '#FF4500',
        default: '#FA8072'
      },
      attribute: {
        default: '#DDA0DD'
      },
      default: {
        default: '#90CAF9'
      }
    };
    
    // Najprv skúsime kategóriu, potom typ
    if (category && colors[category]) {
      return colors[category][type] || colors[category].default;
    }
    
    // Ak nenájdeme farbu pre kategóriu, vrátime predvolenú farbu
    return colors.default.default;
  }, [showDifferences]);
  
  // Samostatná funkcia pre inicializáciu grafu
  const initGraph = useCallback(() => {
    try {
      // Vytvoríme nový graf
      const graph = new Graph();
      
      console.log("Nodes to render:", nodes.length);
      console.log("Links to render:", links.length);
      
      // Prvotné kategorizovanie uzlov pre lepšie rozloženie
      const categorizedNodes: Record<string, NetworkNode[]> = {};
      
      // Roztriedime uzly podľa kategórií
      for (const node of nodes) {
        if (!node.category) continue;
        if (!categorizedNodes[node.category]) {
          categorizedNodes[node.category] = [];
        }
        categorizedNodes[node.category].push(node);
      }
      
      // Najprv pridáme uzly - usporiadame ich do kruhov podľa kategórie
      const categories = Object.keys(categorizedNodes);
      
      for (const category of categories) {
        const nodesInCategory = categorizedNodes[category];
        const nodeCount = nodesInCategory.length;
        
        // Rozmiestňujeme uzly do kruhu s ohľadom na kategóriu
        // Každá kategória má vlastný kruh s iným polomerom
        const categoryIndex = categories.indexOf(category);
        const radius = Math.max(4 + categoryIndex * 3, nodeCount / 2); // Větší poloměr pro více uzlů
        
        nodesInCategory.forEach((node, index) => {
          if (!node.id) return;
          
          // Vypočítame pozíciu na kruhu
          const angle = (index / nodeCount) * 2 * Math.PI;
          const x = radius * Math.cos(angle);
          const y = radius * Math.sin(angle);
          
          // Determine node size based on category
          let nodeSize = 14; // Default size
          let nodeShape = "circle"; // Default shape
          let displayLabel = true; // Whether to display the label
          
          if (node.category === 'Attribute') {
            nodeSize = 8;
            nodeShape = "diamond";
          } else if (node.category === 'Value') {
            nodeSize = 6;
            nodeShape = "square";
            displayLabel = node.name.length < 15; // Only display label if it's not too long
          } else if (node.category === 'BMW') {
            nodeSize = 16;
          } else if (node.category === 'Engine' || node.category === 'Transmission' || node.category === 'Drive') {
            nodeSize = 14;
          } else if (node.category === 'component') {
            nodeSize = 12;
          } else if (node.category === 'Other') {
            nodeSize = 10;
          }
          
          try {
            // Zväčšime uzly, ktoré sú len v jednom z modelov
            const adjustedSize = showDifferences && node.status && node.status !== 'common' 
              ? nodeSize * 1.3 
              : nodeSize;
              
            graph.addNode(node.id, {
              x: x,
              y: y,
              size: adjustedSize,
              label: displayLabel ? (node.name || node.id) : "",
              color: getColorForType(node.class, node.category, node.status),
              type: nodeShape,
              category: node.category,
              class: node.class,
              // Pre lepší hover efekt
              highlightColor: '#FFFFFF',
              borderColor: '#333333',
              borderWidth: 1.5,
              // Dodatočné informácie pre vizualizáciu rozdielov
              status: node.status,
              // Include value display for attributes
              value_display: node.value_display || ""
            });
          } catch (e) {
            console.error(`Failed to add node ${node.id}:`, e);
          }
        });
      }
      
      // Pridáme uzly bez kategórie (ak existujú)
      const nodesWithoutCategory = nodes.filter(n => !n.category);
      nodesWithoutCategory.forEach((node, index) => {
        if (!node.id) return;
        
        try {
          graph.addNode(node.id, {
            x: Math.random() * 6 - 3,
            y: Math.random() * 6 - 3,
            size: 10,
            label: node.name || node.id,
            color: getColorForType(node.class, 'default', node.status),
            type: "circle",
            category: 'unknown',
            class: node.class,
            highlightColor: '#FFFFFF',
            borderColor: '#333333',
            borderWidth: 1.5,
            status: node.status
          });
        } catch (e) {
          console.error(`Failed to add uncategorized node ${node.id}:`, e);
        }
      });
      
      // Pridáme hrany s lepším štýlovaním podľa typu spojenia
      for (const link of links) {
        if (!link.source || !link.target) {
          console.warn("Invalid link: missing source or target", link);
          continue;
        }
        if (!graph.hasNode(link.source) || !graph.hasNode(link.target)) {
          console.warn(`Missing node for link ${link.source} -> ${link.target}`);
          continue;
        }
        
        // Vytvoríme unikátne ID pre hranu
        const edgeId = `${link.source}-${link.target}`;
        
        try {
          // Nastavíme rôzne farby a štýly pre rôzne typy hrán
          // Tu môžeme pridať vizuálne rozlíšenie pre must, must_not, atď.
          const sourceNode = nodes.find(n => n.id === link.source);
          const targetNode = nodes.find(n => n.id === link.target);
          
          const isAttributeEdge = targetNode?.category === 'Attribute';
          const isValueEdge = targetNode?.category === 'Value';
          
          let edgeColor = '#888888';
          let edgeSize = 1.5;
          let edgeType = 'arrow';
          
          // Ak zobrazujeme rozdiely, použijeme farby podľa statusu
          if (showDifferences && link.status) {
            if (link.status === 'only_in_a') {
              edgeColor = '#4a90e2'; // Modrá pre model A
              edgeSize = 2;
            } else if (link.status === 'only_in_b') {
              edgeColor = '#9c27b0'; // Fialová pre model B
              edgeSize = 2;
            }
          } else {
            // Inak použijeme štandardné farby podľa typu spojenia
            if (link.type === 'HAS_ATTRIBUTE') {
              edgeColor = '#9370DB'; // Světle fialová pro atributy
              edgeSize = 1;
              edgeType = 'arrow';
            } else if (link.type === 'VALUE') {
              edgeColor = '#FFD700'; // Zlatá pro hodnoty
              edgeSize = 0.8;
              edgeType = 'line';
            } else if (link.type === 'must') {
              edgeColor = '#00FF00'; // Zelená pre MUST spojenia
              edgeSize = 2;
            } else if (link.type === 'must_not') {
              edgeColor = '#FF0000'; // Červená pre MUST_NOT spojenia
              edgeSize = 2;
              edgeType = 'dashed';
            } else if (link.type === 'must_be_a') {
              edgeColor = '#0000FF'; // Modrá pre MUST_BE_A spojenia
              edgeSize = 1.5;
            } else if (isAttributeEdge) {
              edgeColor = '#9370DB'; // Svetlo-fialová pre atribúty
              edgeSize = 1;
              edgeType = 'line';
            }
          }
          
          graph.addEdge(link.source, link.target, {
            id: edgeId,
            size: edgeSize,
            color: edgeColor,
            type: edgeType,
            linkType: link.type, // Uložíme aj originálny typ pre hover info
            status: link.status  // Uložíme status pre vizualizáciu rozdielov
          });
        } catch (e) {
          console.error(`Failed to add edge ${edgeId}:`, e);
        }
      }
      
      console.log("Graph initialized with", graph.order, "nodes and", graph.size, "edges");
      return graph;
    } catch (e) {
      console.error('Error initializing graph:', e);
      setError('Error initializing graph');
      return null;
    }
  }, [nodes, links, getColorForType, showDifferences]);
  
  useEffect(() => {
    // Vyčistíme predchádzajúcu inštanciu
    cleanupSigma();
    
    // Kontrola, či máme container
    if (!containerRef.current) {
      return;
    }
    
    // Inicializácia grafu
    const graph = initGraph();
    if (!graph) {
      setError('Failed to initialize graph');
      return;
    }
    graphRef.current = graph;
    
    // Vytvoríme novú Sigma inštanciu s nastaveniami
    try {
      sigmaRef.current = new Sigma(graph, containerRef.current, {
        renderLabels: true,
        labelRenderedSizeThreshold: 0, // Zobrazit všechny popisky
        labelSize: 16,
        labelWeight: "bold",
        labelColor: { color: '#000000' },
        defaultEdgeColor: '#000000',
        defaultNodeColor: '#000000',
        labelDensity: 1.5,
        labelGridCellSize: 100,
        nodeReducer: (node, data) => {
          const res = { ...data };
          
          // Pridáme hover efekt
          if (hoveredNode === node) {
            res.highlighted = true;
            res.color = "#FFD700"; // Zvýraznená farba pri hoveri
            res.size = (res.size as number) * 1.3;
          }
          
          return res;
        },
        edgeReducer: (edge, data) => {
          const res = { ...data };
          
          // Zvýrazníme hrany spojené s aktuálne zvýrazneným uzlom
          const nodeSource = graph.source(edge);
          const nodeTarget = graph.target(edge);
          if (hoveredNode === nodeSource || hoveredNode === nodeTarget) {
            res.color = "#FFD700"; // Zvýrazníme súvisiacu hranu
            res.size = (res.size as number) * 1.5;
          }
          
          return res;
        }
      });
      
      // Pridáme event listener pre hover nad uzlami
      sigmaRef.current.on("enterNode", ({ node }) => {
        setHoveredNode(node);
      });
      
      sigmaRef.current.on("leaveNode", () => {
        setHoveredNode(null);
      });
      
      // Nastavíme kameru, aby zobrazila všechny uzly
      setTimeout(() => {
        if (sigmaRef.current) {
          try {
            const camera = sigmaRef.current.getCamera();
            // Pokus o automatické přizpůsobení pohledu
            const state = camera.getState();
            camera.setState({
              ...state,
              ratio: 1.2,
              x: 0,
              y: 0
            });
          } catch (e) {
            console.error("Error setting camera:", e);
          }
        }
      }, 100);
    } catch (e) {
      console.error('Error creating Sigma instance:', e);
      setError('Error creating Sigma instance');
    }
    
    // Cleanup pri unmount
    return () => {
      cleanupSigma();
    };
  }, [nodes, links, cleanupSigma, initGraph, hoveredNode]);
  
  // InfoPanel component to display node details on hover
  const InfoPanel = ({ hoveredNode, nodes, links }: InfoPanelProps) => {
    if (!hoveredNode) return null;
    
    const nodeData = nodes.find(node => node.id === hoveredNode);
    if (!nodeData) return null;
    
    const connectedLinks = links.filter(
      (link: NetworkLink) => link.source === hoveredNode || link.target === hoveredNode
    );
    
    // Find links where this node is a source
    const outgoingLinks = connectedLinks.filter((link: NetworkLink) => link.source === hoveredNode);
    
    // Find links where this node is a target
    const incomingLinks = connectedLinks.filter((link: NetworkLink) => link.target === hoveredNode);
    
    // Status labels
    const getStatusLabel = (status?: string) => {
      if (!status) return "N/A";
      switch(status) {
        case "only_in_a": return "Pouze v modelu A";
        case "only_in_b": return "Pouze v modelu B";
        case "common": return "V obou modelech";
        default: return status;
      }
    };
    
    return (
      <div className="info-panel">
        <h3 style={{ margin: "0 0 8px 0" }}>{nodeData.name}</h3>
        
        <table>
          <tbody>
            <tr>
              <th>ID:</th>
              <td>{nodeData.id}</td>
            </tr>
            <tr>
              <th>Třída:</th>
              <td>{nodeData.class}</td>
            </tr>
            <tr>
              <th>Kategorie:</th>
              <td>{nodeData.category}</td>
            </tr>
            {showDifferences && (
              <tr>
                <th>Status:</th>
                <td>{getStatusLabel(nodeData.status)}</td>
              </tr>
            )}
            {nodeData.category === 'Attribute' && nodeData.value_display && (
              <tr>
                <th>Hodnota:</th>
                <td>{nodeData.value_display}</td>
              </tr>
            )}
            {nodeData.category === 'Value' && (
              <tr>
                <th>Hodnota:</th>
                <td>{nodeData.name}</td>
              </tr>
            )}
            {nodeData.attributes && Object.keys(nodeData.attributes).length > 0 && (
              <tr>
                <th colSpan={2}>Atributy:</th>
              </tr>
            )}
            {nodeData.attributes && Object.entries(nodeData.attributes).map(([key, value]) => (
              <tr key={key}>
                <td style={{ paddingLeft: "20px" }}>{key}:</td>
                <td>{JSON.stringify(value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        
        {outgoingLinks.length > 0 && (
          <>
            <h4 style={{ margin: "12px 0 4px 0" }}>Výstupní spojení ({outgoingLinks.length}):</h4>
            <ul style={{ margin: 0, paddingLeft: "20px" }}>
              {outgoingLinks.slice(0, 5).map((link: NetworkLink, idx: number) => (
                <li key={`out-${idx}`}>
                  {nodeData.name} ⟶ {link.target} ({link.type})
                  {showDifferences && link.status && ` [${getStatusLabel(link.status)}]`}
                </li>
              ))}
              {outgoingLinks.length > 5 && <li>... a dalších {outgoingLinks.length - 5}</li>}
            </ul>
          </>
        )}
        
        {incomingLinks.length > 0 && (
          <>
            <h4 style={{ margin: "12px 0 4px 0" }}>Vstupní spojení ({incomingLinks.length}):</h4>
            <ul style={{ margin: 0, paddingLeft: "20px" }}>
              {incomingLinks.slice(0, 5).map((link: NetworkLink, idx: number) => (
                <li key={`in-${idx}`}>
                  {link.source} ⟶ {nodeData.name} ({link.type})
                  {showDifferences && link.status && ` [${getStatusLabel(link.status)}]`}
                </li>
              ))}
              {incomingLinks.length > 5 && <li>... a dalších {incomingLinks.length - 5}</li>}
            </ul>
          </>
        )}
      </div>
    );
  };
  
  // Zobrazenie legendy pre rozdíly modelů
  const renderDifferenceLegend = () => {
    if (!showDifferences || !modelA || !modelB) return null;
    
    return (
      <div className="network-legend">
        <div className="legend-title">Legenda rozdílů</div>
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#4a90e2' }}></div>
          <div>Pouze v modelu: {modelA}</div>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#9c27b0' }}></div>
          <div>Pouze v modelu: {modelB}</div>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#888888' }}></div>
          <div>Společné pro oba modely</div>
        </div>
        
        <div className="legend-title" style={{ marginTop: "16px" }}>Typy uzlů</div>
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#5D8AA8' }}></div>
          <div>Modely BMW</div>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#DC143C' }}></div>
          <div>Motory</div>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#B22222' }}></div>
          <div>Převodovky</div>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#FF6347' }}></div>
          <div>Pohony</div>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#9370DB' }}></div>
          <div>Atributy</div>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#FFD700' }}></div>
          <div>Hodnoty</div>
        </div>
      </div>
    );
  };
  
  // Zobrazenie chybovej správy
  if (error) {
    return <div className="sigma-error">Error: {error}</div>;
  }
  
  // Zobrazenie sémantickej siete
  return (
    <div className="semantic-network-container">
      {showDifferences && renderDifferenceLegend()}
      <div ref={containerRef} style={{ width: "100%", height: "800px", background: "#f8f9fa" }} />
      <InfoPanel hoveredNode={hoveredNode} nodes={nodes} links={links} />
    </div>
  );
};

export default SigmaNetwork; 