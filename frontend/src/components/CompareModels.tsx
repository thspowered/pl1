import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
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
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  Tab,
  Tabs
} from '@mui/material';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';
import InfoIcon from '@mui/icons-material/Info';
import VisibilityIcon from '@mui/icons-material/Visibility';
import TableChartIcon from '@mui/icons-material/TableChart';
import { SavedModel, ModelComparisonResult } from '../types';
import SigmaNetwork from './SigmaNetwork';
import axios from 'axios';

interface CompareModelsProps {
  isLoading: boolean;
}

const CompareModels: React.FC<CompareModelsProps> = ({ isLoading }) => {
  const [modelAType, setModelAType] = useState<string>('current');
  const [modelAId, setModelAId] = useState<string>('');
  const [modelBType, setModelBType] = useState<string>('current');
  const [modelBId, setModelBId] = useState<string>('');
  
  const [savedModels, setSavedModels] = useState<SavedModel[]>([]);
  const [result, setResult] = useState<ModelComparisonResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<string>('differences');

  // Načítání uložených modelů
  useEffect(() => {
    const fetchSavedModels = async () => {
      try {
        const response = await axios.get('/api/saved-models');
        if (response.data.success && response.data.models) {
          setSavedModels(response.data.models);
        } else {
          console.error('Nepodařilo se načíst uložené modely', response.data);
        }
      } catch (err) {
        console.error('Chyba při načítání uložených modelů', err);
        setError('Nastala chyba při načítání uložených modelů');
      }
    };

    fetchSavedModels();
  }, []);

  const handleSaveCurrentModel = async () => {
    try {
      setLoading(true);
      const modelName = prompt('Zadejte název pro uložení modelu:');
      if (!modelName) {
        setLoading(false);
        return;
      }

      const response = await axios.post('/api/save-model', { name: modelName });
      if (response.data.success) {
        // Aktualizace seznamu uložených modelů
        const updatedModelsResponse = await axios.get('/api/saved-models');
        if (updatedModelsResponse.data.success && updatedModelsResponse.data.models) {
          setSavedModels(updatedModelsResponse.data.models);
        }
      } else {
        setError('Nepodařilo se uložit model: ' + response.data.message);
      }
    } catch (err) {
      console.error('Chyba při ukládání modelu', err);
      setError('Nastala chyba při ukládání modelu');
    } finally {
      setLoading(false);
    }
  };

  const handleModelATypeChange = (event: SelectChangeEvent) => {
    setModelAType(event.target.value);
    if (event.target.value === 'current') {
      setModelAId('');
    }
  };

  const handleModelBTypeChange = (event: SelectChangeEvent) => {
    setModelBType(event.target.value);
    if (event.target.value === 'current') {
      setModelBId('');
    }
  };

  const handleModelAIdChange = (event: SelectChangeEvent) => {
    setModelAId(event.target.value);
  };

  const handleModelBIdChange = (event: SelectChangeEvent) => {
    setModelBId(event.target.value);
  };

  const handleCompare = async () => {
    if ((modelAType === 'saved' && !modelAId) || (modelBType === 'saved' && !modelBId)) {
      setError('Prosím, vyberte oba modely pro porovnání');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const requestData = {
        model_a_type: modelAType,
        model_a_id: modelAType === 'saved' ? parseInt(modelAId) : undefined,
        model_b_type: modelBType,
        model_b_id: modelBType === 'saved' ? parseInt(modelBId) : undefined
      };

      const response = await axios.post('/api/compare-models', requestData);
      
      if (response.data.success) {
        setResult(response.data);
      } else {
        setError('Nastala chyba při porovnávání modelů: ' + response.data.message);
        setResult(null);
      }
    } catch (err: any) {
      console.error('Chyba při porovnávání modelů', err);
      setError('Nastala neočekávaná chyba při porovnávání modelů: ' + (err.response?.data?.detail || err.message));
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: string) => {
    setActiveTab(newValue);
  };

  const renderResultContent = () => {
    if (loading) {
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
          <CircularProgress />
        </Box>
      );
    }
    
    if (!result) {
      return (
        <Box sx={{ 
          height: '400px', 
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
            Vyberte modely a klikněte na tlačítko "Porovnat modely"
          </Typography>
        </Box>
      );
    }
    
    return (
      <Box sx={{ mt: 2 }}>
        {/* Základní informace o modelech */}
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6}>
            <Card sx={{ 
              backgroundColor: 'rgba(0, 0, 0, 0.2)', 
              height: '100%',
              border: '1px solid rgba(255, 255, 255, 0.05)',
            }}>
              <CardContent>
                <Typography variant="subtitle1" sx={{ fontWeight: 600, color: '#90caf9' }}>
                  Model A: {result.model_a.name}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Typ: {result.model_a.type === 'current' ? 'Aktuální model' : 'Uložený model'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6}>
            <Card sx={{ 
              backgroundColor: 'rgba(0, 0, 0, 0.2)', 
              height: '100%',
              border: '1px solid rgba(255, 255, 255, 0.05)',
            }}>
              <CardContent>
                <Typography variant="subtitle1" sx={{ fontWeight: 600, color: '#ce93d8' }}>
                  Model B: {result.model_b.name}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Typ: {result.model_b.type === 'current' ? 'Aktuální model' : 'Uložený model'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Záložky pro přepínání mezi tabulkou a vizualizací */}
        <Box sx={{ mb: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Tabs 
            value={activeTab} 
            onChange={handleTabChange} 
            textColor="primary"
            indicatorColor="primary"
          >
            <Tab 
              icon={<TableChartIcon />} 
              iconPosition="start" 
              label="Tabulkové zobrazení" 
              value="differences"
            />
            <Tab 
              icon={<VisibilityIcon />} 
              iconPosition="start" 
              label="Vizualizace rozdílů" 
              value="visualization"
              disabled={!result.visualization}
            />
          </Tabs>
        </Box>

        {/* Obsah podle aktivní záložky */}
        {activeTab === 'differences' ? (
          <>
            {/* Statistiky */}
            <Card sx={{ 
              mb: 3, 
              backgroundColor: 'rgba(0, 0, 0, 0.2)',
              border: '1px solid rgba(255, 255, 255, 0.05)',
            }}>
              <CardContent>
                <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
                  Statistika
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Typography variant="body2">
                      Počet pravidel v modelu A: <strong>{result.differences.links.count_a}</strong>
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2">
                      Počet pravidel v modelu B: <strong>{result.differences.links.count_b}</strong>
                    </Typography>
                  </Grid>
                  <Grid item xs={12}>
                    <Typography variant="body2">
                      Počet společných pravidel: <strong>{result.differences.links.common_count}</strong>
                    </Typography>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>

            {/* Sekce rozdílů v modelech */}
            <Card sx={{ 
              backgroundColor: 'rgba(0, 0, 0, 0.2)',
              border: '1px solid rgba(255, 255, 255, 0.05)',
            }}>
              <CardContent>
                <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
                  Rozdíly v modelech
                </Typography>
                
                {/* Rozdíly v typech modelů */}
                {Object.keys(result.differences.model_types).length > 0 ? (
                  <>
                    {Object.entries(result.differences.model_types).map(([modelType, differences]) => (
                      <Card key={modelType} sx={{ mb: 3, backgroundColor: 'rgba(0, 0, 0, 0.3)' }}>
                        <CardContent>
                          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2 }}>
                            Model typu: {modelType}
                          </Typography>
                          
                          {/* Pravidla pouze v modelu A */}
                          {differences.only_in_a.must.length > 0 || differences.only_in_a.must_not.length > 0 ? (
                            <Box sx={{ mb: 2 }}>
                              <Typography variant="body2" sx={{ color: '#90caf9', fontWeight: 600, mb: 1 }}>
                                Pravidla pouze v modelu A ({result.model_a.name}):
                              </Typography>
                              <List dense sx={{ bgcolor: 'rgba(0, 0, 0, 0.2)', borderRadius: 1 }}>
                                {differences.only_in_a.must.map((rule, index) => (
                                  <ListItem key={`must-a-${index}`}>
                                    <ListItemIcon sx={{ minWidth: 36 }}>
                                      <ErrorOutlineIcon sx={{ color: '#90caf9' }} />
                                    </ListItemIcon>
                                    <ListItemText 
                                      primary={`MUST: ${rule}`} 
                                      primaryTypographyProps={{
                                        variant: 'body2',
                                        sx: { 
                                          color: 'rgba(255, 255, 255, 0.8)',
                                          fontFamily: 'monospace'
                                        }
                                      }}
                                    />
                                  </ListItem>
                                ))}
                                {differences.only_in_a.must_not.map((rule, index) => (
                                  <ListItem key={`must-not-a-${index}`}>
                                    <ListItemIcon sx={{ minWidth: 36 }}>
                                      <ErrorOutlineIcon sx={{ color: '#90caf9' }} />
                                    </ListItemIcon>
                                    <ListItemText 
                                      primary={`MUST_NOT: ${rule}`} 
                                      primaryTypographyProps={{
                                        variant: 'body2',
                                        sx: { 
                                          color: 'rgba(255, 255, 255, 0.8)',
                                          fontFamily: 'monospace'
                                        }
                                      }}
                                    />
                                  </ListItem>
                                ))}
                              </List>
                            </Box>
                          ) : null}
                          
                          {/* Pravidla pouze v modelu B */}
                          {differences.only_in_b.must.length > 0 || differences.only_in_b.must_not.length > 0 ? (
                            <Box>
                              <Typography variant="body2" sx={{ color: '#ce93d8', fontWeight: 600, mb: 1 }}>
                                Pravidla pouze v modelu B ({result.model_b.name}):
                              </Typography>
                              <List dense sx={{ bgcolor: 'rgba(0, 0, 0, 0.2)', borderRadius: 1 }}>
                                {differences.only_in_b.must.map((rule, index) => (
                                  <ListItem key={`must-b-${index}`}>
                                    <ListItemIcon sx={{ minWidth: 36 }}>
                                      <ErrorOutlineIcon sx={{ color: '#ce93d8' }} />
                                    </ListItemIcon>
                                    <ListItemText 
                                      primary={`MUST: ${rule}`} 
                                      primaryTypographyProps={{
                                        variant: 'body2',
                                        sx: { 
                                          color: 'rgba(255, 255, 255, 0.8)',
                                          fontFamily: 'monospace'
                                        }
                                      }}
                                    />
                                  </ListItem>
                                ))}
                                {differences.only_in_b.must_not.map((rule, index) => (
                                  <ListItem key={`must-not-b-${index}`}>
                                    <ListItemIcon sx={{ minWidth: 36 }}>
                                      <ErrorOutlineIcon sx={{ color: '#ce93d8' }} />
                                    </ListItemIcon>
                                    <ListItemText 
                                      primary={`MUST_NOT: ${rule}`} 
                                      primaryTypographyProps={{
                                        variant: 'body2',
                                        sx: { 
                                          color: 'rgba(255, 255, 255, 0.8)',
                                          fontFamily: 'monospace'
                                        }
                                      }}
                                    />
                                  </ListItem>
                                ))}
                              </List>
                            </Box>
                          ) : null}
                          
                          {/* Pokud nejsou žádné rozdíly */}
                          {differences.only_in_a.must.length === 0 && 
                           differences.only_in_a.must_not.length === 0 && 
                           differences.only_in_b.must.length === 0 && 
                           differences.only_in_b.must_not.length === 0 && (
                            <Typography variant="body2" color="text.secondary">
                              Pro tento model nejsou žádné rozdíly v pravidlech.
                            </Typography>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    Mezi modely nejsou žádné rozdíly v pravidlech.
                  </Typography>
                )}
              </CardContent>
            </Card>
          </>
        ) : (
          <Box sx={{ mt: 2 }}>
            <Card sx={{ 
              p: 2, 
              backgroundColor: 'rgba(0, 0, 0, 0.2)',
              border: '1px solid rgba(255, 255, 255, 0.05)',
            }}>
              <CardContent>
                <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
                  Vizualizace rozdílů mezi modely
                </Typography>
                {result.visualization && (
                  <Box sx={{ 
                    height: '850px',
                    width: '100%',
                    backgroundColor: '#f8f9fa',
                    borderRadius: '4px',
                    position: 'relative',
                    boxShadow: '0 4px 8px rgba(0,0,0,0.15)',
                    overflow: 'hidden',
                    border: '1px solid #ddd'
                  }}>
                    <SigmaNetwork 
                      nodes={result.visualization.nodes} 
                      links={result.visualization.links}
                      showDifferences={true}
                      modelA={result.model_a.name}
                      modelB={result.model_b.name}
                    />
                  </Box>
                )}
              </CardContent>
            </Card>
            {result.visualization && (
              <Box sx={{ mt: 2, p: 2, backgroundColor: 'rgba(0, 0, 0, 0.2)', borderRadius: 1 }}>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  Zobrazeno {result.visualization.nodes.length} uzlů a {result.visualization.links.length} spojení mezi nimi.
                  Pro lepší zobrazení můžete použít kolečko myši pro přiblížení nebo oddálení. Najetím na uzel zobrazíte detailní informace.
                </Typography>

                {result.visualization_stats && (
                  <Box sx={{ mt: 1, borderTop: '1px solid rgba(255, 255, 255, 0.1)', pt: 1 }}>
                    <Typography variant="body2" fontWeight="bold" sx={{ mb: 0.5 }}>
                      Statistiky vizualizace:
                    </Typography>
                    <Grid container spacing={2}>
                      <Grid item xs={12} sm={6}>
                        <Box sx={{ pl: 1, borderLeft: '2px solid #4a90e2' }}>
                          <Typography variant="body2" color="text.secondary">
                            Pouze v modelu A: {result.visualization_stats.nodes_only_in_a} uzlů, {result.visualization_stats.links_only_in_a} spojení
                          </Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={12} sm={6}>
                        <Box sx={{ pl: 1, borderLeft: '2px solid #9c27b0' }}>
                          <Typography variant="body2" color="text.secondary">
                            Pouze v modelu B: {result.visualization_stats.nodes_only_in_b} uzlů, {result.visualization_stats.links_only_in_b} spojení
                          </Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={12}>
                        <Box sx={{ pl: 1, borderLeft: '2px solid #888888' }}>
                          <Typography variant="body2" color="text.secondary">
                            Společné: {result.visualization_stats.nodes_common} uzlů, {result.visualization_stats.links_common} spojení
                          </Typography>
                        </Box>
                      </Grid>
                    </Grid>
                  </Box>
                )}
              </Box>
            )}
          </Box>
        )}
      </Box>
    );
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
            <CompareArrowsIcon sx={{ mr: 1 }} />
            Porovnání modelů
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            Porovnejte dva modely (hypotézy) a zjistěte rozdíly mezi nimi.
          </Typography>
        </Box>

        <Grid container spacing={0}>
          {/* Sekce výběru modelů */}
          <Grid item xs={12} md={5} sx={{ 
            p: 3,
            borderRight: { xs: 'none', md: '1px solid rgba(255, 255, 255, 0.05)' }
          }}>
            <Typography 
              variant="h6" 
              component="h2" 
              sx={{ 
                mb: 3, 
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
              Výběr modelů pro porovnání
            </Typography>

            <Box sx={{ mb: 4 }}>
              <Button
                variant="outlined"
                color="primary"
                onClick={handleSaveCurrentModel}
                disabled={loading}
                fullWidth
                sx={{ mb: 3 }}
              >
                Uložit aktuální model
              </Button>
            </Box>

            <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 600 }}>Model A:</Typography>
            <Grid container spacing={2} sx={{ mb: 4 }}>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Typ modelu A</InputLabel>
                  <Select
                    value={modelAType}
                    label="Typ modelu A"
                    onChange={handleModelATypeChange}
                  >
                    <MenuItem value="current">Aktuální model</MenuItem>
                    <MenuItem value="saved">Uložený model</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth disabled={modelAType !== 'saved'}>
                  <InputLabel>Vyberte uložený model A</InputLabel>
                  <Select
                    value={modelAId}
                    label="Vyberte uložený model A"
                    onChange={handleModelAIdChange}
                    disabled={modelAType !== 'saved'}
                  >
                    {savedModels.map(model => (
                      <MenuItem key={`model-a-${model.id}`} value={model.id.toString()}>
                        {model.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
            </Grid>

            <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 600 }}>Model B:</Typography>
            <Grid container spacing={2} sx={{ mb: 4 }}>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Typ modelu B</InputLabel>
                  <Select
                    value={modelBType}
                    label="Typ modelu B"
                    onChange={handleModelBTypeChange}
                  >
                    <MenuItem value="current">Aktuální model</MenuItem>
                    <MenuItem value="saved">Uložený model</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth disabled={modelBType !== 'saved'}>
                  <InputLabel>Vyberte uložený model B</InputLabel>
                  <Select
                    value={modelBId}
                    label="Vyberte uložený model B"
                    onChange={handleModelBIdChange}
                    disabled={modelBType !== 'saved'}
                  >
                    {savedModels.map(model => (
                      <MenuItem key={`model-b-${model.id}`} value={model.id.toString()}>
                        {model.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
            </Grid>

            <Button
              variant="contained"
              color="primary"
              fullWidth
              onClick={handleCompare}
              disabled={loading}
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
              Porovnat modely
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

          {/* Výsledek sekce */}
          <Grid item xs={12} md={7} sx={{ p: 3 }}>
            <Typography 
              variant="h6" 
              component="h2" 
              sx={{ 
                mb: 3, 
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
              Výsledek porovnání
            </Typography>

            {renderResultContent()}
          </Grid>
        </Grid>
      </Paper>
    </Container>
  );
};

export default CompareModels; 