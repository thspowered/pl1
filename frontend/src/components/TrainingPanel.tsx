import { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  CircularProgress,
  Paper
} from '@mui/material';

interface TrainingPanelProps {
  selectedCount: number;
  totalCount: number;
  onTrain: (retrainAll: boolean) => void;
  isLoading: boolean;
}

const TrainingPanel = ({
  selectedCount,
  totalCount,
  onTrain,
  isLoading
}: TrainingPanelProps) => {
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
        gap: 2
      }}
    >
      <Typography variant="h6" component="h3" sx={{ fontWeight: 600, color: '#90caf9' }}>
        Trénovanie
      </Typography>
      
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, flexGrow: 1 }}>
        <Typography variant="body2" sx={{ color: 'rgba(255, 255, 255, 0.7)' }}>
          Vybrané príklady: {selectedCount} z {totalCount}
        </Typography>
        
        <Typography variant="body2" sx={{ color: 'rgba(255, 255, 255, 0.7)', mb: 1 }}>
          Trénovanie bude vykonané inkrementálne - aktuálna hypotéza bude upravená len pomocou vybraných príkladov.
        </Typography>
        
        <Box sx={{ mt: 2 }}>
          <Button
            variant="contained"
            color="primary"
            fullWidth
            onClick={() => onTrain(false)}
            disabled={isLoading || selectedCount === 0}
            startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : null}
            sx={{
              py: 1.5,
              boxShadow: '0 4px 10px rgba(25, 118, 210, 0.3)',
              fontWeight: 600,
              borderRadius: 2,
              textTransform: 'none',
              '&:hover': {
                boxShadow: '0 6px 12px rgba(25, 118, 210, 0.4)',
              }
            }}
          >
            {isLoading ? 'Trénovanie...' : 'Trénovať model'}
            <Box 
              component="span" 
              sx={{ ml: 1, color: 'rgba(255,255,255,0.7)', fontSize: '0.75rem' }}
            >
              ({selectedCount})
            </Box>
          </Button>
        </Box>
        
        <Box sx={{ 
          display: 'flex', 
          justifyContent: 'space-around',
          mt: 2,
          pt: 2,
          borderTop: '1px solid rgba(255, 255, 255, 0.08)'
        }}>
          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="body2" color="rgba(255, 255, 255, 0.6)" gutterBottom>
              Celkom príkladov
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 700, color: 'rgba(255, 255, 255, 0.9)' }}>
              {totalCount}
            </Typography>
          </Box>
          
          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="body2" color="rgba(255, 255, 255, 0.6)" gutterBottom>
              Vybraných
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 700, color: '#90caf9' }}>
              {selectedCount}
            </Typography>
          </Box>
        </Box>
      </Box>
    </Paper>
  );
};

export default TrainingPanel; 