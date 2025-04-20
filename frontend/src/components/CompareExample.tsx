import React, { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  TextField,
  Button,
  Alert,
  Grid,
  Divider,
  Card,
  CardContent,
  CircularProgress,
  Container,
  FormControlLabel,
  Switch,
  Tooltip,
  Tabs,
  Tab,
  AppBar,
  useTheme,
  useMediaQuery,
  alpha
} from '@mui/material';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';
import CodeIcon from '@mui/icons-material/Code';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import PlaylistAddCheckIcon from '@mui/icons-material/PlaylistAddCheck';
import { ComparisonResult } from '../types';
import ExampleNetworkGraph from './ExampleNetworkGraph';

interface CompareExampleProps {
  isLoading: boolean;
  onCompare: (formula: string, validateAttributes?: boolean) => Promise<any>;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`visualization-tabpanel-${index}`}
      aria-labelledby={`visualization-tab-${index}`}
      {...other}
      style={{ height: '100%' }}
    >
      {value === index && (
        <Box sx={{ p: 0, height: '100%' }}>
          {children}
        </Box>
      )}
    </div>
  );
}

function a11yProps(index: number) {
  return {
    id: `visualization-tab-${index}`,
    'aria-controls': `visualization-tabpanel-${index}`,
  };
}

const CompareExample: React.FC<CompareExampleProps> = ({ isLoading, onCompare }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const defaultExample = "Ι(c1, X5) ∧ Π(c1, e1) ∧ Ι(e1, DieselEngine) ∧ Π(c1, t1) ∧ Ι(t1, AutomaticTransmission) ∧ Π(c1, d1) ∧ Ι(d1, XDrive) ∧ Α(e1, power, 400) ∧ Α(e1, torque, 450) ∧ Α(e1, cylinders, 6)";
  const [formula, setFormula] = useState(defaultExample);
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validateAttrs, setValidateAttrs] = useState(true);
  const [tabValue, setTabValue] = useState(0);
  
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
    }

    if (result.violations && result.violations.length > 0) {
      details.push({ text: 'Porušené pravidlá:', color: '#f44336', symbol: '' });
      
      if (result.categorized_violations) {
        if (result.categorized_violations.component_violations && result.categorized_violations.component_violations.length > 0) {
          details.push({ text: 'Chýbajúce komponenty:', color: '#f44336', symbol: '' });
          result.categorized_violations.component_violations.forEach(violation => {
            details.push({ text: violation, color: '#f44336', symbol: '❌' });
          });
        }
        
        if (result.categorized_violations.must_violations && result.categorized_violations.must_violations.length > 0) {
          details.push({ text: 'Chýbajúce povinné vzťahy:', color: '#f44336', symbol: '' });
          result.categorized_violations.must_violations.forEach(violation => {
            details.push({ text: violation, color: '#f44336', symbol: '❌' });
          });
        }
        
        if (result.categorized_violations.must_not_violations && result.categorized_violations.must_not_violations.length > 0) {
          details.push({ text: 'Porušené zakázané vzťahy:', color: '#f44336', symbol: '' });
          result.categorized_violations.must_not_violations.forEach(violation => {
            details.push({ text: violation, color: '#f44336', symbol: '❌' });
          });
        }
        
        if (result.validate_attributes && result.categorized_violations.attribute_violations && result.categorized_violations.attribute_violations.length > 0) {
          details.push({ text: 'Neplatné hodnoty atribútov (numerické a iné):', color: '#ff5722', symbol: '' });
          result.categorized_violations.attribute_violations.forEach(violation => {
            if (violation.includes("číselnú hodnotu")) {
              details.push({ text: violation, color: '#ff5722', symbol: '⚠️' });
            } else {
              details.push({ text: violation, color: '#ff9800', symbol: '⚠️' });
            }
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

    return { title, description, details };
  };
  
  const handleCompare = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const comparisonResult = await onCompare(formula, validateAttrs);
      setResult(comparisonResult);
      // After successful comparison, switch to results tab
      setTabValue(1);
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
  
  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <Container maxWidth="xl" sx={{ mt: 3, mb: 4, px: { xs: 1, sm: 3 } }}>
      <Paper
        elevation={4}
        sx={{
          borderRadius: 3,
          overflow: 'hidden',
          height: '100%',
          backgroundImage: 'radial-gradient(circle at 10% 20%, rgba(30,41,59,1) 0%, rgba(17,24,39,1) 81%)',
          border: '1px solid',
          borderColor: 'divider'
        }}
      >
        <AppBar position="static" color="transparent" elevation={0} sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Box sx={{ 
            p: 2, 
            display: 'flex',
            flexDirection: { xs: 'column', sm: 'row' },
            alignItems: { xs: 'flex-start', sm: 'center' },
            justifyContent: 'space-between',
            gap: 2
          }}>
            <Box>
              <Typography 
                variant="h4" 
                component="h1"
                sx={{ 
                  fontWeight: 700,
                  color: '#90caf9',
                  fontSize: { xs: '1.5rem', sm: '2rem' }
                }}
              >
                <CompareArrowsIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
                Validácia príkladu
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                Overte správnosť príkladu voči natrénovanému modelu
              </Typography>
            </Box>
            
            <Button
              variant="contained"
              color="primary"
              onClick={handleCompare}
              disabled={loading || !formula.trim()}
              sx={{
                py: 1,
                px: 3,
                fontWeight: 600,
                borderRadius: 2,
                textTransform: 'none',
                boxShadow: '0 4px 14px 0 rgba(0,118,255,0.39)',
                background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
                '&:hover': {
                  boxShadow: '0 6px 20px rgba(0,118,255,0.4)',
                },
                minWidth: '140px'
              }}
              startIcon={loading ? <CircularProgress size={20} color="inherit" /> : null}
            >
              {loading ? "Validujem..." : "Validovať príklad"}
            </Button>
          </Box>
          
          <Tabs 
            value={tabValue} 
            onChange={handleTabChange} 
            aria-label="comparison tabs"
            variant={isMobile ? "fullWidth" : "standard"}
            sx={{
              '& .MuiTab-root': {
                minHeight: '54px',
                textTransform: 'none',
                fontWeight: 500,
                fontSize: '0.9rem',
              },
              '& .Mui-selected': {
                color: '#90caf9 !important',
                fontWeight: 600
              },
              '& .MuiTabs-indicator': {
                backgroundColor: '#90caf9',
                height: 3
              }
            }}
          >
            <Tab icon={<CodeIcon />} iconPosition="start" label="Editor príkladu" {...a11yProps(0)} />
            <Tab 
              icon={<PlaylistAddCheckIcon />} 
              iconPosition="start" 
              label="Výsledky validácie" 
              {...a11yProps(1)} 
              disabled={!result}
            />
            <Tab 
              icon={<AccountTreeIcon />} 
              iconPosition="start" 
              label="Vizualizácia" 
              {...a11yProps(2)} 
              disabled={!result}
            />
          </Tabs>
        </AppBar>
        
        <Box sx={{ p: { xs: 2, md: 3 }, height: 'calc(100% - 140px)' }}>
          <TabPanel value={tabValue} index={0}>
            {/* Editor Tab */}
            <Card 
              variant="outlined" 
              sx={{ 
                height: '100%', 
                bgcolor: alpha('#000', 0.2),
                boxShadow: 'none',
                borderColor: alpha('#fff', 0.1)
              }}
            >
              <CardContent sx={{ p: 3, height: '100%' }}>
                <Grid container spacing={3}>
                  <Grid item xs={12}>
                    <Typography 
                      variant="h6" 
                      sx={{ 
                        mb: 2, 
                        fontWeight: 600,
                        color: 'white',
                        display: 'flex',
                        alignItems: 'center'
                      }}
                    >
                      <CodeIcon sx={{ mr: 1, color: '#90caf9' }} />
                      PL1 Formula príkladu
                    </Typography>
                    <Alert 
                      severity="info" 
                      variant="outlined"
                      sx={{ 
                        mb: 2,
                        borderRadius: 2,
                        bgcolor: alpha('#2196f3', 0.1)
                      }}
                    >
                      <Typography variant="body2">
                        Používajte správne Unicode symboly: <b>Ι</b> (is_a), <b>Π</b> (has_part), <b>Α</b> (has_attribute), <b>∧</b> (and)
                      </Typography>
                    </Alert>
                  </Grid>
                  
                  <Grid item xs={12}>
                    <TextField
                      label="Zadajte PL1 formulu príkladu"
                      multiline
                      fullWidth
                      rows={10}
                      value={formula}
                      onChange={handleEditorChange}
                      placeholder="Príklad: Ι(c1, X5) ∧ Π(c1, e1) ∧ Ι(e1, DieselEngine) ∧ ..."
                      variant="outlined"
                      sx={{ 
                        '& .MuiOutlinedInput-root': {
                          fontFamily: 'monospace',
                          fontSize: '0.95rem'
                        },
                        '& .MuiOutlinedInput-notchedOutline': {
                          borderColor: alpha('#fff', 0.2)
                        }
                      }}
                    />
                  </Grid>
                  
                  <Grid item xs={12}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}>
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
                        />
                      </Tooltip>
                      
                      {error && (
                        <Alert 
                          severity="error" 
                          variant="filled"
                          sx={{ borderRadius: 2 }}
                        >
                          {error}
                        </Alert>
                      )}
                    </Box>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </TabPanel>
          
          <TabPanel value={tabValue} index={1}>
            {/* Results Tab */}
            {result ? (
              <Card 
                variant="outlined" 
                sx={{ 
                  height: '100%', 
                  bgcolor: alpha('#000', 0.2),
                  boxShadow: 'none',
                  borderColor: alpha('#fff', 0.1),
                  overflow: 'auto'
                }}
              >
                <CardContent sx={{ p: 3 }}>
                  <Box sx={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'flex-start',
                    mb: 3,
                    flexDirection: { xs: 'column', sm: 'row' },
                    gap: 2
                  }}>
                    <Typography 
                      variant="h5" 
                      sx={{ 
                        fontWeight: 600,
                        display: 'flex',
                        alignItems: 'center'
                      }}
                    >
                      {result.is_valid ? (
                        <CheckCircleOutlineIcon sx={{ mr: 1, color: '#66bb6a' }} />
                      ) : (
                        <ErrorOutlineIcon sx={{ mr: 1, color: '#f44336' }} />
                      )}
                      Výsledok validácie
                    </Typography>
                    
                    <Alert 
                      severity={result.is_valid ? "success" : "error"}
                      variant="filled"
                      icon={false}
                      sx={{ 
                        borderRadius: 2,
                        py: 1,
                        fontWeight: 500
                      }}
                    >
                      {result.is_valid ? 
                        `Príklad je platný pre model ${result.model_type}` : 
                        `Príklad nie je platný pre model ${result.model_type}`
                      }
                    </Alert>
                  </Box>
                  
                  <Divider sx={{ mb: 3, bgcolor: alpha('#fff', 0.1) }} />
                  
                  <Grid container spacing={3}>
                    <Grid item xs={12}>
                      <Paper
                        variant="outlined"
                        sx={{
                          p: 2,
                          borderRadius: 2,
                          bgcolor: alpha('#000', 0.2),
                          borderColor: alpha('#fff', 0.1),
                          mb: 3
                        }}
                      >
                        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2, color: '#90caf9' }}>
                          Detaily validácie:
                        </Typography>
                        
                        <Box sx={{ pl: 1 }}>
                          {adaptedResult.details.map((detail, index) => (
                            detail.text ? (
                              <Typography 
                                key={index} 
                                variant={detail.symbol === '' ? 'subtitle2' : 'body2'} 
                                sx={{ 
                                  color: detail.color, 
                                  my: detail.symbol === '' ? 1.5 : 0.75,
                                  fontWeight: detail.symbol === '' ? 600 : 400,
                                  display: 'flex',
                                  alignItems: 'center',
                                  pl: detail.symbol ? 2 : 0
                                }}
                              >
                                {detail.symbol && <span style={{ marginRight: '8px', fontSize: '1.1rem' }}>{detail.symbol}</span>}
                                {detail.text}
                              </Typography>
                            ) : (
                              <Divider key={index} sx={{ my: 1.5, bgcolor: alpha('#fff', 0.05) }} />
                            )
                          ))}
                        </Box>
                      </Paper>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            ) : (
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                <Typography variant="body1" sx={{ color: 'text.secondary' }}>
                  Nie sú dostupné žiadne výsledky. Najprv validujte príklad.
                </Typography>
              </Box>
            )}
          </TabPanel>
          
          <TabPanel value={tabValue} index={2}>
            {/* Visualization Tab */}
            {result ? (
              <Box sx={{ height: '100%' }}>
                <Card 
                  variant="outlined" 
                  sx={{ 
                    height: '100%',
                    bgcolor: alpha('#000', 0.2),
                    boxShadow: 'none',
                    borderColor: alpha('#fff', 0.1)
                  }}
                >
                  <CardContent sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
                    <Paper 
                      elevation={0}
                      sx={{ 
                        height: '100%',
                        borderRadius: 2,
                        overflow: 'hidden',
                        border: '1px solid',
                        borderColor: alpha('#fff', 0.1),
                        display: 'flex',
                        flexDirection: 'column',
                        flexGrow: 1
                      }}
                    >
                      <Box sx={{ 
                        p: 1.5, 
                        borderBottom: '1px solid',
                        borderColor: alpha('#fff', 0.1), 
                        bgcolor: alpha('#000', 0.3),
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                      }}>
                        <Typography 
                          variant="subtitle1" 
                          sx={{ 
                            fontWeight: 600, 
                            textAlign: 'center',
                            color: '#2196f3'
                          }}
                        >
                          Vizualizacia hypotezy
                        </Typography>
                      </Box>
                      <Box sx={{ 
                        flexGrow: 1, 
                        minHeight: 0,
                        height: { xs: '650px', sm: '700px', md: '800px' }
                      }}>
                        <ExampleNetworkGraph 
                          comparisonResult={result} 
                          formula={formula} 
                          showLayeredVisualization={true}
                          viewType="combined"
                        />
                      </Box>
                    </Paper>
                    
                    <Box sx={{ pt: 2 }}>
                      <Paper 
                        elevation={0}
                        sx={{ 
                          p: 1.5, 
                          bgcolor: alpha('#000', 0.3),
                          borderRadius: 2,
                          border: '1px solid',
                          borderColor: alpha('#fff', 0.1)
                        }}
                      >
                        <Grid container spacing={1} alignItems="center">
                          <Grid item xs={12} sm="auto">
                            <Typography variant="body2" sx={{ fontWeight: 600, color: '#90caf9', mb: { xs: 1, sm: 0 } }}>
                              Legenda:
                            </Typography>
                          </Grid>
                          <Grid item xs={6} sm="auto" sx={{ minWidth: { sm: '130px' } }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: '#4caf50' }}></Box>
                              <Typography variant="caption">Platný prvok</Typography>
                            </Box>
                          </Grid>
                          <Grid item xs={6} sm="auto" sx={{ minWidth: { sm: '150px' } }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: '#F44336' }}></Box>
                              <Typography variant="caption">Chýbajúci prvok</Typography>
                            </Box>
                          </Grid>
                          <Grid item xs={6} sm="auto" sx={{ minWidth: { sm: '150px' } }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: '#FF9800' }}></Box>
                              <Typography variant="caption">Neplatná hodnota</Typography>
                            </Box>
                          </Grid>
                          <Grid item xs={6} sm="auto" sx={{ minWidth: { sm: '150px' } }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: '#2196f3' }}></Box>
                              <Typography variant="caption">Prebytočný prvok</Typography>
                            </Box>
                          </Grid>
                          <Grid item xs={6} sm="auto" sx={{ minWidth: { sm: '150px' } }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: '#000000' }}></Box>
                              <Typography variant="caption">Chýbajúci v príklade</Typography>
                            </Box>
                          </Grid>
                        </Grid>
                      </Paper>
                    </Box>
                  </CardContent>
                </Card>
              </Box>
            ) : (
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                <Typography variant="body1" sx={{ color: 'text.secondary' }}>
                  Nie sú dostupné žiadne vizualizácie. Najprv validujte príklad.
                </Typography>
              </Box>
            )}
          </TabPanel>
        </Box>
      </Paper>
    </Container>
  );
};

export default CompareExample; 