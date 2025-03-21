import { useState } from 'react';
import {
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemButton,
  Checkbox,
  Typography,
  Paper,
  Box,
  Chip,
  Tooltip,
  FormControlLabel,
  Switch
} from '@mui/material';
import { Example } from '../types';

interface ExampleListProps {
  examples: Example[];
  onExampleSelect: (id: number) => void;
  onSelectAll: (selected: boolean) => void;
}

const ExampleList = ({ examples, onExampleSelect, onSelectAll }: ExampleListProps) => {
  const [showUsedExamples, setShowUsedExamples] = useState(true);
  
  const filteredExamples = examples.filter(ex => showUsedExamples || !ex.usedInTraining);
  
  const handleToggleShowUsed = () => {
    setShowUsedExamples(!showUsedExamples);
  };
  
  const selectedCount = examples.filter(ex => ex.selected).length;
  const newSelectedCount = examples.filter(ex => ex.selected && !ex.usedInTraining).length;
  const usedSelectedCount = selectedCount - newSelectedCount;
  
  const allSelected = examples.length > 0 && examples.every(ex => ex.selected);
  
  return (
    <Paper sx={{ p: 2, mt: 2, bgcolor: 'rgba(30, 30, 30, 0.6)' }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
        <Typography variant="h6">
          Príklady ({examples.length})
        </Typography>
        
        <Box display="flex" alignItems="center">
          <FormControlLabel
            control={
              <Switch
                checked={showUsedExamples}
                onChange={handleToggleShowUsed}
                size="small"
              />
            }
            label="Zobrazovať použité"
          />
          
          <FormControlLabel
            control={
              <Checkbox
                checked={allSelected}
                onChange={(e) => onSelectAll(e.target.checked)}
                indeterminate={selectedCount > 0 && selectedCount < examples.length}
                size="small"
              />
            }
            label="Vybrať všetky"
          />
        </Box>
      </Box>
      
      {selectedCount > 0 && (
        <Box mb={2}>
          <Typography variant="body2">
            Vybrané: {selectedCount} príkladov
            {newSelectedCount > 0 && (
              <Chip 
                size="small" 
                label={`${newSelectedCount} nových`} 
                color="primary" 
                sx={{ ml: 1, mr: 1 }}
              />
            )}
            {usedSelectedCount > 0 && (
              <Chip 
                size="small" 
                label={`${usedSelectedCount} použitých`} 
                color="secondary" 
                sx={{ ml: usedSelectedCount && !newSelectedCount ? 1 : 0 }}
              />
            )}
          </Typography>
        </Box>
      )}
      
      {filteredExamples.length === 0 ? (
        <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>
          Žiadne príklady na zobrazenie
        </Typography>
      ) : (
        <List sx={{ 
          maxHeight: '400px', 
          overflow: 'auto',
          bgcolor: 'rgba(20, 20, 20, 0.3)',
          borderRadius: 1,
          '&::-webkit-scrollbar': {
            width: '8px',
          },
          '&::-webkit-scrollbar-track': {
            background: 'rgba(0, 0, 0, 0.1)',
          },
          '&::-webkit-scrollbar-thumb': {
            background: 'rgba(255, 255, 255, 0.2)',
            borderRadius: '4px',
          }
        }}>
          {filteredExamples.map((example) => (
            <ListItem 
              key={example.id}
              disablePadding
              sx={{ 
                borderLeft: '3px solid',
                borderLeftColor: example.isPositive ? 'success.main' : 'error.main',
                mb: 0.5
              }}
            >
              <ListItemButton
                onClick={() => onExampleSelect(example.id)}
                sx={{ 
                  bgcolor: example.selected ? 'rgba(90, 120, 190, 0.2)' : 'transparent',
                  '&:hover': {
                    bgcolor: 'rgba(90, 120, 190, 0.1)'
                  }
                }}
              >
                <ListItemIcon>
                  <Checkbox
                    edge="start"
                    checked={example.selected}
                    tabIndex={-1}
                    disableRipple
                  />
                </ListItemIcon>
                
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center">
                      <Typography variant="body1" noWrap sx={{ mr: 1 }}>
                        {example.name}
                      </Typography>
                      
                      {example.usedInTraining && (
                        <Tooltip title="Tento príklad už bol použitý na trénovanie">
                          <Chip 
                            size="small" 
                            label="Použité" 
                            color="secondary" 
                            variant="outlined"
                            sx={{ height: 20, fontSize: '0.6rem' }}
                          />
                        </Tooltip>
                      )}
                    </Box>
                  }
                  secondary={
                    <Tooltip title={example.formula}>
                      <Typography 
                        variant="body2" 
                        color="text.secondary" 
                        noWrap
                        sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}
                      >
                        {example.formula.substring(0, 70)}{example.formula.length > 70 ? '...' : ''}
                      </Typography>
                    </Tooltip>
                  }
                />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      )}
    </Paper>
  );
};

export default ExampleList; 