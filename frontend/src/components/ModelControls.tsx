import React from "react";
import { Box, Button, Tooltip, Typography, Badge } from "@mui/material";
import { ChevronLeft, ChevronRight, RestartAlt } from "@mui/icons-material";
import { CircularProgress } from "@mui/material";

export interface ModelControlsProps {
  historyIndex: number;
  historyLength: number;
  isLoading: boolean;
  onStepBack: () => void;
  onStepForward: () => void;
  onReset: () => void;
}

export const ModelControls: React.FC<ModelControlsProps> = ({
  historyIndex,
  historyLength,
  isLoading,
  onStepBack,
  onStepForward,
  onReset,
}) => {
  const canStepBack = historyIndex > 0;
  const canStepForward = historyIndex < historyLength - 1;
  
  // Vypočítame aktuálnu pozíciu a celkový počet krokov
  const currentPosition = historyLength > 0 ? historyIndex + 1 : 0;
  const totalSteps = historyLength || 0;

  return (
    <Box
      sx={{
        display: "flex",
        gap: 1,
        alignItems: "center",
        justifyContent: "flex-end",
        backgroundColor: "transparent",
      }}
    >
      <Typography 
        variant="body2" 
        sx={{ 
          mr: 1, 
          color: 'text.secondary',
          fontSize: '0.875rem'
        }}
      >
        História: {currentPosition}/{totalSteps}
      </Typography>
    
      <Tooltip title={canStepBack ? `Krok späť (${historyIndex}/${historyLength})` : "Žiadna predchádzajúca história modelu"}>
        <span>
          <Button
            variant="outlined"
            size="small"
            disabled={!canStepBack || isLoading}
            onClick={onStepBack}
            sx={{
              minWidth: "40px",
              height: "40px",
              borderRadius: "8px",
              borderColor: "primary.main",
              color: "primary.main",
              "&:hover": {
                borderColor: "primary.dark",
                backgroundColor: "rgba(63, 81, 181, 0.08)",
              },
              "&.Mui-disabled": {
                borderColor: "action.disabledBackground",
                color: "text.disabled",
              },
            }}
          >
            <ChevronLeft />
          </Button>
        </span>
      </Tooltip>

      <Tooltip title={canStepForward ? `Krok vpred (${historyIndex + 2}/${historyLength})` : "Žiadna nasledujúca história modelu"}>
        <span>
          <Button
            variant="outlined"
            size="small"
            disabled={!canStepForward || isLoading}
            onClick={onStepForward}
            sx={{
              minWidth: "40px",
              height: "40px",
              borderRadius: "8px",
              borderColor: "primary.main",
              color: "primary.main",
              "&:hover": {
                borderColor: "primary.dark",
                backgroundColor: "rgba(63, 81, 181, 0.08)",
              },
              "&.Mui-disabled": {
                borderColor: "action.disabledBackground",
                color: "text.disabled",
              },
            }}
          >
            <ChevronRight />
          </Button>
        </span>
      </Tooltip>

      <Tooltip 
        title="Resetovať model, históriu a príklady. Táto akcia vymaže všetky trénovacie kroky a obnoví príklady do stavu, v ktorom ich bude možné znova použiť na trénovanie."
      >
        <Button
          variant="outlined"
          size="small"
          color="error"
          disabled={isLoading}
          onClick={onReset}
          sx={{
            minWidth: "40px",
            height: "40px",
            borderRadius: "8px",
            borderColor: "error.main",
            color: "error.main",
            "&:hover": {
              borderColor: "error.dark",
              backgroundColor: "rgba(211, 47, 47, 0.08)",
            },
            "&.Mui-disabled": {
              borderColor: "action.disabledBackground",
              color: "text.disabled",
            },
          }}
        >
          {isLoading ? <CircularProgress size={20} color="error" /> : <RestartAlt />}
        </Button>
      </Tooltip>
    </Box>
  );
}; 