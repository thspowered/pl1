import React, { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  TextField,
  Button,
  Alert,
  Grid,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Card,
  CardContent,
  CircularProgress,
  Container
} from '@mui/material';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import InfoIcon from '@mui/icons-material/Info';
import { ComparisonResult } from '../types';

interface CompareExampleProps {
  onCompare: (formula: string) => Promise<{
    success: boolean;
    data?: any;
    error?: string;
  }>;
  isLoading: boolean;
}

const CompareExample: React.FC<CompareExampleProps> = ({ onCompare, isLoading }) => {
  const [formula, setFormula] = useState<string>('');
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setFormula(event.target.value);
  };

  // Adaptér pro převod odpovědi z backendu na formát očekávaný frontendem
  const adaptBackendResponse = (response: any): ComparisonResult => {
    // Zkontrolujeme, zda response obsahuje klíčové vlastnosti
    if (response && typeof response.is_valid === 'boolean') {
      // Vytvoříme symbolické rozdíly z violations a satisfied_rules
      const violations = Array.isArray(response.violations) ? response.violations : [];
      const satisfiedRules = Array.isArray(response.satisfied_rules) ? response.satisfied_rules : [];
      
      // Vytvoříme vysvětlení na základě porušení pravidel
      let explanation = '';
      if (response.is_valid) {
        explanation = `Příklad je platný pro model ${response.model_type || 'auta'}.`;
        if (satisfiedRules.length > 0) {
          explanation += ` Splňuje ${satisfiedRules.length} pravidel.`;
        }
      } else {
        explanation = `Příklad není platný pro model ${response.model_type || 'auta'}.`;
        if (violations.length > 0) {
          explanation += ` Porušuje ${violations.length} pravidel.`;
        }
      }
      
      // Zkombinujeme porušení a splněná pravidla do symbolických rozdílů
      const symbolicDifferences = [
        ...violations,
        ...satisfiedRules.map((rule: string) => `✓ ${rule}`)
      ];
      
      // Vrátíme objekt ve formátu ComparisonResult
      return {
        is_valid: response.is_valid,
        explanation,
        symbolic_differences: symbolicDifferences
      };
    }
    
    // Pokud odpověď nemá očekávanou strukturu, vrátíme výchozí objekt
    return {
      is_valid: false,
      explanation: 'Neplatná odpověď ze serveru',
      symbolic_differences: ['Chyba při zpracování odpovědi']
    };
  };

  const handleCompare = async () => {
    if (!formula.trim()) {
      setError('Prosím, zadajte formulu v predikátovej logike prvého rádu.');
      return;
    }

    try {
      const response = await onCompare(formula);
      
      if (response.success && response.data) {
        // Použijeme adaptér k převodu odpovědi do očekávaného formátu
        const adaptedResult = adaptBackendResponse(response.data);
        setResult(adaptedResult);
        setError(null);
      } else {
        setError(response.error || 'Nastala chyba pri porovnávaní príkladu.');
        setResult(null);
      }
    } catch (err) {
      setError('Nastala neočakávaná chyba pri porovnávaní príkladu.');
      setResult(null);
    }
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
        <Box sx={{ 
          p: 3,
          borderBottom: '1px solid rgba(255, 255, 255, 0.05)'
        }}>
          <Typography 
            variant="h4" 
            gutterBottom
            sx={{ 
              fontWeight: 600,
              color: '#90caf9',
              mb: 1,
              display: 'flex',
              alignItems: 'center',
              '&::after': {
                content: '""',
                flexGrow: 1,
                height: '1px',
                ml: 2,
                background: 'linear-gradient(90deg, rgba(144, 202, 249, 0.5) 0%, rgba(144, 202, 249, 0) 100%)'
              }
            }}
          >
            Porovnanie príkladu s modelom
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            Zadajte príklad v predikátovej logike prvého rádu a porovnajte ho s natrénovaným modelom.
          </Typography>
        </Box>

        <Grid container spacing={0}>
          {/* Editor sekcia */}
          <Grid item xs={12} md={6} sx={{ 
            p: 3,
            borderRight: { xs: 'none', md: '1px solid rgba(255, 255, 255, 0.05)' }
          }}>
            <Typography 
              variant="h6" 
              component="h2" 
              sx={{ 
                mb: 2, 
                fontWeight: 600,
                color: 'rgba(255, 255, 255, 0.8)',
                display: 'flex',
                alignItems: 'center',
                '&::after': {
                  content: '""',
                  flexGrow: 1,
                  height: '1px',
                  ml: 2,
                  background: 'linear-gradient(90deg, rgba(255, 255, 255, 0.2) 0%, rgba(255, 255, 255, 0) 100%)'
                }
              }}
            >
              <InfoIcon sx={{ mr: 1, color: '#90caf9' }} />
              Editor príkladu
            </Typography>

            <TextField
              label="Formalizovaný príklad v PL1"
              multiline
              fullWidth
              rows={14}
              value={formula}
              onChange={handleChange}
              variant="outlined"
              placeholder="Napríklad: Ι(c₁, X5) ∧ Π(c₁, e₁) ∧ Ι(e₁, PetrolEngine) ∧ Π(c₁, t₁) ∧ Ι(t₁, ManualTransmission) ∧ Π(c₁, d₁) ∧ Ι(d₁, XDrive)"
              sx={{
                mb: 3,
                '& .MuiOutlinedInput-root': {
                  fontFamily: 'monospace',
                  fontSize: '0.9rem'
                }
              }}
            />

            <Button
              variant="contained"
              color="primary"
              fullWidth
              onClick={handleCompare}
              disabled={isLoading || !formula.trim()}
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
              {isLoading ? (
                <CircularProgress size={24} color="inherit" sx={{ mr: 1 }} />
              ) : null}
              Porovnať s modelom
            </Button>

            {error && (
              <Alert 
                severity="error" 
                sx={{ 
                  mt: 3, 
                  borderRadius: 1,
                  background: 'rgba(244, 67, 54, 0.15)',
                  border: '1px solid rgba(244, 67, 54, 0.3)',
                  color: 'white',
                  '& .MuiAlert-icon': { color: '#f44336' },
                }}
              >
                {error}
              </Alert>
            )}
          </Grid>

          {/* Výsledok sekcia */}
          <Grid item xs={12} md={6} sx={{ p: 3 }}>
            <Typography 
              variant="h6" 
              component="h2" 
              sx={{ 
                mb: 2, 
                fontWeight: 600,
                color: 'rgba(255, 255, 255, 0.8)',
                display: 'flex',
                alignItems: 'center',
                '&::after': {
                  content: '""',
                  flexGrow: 1,
                  height: '1px',
                  ml: 2,
                  background: 'linear-gradient(90deg, rgba(255, 255, 255, 0.2) 0%, rgba(255, 255, 255, 0) 100%)'
                }
              }}
            >
              <InfoIcon sx={{ mr: 1, color: '#90caf9' }} />
              Výsledok porovnania
            </Typography>

            {isLoading ? (
              <Box sx={{ 
                display: 'flex', 
                flexDirection: 'column', 
                alignItems: 'center', 
                justifyContent: 'center',
                height: '300px'
              }}>
                <CircularProgress size={40} />
                <Typography sx={{ mt: 2, color: 'text.secondary' }}>
                  Prebieha porovnávanie príkladu s modelom...
                </Typography>
              </Box>
            ) : result ? (
              <Box>
                <Card 
                  sx={{ 
                    mb: 3, 
                    backgroundColor: result.is_valid ? 'rgba(102, 187, 106, 0.1)' : 'rgba(244, 67, 54, 0.1)',
                    border: result.is_valid ? '1px solid rgba(102, 187, 106, 0.3)' : '1px solid rgba(244, 67, 54, 0.3)',
                    borderRadius: 2
                  }}
                >
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      {result.is_valid ? (
                        <CheckCircleOutlineIcon sx={{ color: '#66bb6a', mr: 1 }} />
                      ) : (
                        <ErrorOutlineIcon sx={{ color: '#f44336', mr: 1 }} />
                      )}
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>
                        {result.is_valid ? 'Príklad je platný' : 'Príklad nie je platný'}
                      </Typography>
                    </Box>
                    <Typography variant="body1">
                      {result.explanation}
                    </Typography>
                  </CardContent>
                </Card>

                {result.symbolic_differences.length > 0 && (
                  <Paper sx={{ 
                    p: 2,
                    backgroundColor: 'rgba(0, 0, 0, 0.2)',
                    border: '1px solid rgba(255, 255, 255, 0.05)',
                    borderRadius: 2
                  }}>
                    <Typography 
                      variant="subtitle1" 
                      sx={{ 
                        mb: 2, 
                        fontWeight: 600,
                        color: result.is_valid ? '#66bb6a' : '#f8bb86'
                      }}
                    >
                      {result.is_valid ? 'Splněná pravidla:' : 'Zistené problémy:'}
                    </Typography>
                    <List sx={{ 
                      p: 0,
                      '& .MuiListItem-root': {
                        px: 2,
                        py: 1,
                        borderRadius: 1,
                        mb: 1,
                        backgroundColor: 'rgba(255, 255, 255, 0.03)'
                      }
                    }}>
                      {result.symbolic_differences.map((diff, index) => (
                        <ListItem key={index}>
                          <ListItemIcon sx={{ minWidth: 36 }}>
                            {diff.startsWith('✓') ? (
                              <CheckCircleOutlineIcon sx={{ color: '#66bb6a' }} />
                            ) : (
                              <ErrorOutlineIcon sx={{ color: '#f44336' }} />
                            )}
                          </ListItemIcon>
                          <ListItemText 
                            primary={diff.startsWith('✓') ? diff.substring(2) : diff} 
                            primaryTypographyProps={{
                              variant: 'body2',
                              sx: { 
                                color: 'rgba(255, 255, 255, 0.8)',
                                fontFamily: 'monospace',
                                whiteSpace: 'pre-wrap'
                              }
                            }}
                          />
                        </ListItem>
                      ))}
                    </List>
                  </Paper>
                )}
              </Box>
            ) : (
              <Box sx={{ 
                height: '300px', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                flexDirection: 'column',
                backgroundColor: 'rgba(0, 0, 0, 0.1)',
                borderRadius: 2,
                border: '1px dashed rgba(255, 255, 255, 0.1)'
              }}>
                <InfoIcon sx={{ color: 'text.secondary', fontSize: 40, mb: 2 }} />
                <Typography variant="body1" color="text.secondary" align="center">
                  Zadajte príklad do editora a kliknite na tlačidlo "Porovnať s modelom"
                </Typography>
              </Box>
            )}
          </Grid>
        </Grid>
      </Paper>
    </Container>
  );
};

export default CompareExample; 