import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Divider,
  Checkbox,
  FormControlLabel,
  Grid,
  Card,
  CardContent,
  CardActionArea,
  Alert,
  Container,
  IconButton,
  Tooltip,
  Chip
} from '@mui/material';
import { NetworkNode, NetworkLink, Example, TrainingResult } from "../types";
import TrainingPanel from "./TrainingPanel";
import TrainingResultDisplay from "./TrainingResult";
import { ModelControls } from "./ModelControls";

// Nová komponenta pro zobrazení logu heuristik
const HeuristicsLog: React.FC<{ trainingSteps: any[] }> = ({ trainingSteps }) => {
  // Projdeme všechny kroky trénovania a zobrazíme heuristiky v chronologickém pořadí
  if (!trainingSteps || trainingSteps.length === 0) return null;
  
  return (
    <Box sx={{ mt: 2, p: 0 }}>
      <Typography variant="subtitle1" sx={{ 
        fontWeight: 600, 
        color: '#90caf9', 
        mb: 1.5,
        display: 'flex',
        alignItems: 'center',
        '&::after': {
          content: '""',
          height: '1px',
          flexGrow: 1,
          ml: 2,
          background: 'linear-gradient(90deg, rgba(144, 202, 249, 0.5) 0%, rgba(144, 202, 249, 0) 100%)'
        }
      }}>
        Aplikované heuristiky
      </Typography>
      
      {/* Rolovací okno s chronologickým seznamem heuristik */}
      <Box 
        sx={{ 
          maxHeight: '200px',
          overflowY: 'auto',
          p: 1.5,
          bgcolor: 'rgba(0,0,0,0.2)',
          borderRadius: 1.5,
          border: '1px solid rgba(255,255,255,0.05)',
          '&::-webkit-scrollbar': {
            width: '6px',
          },
          '&::-webkit-scrollbar-track': {
            background: 'rgba(255,255,255,0.03)',
            borderRadius: '3px',
          },
          '&::-webkit-scrollbar-thumb': {
            background: 'rgba(144, 202, 249, 0.2)',
            borderRadius: '3px',
            '&:hover': {
              background: 'rgba(144, 202, 249, 0.4)',
            },
          }
        }}
      >
        {trainingSteps.map((step, stepIndex) => {
          // Pokud krok neobsahuje heuristiky, přeskočíme ho
          if (!step.heuristics || step.heuristics.length === 0) return null;
          
          return (
            <Box 
              key={`step-${stepIndex}`} 
              sx={{ 
                mb: 1.5,
                pb: 1.5,
                borderBottom: stepIndex < trainingSteps.length - 1 ? '1px dashed rgba(255,255,255,0.1)' : 'none',
                position: 'relative'
              }}
            >
              <Box sx={{ 
                display: 'flex', 
                alignItems: 'center', 
                mb: 1 
              }}>
                <Box sx={{ 
                  width: '24px', 
                  height: '24px', 
                  borderRadius: '50%', 
                  bgcolor: 'rgba(144, 202, 249, 0.2)', 
                  border: '1px solid rgba(144, 202, 249, 0.4)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  color: '#90caf9',
                  mr: 1.5
                }}>
                  {stepIndex + 1}
                </Box>
                <Typography variant="caption" sx={{ 
                  color: 'rgba(255,255,255,0.7)',
                  fontSize: '0.75rem',
                  fontWeight: 500
                }}>
                  {step.example_name ? `Príklad: ${step.example_name}` : 'Krok trénovania'}
                  {step.is_positive !== undefined && (
                    <Box 
                      component="span" 
                      sx={{ 
                        ml: 1,
                        borderRadius: 1, 
                        px: 1, 
                        py: 0.2, 
                        display: 'inline-block',
                        bgcolor: step.is_positive ? 'rgba(102, 187, 106, 0.2)' : 'rgba(244, 67, 54, 0.2)',
                        color: step.is_positive ? '#66bb6a' : '#f44336',
                        fontSize: '0.65rem',
                        fontWeight: 600,
                        border: step.is_positive ? '1px solid rgba(102, 187, 106, 0.4)' : '1px solid rgba(244, 67, 54, 0.4)',
                      }}
                    >
                      {step.is_positive ? 'Pozitívny' : 'Negatívny'}
                    </Box>
                  )}
                </Typography>
              </Box>
              
              <Box sx={{ 
                display: 'flex', 
                flexWrap: 'wrap', 
                gap: 1,
                ml: 4.5, // odsadenie od čísla kroku
                position: 'relative',
                '&::before': {
                  content: '""',
                  position: 'absolute',
                  left: '-10px',
                  top: 0,
                  bottom: 0,
                  width: '1px',
                  bgcolor: 'rgba(144, 202, 249, 0.2)',
                  zIndex: 0
                }
              }}>
                {step.heuristics.map((heuristic: string | { name: string; description: string }, hIndex: number) => {
                  // Spracujeme rôzne formáty heuristík - niektoré môžu byť len stringy, iné objekty
                  const heuristicName = typeof heuristic === 'string' ? heuristic : heuristic.name;
                  const heuristicDescription = typeof heuristic === 'string' ? '' : (heuristic.description || '');
                  
                  return (
                    <Chip
                      key={`${heuristicName}-${stepIndex}-${hIndex}`}
                      label={heuristicName}
                      sx={{ 
                        backgroundColor: getHeuristicColor(heuristicName),
                        color: '#000',
                        fontWeight: 500,
                        fontSize: '0.72rem',
                        px: 0.5,
                        height: '24px',
                        '& .MuiChip-label': { px: 1.5 }
                      }}
                      title={heuristicDescription}
                    />
                  );
                })}
              </Box>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
};

// Funkce pro přiřazení barvy podle typu heuristiky
const getHeuristicColor = (heuristicName: string): string => {
  // Kontrola na undefined alebo null hodnotu
  if (!heuristicName) {
    return 'rgba(189, 189, 189, 0.8)'; // šedá
  }
  
  switch (heuristicName.toLowerCase()) {
    case 'require_link':
      return 'rgba(144, 202, 249, 0.8)'; // modrá
    case 'forbid_link':
      return 'rgba(244, 67, 54, 0.7)'; // červená
    case 'drop_link':
      return 'rgba(255, 167, 38, 0.8)'; // oranžová
    case 'climb_tree':
      return 'rgba(102, 187, 106, 0.8)'; // zelená
    case 'enlarge_set':
      return 'rgba(186, 104, 200, 0.7)'; // fialová
    case 'close_interval':
      return 'rgba(255, 235, 59, 0.8)'; // žlutá
    case 'add_object':
      return 'rgba(0, 188, 212, 0.7)'; // tyrkysová
    case 'add_link':
      return 'rgba(0, 150, 136, 0.7)'; // teal
    case 'resolve_class_conflict':
      return 'rgba(121, 85, 72, 0.7)'; // hnedá
    case 'find_common_ancestor':
      return 'rgba(96, 125, 139, 0.7)'; // modrošedá
    case 'update_attribute':
      return 'rgba(233, 30, 99, 0.7)'; // ružová
    default:
      return 'rgba(189, 189, 189, 0.8)'; // šedá
  }
};

interface ExamplesTrainingViewProps {
  examples: Example[];
  trainingResult: TrainingResult | null;
  trainingSteps: Array<{
    step: string;
    description: string;
    example_name?: string;
    is_positive?: boolean;
    positive_example?: string;
    negative_example?: string;
    negative_examples?: string[];
    heuristics?: Array<{
      name: string;
      description: string;
      example_id?: number;
      details?: Record<string, any>;
    }>;
  }>;
  isLoading: boolean;
  onTrain: (retrainAll: boolean) => void;
  isTraining: boolean;
  isUpdatingModel: boolean;
  historyIndex: number;
  historyLength: number;
  onExampleSelect: (id: number, selected: boolean) => void;
  onSelectAll: (selected: boolean) => void;
  onStepBack: () => void;
  onStepForward: () => void;
  onReset: () => void;
  onFileUpload: () => void;
}

const ExamplesTrainingView: React.FC<ExamplesTrainingViewProps> = ({
  examples,
  trainingResult,
  trainingSteps,
  isLoading,
  onTrain,
  isTraining,
  isUpdatingModel,
  historyIndex,
  historyLength,
  onExampleSelect,
  onSelectAll,
  onStepBack,
  onStepForward,
  onReset,
  onFileUpload
}) => {
  const selectedExamplesCount = examples.filter(e => e.selected).length;
  const allSelected = examples.length > 0 && examples.every(e => e.selected);
  const usedInTrainingCount = examples.filter(e => e.usedInTraining).length;

  const handleExampleClick = (example: Example) => {
    onExampleSelect(example.id, !example.selected);
  };

  return (
    <Container maxWidth="xl" sx={{ mt: 3, mb: 4 }}>
      <Paper
        elevation={6}
        sx={{
          borderRadius: 2,
          overflow: 'hidden',
          height: '100%',
          boxShadow: '0 8px 32px rgba(0,0,0,0.15)',
          background: 'linear-gradient(145deg, rgba(18,18,18,1) 0%, rgba(30,30,30,1) 100%)',
          border: '1px solid rgba(255, 255, 255, 0.05)'
        }}
      >
        <Grid container>
          {/* EXAMPLES SECTION - LEFT SIDE */}
          <Grid item xs={12} md={8} 
            sx={{ 
              borderRight: { md: '1px solid rgba(255, 255, 255, 0.05)' },
              display: 'flex',
              flexDirection: 'column'
            }}
          >
            <Box sx={{ 
              p: 2, 
              display: 'flex', 
              alignItems: 'center',
              justifyContent: 'space-between',
              bgcolor: 'rgba(25, 118, 210, 0.08)',
              borderBottom: '1px solid rgba(255, 255, 255, 0.05)'
            }}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Typography variant="h6" component="h2" sx={{ fontWeight: 600, color: '#90caf9' }}>
                  Príklady
                </Typography>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={allSelected}
                      onChange={(e) => onSelectAll(e.target.checked)}
                      color="primary"
                      size="small"
                    />
                  }
                  label={
                    <Typography variant="body2" sx={{ ml: 0.5, color: 'rgba(255, 255, 255, 0.7)' }}>
                      Vybrať všetky
                    </Typography>
                  }
                  sx={{ ml: 2 }}
                />
              </Box>
              
              <Button
                variant="outlined"
                color="primary"
                onClick={onFileUpload}
                size="small"
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
                Nahrať dataset
              </Button>
            </Box>
          
            <Box sx={{ 
              p: 2,
              flexGrow: 1,
              overflowY: 'auto',
              height: examples.length === 0 ? '300px' : 'auto',
              minHeight: '300px',
              maxHeight: 'calc(100vh - 240px)',
              '&::-webkit-scrollbar': {
                width: '8px',
              },
              '&::-webkit-scrollbar-track': {
                background: 'rgba(255,255,255,0.03)',
                borderRadius: '4px',
              },
              '&::-webkit-scrollbar-thumb': {
                background: 'rgba(144, 202, 249, 0.2)',
                borderRadius: '4px',
                '&:hover': {
                  background: 'rgba(144, 202, 249, 0.4)',
                },
              }
            }}>
              {examples.length === 0 ? (
                <Box sx={{ 
                  display: 'flex', 
                  flexDirection: 'column', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  height: '100%',
                  p: 3,
                  textAlign: 'center',
                  border: '2px dashed rgba(144, 202, 249, 0.3)',
                  borderRadius: 2,
                  backgroundColor: 'rgba(144, 202, 249, 0.05)'
                }}>
                  <Typography variant="h6" sx={{ color: '#90caf9', mb: 2 }}>
                    Žiadne príklady na zobrazenie
                  </Typography>
                  <Typography variant="body2" sx={{ color: 'rgba(255, 255, 255, 0.7)', maxWidth: '400px', mb: 3 }}>
                    Nahrajte dataset s príkladmi pomocou tlačidla "Nahrať dataset" alebo pridajte nové príklady manuálne.
                  </Typography>
                  <Button
                    variant="outlined"
                    color="primary"
                    onClick={onFileUpload}
                    sx={{ 
                      borderRadius: 2,
                      textTransform: 'none',
                      borderColor: 'rgba(144, 202, 249, 0.5)',
                      color: '#90caf9',
                      px: 3,
                      py: 1,
                      '&:hover': {
                        borderColor: 'rgba(144, 202, 249, 0.8)',
                        backgroundColor: 'rgba(144, 202, 249, 0.08)'
                      }
                    }}
                  >
                    Nahrať dataset
                  </Button>
                </Box>
              ) : (
                <>
                  <Box 
                    sx={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      p: 1,
                      pt: 1.5,
                      pb: 1.5,
                      height: '40px',
                      borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                      color: 'rgba(255, 255, 255, 0.6)',
                      fontWeight: 500,
                      fontSize: '0.8rem',
                      position: 'sticky',
                      top: 0,
                      bgcolor: 'rgba(18,18,18,0.95)',
                      zIndex: 10,
                      mb: 1.5
                    }}
                  >
                    <Box sx={{ width: '28px', mr: 1 }}></Box>
                    <Box sx={{ flexGrow: 1, pl: 0.5 }}>PRÍKLADY</Box>
                  </Box>
                
                  <Grid container spacing={0} sx={{ mt: 0 }}>
                    {examples.map((example) => (
                      <Grid item xs={12} key={example.id}>
                        <Box 
                          sx={{
                            display: 'flex',
                            flexDirection: 'column',
                            p: 1.5,
                            mb: 1.5,
                            borderRadius: 1.5,
                            backgroundColor: 'transparent',
                            background: example.selected 
                              ? 'linear-gradient(145deg, rgba(25, 118, 210, 0.15) 0%, rgba(25, 118, 210, 0.05) 100%)'
                              : 'linear-gradient(145deg, rgba(30,30,30,0.6) 0%, rgba(18,18,18,0.6) 100%)',
                            border: example.selected 
                              ? '1px solid rgba(144, 202, 249, 0.5)' 
                              : '1px solid rgba(255, 255, 255, 0.05)',
                            boxShadow: example.selected 
                              ? '0 4px 8px rgba(25, 118, 210, 0.2)' 
                              : '0 2px 4px rgba(0,0,0,0.1)',
                            transition: 'all 0.2s ease',
                            '&:hover': {
                              boxShadow: '0 3px 10px rgba(0,0,0,0.2)',
                              borderColor: example.selected 
                                ? 'rgba(144, 202, 249, 0.8)'
                                : 'rgba(255, 255, 255, 0.1)',
                              cursor: 'pointer'
                            }
                          }}
                          onClick={() => handleExampleClick(example)}
                        >
                          {/* Prvý riadok: Názov a tag */}
                          <Box sx={{ 
                            display: 'flex', 
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            mb: 1
                          }}>
                            <Box sx={{ 
                              display: 'flex', 
                              alignItems: 'center', 
                              flexGrow: 1, 
                              maxWidth: 'calc(100% - 145px)',
                              overflow: 'hidden'
                            }}>
                              {/* Checkbox */}
                              <Checkbox
                                checked={example.selected}
                                size="small"
                                color="primary"
                                sx={{ 
                                  mr: 1, 
                                  p: 0.5,
                                  width: '28px',
                                  height: '28px',
                                  '& .MuiSvgIcon-root': {
                                    fontSize: '1.1rem'
                                  }
                                }}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleExampleClick(example);
                                }}
                              />
                              
                              {/* Name */}
                              <Typography 
                                variant="subtitle2" 
                                sx={{ 
                                  fontWeight: 600, 
                                  color: example.selected ? '#90caf9' : 'white',
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap'
                                }}
                                title={example.name}
                              >
                                {example.name}
                              </Typography>
                            </Box>
                            
                            {/* Tags */}
                            <Box sx={{ 
                              display: 'flex', 
                              ml: 1, 
                              flexShrink: 0, 
                              width: '140px',
                              justifyContent: 'flex-end'
                            }}>
                              <Box 
                                sx={{ 
                                  borderRadius: 1, 
                                  px: 1, 
                                  py: 0.3, 
                                  display: 'inline-block',
                                  bgcolor: example.isPositive ? 'rgba(102, 187, 106, 0.2)' : 'rgba(244, 67, 54, 0.2)',
                                  color: example.isPositive ? '#66bb6a' : '#f44336',
                                  fontSize: '0.7rem',
                                  fontWeight: 600,
                                  border: example.isPositive ? '1px solid rgba(102, 187, 106, 0.4)' : '1px solid rgba(244, 67, 54, 0.4)',
                                  width: '64px',
                                  textAlign: 'center'
                                }}
                              >
                                {example.isPositive ? 'Pozitívny' : 'Negatívny'}
                              </Box>
                              {example.usedInTraining && (
                                <Box 
                                  sx={{ 
                                    borderRadius: 1, 
                                    px: 1, 
                                    py: 0.3, 
                                    ml: 0.5,
                                    display: 'inline-block',
                                    bgcolor: 'rgba(144, 202, 249, 0.15)',
                                    color: '#90caf9',
                                    fontSize: '0.7rem',
                                    fontWeight: 600,
                                    border: '1px solid rgba(144, 202, 249, 0.3)',
                                    width: '52px',
                                    textAlign: 'center'
                                  }}
                                >
                                  Použitý
                                </Box>
                              )}
                            </Box>
                          </Box>
                          
                          {/* Druhý riadok: Formula */}
                          <Box 
                            sx={{ 
                              pl: 4,
                              pr: 1,
                              py: 0.5,
                              mt: 0.5,
                              bgcolor: 'rgba(0,0,0,0.15)',
                              borderRadius: 1,
                              border: '1px solid rgba(255, 255, 255, 0.03)',
                              maxHeight: '60px',
                              overflowY: 'auto',
                              '&::-webkit-scrollbar': {
                                width: '4px',
                                height: '4px'
                              },
                              '&::-webkit-scrollbar-track': {
                                background: 'transparent',
                              },
                              '&::-webkit-scrollbar-thumb': {
                                background: 'rgba(144, 202, 249, 0.2)',
                                borderRadius: '2px',
                              }
                            }}
                          >
                            <Typography 
                              variant="body2" 
                              sx={{ 
                                color: 'rgba(255, 255, 255, 0.8)',
                                textAlign: 'left',
                                fontFamily: 'monospace',
                                fontSize: '0.8rem',
                                lineHeight: 1.3,
                                overflowX: 'auto',
                                whiteSpace: 'pre-wrap',
                                wordBreak: 'break-all',
                                display: '-webkit-box',
                                WebkitLineClamp: 2,
                                WebkitBoxOrient: 'vertical',
                                overflow: 'hidden'
                              }}
                              title={example.formula}
                            >
                              {example.formula}
                            </Typography>
                          </Box>
                        </Box>
                      </Grid>
                    ))}
                  </Grid>
                </>
              )}
            </Box>
          </Grid>
        
          {/* CONTROL SECTION - RIGHT SIDE */}
          <Grid item xs={12} md={4} sx={{ display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ 
              p: 2,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              bgcolor: 'rgba(25, 118, 210, 0.08)',
              borderBottom: '1px solid rgba(255, 255, 255, 0.05)'
            }}>
              <Typography variant="h6" component="h2" sx={{ fontWeight: 600, color: '#90caf9' }}>
                Ovládanie modelu
              </Typography>
            </Box>
            
            <Box sx={{ p: 2 }}>
              <ModelControls 
                historyIndex={historyIndex} 
                historyLength={historyLength}
                onStepBack={onStepBack}
                onStepForward={onStepForward}
                onReset={onReset}
                isLoading={isUpdatingModel}
              />
            </Box>
            
            <Divider sx={{ my: 2, borderColor: 'rgba(255, 255, 255, 0.05)' }} />
            
            <Box sx={{ p: 2 }}>
              <TrainingPanel 
                selectedCount={selectedExamplesCount}
                totalCount={examples.length}
                onTrain={onTrain}
                isLoading={isTraining}
              />
              
              {trainingResult?.training_steps && trainingResult.training_steps.length > 0 && (
                <HeuristicsLog trainingSteps={trainingResult.training_steps} />
              )}
            </Box>
          </Grid>
          
          {/* TRAINING RESULT SECTION - FULL WIDTH */}
          {trainingResult && (
            <Grid item xs={12}>
              <Divider sx={{ borderColor: 'rgba(255, 255, 255, 0.05)' }} />
              <Box sx={{ 
                p: 3,
                background: 'linear-gradient(145deg, rgba(25, 118, 210, 0.12) 0%, rgba(25, 118, 210, 0.05) 100%)',
                borderTop: '1px solid rgba(255, 255, 255, 0.08)',
                boxShadow: 'inset 0 2px 10px rgba(0,0,0,0.1)'
              }}>
                <Typography variant="h6" component="h2" sx={{ 
                  fontWeight: 600, 
                  color: '#90caf9', 
                  mb: 3,
                  display: 'flex',
                  alignItems: 'center',
                  '&::after': {
                    content: '""',
                    height: '2px',
                    flexGrow: 1,
                    ml: 2,
                    background: 'linear-gradient(90deg, rgba(144, 202, 249, 0.5) 0%, rgba(144, 202, 249, 0) 100%)'
                  }
                }}>
                  Výsledok trénovania
                </Typography>
                <TrainingResultDisplay result={trainingResult} />
              </Box>
            </Grid>
          )}
        </Grid>
      </Paper>
    </Container>
  );
};

export default ExamplesTrainingView; 