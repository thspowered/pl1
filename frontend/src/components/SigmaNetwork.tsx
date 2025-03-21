import { useRef, useState, useCallback, useEffect } from 'react';
import { Box, Typography, Paper } from '@mui/material';
import Graph from 'graphology';
import Sigma from 'sigma';
import { circular } from 'graphology-layout';
import { SigmaNetworkProps, NetworkNode } from '../types';

// SigmaNetwork component that displays the semantic network visualization
const SigmaNetwork = ({ nodes, links }: SigmaNetworkProps) => {
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
  const getColorForType = useCallback((type: string, category: string) => {
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
  }, []);
  
  // Samostatná funkcia pre inicializáciu grafu
  const initGraph = useCallback(() => {
    try {
      // Vytvoríme nový graf
      const graph = new Graph();
      
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
        const radius = 3 + categoryIndex * 2;
        
        nodesInCategory.forEach((node, index) => {
          if (!node.id) return;
          
          // Vypočítame pozíciu na kruhu
          const angle = (index / nodeCount) * 2 * Math.PI;
          const x = radius * Math.cos(angle);
          const y = radius * Math.sin(angle);
          
          const nodeSize = node.category === 'attribute' ? 6 : 
                          node.category === 'component' ? 10 : 12;
          
          try {
            graph.addNode(node.id, {
              x: x,
              y: y,
              size: nodeSize,
              label: node.name || node.id,
              color: getColorForType(node.class, node.category),
              nodeType: "circle", // Vždy použijeme "circle" ako typ uzla
              category: node.category,
              class: node.class,
              // Pre lepší hover efekt
              highlightColor: '#FFFFFF',
              borderColor: '#333333',
              borderWidth: 1.5
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
            x: Math.random() * 5,
            y: Math.random() * 5,
            size: 8,
            label: node.name || node.id,
            color: getColorForType(node.class, 'default'),
            nodeType: "circle",
            category: 'unknown',
            class: node.class,
            highlightColor: '#FFFFFF',
            borderColor: '#333333',
            borderWidth: 1.5
          });
        } catch (e) {
          console.error(`Failed to add uncategorized node ${node.id}:`, e);
        }
      });
      
      // Pridáme hrany s lepším štýlovaním podľa typu spojenia
      for (const link of links) {
        if (!link.source || !link.target) continue;
        if (!graph.hasNode(link.source) || !graph.hasNode(link.target)) continue;
        
        // Vytvoríme unikátne ID pre hranu
        const edgeId = `${link.source}-${link.target}`;
        
        try {
          // Nastavíme rôzne farby a štýly pre rôzne typy hrán
          // Tu môžeme pridať vizuálne rozlíšenie pre must, must_not, atď.
          const sourceNode = nodes.find(n => n.id === link.source);
          const targetNode = nodes.find(n => n.id === link.target);
          const isAttributeEdge = targetNode?.category === 'attribute';
          
          let edgeColor = '#888888';
          let edgeSize = 1;
          let edgeType = 'arrow';
          
          if (link.type === 'must') {
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
          
          graph.addEdge(link.source, link.target, {
            id: edgeId,
            size: edgeSize,
            color: edgeColor,
            type: edgeType,
            linkType: link.type // Uložíme aj originálny typ pre hover info
          });
        } catch (e) {
          console.error(`Failed to add edge ${link.source} -> ${link.target}:`, e);
        }
      }
      
      return graph;
    } catch (e) {
      console.error('Error initializing graph:', e);
      setError('Chyba pri inicializácii grafu: ' + e);
      return null;
    }
  }, [nodes, links, getColorForType]);
  
  useEffect(() => {
    // Kontrola, či máme kontajner
    if (!containerRef.current) return;
    
    // Kontrola, či máme uzly a hrany
    if (!nodes.length) {
      setError('Žiadne uzly na zobrazenie');
      return;
    }
    
    // Cleanup predchádzajúcej inštancie
    cleanupSigma();
    
    // Inicializácia grafu so všetkými uzlami a spojeniami
    try {
      const timer = setTimeout(() => {
        try {
          if (!containerRef.current) return;
          
          // Inicializácia grafu
          const graph = initGraph();
          if (!graph) return;
          
          graphRef.current = graph;
          
          // Aplikovanie layoutu
          circular.assign(graph);
          
          // Vytvorenie Sigma inštancie
          sigmaRef.current = new Sigma(graph, containerRef.current, {
            renderEdgeLabels: false,
            labelSize: 12,
            labelColor: {
              color: '#FFFFFF',
            },
            nodeReducer: (node, data) => {
              const res = { ...data };
              
              // Vysoká kvalita renderovania pre lepší vzhľad
              res.forceLabel = true;
              
              // Highlight node on hover
              if (hoveredNode === node) {
                res.highlighted = true;
                res.color = '#FFFFFF';
                res.size = data.size * 1.5;
              }
              
              return res;
            },
            edgeReducer: (edge, data) => {
              const res = { ...data };
              
              // Highlight connected edges when node is hovered
              if (hoveredNode && (graph.source(edge) === hoveredNode || graph.target(edge) === hoveredNode)) {
                res.size = data.size * 2;
                res.color = '#FFFFFF';
              }
              
              return res;
            }
          });
          
          // Priblížime kameru, aby bol graf viditeľný
          const camera = sigmaRef.current.getCamera();
          camera.animatedReset();
          
          // Pridáme hover event pre zobrazenie detailných informácií
          sigmaRef.current.on('enterNode', ({ node }) => {
            setHoveredNode(node);
          });
          
          sigmaRef.current.on('leaveNode', () => {
            setHoveredNode(null);
          });
          
          // Refresh the visualization
          sigmaRef.current.refresh();
          
        } catch (e) {
          console.error('Error setting up Sigma visualization:', e);
          setError('Chyba pri nastavení vizualizácie: ' + e);
        }
      }, 100);
      
      return () => {
        clearTimeout(timer);
        cleanupSigma();
      };
    } catch (e) {
      console.error('Error in useEffect:', e);
      setError('Chyba pri inicializácii: ' + e);
    }
  }, [nodes, links, hoveredNode, cleanupSigma, initGraph]);
  
  // Infopanel pre zobrazenie detailov o uzle pri najazdení myšou
  const InfoPanel = () => {
    if (!hoveredNode) return null;
    
    const nodeData = nodes.find(n => n.id === hoveredNode);
    if (!nodeData) return null;
    
    // Získaj spojenia pre tento uzol
    const incomingLinks = links.filter(l => l.target === hoveredNode);
    const outgoingLinks = links.filter(l => l.source === hoveredNode);
    
    return (
      <Paper 
        elevation={3} 
        sx={{ 
          position: 'absolute', 
          bottom: 10, 
          left: 10, 
          padding: 2, 
          maxWidth: 350,
          backgroundColor: 'rgba(30, 30, 30, 0.9)',
          color: 'white',
          zIndex: 1000
        }}
      >
        <Typography variant="h6" gutterBottom>{nodeData.name}</Typography>
        <Typography variant="body2">Trieda: {nodeData.class}</Typography>
        <Typography variant="body2">Kategória: {nodeData.category}</Typography>
        
        {nodeData.attributes && Object.keys(nodeData.attributes).length > 0 && (
          <Box mt={1}>
            <Typography variant="subtitle2">Atribúty:</Typography>
            {Object.entries(nodeData.attributes).map(([key, value]) => (
              <Typography key={key} variant="body2">
                {key}: {typeof value === 'object' ? JSON.stringify(value) : value.toString()}
              </Typography>
            ))}
          </Box>
        )}
        
        {incomingLinks.length > 0 && (
          <Box mt={1}>
            <Typography variant="subtitle2">Prichádzajúce spojenia:</Typography>
            {incomingLinks.map((link, index) => {
              const sourceNode = nodes.find(n => n.id === link.source);
              return (
                <Typography key={index} variant="body2">
                  {sourceNode?.name || link.source} ({link.type})
                </Typography>
              );
            })}
          </Box>
        )}
        
        {outgoingLinks.length > 0 && (
          <Box mt={1}>
            <Typography variant="subtitle2">Odchádzajúce spojenia:</Typography>
            {outgoingLinks.map((link, index) => {
              const targetNode = nodes.find(n => n.id === link.target);
              return (
                <Typography key={index} variant="body2">
                  {targetNode?.name || link.target} ({link.type})
                </Typography>
              );
            })}
          </Box>
        )}
      </Paper>
    );
  };
  
  return (
    <Box sx={{ position: 'relative', width: '100%', height: '500px', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: 1 }}>
      {error && (
        <Box sx={{ 
          position: 'absolute', 
          top: '50%', 
          left: '50%', 
          transform: 'translate(-50%, -50%)',
          color: 'error.main',
          backgroundColor: 'rgba(0, 0, 0, 0.7)',
          padding: 2,
          borderRadius: 1
        }}>
          <Typography variant="body1">{error}</Typography>
        </Box>
      )}
      
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
      <InfoPanel />
    </Box>
  );
};

export default SigmaNetwork; 