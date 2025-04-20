import {
  Typography,
  Paper,
  Box,
  Alert,
  Button,
  Grid
} from '@mui/material';
import { TrainingResult as TrainingResultType } from '../types';
import NetworkGraph from './NetworkGraph';
import { useEffect, ReactNode } from 'react';

interface TrainingResultProps {
  result: TrainingResultType | null;
  onRefreshGraph?: () => void;
}

// Nová funkcia pre formátovanie pravidla ako React element
// Nahrádza množinový zápis disjunkciou a zvýrazňuje všetky logické operátory
const formatRuleWithColorsAsReact = (rule: string): ReactNode => {
  if (!rule) return null;
  
  // Najprv nahradíme množiny disjunkciami v reťazci
  let processedRule = rule;
  // Regulárny výraz na detekciu množiny {a, b, c}
  const setRegex = /∈\s*\{([^}]+)\}/g;
  
  // Nahradíme množiny disjunkciou hodnôt
  processedRule = processedRule.replace(setRegex, (match, valuesStr) => {
    // Rozdelíme hodnoty podľa čiarky
    const values = valuesStr.split(',').map((v: string) => v.trim());
    
    // Ak je len jedna hodnota, vrátime ju
    if (values.length === 1) {
      return `= ${values[0]}`;
    }
    
    // Inak vytvoríme disjunkciu
    return `= ${values.join(' ∨ ')}`;
  });
  
  // Ďalšie nahradenie pre formát {250, 340}
  const numericSetRegex = /\{(\d+),\s*(\d+)\}/g;
  processedRule = processedRule.replace(numericSetRegex, (match, val1, val2) => {
    return `${val1} ∨ ${val2}`;
  });
  
  // Nové nahradenie pre Α(e, power, 250 ∨ 340) -> Α(e, power, 250) ∨ Α(e, power, 340)
  // Regex na vyhľadanie atribútov s disjunkciou v hodnotách - rozšírené pre akékoľvek hodnoty
  const attrDisjunctionRegex = /(Α|A)\s*\(\s*([^,]+),\s*([^,]+),\s*([^∨)]+)\s*∨\s*([^)]+)\s*\)/g;
  
  // Funkcia na transformáciu atribútu s disjunkciou
  const transformAttributeDisjunction = (rule: string): string => {
    // Najprv hľadáme disjunkcie v atribútoch s dvomi hodnotami
    let result = rule.replace(attrDisjunctionRegex, (match, attrSymbol, obj, attr, val1, val2) => {
      return `${attrSymbol}(${obj}, ${attr}, ${val1.trim()}) ∨ ${attrSymbol}(${obj}, ${attr}, ${val2.trim()})`;
    });
    
    // Skontrolujeme, či sa niečo zmenilo
    if (result !== rule) {
      // Ak áno, rekurzívne pokračujeme v spracovaní ďalších výskytov
      return transformAttributeDisjunction(result);
    }
    
    // Ak sa už nič nezmenilo, vrátime výsledok
    return result;
  };
  
  // Aplikujeme transformáciu
  processedRule = transformAttributeDisjunction(processedRule);
  
  // Teraz pokračujeme so štandardným formátovaním
  const parts: ReactNode[] = [];
  let currentText = '';
  let index = 0;
  
  // Funkcia na pridanie aktuálneho textu do zoznamu častí
  const addCurrentText = () => {
    if (currentText) {
      parts.push(<span key={`text-${index}`}>{currentText}</span>);
      currentText = '';
      index++;
    }
  };

  // Funkcia na spracovanie pravidla znak po znaku
  const processRule = () => {
    for (let i = 0; i < processedRule.length; i++) {
      const char = processedRule[i];
      
      // Zvýrazňujeme všetky logické operátory
      if (char === '∧') {
        addCurrentText();
        parts.push(<span key={`and-${index}`} style={{ color: '#64b5f6', fontWeight: 'bold' }}>∧</span>);
        index++;
      }
      else if (char === '∨') {
        addCurrentText();
        parts.push(<span key={`or-${index}`} style={{ color: '#ffb74d', fontWeight: 'bold' }}>∨</span>);
        index++;
      }
      else if (char === '¬') {
        addCurrentText();
        parts.push(<span key={`not-${index}`} style={{ color: '#ef5350', fontWeight: 'bold' }}>¬</span>);
        index++;
      }
      else if (char === '→') {
        addCurrentText();
        parts.push(<span key={`impl-${index}`} style={{ color: '#ba68c8', fontWeight: 'bold' }}>→</span>);
        index++;
      }
      // Všetok ostatný text sa pridáva do currentText
      else {
        currentText += char;
      }
    }
    
    // Pridáme zvyšok textu
    addCurrentText();
  };
  
  processRule();
  
  return <>{parts}</>;
};

const TrainingResultDisplay = ({ result, onRefreshGraph }: TrainingResultProps) => {
  // Vypíšeme hypothesis pre debugging
  useEffect(() => {
    if (result?.model_hypothesis) {
      console.log("Model hypothesis:", result.model_hypothesis);
    }
  }, [result?.model_hypothesis]);
  
  if (!result) {
    return (
      <Paper 
        elevation={3}
        sx={{
          p: 2,
          borderRadius: 2,
          bgcolor: 'transparent',
          background: 'linear-gradient(145deg, rgba(25, 118, 210, 0.08) 0%, rgba(25, 118, 210, 0.03) 100%)',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          border: '1px solid rgba(255, 255, 255, 0.08)'
        }}
      >
        <Alert 
          severity="info" 
          sx={{ 
            borderRadius: 2,
            background: 'rgba(25, 118, 210, 0.15)',
            border: '1px solid rgba(25, 118, 210, 0.3)',
            color: 'white',
            '& .MuiAlert-icon': { color: '#90caf9' },
          }}
        >
          Zatiaľ nebol spustený žiadny trénovací proces. Vyberte príklady a kliknite na tlačidlo "Trénovať model".
        </Alert>
      </Paper>
    );
  }

  // Handling success or error cases
  return (
    <Box sx={{ width: '100%' }}>
      {result.success ? (
        <>
          <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
            <Alert 
              severity="success" 
              sx={{ 
                minWidth: '200px',
                flex: '1 1 100%',
                borderRadius: 2,
                background: 'rgba(102, 187, 106, 0.15)',
                border: '1px solid rgba(102, 187, 106, 0.3)',
                color: 'white',
                '& .MuiAlert-icon': { color: '#66bb6a' },
              }}
            >
              Trénovanie úspešne dokončené!
            </Alert>
          </Box>
          
          <Grid container spacing={3}>
            {/* Natrénovaná formula */}
            {result.model_hypothesis && (
              <Grid item xs={12}>
                <Paper
                  elevation={2}
                  sx={{
                    p: 2,
                    borderRadius: 2,
                    background: 'linear-gradient(145deg, rgba(30,30,30,0.6) 0%, rgba(18,18,18,0.6) 100%)',
                    border: '1px solid rgba(255, 255, 255, 0.08)'
                  }}
                >
                  <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2, color: '#90caf9' }}>
                    Výsledok trénovania
                  </Typography>
                  <Box 
                    sx={{ 
                      p: 2, 
                      borderRadius: 1, 
                      bgcolor: 'rgba(0,0,0,0.2)', 
                      border: '1px solid rgba(255,255,255,0.05)',
                      fontFamily: 'monospace',
                      fontSize: '0.85rem',
                      overflowX: 'auto',
                      color: 'rgba(255,255,255,0.7)',
                      maxHeight: '400px',
                      overflowY: 'auto'
                    }}
                  >
                    <div className="formula-container" data-formula={result.model_hypothesis}>
                      {formatRuleWithColorsAsReact(result.model_hypothesis)}
                    </div>
                  </Box>
                </Paper>
              </Grid>
            )}
            
            {/* Sémantická sieť */}
            {result.model_visualization && result.model_visualization.nodes && (
              <Grid item xs={12}>
                <Paper
                  elevation={2}
                  sx={{
                    p: 2,
                    borderRadius: 2,
                    background: 'linear-gradient(145deg, rgba(30,30,30,0.6) 0%, rgba(18,18,18,0.6) 100%)',
                    border: '1px solid rgba(255, 255, 255, 0.08)'
                  }}
                >
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600, color: '#90caf9' }}>
                      Vizualizácia porovnania
                    </Typography>
                    {onRefreshGraph && (
                      <Button 
                        variant="outlined" 
                        color="primary" 
                        size="small" 
                        onClick={onRefreshGraph}
                        sx={{ 
                          borderRadius: 2,
                          textTransform: 'none',
                          borderColor: 'rgba(144, 202, 249, 0.5)',
                          color: '#90caf9',
                          '&:hover': {
                            borderColor: 'rgba(144, 202, 249, 0.8)',
                            backgroundColor: 'rgba(144, 202, 249, 0.08)'
                          }
                        }}
                      >
                        Obnoviť graf
                      </Button>
                    )}
                  </Box>
                  
                  {/* Single view for visualization */}
                  <Box>
                    <Typography variant="body2" sx={{ fontWeight: 500, mb: 1, color: '#e0e0e0', textAlign: 'center' }}>
                      Vizualizácia porovnania
                    </Typography>
                    <Box sx={{ 
                      height: '600px',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                      borderRadius: 1,
                      overflow: 'hidden',
                      position: 'relative'
                    }}>
                      {result.model_visualization.nodes.length > 0 ? (
                        <NetworkGraph 
                          nodes={result.model_visualization.nodes.map(node => ({
                            ...node,
                            // Use 'common' status for nodes that don't have a specific status
                            status: node.status || 'common'
                          }))}
                          links={result.model_visualization.links.map(link => ({
                            ...link,
                            // Use 'common' status for links that don't have a specific status
                            status: link.status || 'common'
                          }))}
                          formula={result.model_hypothesis}
                          showDifferences={true}
                          modelA="Model"
                          modelB="Príklad"
                        />
                      ) : (
                        <Box 
                          sx={{ 
                            height: '100%', 
                            display: 'flex', 
                            alignItems: 'center', 
                            justifyContent: 'center',
                            backgroundColor: 'rgba(0,0,0,0.2)'
                          }}
                        >
                          <Typography color="text.secondary">
                            Prázdna sémantická sieť - nie sú k dispozícii žiadne uzly pre vizualizáciu.
                          </Typography>
                        </Box>
                      )}
                    </Box>
                  </Box>
                  
                  {/* Legend */}
                  <Box sx={{ mt: 2, p: 2, borderRadius: 1, bgcolor: 'rgba(0, 0, 0, 0.3)', border: '1px solid rgba(255,255,255,0.1)' }}>
                    <Typography variant="body2" sx={{ fontWeight: 600, mb: 1, color: '#e0e0e0' }}>
                      Legenda:
                    </Typography>
                    <Grid container spacing={2}>
                      <Grid item xs={6} sm={3}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: '#DC143C' }}></Box>
                          <Typography variant="caption">Motor</Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={6} sm={3}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: '#CD5C5C' }}></Box>
                          <Typography variant="caption">Prevodovka</Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={6} sm={3}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: '#FF6347' }}></Box>
                          <Typography variant="caption">Pohon</Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={6} sm={3}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: '#4682B4' }}></Box>
                          <Typography variant="caption">Vozidlo</Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={6} sm={3}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: '#A0522D' }}></Box>
                          <Typography variant="caption">Komponent</Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={6} sm={3}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Box sx={{ width: 12, height: 12, borderRadius: '0%', bgcolor: '#9370DB' }}></Box>
                          <Typography variant="caption">Atribút</Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={6} sm={3}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Box sx={{ width: 12, height: 12, borderRadius: '0%', bgcolor: '#FFD700' }}></Box>
                          <Typography variant="caption">Hodnota</Typography>
                        </Box>
                      </Grid>
                    </Grid>
                  </Box>
                </Paper>
              </Grid>
            )}
          </Grid>
        </>
      ) : (
        <Alert 
          severity="error" 
          sx={{ 
            borderRadius: 2,
            background: 'rgba(244, 67, 54, 0.15)',
            border: '1px solid rgba(244, 67, 54, 0.3)',
            color: 'white',
            '& .MuiAlert-icon': { color: '#f44336' },
          }}
        >
          {result.message || 'Nastala chyba pri trénovaní modelu.'}
        </Alert>
      )}
    </Box>
  );
};

export default TrainingResultDisplay;