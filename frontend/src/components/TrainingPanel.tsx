import { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  CircularProgress,
  Paper,
  Switch,
  Tooltip
} from '@mui/material';

interface TrainingPanelProps {
  isTraining: boolean;
  onTrain: (retrainAll: boolean) => void;
  selectedExamplesCount: number;
  usedInTrainingCount: number;
}

const TrainingPanel = ({
  isTraining,
  onTrain,
  selectedExamplesCount,
  usedInTrainingCount
}: TrainingPanelProps) => {
  const [retrainAll, setRetrainAll] = useState<boolean>(false);

  const handleTrainClick = () => {
    onTrain(retrainAll);
  };

  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Trénovanie modelu
      </Typography>
      
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <Typography variant="body2">Inkrementálne dotrénovanie</Typography>
        <Tooltip title={
          retrainAll 
            ? "Model sa natrénuje od začiatku na všetkých príkladoch (pôvodných + nových)" 
            : "Model sa dotrénuje len na nových príkladoch"
        }>
          <Switch
            checked={retrainAll}
            onChange={(e) => setRetrainAll(e.target.checked)}
            color="primary"
          />
        </Tooltip>
        <Typography variant="body2">Úplné pretrénovanie</Typography>
      </Box>
      
      <Button
        variant="contained"
        color="primary"
        onClick={handleTrainClick}
        disabled={isTraining || selectedExamplesCount === 0}
        startIcon={isTraining ? <CircularProgress size={20} color="inherit" /> : null}
      >
        {isTraining 
          ? 'Trénujem...' 
          : retrainAll 
            ? 'Pretrénovať model od začiatku' 
            : 'Dotrénovať model'
        }
      </Button>

      {usedInTrainingCount > 0 && (
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block', textAlign: 'center' }}>
          ({usedInTrainingCount} príkladov už bolo použitých v trénovaní)
        </Typography>
      )}
    </Paper>
  );
};

export default TrainingPanel; 