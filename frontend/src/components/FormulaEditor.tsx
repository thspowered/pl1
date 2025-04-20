import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Chip,
  Tooltip,
  IconButton,
  Button,
  InputAdornment,
  Popper,
  Fade,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  Divider,
  alpha
} from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';
import FormatQuoteIcon from '@mui/icons-material/FormatQuote';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CodeIcon from '@mui/icons-material/Code';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';

interface FormulaEditorProps {
  value: string;
  onChange: (value: string) => void;
  onValidate?: () => void;
  validateAttributes?: boolean;
  onValidateAttributesChange?: (checked: boolean) => void;
  placeholder?: string;
  height?: string | number;
  label?: string;
  title?: string;
  subtitle?: string;
}

// Symbols used in PL1 formulas
const SYMBOLS = {
  IS_A: 'Ι',
  HAS_PART: 'Π',
  HAS_ATTRIBUTE: 'Α',
  AND: '∧',
  OR: '∨',
  NOT: '¬',
  IMPLIES: '→',
  EXISTS: '∃',
  FOR_ALL: '∀',
  ELEMENT_OF: '∈',
  EQUALS: '='
};

// Example templates that can be inserted
const EXAMPLES = [
  {
    name: 'BMW X5 s diesel motorom',
    formula: 'Ι(c1, X5) ∧ Π(c1, e1) ∧ Ι(e1, DieselEngine) ∧ Α(e1, power, 265)'
  },
  {
    name: 'BMW X5 s benzínovým motorom',
    formula: 'Ι(c1, X5) ∧ Π(c1, e1) ∧ Ι(e1, PetrolEngine) ∧ Α(e1, power, 340) ∧ Α(e1, cylinders, 8)'
  },
  {
    name: 'BMW X5 s automatickou prevodovkou',
    formula: 'Ι(c1, X5) ∧ Π(c1, e1) ∧ Ι(e1, Engine) ∧ Π(c1, t1) ∧ Ι(t1, AutomaticTransmission)'
  }
];

// Suggestions for auto-completion
const SUGGESTIONS = [
  { text: 'Ι(x, X5)', description: 'x je model X5' },
  { text: 'Π(c, e)', description: 'c má komponent e' },
  { text: 'Ι(e, DieselEngine)', description: 'e je dieselový motor' },
  { text: 'Ι(e, PetrolEngine)', description: 'e je benzínový motor' },
  { text: 'Ι(t, AutomaticTransmission)', description: 't je automatická prevodovka' },
  { text: 'Ι(t, ManualTransmission)', description: 't je manuálna prevodovka' },
  { text: 'Α(e, power, 265)', description: 'e má výkon 265' },
  { text: 'Α(e, torque, 450)', description: 'e má krútiaci moment 450' },
  { text: 'Α(e, cylinders, 6)', description: 'e má 6 valcov' },
];

// Helper components
const SymbolButton: React.FC<{
  symbol: string;
  label: string;
  onClick: (symbol: string) => void;
}> = ({ symbol, label, onClick }) => (
  <Tooltip title={label} arrow>
    <Chip
      label={symbol}
      onClick={() => onClick(symbol)}
      sx={{
        fontFamily: 'monospace',
        fontSize: '1rem',
        fontWeight: 'bold',
        m: 0.5,
        cursor: 'pointer',
        bgcolor: 'rgba(30, 41, 59, 0.8)',
        color: '#90caf9',
        borderColor: 'rgba(144, 202, 249, 0.2)',
        '&:hover': {
          bgcolor: 'rgba(144, 202, 249, 0.2)',
        }
      }}
      variant="outlined"
    />
  </Tooltip>
);

// Main component
const FormulaEditor: React.FC<FormulaEditorProps> = ({
  value,
  onChange,
  onValidate,
  validateAttributes = true,
  onValidateAttributesChange,
  placeholder = 'Zadajte PL1 formulu príkladu...',
  height = '200px',
  label = 'PL1 Formula príkladu',
  title = 'PL1 Formula príkladu',
  subtitle
}) => {
  const [cursorPosition, setCursorPosition] = useState<number | null>(null);
  const [showSuggestions, setShowSuggestions] = useState<boolean>(false);
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const editorRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  
  // Insert a symbol at the current cursor position
  const insertSymbol = useCallback((symbol: string) => {
    if (inputRef.current) {
      const input = inputRef.current;
      const start = input.selectionStart || 0;
      const end = input.selectionEnd || 0;
      
      const newValue = value.substring(0, start) + symbol + value.substring(end);
      onChange(newValue);
      
      // Set the cursor position after the inserted symbol
      setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.focus();
          inputRef.current.setSelectionRange(start + symbol.length, start + symbol.length);
        }
      }, 10);
    }
  }, [value, onChange]);
  
  // Insert an example formula
  const insertExample = useCallback((formula: string) => {
    onChange(formula);
    setShowSuggestions(false);
  }, [onChange]);
  
  // Insert a suggestion
  const insertSuggestion = useCallback((suggestion: string) => {
    insertSymbol(suggestion);
    setShowSuggestions(false);
  }, [insertSymbol]);
  
  // Handle the change in the text field
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(e.target.value);
  };
  
  // Handle key down events in the text field
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setShowSuggestions(false);
    } else if (e.ctrlKey && e.key === ' ') {
      e.preventDefault();
      if (inputRef.current) {
        setAnchorEl(inputRef.current);
        setShowSuggestions(true);
      }
    }
  };
  
  // Show suggestions button click handler
  const handleShowSuggestions = () => {
    if (inputRef.current) {
      setAnchorEl(inputRef.current);
      setShowSuggestions(!showSuggestions);
    }
  };
  
  // Format the formula with syntax highlighting
  const getFormattedFormula = () => {
    if (!value) return null;
    
    const parts = [];
    let currentText = '';
    let index = 0;
    
    // Helper function to add the current text to parts
    const addCurrentText = () => {
      if (currentText) {
        parts.push(<span key={`text-${index}`}>{currentText}</span>);
        currentText = '';
        index++;
      }
    };
    
    // Process the formula character by character
    for (let i = 0; i < value.length; i++) {
      const char = value[i];
      
      if (char === SYMBOLS.IS_A || char === 'I') {
        addCurrentText();
        parts.push(<span key={`is-a-${index}`} style={{ color: '#90caf9', fontWeight: 'bold' }}>{char}</span>);
        index++;
      } else if (char === SYMBOLS.HAS_PART || char === 'Π') {
        addCurrentText();
        parts.push(<span key={`has-part-${index}`} style={{ color: '#8a2be2', fontWeight: 'bold' }}>{char}</span>);
        index++;
      } else if (char === SYMBOLS.HAS_ATTRIBUTE || char === 'A') {
        addCurrentText();
        parts.push(<span key={`has-attr-${index}`} style={{ color: '#9370db', fontWeight: 'bold' }}>{char}</span>);
        index++;
      } else if (char === SYMBOLS.AND || char === '∧') {
        addCurrentText();
        parts.push(<span key={`and-${index}`} style={{ color: '#64b5f6', fontWeight: 'bold' }}>{char}</span>);
        index++;
      } else if (char === SYMBOLS.OR || char === '∨') {
        addCurrentText();
        parts.push(<span key={`or-${index}`} style={{ color: '#ffb74d', fontWeight: 'bold' }}>{char}</span>);
        index++;
      } else if (char === SYMBOLS.NOT || char === '¬') {
        addCurrentText();
        parts.push(<span key={`not-${index}`} style={{ color: '#ef5350', fontWeight: 'bold' }}>{char}</span>);
        index++;
      } else if (char === '(' || char === ')') {
        addCurrentText();
        parts.push(<span key={`paren-${index}`} style={{ color: '#9e9e9e' }}>{char}</span>);
        index++;
      } else if (char === ',') {
        addCurrentText();
        parts.push(<span key={`comma-${index}`} style={{ color: '#9e9e9e' }}>{char}</span>);
        index++;
      } else {
        currentText += char;
      }
    }
    
    // Add any remaining text
    addCurrentText();
    
    return <>{parts}</>;
  };
  
  return (
    <Paper
      elevation={0}
      sx={{
        borderRadius: 2,
        overflow: 'hidden',
        background: 'linear-gradient(145deg, rgba(30, 41, 59, 0.8) 0%, rgba(17, 24, 39, 0.8) 100%)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        boxShadow: '0 4px 15px rgba(0, 0, 0, 0.3)',
        position: 'relative'
      }}
    >
      <Box
        sx={{
          p: 2,
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'rgba(0, 0, 0, 0.2)'
        }}
      >
        <Box>
          <Typography
            variant="subtitle1"
            sx={{
              fontWeight: 600,
              color: '#90caf9',
              display: 'flex',
              alignItems: 'center',
              gap: 1
            }}
          >
            <CodeIcon fontSize="small" />
            {title}
          </Typography>
          {subtitle && (
            <Typography variant="caption" sx={{ color: 'text.secondary', mt: 0.5 }}>
              {subtitle}
            </Typography>
          )}
        </Box>
        
        <Box>
          <Tooltip title="Zobraziť príklady a tipy" arrow>
            <IconButton onClick={handleShowSuggestions} size="small" sx={{ color: '#90caf9' }}>
              <AutoFixHighIcon />
            </IconButton>
          </Tooltip>
          {onValidate && (
            <Button
              variant="contained"
              size="small"
              startIcon={<CheckCircleIcon />}
              onClick={onValidate}
              sx={{
                ml: 1,
                textTransform: 'none',
                background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
                boxShadow: '0 3px 10px rgba(33, 150, 243, 0.3)',
                '&:hover': {
                  boxShadow: '0 5px 15px rgba(33, 150, 243, 0.4)',
                }
              }}
            >
              Validovať
            </Button>
          )}
        </Box>
      </Box>
      
      <Box sx={{ p: 2 }}>
        <Box
          sx={{
            mb: 2,
            p: 1.5,
            borderRadius: 1,
            bgcolor: 'rgba(144, 202, 249, 0.08)',
            border: '1px solid rgba(144, 202, 249, 0.2)',
            display: 'flex',
            alignItems: 'center',
            gap: 1
          }}
        >
          <InfoIcon sx={{ color: '#90caf9', fontSize: '1.2rem' }} />
          <Typography variant="body2" sx={{ color: 'rgba(255, 255, 255, 0.7)', fontSize: '0.9rem' }}>
            Používajte správne Unicode symboly: <b>Ι</b> (is_a), <b>Π</b> (has_part), <b>Α</b> (has_attribute), <b>∧</b> (and)
          </Typography>
        </Box>
        
        <Box sx={{ mb: 2, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
          <SymbolButton symbol={SYMBOLS.IS_A} label="is_a" onClick={insertSymbol} />
          <SymbolButton symbol={SYMBOLS.HAS_PART} label="has_part" onClick={insertSymbol} />
          <SymbolButton symbol={SYMBOLS.HAS_ATTRIBUTE} label="has_attribute" onClick={insertSymbol} />
          <SymbolButton symbol={SYMBOLS.AND} label="and" onClick={insertSymbol} />
          <SymbolButton symbol={SYMBOLS.OR} label="or" onClick={insertSymbol} />
          <SymbolButton symbol={SYMBOLS.NOT} label="not" onClick={insertSymbol} />
          <SymbolButton symbol={SYMBOLS.FOR_ALL} label="for all" onClick={insertSymbol} />
          <SymbolButton symbol={SYMBOLS.EXISTS} label="exists" onClick={insertSymbol} />
        </Box>
        
        <Box
          ref={editorRef}
          sx={{
            position: 'relative',
            width: '100%'
          }}
        >
          <TextField
            inputRef={inputRef}
            multiline
            fullWidth
            variant="outlined"
            placeholder={placeholder}
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            rows={5}
            InputProps={{
              sx: {
                fontFamily: 'monospace',
                fontSize: '0.9rem',
                color: 'rgba(255, 255, 255, 0.9)',
                '.MuiOutlinedInput-notchedOutline': {
                  borderColor: 'rgba(255, 255, 255, 0.1)',
                },
                '&:hover .MuiOutlinedInput-notchedOutline': {
                  borderColor: 'rgba(144, 202, 249, 0.3)',
                },
                '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                  borderColor: '#90caf9',
                },
                bgcolor: alpha('#000', 0.3)
              },
              endAdornment: value ? (
                <InputAdornment position="end">
                  <Tooltip title="Vyčistiť" arrow>
                    <IconButton
                      edge="end"
                      onClick={() => onChange('')}
                      sx={{ color: 'rgba(255, 255, 255, 0.4)' }}
                    >
                      <FormatQuoteIcon />
                    </IconButton>
                  </Tooltip>
                </InputAdornment>
              ) : null
            }}
          />
          
          {value && (
            <Box
              sx={{
                mt: 2,
                p: 2,
                borderRadius: 1,
                bgcolor: alpha('#000', 0.3),
                border: '1px solid rgba(255, 255, 255, 0.1)',
                fontFamily: 'monospace',
                fontSize: '0.9rem',
                lineHeight: 1.7,
                minHeight: '60px',
                overflow: 'auto'
              }}
            >
              {getFormattedFormula()}
            </Box>
          )}
          
          <Popper
            open={showSuggestions}
            anchorEl={anchorEl}
            placement="bottom-start"
            transition
            style={{ zIndex: 1300, width: editorRef.current?.offsetWidth || 'auto' }}
          >
            {({ TransitionProps }) => (
              <Fade {...TransitionProps} timeout={350}>
                <Card
                  sx={{
                    mt: 1,
                    bgcolor: 'rgba(30, 41, 59, 0.95)',
                    border: '1px solid rgba(144, 202, 249, 0.2)',
                    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
                    borderRadius: 2,
                    backdropFilter: 'blur(12px)'
                  }}
                >
                  <CardContent sx={{ p: 0 }}>
                    <Box sx={{ p: 2, pb: 1 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 600, color: '#90caf9', mb: 1 }}>
                        Príklady formúl
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        {EXAMPLES.map((example, index) => (
                          <Chip
                            key={index}
                            label={example.name}
                            onClick={() => insertExample(example.formula)}
                            sx={{
                              bgcolor: 'rgba(144, 202, 249, 0.1)',
                              color: '#90caf9',
                              borderColor: 'rgba(144, 202, 249, 0.3)',
                              '&:hover': {
                                bgcolor: 'rgba(144, 202, 249, 0.2)',
                              }
                            }}
                            variant="outlined"
                          />
                        ))}
                      </Box>
                    </Box>
                    
                    <Divider sx={{ borderColor: 'rgba(255, 255, 255, 0.1)' }} />
                    
                    <Box sx={{ p: 2, pt: 1 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 600, color: '#90caf9', mb: 1 }}>
                        Časti formúl
                      </Typography>
                      <List dense disablePadding>
                        {SUGGESTIONS.map((suggestion, index) => (
                          <ListItem
                            key={index}
                            onClick={() => insertSuggestion(suggestion.text)}
                            sx={{
                              borderRadius: 1,
                              mb: 0.5,
                              cursor: 'pointer',
                              '&:hover': {
                                bgcolor: 'rgba(144, 202, 249, 0.1)',
                              }
                            }}
                          >
                            <ListItemText
                              primary={
                                <Box component="span" sx={{ fontFamily: 'monospace', color: '#fff' }}>
                                  {suggestion.text}
                                </Box>
                              }
                              secondary={suggestion.description}
                              secondaryTypographyProps={{
                                sx: { color: 'rgba(255, 255, 255, 0.6)', fontSize: '0.8rem' }
                              }}
                            />
                          </ListItem>
                        ))}
                      </List>
                    </Box>
                    
                    <Box sx={{ p: 2, bgcolor: 'rgba(0, 0, 0, 0.2)' }}>
                      <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                        Tip: Použite Ctrl+Space pre zobrazenie návrhov. ESC pre zatvorenie.
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Fade>
            )}
          </Popper>
        </Box>
        
        {onValidateAttributesChange && (
          <Box
            sx={{
              mt: 2,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'flex-end'
            }}
          >
            <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.6)', mr: 1 }}>
              Validovať hodnoty atribútov
            </Typography>
            <div className="toggle-switch">
              <input
                type="checkbox"
                id="validate-attributes"
                checked={validateAttributes}
                onChange={(e) => onValidateAttributesChange(e.target.checked)}
                className="toggle-switch-checkbox"
              />
              <label className="toggle-switch-label" htmlFor="validate-attributes">
                <span className="toggle-switch-inner"></span>
                <span className="toggle-switch-switch"></span>
              </label>
            </div>
          </Box>
        )}
      </Box>
      
      <style>{`
        .toggle-switch {
          position: relative;
          width: 50px;
          height: 24px;
          overflow: hidden;
        }
        .toggle-switch-checkbox {
          position: absolute;
          opacity: 0;
          height: 0;
          width: 0;
        }
        .toggle-switch-label {
          display: block;
          overflow: hidden;
          cursor: pointer;
          border: 0 solid #bbb;
          border-radius: 24px;
        }
        .toggle-switch-inner {
          display: block;
          width: 200%;
          margin-left: -100%;
          transition: margin 0.2s ease-in-out;
        }
        .toggle-switch-inner:before,
        .toggle-switch-inner:after {
          display: block;
          float: left;
          width: 50%;
          height: 24px;
          padding: 0;
          line-height: 24px;
          color: white;
          font-weight: bold;
          box-sizing: border-box;
        }
        .toggle-switch-inner:before {
          content: "";
          padding-left: 10px;
          background-color: #3f51b5;
          color: #fff;
        }
        .toggle-switch-inner:after {
          content: "";
          padding-right: 10px;
          background-color: #444;
          color: #999;
          text-align: right;
        }
        .toggle-switch-switch {
          display: block;
          width: 18px;
          height: 18px;
          margin: 3px;
          background: #fff;
          position: absolute;
          top: 0;
          bottom: 0;
          right: 26px;
          border-radius: 50%;
          transition: all 0.2s ease-in-out;
        }
        .toggle-switch-checkbox:checked + .toggle-switch-label .toggle-switch-inner {
          margin-left: 0;
        }
        .toggle-switch-checkbox:checked + .toggle-switch-label .toggle-switch-switch {
          right: 0px;
        }
      `}</style>
    </Paper>
  );
};

export default FormulaEditor; 