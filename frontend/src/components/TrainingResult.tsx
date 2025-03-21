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
  Chip
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { TrainingResult as TrainingResultType } from '../types';
import SigmaNetwork from './SigmaNetwork';

interface TrainingResultProps {
  result: TrainingResultType | null;
  onRefreshGraph: () => void;
}

const TrainingResultDisplay = ({ result, onRefreshGraph }: TrainingResultProps) => {
  if (!result) return null;

  return (
    <>
      <Paper sx={{ p: 2, mt: 3, bgcolor: result.success ? 'success.dark' : 'error.dark' }}>
        <Typography variant="h6" gutterBottom>
          {result.success ? 'Trénovanie úspešné' : 'Chyba trénovania'}
        </Typography>
        <Typography variant="body1">{result.message}</Typography>
        
        {result.success && (
          <Box sx={{ mt: 1 }}>
            <Typography variant="body2" sx={{ mt: 1 }}>
              Použitých {result.used_examples_count || 0} z {result.total_examples_count || 0} príkladov
            </Typography>
            <Typography variant="body2" sx={{ mt: 1 }}>
              Režim trénovania: {result.training_mode === 'retrained' ? 'Úplné pretrénovanie' : 'Inkrementálne dotrénovanie'}
            </Typography>
          </Box>
        )}
      </Paper>
      
      {result.training_steps && result.training_steps.length > 0 && (
        <Box sx={{ mt: 4, mb: 4 }}>
          <Typography variant="h6" gutterBottom>
            Kroky trénovania
          </Typography>
          <Stepper orientation="vertical">
            {result.training_steps.map((step, index) => (
              <Step key={index} active={true} completed={true}>
                <StepLabel>
                  {step.step === 'initialize' && 'Inicializácia modelu'}
                  {step.step === 'update' && 'Aktualizácia modelu'}
                  {step.step === 'update_multi' && 'Hromadná aktualizácia modelu'}
                  {step.step === 'error' && 'Chyba pri trénovaní'}
                </StepLabel>
                <StepContent>
                  <Typography variant="body1">{step.description}</Typography>
                  
                  {/* Zobrazenie detailov o použitých príkladoch */}
                  {step.example_name && (
                    <Box sx={{ mt: 1, mb: 1 }}>
                      <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                        Použitý príklad: {step.example_name} ({step.is_positive ? 'pozitívny' : 'negatívny'})
                      </Typography>
                    </Box>
                  )}
                  
                  {step.negative_examples && step.negative_examples.length > 0 && (
                    <Box sx={{ mt: 1, mb: 1 }}>
                      <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                        Negatívne príklady:
                      </Typography>
                      <ul style={{ margin: '4px 0', paddingLeft: '20px' }}>
                        {step.negative_examples.map((name, i) => (
                          <li key={i}>
                            <Typography variant="body2">{name}</Typography>
                          </li>
                        ))}
                      </ul>
                    </Box>
                  )}
                  
                  {/* Zobrazenie použitých heuristík */}
                  {step.heuristics && step.heuristics.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'info.main' }}>
                        Použité heuristiky, ktoré vykonali zmeny v modeli:
                      </Typography>
                      <Accordion sx={{ mt: 1, bgcolor: 'background.paper' }}>
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Typography variant="body2">
                            {step.heuristics.length} aplikovaných heuristík v tomto kroku
                          </Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          <List dense>
                            {step.heuristics.map((heuristic, hIndex) => (
                              <ListItem key={hIndex} sx={{ mb: 1, flexDirection: 'column', alignItems: 'flex-start' }}>
                                <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'info.main' }}>
                                  {heuristic.description}
                                </Typography>
                                {heuristic.details && (
                                  <Box sx={{ mt: 0.5, ml: 2 }}>
                                    <Typography variant="caption" component="div" sx={{ color: 'text.secondary' }}>
                                      Spracované objekty: {heuristic.details.good_objects} (pozitívny príklad) 
                                      {heuristic.details.near_miss_objects !== undefined && `, ${heuristic.details.near_miss_objects} (negatívny príklad)`}
                                    </Typography>
                                    {heuristic.details.changes_made && (
                                      <Typography variant="caption" component="div" sx={{ color: 'success.main' }}>
                                        Pridaných spojení: {heuristic.details.changes_made}
                                      </Typography>
                                    )}
                                    {heuristic.details.links_removed && (
                                      <Typography variant="caption" component="div" sx={{ color: 'success.main' }}>
                                        Odstránených spojení: {heuristic.details.links_removed}
                                      </Typography>
                                    )}
                                  </Box>
                                )}
                              </ListItem>
                            ))}
                          </List>
                        </AccordionDetails>
                      </Accordion>
                    </Box>
                  )}
                </StepContent>
              </Step>
            ))}
          </Stepper>
        </Box>
      )}
      
      {result.model_hypothesis && (
        <Accordion sx={{ mt: 3 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">
              Naučená hypotéza modelu
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Box sx={{ p: 2, backgroundColor: '#112', borderRadius: 1, overflow: 'auto' }}>
              <Typography 
                variant="body2" 
                component="pre" 
                sx={{ 
                  whiteSpace: 'pre-wrap', 
                  fontFamily: 'monospace',
                  fontSize: '0.85rem',
                  color: '#66f'
                }}
              >
                {result.model_hypothesis}
              </Typography>
            </Box>
            <Typography variant="body2" sx={{ mt: 2, color: 'text.secondary' }}>
              Toto je formálny zápis odvodenej hypotézy. Vyjadruje, čo sa model naučil o koncepte na základe poskytnutých príkladov.
            </Typography>
          </AccordionDetails>
        </Accordion>
      )}
      
      {result.model_visualization && (
        <Accordion sx={{ mt: 3 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">
              Vizualizácia naučeného modelu
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Typography variant="body2" gutterBottom>
              Model obsahuje {result.model_visualization.nodes.length} objektov a {result.model_visualization.links.length} spojení.
            </Typography>
            
            <Typography variant="subtitle1" sx={{ mt: 2, mb: 1 }}>
              Objekty:
            </Typography>
            <List dense>
              {result.model_visualization.nodes.map((node, index) => (
                <li key={index}>
                  <Chip 
                    label={`${node.name} (${node.class})`} 
                    color={node.category === 'attribute' ? 'secondary' : 'primary'} 
                    size="small"
                    sx={{ m: 0.5 }}
                  />
                </li>
              ))}
            </List>
            
            <Typography variant="subtitle1" sx={{ mt: 2, mb: 1 }}>
              Spojenia:
            </Typography>
            <List dense>
              {result.model_visualization.links.map((link, index) => (
                <li key={index}>
                  <Chip 
                    label={`${link.source} → ${link.target} (${link.type})`} 
                    variant="outlined"
                    size="small"
                    sx={{ m: 0.5 }}
                  />
                </li>
              ))}
            </List>
            
            <Box sx={{ mt: 4, mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6">
                Sémantická sieť modelu
              </Typography>
              <Box>
                <button 
                  onClick={onRefreshGraph}
                  style={{
                    background: 'transparent',
                    border: '1px solid #90caf9',
                    borderRadius: '4px',
                    padding: '6px 12px',
                    color: '#90caf9',
                    cursor: 'pointer',
                    fontSize: '0.875rem',
                    textTransform: 'uppercase',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}
                >
                  <span style={{ fontSize: '1rem' }}>🔄</span>
                  Obnoviť graf
                </button>
              </Box>
            </Box>
            
            <Box sx={{ mt: 2, border: '1px solid #333', borderRadius: '8px', overflow: 'hidden' }}>
              {result.model_visualization.nodes.length > 0 ? (
                <Box sx={{ position: 'relative' }}>
                  <SigmaNetwork 
                    key={`graph-${Date.now()}`}
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
                </Box>
              ) : (
                <Box 
                  sx={{ 
                    height: '200px', 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center',
                    backgroundColor: '#1e1e1e'
                  }}
                >
                  <Typography color="text.secondary">
                    Prázdna sémantická sieť - nie sú k dispozícii žiadne uzly pre vizualizáciu.
                  </Typography>
                </Box>
              )}
            </Box>
          </AccordionDetails>
        </Accordion>
      )}
    </>
  );
};

export default TrainingResultDisplay; 