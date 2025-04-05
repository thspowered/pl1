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
  Container,
  FormControlLabel,
  Switch,
  Tooltip,
  IconButton
} from '@mui/material';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import InfoIcon from '@mui/icons-material/Info';
import { ComparisonResult } from '../types';
import { useApi } from '../hooks/useApi';

interface CompareExampleProps {
  exampleFormula: string;
  validateAttributes?: boolean;
}

const CompareExample: React.FC<CompareExampleProps> = ({ exampleFormula, validateAttributes = true }) => {
  const [formula, setFormula] = useState(exampleFormula || '');
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validateAttrs, setValidateAttrs] = useState(validateAttributes);
  
  const { compareExample } = useApi();
  
  const adaptBackendResponse = (result: ComparisonResult | null) => {
    if (!result) {
      return { title: 'Žiadny výsledok', description: '', details: [] };
    }

    let title = '';
    let description = '';
    let details: { text: string; color: string; symbol?: string }[] = [];

    if (!result.model_type || !result.violations || !result.satisfied_rules) {
      return { title: 'Neplatná odpoveď', description: 'Odpoveď neobsahuje platné dáta', details: [] };
    }

    if (result.is_valid) {
      title = `✅ Príklad je platný pre model ${result.model_type}`;
      description = `Príklad spĺňa všetkých ${result.satisfied_rules.length} pravidiel pre model ${result.model_type}.`;
    }
    else {
      title = `❌ Príklad nie je platný pre model ${result.model_type}`;
      description = `Príklad porušuje ${result.violations.length} z ${result.violations.length + result.satisfied_rules.length} pravidiel.`;
      
      if (result.allowed_alternatives && Object.keys(result.allowed_alternatives).length > 0) {
        description += ' Povolené alternatívy komponentov:';
      }
    }

    if (result.violations && result.violations.length > 0) {
      details.push({ text: 'Porušené pravidlá:', color: '#f44336', symbol: '' });
      
      if (result.categorized_violations) {
        if (result.categorized_violations.component_violations && result.categorized_violations.component_violations.length > 0) {
          result.categorized_violations.component_violations.forEach(violation => {
            details.push({ text: violation, color: '#f44336', symbol: '❌' });
          });
        }
        
        if (result.categorized_violations.must_violations && result.categorized_violations.must_violations.length > 0) {
          result.categorized_violations.must_violations.forEach(violation => {
            details.push({ text: violation, color: '#f44336', symbol: '❌' });
          });
        }
        
        if (result.categorized_violations.must_not_violations && result.categorized_violations.must_not_violations.length > 0) {
          result.categorized_violations.must_not_violations.forEach(violation => {
            details.push({ text: violation, color: '#f44336', symbol: '❌' });
          });
        }
        
        if (result.categorized_violations.attribute_violations && result.categorized_violations.attribute_violations.length > 0) {
          result.categorized_violations.attribute_violations.forEach(violation => {
            details.push({ text: violation, color: '#f44336', symbol: '❌' });
          });
        }
      } else {
        result.violations.forEach(violation => {
          details.push({ text: violation, color: '#f44336', symbol: '❌' });
        });
      }
      
      if (result.satisfied_rules && result.satisfied_rules.length > 0) {
        details.push({ text: '', color: '', symbol: '' });
      }
    }

    if (result.satisfied_rules && result.satisfied_rules.length > 0) {
      details.push({ text: 'Splnené pravidlá:', color: '#4caf50', symbol: '' });
      result.satisfied_rules.forEach(rule => {
        details.push({ text: rule, color: '#4caf50', symbol: '✅' });
      });
    }

    if (!result.is_valid && result.allowed_alternatives) {
      if (result.allowed_alternatives.engines && result.allowed_alternatives.engines.length > 0 || 
          result.allowed_alternatives.transmissions && result.allowed_alternatives.transmissions.length > 0 ||
          result.allowed_alternatives.drives && result.allowed_alternatives.drives.length > 0) {
        details.push({ text: '', color: '', symbol: '' });
        details.push({ text: 'Povolené alternatívy:', color: '#2196f3', symbol: '' });
        
        if (result.allowed_alternatives.engines && result.allowed_alternatives.engines.length > 0) {
          details.push({ 
            text: `Motory: ${result.allowed_alternatives.engines.join(', ')}`, 
            color: '#2196f3', 
            symbol: 'ℹ️' 
          });
        }
        
        if (result.allowed_alternatives.transmissions && result.allowed_alternatives.transmissions.length > 0) {
          details.push({ 
            text: `Prevodovky: ${result.allowed_alternatives.transmissions.join(', ')}`, 
            color: '#2196f3', 
            symbol: 'ℹ️' 
          });
        }
        
        if (result.allowed_alternatives.drives && result.allowed_alternatives.drives.length > 0) {
          details.push({ 
            text: `Pohony: ${result.allowed_alternatives.drives.join(', ')}`, 
            color: '#2196f3', 
            symbol: 'ℹ️' 
          });
        }
      }
    }

    return { title, description, details };
  };
  
  const handleCompare = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const comparisonResult = await compareExample(formula, validateAttrs);
      setResult(comparisonResult);
    } catch (err) {
      console.error('Error comparing example:', err);
      setError('Nastala chyba pri porovnávaní príkladu');
    } finally {
      setLoading(false);
    }
  };
  
  const adaptedResult = adaptBackendResponse(result);
  
  const handleEditorChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setFormula(event.target.value);
  };
  
  const handleValidateAttributesChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setValidateAttrs(event.target.checked);
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
              label="Zadajte PL1 formulu príkladu"
              multiline
              fullWidth
              rows={6}
              value={formula}
              onChange={handleEditorChange}
              placeholder="Zadajte PL1 formulu príkladu..."
              variant="outlined"
              sx={{ 
                mb: 2,
                '& .MuiOutlinedInput-root': {
                  fontFamily: 'monospace'
                }
              }}
            />

            <Box sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
              <Tooltip title="Kontrolovať aj číselné hodnoty atribútov ako výkon, krútiaci moment, počet valcov...">
                <FormControlLabel 
                  control={
                    <Switch 
                      checked={validateAttrs} 
                      onChange={handleValidateAttributesChange}
                      color="primary" 
                    />
                  } 
                  label="Validovať hodnoty atribútov" 
                  sx={{ 
                    color: 'rgba(255, 255, 255, 0.7)',
                    mr: 0
                  }}
                />
              </Tooltip>
            </Box>

            <Button
              variant="contained"
              color="primary"
              fullWidth
              onClick={handleCompare}
              disabled={loading || !formula.trim()}
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
              {loading ? (
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
              {result ? (
                result.is_valid ? (
                  <CheckCircleOutlineIcon sx={{ mr: 1, color: '#66bb6a' }} />
                ) : (
                  <ErrorOutlineIcon sx={{ mr: 1, color: '#f44336' }} />
                )
              ) : (
                <InfoIcon sx={{ mr: 1, color: '#90caf9' }} />
              )}
              Výsledok porovnania
            </Typography>

            {!result && !loading && (
              <Card sx={{ 
                mb: 3, 
                background: 'rgba(0, 0, 0, 0.2)',
                boxShadow: 'none',
                border: '1px dashed rgba(255, 255, 255, 0.1)',
                borderRadius: 2,
                height: 'calc(100% - 30px)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <CardContent sx={{ textAlign: 'center', py: 8 }}>
                  <InfoIcon sx={{ fontSize: 48, color: 'rgba(255, 255, 255, 0.2)', mb: 2 }} />
                  <Typography sx={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                    Tu sa zobrazia výsledky porovnania príkladu s modelom.
                  </Typography>
                </CardContent>
              </Card>
            )}

            {loading && (
              <Box sx={{ 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                height: 'calc(100% - 30px)',
                border: '1px dashed rgba(25, 118, 210, 0.2)',
                borderRadius: 2,
                background: 'rgba(25, 118, 210, 0.05)',
                p: 4
              }}>
                <CircularProgress size={40} />
                <Typography sx={{ ml: 2, color: 'rgba(255, 255, 255, 0.7)' }}>
                  Porovnávam príklad s modelom...
                </Typography>
              </Box>
            )}

            {result && (
              <Box>
                <Alert 
                  severity={result.is_valid ? "success" : "error"}
                  sx={{ 
                    mb: 3,
                    borderRadius: 2,
                    background: result.is_valid 
                      ? 'rgba(102, 187, 106, 0.15)'
                      : 'rgba(244, 67, 54, 0.15)',
                    border: result.is_valid
                      ? '1px solid rgba(102, 187, 106, 0.3)'
                      : '1px solid rgba(244, 67, 54, 0.3)',
                    color: 'white'
                  }}
                >
                  <Typography fontWeight={500}>
                    {adaptedResult.title}
                  </Typography>
                </Alert>

                <Typography 
                  variant="subtitle1" 
                  sx={{ 
                    fontWeight: 600, 
                    mb: 1.5, 
                    color: 'rgba(255, 255, 255, 0.8)',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                    pb: 1
                  }}
                >
                  Detaily porovnania:
                </Typography>
                
                {adaptedResult.details.map((detail, index) => (
                  detail.text ? (
                    <Typography 
                      key={index} 
                      variant={detail.symbol === '' ? 'subtitle1' : 'body1'} 
                      sx={{ 
                        color: detail.color, 
                        my: detail.symbol === '' ? 1 : 0.5,
                        fontWeight: detail.symbol === '' ? 'bold' : 'normal',
                        display: 'flex',
                        alignItems: 'center'
                      }}
                    >
                      {detail.symbol && <span style={{ marginRight: '8px' }}>{detail.symbol}</span>}
                      {detail.text}
                    </Typography>
                  ) : (
                    <Divider key={index} sx={{ my: 1 }} />
                  )
                ))}

                {result && !result.is_valid && result.allowed_alternatives && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2" color="warning.main" sx={{ fontWeight: 600 }}>
                      Povolené alternatívy pre komponenty:
                    </Typography>
                    <Card variant="outlined" sx={{ mt: 1, bgcolor: 'rgba(255, 255, 255, 0.03)' }}>
                      <CardContent>
                        {result.allowed_alternatives.engines && result.allowed_alternatives.engines.length > 0 && (
                          <Box sx={{ mb: 1 }}>
                            <Typography variant="body2" sx={{ color: 'info.main', fontWeight: 600 }}>
                              Motory:
                            </Typography>
                            <Typography variant="body2">
                              {result.allowed_alternatives.engines.join(', ')}
                            </Typography>
                          </Box>
                        )}
                        {result.allowed_alternatives.transmissions && result.allowed_alternatives.transmissions.length > 0 && (
                          <Box sx={{ mb: 1 }}>
                            <Typography variant="body2" sx={{ color: 'info.main', fontWeight: 600 }}>
                              Prevodovky:
                            </Typography>
                            <Typography variant="body2">
                              {result.allowed_alternatives.transmissions.join(', ')}
                            </Typography>
                          </Box>
                        )}
                        {result.allowed_alternatives.drives && result.allowed_alternatives.drives.length > 0 && (
                          <Box>
                            <Typography variant="body2" sx={{ color: 'info.main', fontWeight: 600 }}>
                              Pohony:
                            </Typography>
                            <Typography variant="body2">
                              {result.allowed_alternatives.drives.join(', ')}
                            </Typography>
                          </Box>
                        )}
                      </CardContent>
                    </Card>
                  </Box>
                )}
              </Box>
            )}
          </Grid>
        </Grid>
      </Paper>
    </Container>
  );
};

export default CompareExample; 