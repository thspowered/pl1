import React, { useRef, useState, useCallback, useEffect } from 'react';
import Graph from 'graphology';
import Sigma from 'sigma';
import { circular } from 'graphology-layout';
import ForceAtlas2 from 'graphology-layout-forceatlas2';
import { SigmaNetworkProps, NetworkNode, NetworkLink } from '../types';
import './SigmaNetwork.css';

// SigmaNetwork component with simplified implementation
const SigmaNetwork = ({ nodes, links, showDifferences, modelA, modelB }: SigmaNetworkProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    // Ensure container exists
    if (!containerRef.current) {
      setError('Container reference is not available');
      return;
    }

    // Clear container
    containerRef.current.innerHTML = '';

    try {
      console.log('Initializing graph with nodes:', nodes.length, 'links:', links.length);
      
      // Create graph
      const graph = new Graph();
      
      // Debug node and link data
      console.log('Node data sample:', nodes.slice(0, 5));
      console.log('Link data sample:', links.slice(0, 5));
      
      // Map node IDs to more readable labels if they are generated variables
      const nodeLabels: Record<string, string> = {};
      
      // Pre-process nodes to detect variable patterns and assign better labels
      nodes.forEach(node => {
        if (!node.id) return;
        
        // Clean up node names with subscripts (x₁, e₁, etc.)
        if (node.name && /^[a-zA-Z]₍[0-9]+₎$/.test(node.name)) {
          const baseName = node.name.charAt(0);
          const readableName = getReadableVariableName(baseName, node.category);
          nodeLabels[node.id] = readableName;
        }
      });
      
      // Prepare categories for better layout
      const nodesByCategory: Record<string, NetworkNode[]> = {};
      
      // Group nodes by category
      for (const node of nodes) {
        if (!node.id) continue;
        const category = node.category || 'default';
        if (!nodesByCategory[category]) {
          nodesByCategory[category] = [];
        }
        nodesByCategory[category].push(node);
      }
      
      // Add nodes by category
      const categories = Object.keys(nodesByCategory);
      categories.forEach((category, categoryIndex) => {
        const categoryNodes = nodesByCategory[category];
        const radius = 6 + (categoryIndex * 3); // Larger radius for each category
        
        categoryNodes.forEach((node, i) => {
          // Determine node size
          let size = 5;
          if (node.category === 'BMW') size = 12;
          else if (['Engine', 'Transmission', 'Drive'].includes(node.category || '')) size = 10;
          else if (node.category === 'Attribute') size = 8;
          else if (node.category === 'Value') size = 6;
          
          // Determine node color
          let color = '#999';
          switch (node.category) {
            case 'BMW': color = '#5D8AA8'; break;
            case 'Engine': color = '#DC143C'; break;
            case 'Transmission': color = '#B22222'; break;
            case 'Drive': color = '#FF6347'; break;
            case 'Attribute': color = '#9370DB'; break;
            case 'Value': color = '#FFD700'; break;
          }
          
          // Calculate position in a circle
          const angle = (i / categoryNodes.length) * 2 * Math.PI;
          const x = radius * Math.cos(angle);
          const y = radius * Math.sin(angle);
          
          // Use better label if available
          const nodeLabel = nodeLabels[node.id] || node.displayName || node.name || node.id;
          
          // Show value in label for attributes
          let displayLabel = nodeLabel;
          if (node.category === 'Attribute' && node.value_display) {
            displayLabel = `${nodeLabel}: ${node.value_display}`;
          }
          
          // Add node with attributes
          try {
            graph.addNode(node.id, {
              x: x,
              y: y,
              size,
              color,
              label: displayLabel
            });
          } catch (e) {
            console.warn(`Failed to add node ${node.id}:`, e);
          }
        });
      });
      
      // Add edges with increased visibility
      for (const link of links) {
        if (!link.source || !link.target) continue;
        if (!graph.hasNode(link.source) || !graph.hasNode(link.target)) continue;
        
        // Determine edge color and thickness based on type
        let color = '#999';
        let size = 1.5;
        
        switch (link.type) {
          case 'must':
            color = '#00CC00';
            size = 3;
            break;
          case 'must_not':
            color = '#FF0000';
            size = 3;
            break;
          case 'must_be_a':
            color = '#0000FF';
            size = 2;
            break;
          case 'HAS_ATTRIBUTE':
            color = '#9370DB';
            size = 2;
            break;
          case 'VALUE':
            color = '#FFD700';
            size = 1.5;
            break;
          default:
            color = '#777';
            size = 1;
        }
        
        try {
          graph.addEdge(link.source, link.target, {
            color,
            size,
            type: 'arrow' // Add arrow to show direction
          });
        } catch (e) {
          console.warn(`Failed to add edge ${link.source} -> ${link.target}:`, e);
        }
      }
      
      // Apply circular layout with larger spacing
      circular.assign(graph, {scale: 10});
      
      // Apply force layout with optimized settings for better visualization
      ForceAtlas2.assign(graph, {
        iterations: 100, // More iterations for better layout
        settings: {
          gravity: 1,
          scalingRatio: 8,
          strongGravityMode: true,
          linLogMode: false, // Disable linLogMode for more natural layout
          outboundAttractionDistribution: true,
          adjustSizes: true
        }
      });
      
      // Create renderer with improved settings
      const renderer = new Sigma(graph, containerRef.current, {
        defaultNodeColor: '#999',
        defaultEdgeColor: '#ccc',
        minCameraRatio: 0.1,
        maxCameraRatio: 20,
        renderLabels: true,
        labelSize: 16,
        labelColor: { color: '#000' }
      });
      
      console.log('Graph visualization created with', graph.order, 'nodes and', graph.size, 'edges');
      setError(null);
      
      // Cleanup
      return () => {
        renderer.kill();
      };
    } catch (e) {
      console.error('Error creating visualization:', e);
      setError(`Error creating visualization: ${(e as Error).message}`);
    }
  }, [nodes, links, showDifferences]);
  
  // Helper function to generate readable variable names
  function getReadableVariableName(baseChar: string, category?: string): string {
    switch (baseChar) {
      case 'x': return 'Car';
      case 'e': return 'Engine';
      case 't': return 'Transmission';
      case 'd': return 'Drive';
      case 'w': return 'Wheels';
      case 's': return 'Suspension';
      case 'b': return 'Brakes';
      case 'l': return 'Lights';
      case 'i': return 'Infotainment';
      case 'c': return 'Component';
      case 'v': return 'Vehicle';
      case 'su': return 'Suspension';
      default: return category || baseChar;
    }
  }
  
  // Render legend
  const renderLegend = () => (
    <div className="network-legend">
      <div className="legend-title">Typy uzlov</div>
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
        <div>Prevodovky</div>
      </div>
      <div className="legend-item">
        <div className="legend-color" style={{ backgroundColor: '#FF6347' }}></div>
        <div>Pohony</div>
      </div>
      <div className="legend-item">
        <div className="legend-color" style={{ backgroundColor: '#9370DB' }}></div>
        <div>Atribúty</div>
      </div>
      <div className="legend-item">
        <div className="legend-color" style={{ backgroundColor: '#FFD700' }}></div>
        <div>Hodnoty</div>
      </div>
      
      <div className="legend-title" style={{ marginTop: "16px" }}>Typy spojení</div>
      <div className="legend-item">
        <div className="legend-line">
          <hr style={{ borderColor: '#00FF00', borderWidth: '2px' }} />
          <span style={{ marginLeft: '5px' }}>MUST</span>
        </div>
        <div>Povinné spojenie</div>
      </div>
      <div className="legend-item">
        <div className="legend-line">
          <hr style={{ borderColor: '#FF0000', borderWidth: '2px' }} />
          <span style={{ marginLeft: '5px' }}>MUST_NOT</span>
        </div>
        <div>Zakázané spojenie</div>
      </div>
      <div className="legend-item">
        <div className="legend-line">
          <hr style={{ borderColor: '#0000FF', borderWidth: '2px' }} />
          <span style={{ marginLeft: '5px' }}>MUST_BE_A</span>
        </div>
        <div>Dedičnosť</div>
      </div>
      <div className="legend-item">
        <div className="legend-line">
          <hr style={{ borderColor: '#9370DB', borderWidth: '2px' }} />
          <span style={{ marginLeft: '5px' }}>HAS_ATTRIBUTE</span>
        </div>
        <div>Atribút objektu</div>
      </div>
      <div className="legend-item">
        <div className="legend-line">
          <hr style={{ borderColor: '#FFD700', borderWidth: '2px' }} />
          <span style={{ marginLeft: '5px' }}>VALUE</span>
        </div>
        <div>Hodnota atribútu</div>
      </div>
    </div>
  );
  
  // Display error message
  if (error) {
    return <div className="sigma-error">Error: {error}</div>;
  }
  
  // Render semantic network
  return (
    <div className="semantic-network-container">
      {renderLegend()}
      <div 
        ref={containerRef} 
        style={{ width: "100%", height: "800px" }} 
      />
    </div>
  );
};

export default SigmaNetwork; 