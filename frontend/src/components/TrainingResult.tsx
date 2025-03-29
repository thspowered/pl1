import {
  Typography,
  Paper,
  Box,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  Chip,
  Alert,
  Button,
  Grid
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { TrainingResult as TrainingResultType } from '../types';
import SigmaNetwork from './SigmaNetwork';
import { useMemo, useEffect } from 'react';

interface TrainingResultProps {
  result: TrainingResultType | null;
  onRefreshGraph?: () => void;
}

// Funkcia na parsovanie identifikačných pravidiel pre konkrétny model auta
const extractModelRules = (hypothesis: string | null, modelName: string): string | null => {
  if (!hypothesis) return null;
  
  // Pokúsime sa nájsť vzorce, ktoré obsahujú IS(x, modelName)
  // Upravená verzia regexu, ktorá by mala byť flexibilnejšia
  try {
    // Skúsime najprv nájsť sekciu, ktorá vedie k danému modelu
    const regex = new RegExp(`.*→\\s*IS\\s*\\(.*?,\\s*${modelName}\\s*\\)`, 'i');
    const match = hypothesis.match(regex);
    
    if (match && match[0]) {
      // Vyčistíme a naformátujeme pravidlo
      let rule = match[0].trim();
      
      // Odstránime prípadné úvodné logické spojky, ak sa začína s ∧ alebo ∨
      rule = rule.replace(/^(\s*[∧∨]\s*)/, '');
      
      // Pridanie kvantifikátora a zátvoriek pre štandardnú logickú formulu
      return `∀x: [\n  ${rule}\n]`;
    }
    
    // Alternatívny prístup - hľadanie častí pre IS(x, modelName)
    const simpleRegex = new RegExp(`IS\\s*\\(.*?,\\s*${modelName}\\s*\\)`, 'i');
    const simpleMatch = hypothesis.match(simpleRegex);
    
    if (simpleMatch && simpleMatch[0]) {
      // Získame širší kontext okolo nájdeného výrazu
      const index = hypothesis.indexOf(simpleMatch[0]);
      const startIndex = Math.max(0, hypothesis.lastIndexOf(')') >= 0 ? hypothesis.lastIndexOf(')', index - 100) : index - 100);
      const endIndex = Math.min(hypothesis.length, index + simpleMatch[0].length + 1);
      let context = hypothesis.substring(startIndex, endIndex).trim();
      
      // Upravíme kontext tak, aby bol validný výraz
      if (!context.includes('→')) {
        context = `... → ${simpleMatch[0]}`;
      }
      
      return `∀x: [\n  ${context}\n]`;
    }
  } catch (error) {
    console.error(`Chyba pri parsovaní pravidiel pre ${modelName}:`, error);
  }
  
  return null;
};

// Nová funkcia na extrakciu pravidiel v štýle ∀x: [ conditions → IS(x, model) ]
const extractModelRulesAlternative = (hypothesis: string | null): Record<string, string> => {
  if (!hypothesis) return {};
  
  const results: Record<string, string> = {};
  
  // Vzor pre jednoduché pravidlá ako boli ukázané v obraze
  // Hľadá vzory: HAS(x, something) ∧ ... → IS(x, ModelName)
  try {
    // Hľadáme časti s IS(x, <model>)
    const modelRegex = /IS\s*\(\s*\w+\s*,\s*(\w+)\s*\)/g;
    let match;
    
    // Pre každý model nájdený v hypotéze
    while ((match = modelRegex.exec(hypothesis)) !== null) {
      const modelName = match[1]; // Získaj názov modelu
      if (!modelName) continue;
      
      // Hľadáme pravidlo pred IS(x, model)
      const rulePart = hypothesis.substring(Math.max(0, match.index - 300), match.index).trim();
      const arrowIndex = rulePart.lastIndexOf('→');
      
      if (arrowIndex >= 0) {
        // Berieme časť za poslednou šípkou a pridáme IS výraz
        const conditions = rulePart.substring(arrowIndex + 1).trim();
        const completeRule = `${conditions} → ${match[0]}`;
        
        // Formátujeme ako v príklade
        results[modelName] = `∀x: [\n  ${completeRule}\n]`;
      } else {
        // Ak nenájdeme šípku, vezmeme aspoň časť pred výrazom IS
        const lastConjunction = Math.max(
          rulePart.lastIndexOf('∧'),
          rulePart.lastIndexOf('∨'),
          rulePart.lastIndexOf('¬')
        );
        
        if (lastConjunction >= 0) {
          const partialConditions = rulePart.substring(lastConjunction).trim();
          const completeRule = `${partialConditions} → ${match[0]}`;
          
          // Formátujeme ako v príklade
          results[modelName] = `∀x: [\n  ${completeRule}\n]`;
        }
      }
    }
    
    // Ak sme nenašli žiadne výsledky, skúsime ešte jeden alternatívny prístup
    if (Object.keys(results).length === 0) {
      // Skúsime nájsť vzor podobný tomu z obrazu
      const fullRuleRegex = /∀x:\s*\[\s*([^→]*?)→\s*IS\s*\(\s*\w+\s*,\s*(\w+)\s*\)\s*\]/g;
      
      while ((match = fullRuleRegex.exec(hypothesis)) !== null) {
        const conditions = match[1]?.trim();
        const modelName = match[2]?.trim();
        
        if (conditions && modelName) {
          results[modelName] = `∀x: [\n  ${conditions} → IS(x, ${modelName})\n]`;
        }
      }
    }
  } catch (error) {
    console.error("Chyba pri alternatívnej extrakcii pravidiel:", error);
  }
  
  return results;
};

const TrainingResultDisplay = ({ result, onRefreshGraph }: TrainingResultProps) => {
  // Vypíšeme hypothesis pre debugging
  useEffect(() => {
    if (result?.model_hypothesis) {
      console.log("Model hypothesis:", result.model_hypothesis);
    }
    if (result?.model_rules) {
      console.log("Model rules received from backend:", result.model_rules);
      console.log("Type of model_rules:", typeof result.model_rules);
      console.log("Keys in model_rules:", Object.keys(result.model_rules));
    }
  }, [result?.model_hypothesis, result?.model_rules]);

  // Skúsime aj alternatívnu metódu extrakcie
  const alternativeRules = useMemo(() => {
    return result?.model_hypothesis 
      ? extractModelRulesAlternative(result.model_hypothesis)
      : {};
  }, [result?.model_hypothesis]);

  // Dynamicky získaj pravidlá
  const modelRules = useMemo(() => {
    // Ak máme pravidlá priamo z backendu, použijeme ich prioritne
    if (result?.model_rules && Object.keys(result.model_rules).length > 0) {
      console.log("Using rules directly from backend:", result.model_rules);
      return result.model_rules;
    }
    
    console.log("No rules from backend, falling back to extraction");
    
    // Inak sa pokúsime extrahovať ich z hypotézy (fallback pre spätnú kompatibilitu)
    if (!result?.model_hypothesis) return {};
    
    const rules = {
      'BMW': extractModelRules(result.model_hypothesis, 'BMW'),
      'Series3': extractModelRules(result.model_hypothesis, 'Series3'),
      'Series5': extractModelRules(result.model_hypothesis, 'Series5'),
      'Series7': extractModelRules(result.model_hypothesis, 'Series7'),
      'X5': extractModelRules(result.model_hypothesis, 'X5'),
      'X7': extractModelRules(result.model_hypothesis, 'X7')
    };
    
    // Debug log pre extrahované pravidlá
    console.log("Extrahované pravidlá pôvodnou metódou:", rules);
    console.log("Extrahované pravidlá alternatívnou metódou:", alternativeRules);
    
    // Ak máme viac pravidiel z alternatívnej metódy, použijeme tie
    const validRulesCount = Object.keys(rules).filter(k => rules[k as keyof typeof rules] !== null).length;
    const alternativeRulesCount = Object.keys(alternativeRules).length;
    
    console.log(`Porovnanie metód: pôvodná (${validRulesCount}) vs. alternatívna (${alternativeRulesCount})`);
    
    if (alternativeRulesCount > validRulesCount) {
      console.log("Using alternative extraction method");
      return alternativeRules;
    }
    
    console.log("Using original extraction method");
    return rules;
  }, [result?.model_hypothesis, alternativeRules, result?.model_rules]);
  
  // Zistíme, či vôbec máme nejaké extrahované pravidlá
  const hasRules = useMemo(() => {
    return Object.values(modelRules).some(rule => rule !== null && rule !== undefined);
  }, [modelRules]);
  
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
                <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1, color: '#90caf9' }}>
                  Identifikačné pravidlá pre modely áut:
                </Typography>
                {result.model_hypothesis ? (
                  <Box sx={{ maxHeight: '400px', overflowY: 'auto' }}>
                    {!hasRules && (
                      <Alert 
                        severity="info" 
                        sx={{ 
                          mb: 2,
                          borderRadius: 1,
                          background: 'rgba(25, 118, 210, 0.15)',
                          border: '1px solid rgba(25, 118, 210, 0.3)',
                          color: 'white',
                          '& .MuiAlert-icon': { color: '#90caf9' },
                        }}
                      >
                        Neboli nájdené žiadne pravidlá pre konkrétne modely. Pozrite si kompletnú formulu nižšie.
                      </Alert>
                    )}
                    
                    <Grid container spacing={2}>
                      {/* Dynamicky vygenerované komponenty pre každý model auta */}
                      {Object.entries(modelRules).map(([modelName, rule]) => 
                        rule ? (
                          <Grid item xs={12} key={modelName}>
                            <Box 
                              sx={{ 
                                p: 2, 
                                borderRadius: 1, 
                                bgcolor: 'rgba(0,0,0,0.2)', 
                                border: '1px solid rgba(255,255,255,0.05)',
                                height: '100%',
                                fontFamily: 'monospace',
                                fontSize: '0.9rem',
                                whiteSpace: 'pre-wrap',
                                overflowX: 'auto'
                              }}
                            >
                              <Typography variant="h6" sx={{ fontSize: '1rem', mb: 1, color: '#f8bb86' }}>
                                {modelName}
                              </Typography>
                              <Box sx={{ 
                                p: 1.5, 
                                borderRadius: 1, 
                                bgcolor: 'rgba(0,0,0,0.15)',
                                color: 'rgba(255,255,255,0.85)',
                                fontFamily: 'monospace',
                                lineHeight: 1.5
                              }}>
                                {rule}
                              </Box>
                            </Box>
                          </Grid>
                        ) : null
                      )}
                      
                      {/* Tlačidlo pre zobrazenie detailov formuly */}
                      <Grid item xs={12}>
                        <Accordion 
                          sx={{
                            mt: 1,
                            background: 'rgba(25, 118, 210, 0.08)',
                            border: '1px solid rgba(144, 202, 249, 0.3)',
                            borderRadius: '4px',
                            '&:before': {
                              display: 'none'
                            }
                          }}
                        >
                          <AccordionSummary
                            expandIcon={<ExpandMoreIcon sx={{ color: 'rgba(255, 255, 255, 0.7)' }} />}
                            sx={{
                              minHeight: '48px',
                              '& .MuiAccordionSummary-content': {
                                margin: '8px 0'
                              }
                            }}
                          >
                            <Typography variant="body2" sx={{ fontWeight: 500, color: '#90caf9' }}>
                              Zobraziť kompletnú natrénovanú formulu
                            </Typography>
                          </AccordionSummary>
                          <AccordionDetails>
                            <Box 
                              sx={{ 
                                p: 2, 
                                borderRadius: 1, 
                                bgcolor: 'rgba(0,0,0,0.2)', 
                                border: '1px solid rgba(255,255,255,0.05)',
                                fontFamily: 'monospace',
                                fontSize: '0.85rem',
                                overflowX: 'auto',
                                color: 'rgba(255,255,255,0.7)'
                              }}
                            >
                              {result.model_hypothesis}
                            </Box>
                          </AccordionDetails>
                        </Accordion>
                      </Grid>
                    </Grid>
                  </Box>
                ) : (
                  <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)' }}>
                    Žiadna hypotéza nie je k dispozícii
                  </Typography>
                )}
              </Paper>
            </Grid>
            
            {/* Trénovacie kroky - stručnejší prehľad */}
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
                <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1, color: '#90caf9' }}>
                  Použité príklady:
                </Typography>
                {result.training_steps && result.training_steps.length > 0 ? (
                  <Box sx={{ mt: 1 }}>
                    {result.training_steps.map((step, index) => (
                      <Accordion 
                        key={index}
                        sx={{
                          mb: 1,
                          background: 'rgba(0,0,0,0.2)',
                          border: '1px solid rgba(255, 255, 255, 0.05)',
                          borderRadius: '4px',
                          '&:before': {
                            display: 'none'
                          },
                          '&.Mui-expanded': {
                            margin: 0,
                            mb: 1,
                            background: 'rgba(25, 118, 210, 0.08)'
                          },
                          '&:hover': {
                            borderColor: 'rgba(144, 202, 249, 0.3)'
                          }
                        }}
                      >
                        <AccordionSummary
                          expandIcon={<ExpandMoreIcon sx={{ color: 'rgba(255, 255, 255, 0.7)' }} />}
                          sx={{
                            flexDirection: 'row',
                            minHeight: '48px',
                            transition: 'background-color 0.2s',
                            '&:hover': {
                              background: 'rgba(144, 202, 249, 0.05)'
                            },
                            '&.Mui-expanded': {
                              background: 'rgba(25, 118, 210, 0.1)',
                              borderBottom: '1px solid rgba(144, 202, 249, 0.3)'
                            },
                            '& .MuiAccordionSummary-content': {
                              display: 'flex',
                              alignItems: 'center',
                              gap: 1,
                              margin: '6px 0'
                            }
                          }}
                        >
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>
                            {step.example_name || `Krok ${index + 1}`}
                          </Typography>
                          {step.is_positive !== undefined && (
                            <Chip 
                              size="small" 
                              label={step.is_positive ? "Pozitívny" : "Negatívny"} 
                              sx={{ 
                                height: '20px',
                                fontSize: '0.7rem',
                                fontWeight: 600,
                                bgcolor: step.is_positive ? 'rgba(102, 187, 106, 0.2)' : 'rgba(244, 67, 54, 0.2)',
                                color: step.is_positive ? '#66bb6a' : '#f44336',
                                border: step.is_positive ? '1px solid rgba(102, 187, 106, 0.3)' : '1px solid rgba(244, 67, 54, 0.3)'
                              }}
                            />
                          )}
                        </AccordionSummary>
                        <AccordionDetails sx={{ pt: 1, pb: 2, background: 'rgba(0,0,0,0.1)' }}>
                          <Typography variant="body2" sx={{ mt: 1, mb: 2, color: 'rgba(255,255,255,0.7)' }}>
                            {step.description}
                          </Typography>
                          
                          {/* Zobrazenie heuristík, ak existujú */}
                          {step.heuristics && step.heuristics.length > 0 && (
                            <Box sx={{ mt: 2 }}>
                              <Typography variant="body2" sx={{ fontWeight: 500, color: '#90caf9', mb: 1 }}>
                                Použité heuristiky:
                              </Typography>
                              <Box sx={{ 
                                ml: 1,
                                pl: 1, 
                                borderLeft: '2px solid rgba(144, 202, 249, 0.3)',
                                py: 0.5
                              }}>
                                {step.heuristics.map((heuristic, hIndex) => (
                                  <Box key={hIndex} sx={{ 
                                    mb: 1.5,
                                    p: 1,
                                    borderRadius: 1,
                                    backgroundColor: 'rgba(255,255,255,0.03)',
                                    border: '1px solid rgba(255,255,255,0.05)'
                                  }}>
                                    <Typography variant="body2" sx={{ fontWeight: 500, color: 'rgba(255,255,255,0.9)' }}>
                                      {heuristic.name || `Heuristika ${hIndex + 1}`}
                                    </Typography>
                                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)', display: 'block', ml: 1, mt: 0.5 }}>
                                      {heuristic.description}
                                    </Typography>
                                    {heuristic.details && Object.keys(heuristic.details).length > 0 && (
                                      <Box sx={{ 
                                        ml: 1, 
                                        mt: 0.5, 
                                        p: 1, 
                                        borderRadius: 1,
                                        background: 'rgba(0,0,0,0.2)'
                                      }}>
                                        {Object.entries(heuristic.details).map(([key, value]) => (
                                          <Typography 
                                            key={key} 
                                            variant="caption" 
                                            sx={{ 
                                              display: 'block', 
                                              color: 'rgba(255,255,255,0.6)',
                                              fontFamily: 'monospace',
                                              fontSize: '0.75rem'
                                            }}
                                          >
                                            <Box component="span" sx={{ color: '#90caf9', mr: 1, fontWeight: 500 }}>{key}:</Box> {value}
                                          </Typography>
                                        ))}
                                      </Box>
                                    )}
                                  </Box>
                                ))}
                              </Box>
                            </Box>
                          )}
                        </AccordionDetails>
                      </Accordion>
                    ))}
                  </Box>
                ) : (
                  <Typography variant="body2" sx={{ mt: 1, color: 'rgba(255,255,255,0.7)' }}>
                    Nie sú dostupné žiadne trénovacie kroky.
                  </Typography>
                )}
              </Paper>
            </Grid>
            
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
                      Sémantická sieť modelu
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
                  
                  <Box sx={{ 
                    height: '400px',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    borderRadius: 1,
                    overflow: 'hidden',
                    position: 'relative'
                  }}>
                    {result.model_visualization.nodes.length > 0 ? (
                      <>
                        <SigmaNetwork 
                          nodes={result.model_visualization.nodes}
                          links={result.model_visualization.links}
                        />
                        <Box
                          sx={{
                            position: 'absolute',
                            bottom: 8,
                            right: 8,
                            backgroundColor: 'rgba(0,0,0,0.7)',
                            p: 1,
                            borderRadius: 1,
                            color: 'white',
                            fontSize: '0.75rem'
                          }}
                        >
                          Tip: Použite myš na približovanie a posun v grafe
                        </Box>
                      </>
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
                  
                  {result.model_visualization.nodes.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="body2" sx={{ fontWeight: 500, mb: 1, color: 'rgba(255,255,255,0.8)' }}>
                        Zoznam prepojení:
                      </Typography>
                      <Box 
                        sx={{ 
                          display: 'flex', 
                          flexWrap: 'wrap', 
                          gap: 1, 
                          maxHeight: '100px', 
                          overflowY: 'auto',
                          p: 1,
                          borderRadius: 1,
                          bgcolor: 'rgba(0,0,0,0.2)'
                        }}
                      >
                        {result.model_visualization.links.map((link, index) => (
                          <Chip 
                            key={index}
                            label={`${link.source} → ${link.target} (${link.type})`} 
                            variant="outlined"
                            size="small"
                            sx={{ 
                              bgcolor: 'rgba(255,255,255,0.05)',
                              color: 'rgba(255,255,255,0.8)',
                              borderColor: 'rgba(255,255,255,0.2)'
                            }}
                          />
                        ))}
                      </Box>
                    </Box>
                  )}
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