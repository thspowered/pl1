import React from 'react';
import {
  Box,
  Typography,
  Paper,
  List,
  ListItem,
  Divider,
  Chip,
  Tooltip,
  alpha
} from '@mui/material';


interface Heuristic {
  name: string;
  description: string;
  example_id?: number;
  details?: Record<string, any>;
}

interface Example {
  id: number;
  name: string;
  formula: string;
  isPositive: boolean;
}

interface HeuristicsLogProps {
  examples: Example[];
  trainedExamples: Array<{
    id: number;
    heuristics: Heuristic[];
    isPositive: boolean;
  }>;
}

const heuristicColors: Record<string, string> = {
  'require_link': '#4caf50', // Green
  'forbid_link': '#f44336', // Red
  'drop_link': '#ff9800', // Orange
  'climb_tree': '#2196f3', // Blue
  'close_interval': '#9c27b0', // Purple
  'enlarge_set': '#00bcd4', // Cyan
  'add_object': '#607d8b', // Blue Grey
  'add_link': '#795548', // Brown
  'initialization': '#64b5f6' // Light Blue
};

const HeuristicsLog: React.FC<HeuristicsLogProps> = ({ examples, trainedExamples }) => {

  console.log('HeuristicsLog - examples:', examples);
  console.log('HeuristicsLog - trainedExamples:', trainedExamples);
  
  return (
    <Paper
      elevation={3}
      sx={{
        p: 2,
        borderRadius: 2,
        background: 'linear-gradient(145deg, rgba(25, 118, 210, 0.08) 0%, rgba(25, 118, 210, 0.03) 100%)',
        border: '1px solid rgba(25, 118, 210, 0.15)',
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
        maxHeight: '500px',
        overflow: 'hidden'
      }}
    >
      <Typography variant="h6" component="h3" sx={{ fontWeight: 600, color: '#90caf9' }}>
        Heuristiky a príklady
      </Typography>
      
      {trainedExamples.length === 0 ? (
        <Box sx={{ p: 2, textAlign: 'center', color: 'rgba(255, 255, 255, 0.5)' }}>
          <Typography variant="body2">
            Zatiaľ neboli použité žiadne príklady na trénovanie.
          </Typography>
        </Box>
      ) : (
        <Box sx={{ overflowY: 'auto', maxHeight: '430px', pr: 1 }}>
          <List disablePadding>
            {trainedExamples.map((trainedExample, index) => {

              const example = examples.find(e => e.id === trainedExample.id);
              
              return (
                <React.Fragment key={trainedExample.id}>
                  {index > 0 && <Divider sx={{ my: 1, borderColor: 'rgba(255, 255, 255, 0.08)' }} />}
                  
                  <ListItem 
                    sx={{ 
                      px: 2, 
                      py: 1.5, 
                      borderRadius: 1, 
                      bgcolor: trainedExample.isPositive 
                        ? alpha('#4caf50', 0.1) 
                        : alpha('#f44336', 0.1),
                      border: '1px solid',
                      borderColor: trainedExample.isPositive 
                        ? alpha('#4caf50', 0.3) 
                        : alpha('#f44336', 0.3),
                      mb: 1,
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'flex-start'
                    }}
                  >
                    <Box sx={{ display: 'flex', width: '100%', alignItems: 'center', mb: 1 }}>
                      <Chip 
                        label={trainedExample.isPositive ? "Pozitívny" : "Negatívny"} 
                        size="small"
                        color={trainedExample.isPositive ? "success" : "error"}
                        sx={{ 
                          mr: 1,
                          height: '20px',
                          '& .MuiChip-label': { px: 1, py: 0, fontSize: '0.7rem' }
                        }}
                      />
                      <Typography 
                        variant="subtitle2"
                        sx={{ 
                          fontWeight: 600, 
                          color: trainedExample.isPositive ? '#81c784' : '#e57373'
                        }}
                      >
                        Príklad {trainedExample.id}: {example?.name || `Príklad ${trainedExample.id}`}
                      </Typography>
                    </Box>
                    
                    {trainedExample.heuristics.length > 0 ? (
                      <Box sx={{ pl: 1 }}>
                        <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.5)', mb: 0.5, display: 'block' }}>
                          Aplikované heuristiky:
                        </Typography>
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                          {trainedExample.heuristics.map((heuristic, idx) => (
                            <Tooltip 
                              key={idx} 
                              title={heuristic.description || heuristic.name}
                              arrow
                            >
                              <Chip
                                label={heuristic.name.replace('_', '-').toUpperCase()}
                                size="small"
                                sx={{
                                  bgcolor: heuristicColors[heuristic.name] || '#757575',
                                  color: 'white',
                                  fontWeight: 500,
                                  fontSize: '0.7rem',
                                  height: '20px',
                                  '& .MuiChip-label': { px: 1, py: 0 }
                                }}
                              />
                            </Tooltip>
                          ))}
                        </Box>
                      </Box>
                    ) : (
                      <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.5)', pl: 1 }}>
                        Žiadne heuristiky neboli aplikované
                      </Typography>
                    )}
                  </ListItem>
                </React.Fragment>
              );
            })}
          </List>
        </Box>
      )}
    </Paper>
  );
};

export default HeuristicsLog; 