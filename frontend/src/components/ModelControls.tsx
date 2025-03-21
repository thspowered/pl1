import { 
  Box, 
  Button,
  Tooltip 
} from '@mui/material';

interface ModelControlsProps {
  historyIndex: number;
  historyLength: number;
  isLoading: boolean;
  onStepBack: () => void;
  onStepForward: () => void;
  onReset: () => void;
}

const ModelControls = ({
  historyIndex,
  historyLength,
  isLoading,
  onStepBack,
  onStepForward,
  onReset
}: ModelControlsProps) => {
  return (
    <Box sx={{ display: 'flex', gap: 2 }}>
      <Tooltip title="Vymaže aktuálnu hypotézu a resetuje model">
        <span>
          <Button
            variant="outlined"
            color="error"
            onClick={onReset}
            disabled={isLoading || historyIndex < 0}
            startIcon={<span>🗑️</span>}
            size="small"
          >
            Vymazať hypotézu
          </Button>
        </span>
      </Tooltip>
      
      <Tooltip title="Vráti model o jeden krok späť">
        <span>
          <Button
            variant="outlined"
            color="primary"
            onClick={onStepBack}
            disabled={isLoading || historyIndex <= 0}
            startIcon={<span>⬅️</span>}
            size="small"
          >
            Krok späť
          </Button>
        </span>
      </Tooltip>
      
      <Tooltip title="Posunie model o jeden krok dopredu">
        <span>
          <Button
            variant="outlined"
            color="primary"
            onClick={onStepForward}
            disabled={isLoading || historyIndex >= historyLength - 1}
            startIcon={<span>➡️</span>}
            size="small"
          >
            Krok vpred
          </Button>
        </span>
      </Tooltip>
    </Box>
  );
};

export default ModelControls; 