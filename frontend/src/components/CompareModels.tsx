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
  Tabs,
  AppBar,
  useTheme,
  useMediaQuery,
  alpha,
} from '@mui/material';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';
import InfoIcon from '@mui/icons-material/Info';
import VisibilityIcon from '@mui/icons-material/Visibility';
import TableChartIcon from '@mui/icons-material/TableChart';
import FactCheckIcon from '@mui/icons-material/FactCheck';
import { SavedModel, ModelComparisonResult } from '../types';
import NetworkGraph from './NetworkGraph';
import axios from 'axios';

interface CompareModelsProps {
  isLoading: boolean;
}

// Helper to format source, type, target into PL1 notation
const formatAsPL1 = (source: string, type: string, target: string): string => {
  const targetName = target.split('_').pop() || target;
  
  // Convert to PL1 notation based on type
  switch (type.toLowerCase()) {
    case 'must':
      return `Μ(${source}, ${target})`;
    case 'must_not':
      return `Ν(${source}, ${target})`;
    case 'must_be_a':
    case 'is_a':
      return `Ι(${source}, ${target})`;
    case 'has_part':
      return `Π(${source}, ${target})`;
    case 'has_attribute':
      return `A(${source}, ${targetName})`;
    case 'regular':
      return `${source} -regular-> ${target}`;
    case 'value':
      return `${source} -VALUE-> ${target}`;
    default:
      return `${source} -${type}-> ${target}`;
  }
};

// Helper function to convert relationship types to PL1 notation
const convertToPl1Notation = (link: string): string => {
  // Case 1: Handle format already in PL1 notation (e.g., "A(e, vykon)")
  if (link.match(/^[A-ZΑΙΜΝΠ]\([^,]+,\s*[^)]+\)$/)) {
    return link;
  }
  
  // Case 2: Handle LinkType format
  const linkTypeMatch = link.match(/(.*)\s+-LinkType\.(\w+)(?:_(\w+))?->\s+(.*)/);
  if (linkTypeMatch) {
    const [_, source, mainType, subType, target] = linkTypeMatch;
    return formatAsPL1(source, mainType, target);
  }
  
  // Case 3: Handle regular format (without LinkType prefix)
  const regularMatch = link.match(/(.*)\s+-([a-z_]+)->(.+)/);
  if (regularMatch) {
    const [_, source, type, target] = regularMatch;
    return formatAsPL1(source.trim(), type.trim(), target.trim());
  }
  
  // If no patterns match, return the original
  return link;
};

const CompareModels: React.FC<CompareModelsProps> = ({ isLoading }) => {
  const [modelA, setModelA] = useState<string>('current');
  const [modelB, setModelB] = useState<string>('saved');
  const [modelAId, setModelAId] = useState<string>('');
  const [modelBId, setModelBId] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [comparisonResult, setComparisonResult] = useState<ModelComparisonResult | null>(null);
  const [savedModels, setSavedModels] = useState<SavedModel[]>([]);
  const [showCommonRules, setShowCommonRules] = useState<boolean>(false);

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
    setModelA(event.target.value);
    if (event.target.value === 'current') {
      setModelAId('');
    }
  };

  const handleModelBTypeChange = (event: SelectChangeEvent) => {
    setModelB(event.target.value);
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
    if ((modelA === 'saved' && !modelAId) || (modelB === 'saved' && !modelBId)) {
      setError('Prosím, vyberte oba modely pro porovnání');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const requestData = {
        model_a_type: modelA,
        model_a_id: modelA === 'saved' ? parseInt(modelAId) : undefined,
        model_b_type: modelB,
        model_b_id: modelB === 'saved' ? parseInt(modelBId) : undefined
      };

      const response = await axios.post('/api/compare-models', requestData);
      
      if (response.data.success) {
        setComparisonResult(response.data);
      } else {
        setError('Nastala chyba při porovnávání modelů: ' + response.data.message);
        setComparisonResult(null);
      }
    } catch (err: any) {
      console.error('Chyba při porovnávání modelů', err);
      setError('Nastala neočekávaná chyba při porovnávání modelů: ' + (err.response?.data?.detail || err.message));
      setComparisonResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: string) => {
    // Handle tab change
  };

  const renderResultContent = () => {
    if (loading) {
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
          <CircularProgress />
        </Box>
      );
    }
    
    if (!comparisonResult) {
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
        {/* Obsah podle aktivní záložky */}
        {''} === 'differences' ? (
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
                  <Grid item xs={12}>
                    <Box sx={{ mb: 2, p: 2, bgcolor: 'rgba(0, 0, 0, 0.2)', borderRadius: 1 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        Přehled pravidel
                      </Typography>
                      
                      {/* Model A Stats */}
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
                        <Box sx={{ width: '25%', mr: 2 }}>
                          <Typography variant="body2" sx={{ color: '#90caf9' }}>
                            Model A: {comparisonResult.differences.links.count_a}
                          </Typography>
                        </Box>
                        <Box sx={{ width: '75%', display: 'flex' }}>
                          <Box 
                            sx={{ 
                              height: 20, 
                              bgcolor: '#90caf9', 
                              width: `${((comparisonResult.differences.links.count_a - (comparisonResult.differences.links.only_in_a.length)) / Math.max(comparisonResult.differences.links.count_a, comparisonResult.differences.links.count_b)) * 100}%`,
                              borderRadius: '4px 0 0 4px'
                            }} 
                          />
                          <Box 
                            sx={{ 
                              height: 20, 
                              bgcolor: '#4fc3f7',
                              width: `${(comparisonResult.differences.links.only_in_a.length / Math.max(comparisonResult.differences.links.count_a, comparisonResult.differences.links.count_b)) * 100}%`,
                              borderRadius: '0 4px 4px 0',
                              borderLeft: '2px solid rgba(0,0,0,0.3)'
                            }} 
                          />
                        </Box>
                      </Box>
                      
                      {/* Model B Stats */}
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
                        <Box sx={{ width: '25%', mr: 2 }}>
                          <Typography variant="body2" sx={{ color: '#ce93d8' }}>
                            Model B: {comparisonResult.differences.links.count_b}
                          </Typography>
                        </Box>
                        <Box sx={{ width: '75%', display: 'flex' }}>
                          <Box 
                            sx={{ 
                              height: 20, 
                              bgcolor: '#ce93d8', 
                              width: `${((comparisonResult.differences.links.count_b - (comparisonResult.differences.links.only_in_b.length)) / Math.max(comparisonResult.differences.links.count_a, comparisonResult.differences.links.count_b)) * 100}%`,
                              borderRadius: '4px 0 0 4px'
                            }} 
                          />
                          <Box 
                            sx={{ 
                              height: 20, 
                              bgcolor: '#ba68c8',
                              width: `${(comparisonResult.differences.links.only_in_b.length / Math.max(comparisonResult.differences.links.count_a, comparisonResult.differences.links.count_b)) * 100}%`,
                              borderRadius: '0 4px 4px 0',
                              borderLeft: '2px solid rgba(0,0,0,0.3)'
                            }} 
                          />
                        </Box>
                      </Box>
                      
                      {/* Legend */}
                      <Box sx={{ mt: 2, display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <Box sx={{ width: 12, height: 12, bgcolor: '#90caf9', mr: 1, borderRadius: 1 }} />
                          <Typography variant="caption">Společná A ({comparisonResult.differences.links.count_a - comparisonResult.differences.links.only_in_a.length})</Typography>
                        </Box>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <Box sx={{ width: 12, height: 12, bgcolor: '#4fc3f7', mr: 1, borderRadius: 1 }} />
                          <Typography variant="caption">Pouze v A ({comparisonResult.differences.links.only_in_a.length})</Typography>
                        </Box>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <Box sx={{ width: 12, height: 12, bgcolor: '#ce93d8', mr: 1, borderRadius: 1 }} />
                          <Typography variant="caption">Společná B ({comparisonResult.differences.links.count_b - comparisonResult.differences.links.only_in_b.length})</Typography>
                        </Box>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <Box sx={{ width: 12, height: 12, bgcolor: '#ba68c8', mr: 1, borderRadius: 1 }} />
                          <Typography variant="caption">Pouze v B ({comparisonResult.differences.links.only_in_b.length})</Typography>
                        </Box>
                      </Box>
                    </Box>
                  </Grid>
                  <Grid item xs={12}>
                    <Typography variant="body2" fontWeight="bold">
                      Shrnutí:
                    </Typography>
                    <Box sx={{ pl: 2, mt: 1 }}>
                      <Typography variant="body2">
                        Počet pravidel v modelu A: <strong>{comparisonResult.differences.links.count_a}</strong>
                      </Typography>
                      <Typography variant="body2">
                        Počet pravidel v modelu B: <strong>{comparisonResult.differences.links.count_b}</strong>
                      </Typography>
                      <Typography variant="body2">
                        Počet společných pravidel: <strong>{comparisonResult.differences.links.common_count}</strong>
                      </Typography>
                      <Typography variant="body2">
                        Pravidla pouze v A: <strong>{comparisonResult.differences.links.only_in_a.length}</strong>
                      </Typography>
                      <Typography variant="body2">
                        Pravidla pouze v B: <strong>{comparisonResult.differences.links.only_in_b.length}</strong>
                      </Typography>
                    </Box>
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
                
                {/* Detailní seznam rozdílných spojení mezi modely */}
                <Card sx={{ mb: 3, backgroundColor: 'rgba(0, 0, 0, 0.3)' }}>
                  <CardContent>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2 }}>
                      Rozdíly ve vztazích
                    </Typography>
                    
                    {/* Links pouze v modelu A */}
                    {comparisonResult.differences.links.only_in_a.length > 0 ? (
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="h6" sx={{ color: '#90caf9', fontWeight: 600, mb: 1 }}>
                          Vztahy pouze v modelu A ({comparisonResult.model_a.name}):
                        </Typography>
                        <List dense sx={{ bgcolor: 'rgba(0, 0, 0, 0.2)', borderRadius: 1 }}>
                          {comparisonResult.differences.links.only_in_a.map((link, index) => (
                            <ListItem key={`link-a-${index}`}>
                              <ListItemIcon sx={{ minWidth: 36 }}>
                                <span style={{ color: '#90caf9', fontSize: '20px' }}>ⓘ</span>
                              </ListItemIcon>
                              <ListItemText 
                                primary={convertToPl1Notation(link)} 
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
                    
                    {/* Links pouze v modelu B */}
                    {comparisonResult.differences.links.only_in_b.length > 0 ? (
                      <Box>
                        <Typography variant="h6" sx={{ color: '#ce93d8', fontWeight: 600, mb: 1 }}>
                          Vztahy pouze v modelu B ({comparisonResult.model_b.name}):
                        </Typography>
                        <List dense sx={{ bgcolor: 'rgba(0, 0, 0, 0.2)', borderRadius: 1 }}>
                          {comparisonResult.differences.links.only_in_b.map((link, index) => (
                            <ListItem key={`link-b-${index}`}>
                              <ListItemIcon sx={{ minWidth: 36 }}>
                                <span style={{ color: '#ce93d8', fontSize: '20px' }}>ⓘ</span>
                              </ListItemIcon>
                              <ListItemText 
                                primary={convertToPl1Notation(link)} 
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
                    
                    {/* Pokud nejsou žádné rozdíly ve vztazích */}
                    {comparisonResult.differences.links.only_in_a.length === 0 && comparisonResult.differences.links.only_in_b.length === 0 && (
                      <Typography variant="body2" color="text.secondary">
                        Mezi modely nejsou žádné rozdíly ve vztazích.
                      </Typography>
                    )}
                  </CardContent>
                </Card>
                
                {/* Společná pravidla mezi modely */}
                <Card sx={{ mb: 3, backgroundColor: 'rgba(0, 0, 0, 0.3)' }}>
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>
                        Společná pravidla mezi modely ({comparisonResult.differences.links.common_count})
                      </Typography>
                      <Button 
                        size="small" 
                        onClick={() => setShowCommonRules(!showCommonRules)}
                        sx={{ fontSize: '0.75rem' }}
                      >
                        {showCommonRules ? 'SKRÝT' : 'ZOBRAZIT'}
                      </Button>
                    </Box>
                    
                    {showCommonRules && comparisonResult.differences.links.common_count > 0 ? (
                      <Box>
                        <Box sx={{ 
                          display: 'flex', 
                          alignItems: 'center', 
                          mb: 2, 
                          backgroundColor: 'rgba(0, 0, 0, 0.3)',
                          p: 2,
                          borderRadius: 1
                        }}>
                          <span style={{ color: '#2196f3', fontSize: '24px', marginRight: '12px' }}>ⓘ</span>
                          <Typography variant="body2" color="text.secondary">
                            Společná pravidla jsou přítomna v obou modelech a představují sdílené vlastnosti modelů.
                          </Typography>
                        </Box>
                        
                        {/* Zde bychom potřebovali získat seznam společných pravidel z API */}
                        {/* Jako jednoduchý workaround můžeme extrahovat společné části z vizualizace */}
                        {comparisonResult.differences.links.common_links ? (
                          <List dense sx={{ bgcolor: 'rgba(0, 0, 0, 0.2)', borderRadius: 1, maxHeight: '300px', overflow: 'auto' }}>
                            {comparisonResult.differences.links.common_links.map((link, index) => (
                              <ListItem key={`common-link-${index}`}>
                                <ListItemIcon sx={{ minWidth: 36 }}>
                                  <span style={{ color: '#66bb6a', fontSize: '20px' }}>✅</span>
                                </ListItemIcon>
                                <ListItemText 
                                  primary={link}
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
                        ) : (
                          <Typography variant="body2" color="text.secondary">
                            Detailní informace o společných pravidlech nejsou k dispozici.
                          </Typography>
                        )}
                      </Box>
                    ) : (
                      !showCommonRules && comparisonResult.differences.links.common_count > 0 && (
                        <Typography variant="body2" color="text.secondary">
                          Klikněte na "ZOBRAZIT" pro zobrazení {comparisonResult.differences.links.common_count} společných pravidel.
                        </Typography>
                      )
                    )}
                    
                    {comparisonResult.differences.links.common_count === 0 && (
                      <Typography variant="body2" color="text.secondary">
                        Modely nemají žádná společná pravidla.
                      </Typography>
                    )}
                  </CardContent>
                </Card>
                
                {/* Rozdíly v typech modelů */}
                {Object.keys(comparisonResult.differences.model_types).length > 0 ? (
                  <>
                    {Object.entries(comparisonResult.differences.model_types).map(([modelType, differences]) => (
                      <Card key={modelType} sx={{ mb: 3, backgroundColor: 'rgba(0, 0, 0, 0.3)' }}>
                        <CardContent>
                          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2 }}>
                            Model typu: {modelType}
                          </Typography>
                          
                          {/* Pravidla pouze v modelu A */}
                          {differences.only_in_a.must.length > 0 || differences.only_in_a.must_not.length > 0 ? (
                            <Box sx={{ mb: 2 }}>
                              <Typography variant="body2" sx={{ color: '#90caf9', fontWeight: 600, mb: 1 }}>
                                Pravidla pouze v modelu A ({comparisonResult.model_a.name}):
                              </Typography>
                              <List dense sx={{ bgcolor: 'rgba(0, 0, 0, 0.2)', borderRadius: 1 }}>
                                {differences.only_in_a.must.map((rule, index) => (
                                  <ListItem key={`must-a-${index}`}>
                                    <ListItemIcon sx={{ minWidth: 36 }}>
                                      <ErrorOutlineIcon sx={{ color: '#90caf9' }} />
                                    </ListItemIcon>
                                    <ListItemText 
                                      primary={convertToPl1Notation(rule)} 
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
                                      primary={convertToPl1Notation(rule)} 
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
                                Pravidla pouze v modelu B ({comparisonResult.model_b.name}):
                              </Typography>
                              <List dense sx={{ bgcolor: 'rgba(0, 0, 0, 0.2)', borderRadius: 1 }}>
                                {differences.only_in_b.must.map((rule, index) => (
                                  <ListItem key={`must-b-${index}`}>
                                    <ListItemIcon sx={{ minWidth: 36 }}>
                                      <ErrorOutlineIcon sx={{ color: '#ce93d8' }} />
                                    </ListItemIcon>
                                    <ListItemText 
                                      primary={convertToPl1Notation(rule)} 
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
                                      primary={convertToPl1Notation(rule)} 
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
                {comparisonResult.visualization && (
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
                    <NetworkGraph 
                      nodes={comparisonResult.visualization.nodes} 
                      links={comparisonResult.visualization.links}
                      showDifferences={true}
                      modelA={comparisonResult.model_a?.name}
                      modelB={comparisonResult.model_b?.name}
                    />
                  </Box>
                )}
              </CardContent>
            </Card>
            {comparisonResult.visualization && (
              <Box sx={{ mt: 2, p: 2, backgroundColor: 'rgba(0, 0, 0, 0.2)', borderRadius: 1 }}>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  Zobrazeno {comparisonResult.visualization.nodes.length} uzlů a {comparisonResult.visualization.links.length} spojení mezi nimi.
                  Pro lepší zobrazení můžete použít kolečko myši pro přiblížení nebo oddálení. Najetím na uzel zobrazíte detailní informace.
                </Typography>

                {comparisonResult.visualization_stats && (
                  <Box sx={{ mt: 1, borderTop: '1px solid rgba(255, 255, 255, 0.1)', pt: 1 }}>
                    <Typography variant="body2" fontWeight="bold" sx={{ mb: 0.5 }}>
                      Statistiky vizualizace:
                    </Typography>
                    <Grid container spacing={2}>
                      <Grid item xs={12} sm={6}>
                        <Box sx={{ pl: 1, borderLeft: '2px solid #4a90e2' }}>
                          <Typography variant="body2" color="text.secondary">
                            Pouze v modelu A: {comparisonResult.visualization_stats.nodes_only_in_a} uzlů, {comparisonResult.visualization_stats.links_only_in_a} spojení
                          </Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={12} sm={6}>
                        <Box sx={{ pl: 1, borderLeft: '2px solid #9c27b0' }}>
                          <Typography variant="body2" color="text.secondary">
                            Pouze v modelu B: {comparisonResult.visualization_stats.nodes_only_in_b} uzlů, {comparisonResult.visualization_stats.links_only_in_b} spojení
                          </Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={12}>
                        <Box sx={{ pl: 1, borderLeft: '2px solid #888888' }}>
                          <Typography variant="body2" color="text.secondary">
                            Společné: {comparisonResult.visualization_stats.nodes_common} uzlů, {comparisonResult.visualization_stats.links_common} spojení
                          </Typography>
                        </Box>
                      </Grid>
                    </Grid>
                  </Box>
                )}
              </Box>
            )}
          </Box>
        )
      </Box>
    );
  };

  // Funkce pro získání jména modelu
  const getModelName = (modelType: string, modelId: number | null): string => {
    if (modelType === 'current') {
      return 'Aktuální model';
    } else if (modelType === 'saved' && modelId) {
      // Zde by mělo být získání jména uloženého modelu z cache nebo znovu z API
      return `Uložený model #${modelId}`;
    }
    return 'Neznámý model';
  };

  // Funkce pro zobrazení seznamu rozdílů
  const renderDifferenceList = (title: string, items: string[], color: string, icon: string = '•') => {
    if (!items || items.length === 0) return null;
    
    return (
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, color, mb: 1 }}>
          {title} ({items.length})
        </Typography>
        <Box sx={{ ml: 2 }}>
          {items.map((item, index) => (
            <Typography key={index} variant="body2" sx={{ color, my: 0.5 }}>
              <span style={{ marginRight: '8px' }}>{icon}</span>
              {item}
            </Typography>
          ))}
        </Box>
      </Box>
    );
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
        <Box sx={{ 
            p: 2, 
            borderBottom: 1, 
            borderColor: 'divider',
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
                Porovnání modelů
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                Porovnejte dva modely (hypotézy) a zjistěte rozdíly mezi nimi.
              </Typography>
            </Box>
        </Box>
        
        <Box sx={{ p: { xs: 2, md: 3 } }}>
          {/* Výběr modelů - nyní na celou šířku nahoře */}
          <Box sx={{ mb: 3 }}>
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
              <FactCheckIcon sx={{ mr: 1, color: '#90caf9' }} />
              Výběr modelů pro porovnání
            </Typography>
            
            <Grid container spacing={3}>
              {/* Model A selection */}
              <Grid item xs={12} md={6}>
                <Paper
                  variant="outlined"
                  sx={{
                    p: 2,
                    borderRadius: 2,
                    bgcolor: alpha('#fff', 0.05),
                    borderColor: alpha('#fff', 0.1)
                  }}
                >
                  <Typography variant="h6" sx={{ mb: 2, color: '#90caf9' }}>
                    Model A:
                  </Typography>
                  
                  <FormControl fullWidth variant="outlined" sx={{ mb: 2 }}>
                    <InputLabel id="model-a-type-label">Typ modelu A</InputLabel>
                    <Select
                      labelId="model-a-type-label"
                      id="model-a-type"
                      value={modelA}
                      onChange={handleModelATypeChange}
                      label="Typ modelu A"
                    >
                      <MenuItem value="current">Aktuální model</MenuItem>
                      <MenuItem value="saved">Uložený model</MenuItem>
                    </Select>
                  </FormControl>
                  
                  {modelA === 'saved' && (
                    <FormControl fullWidth variant="outlined">
                      <InputLabel id="model-a-id-label">Vyberte uložený model</InputLabel>
                      <Select
                        labelId="model-a-id-label"
                        id="model-a-id"
                        value={modelAId}
                        onChange={handleModelAIdChange}
                        label="Vyberte uložený model"
                      >
                        {savedModels.map(model => (
                          <MenuItem key={model.id} value={model.id.toString()}>
                            {model.name}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  )}
                </Paper>
              </Grid>

              {/* Model B selection */}
              <Grid item xs={12} md={6}>
                <Paper
                  variant="outlined"
                  sx={{
                    p: 2,
                    borderRadius: 2,
                    bgcolor: alpha('#fff', 0.05),
                    borderColor: alpha('#fff', 0.1)
                  }}
                >
                  <Typography variant="h6" sx={{ mb: 2, color: '#90caf9' }}>
                    Model B:
                  </Typography>
                  
                  <FormControl fullWidth variant="outlined" sx={{ mb: 2 }}>
                    <InputLabel id="model-b-type-label">Typ modelu B</InputLabel>
                    <Select
                      labelId="model-b-type-label"
                      id="model-b-type"
                      value={modelB}
                      onChange={handleModelBTypeChange}
                      label="Typ modelu B"
                    >
                      <MenuItem value="current">Aktuální model</MenuItem>
                      <MenuItem value="saved">Uložený model</MenuItem>
                    </Select>
                  </FormControl>
                  
                  {modelB === 'saved' && (
                    <FormControl fullWidth variant="outlined">
                      <InputLabel id="model-b-id-label">Vyberte uložený model</InputLabel>
                      <Select
                        labelId="model-b-id-label"
                        id="model-b-id"
                        value={modelBId}
                        onChange={handleModelBIdChange}
                        label="Vyberte uložený model"
                      >
                        {savedModels.map(model => (
                          <MenuItem key={model.id} value={model.id.toString()}>
                            {model.name}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  )}
                </Paper>
              </Grid>

              <Grid item xs={12}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}>
                  <Button
                    variant="outlined"
                    color="primary"
                    onClick={handleSaveCurrentModel}
                    disabled={loading}
                    startIcon={loading ? <CircularProgress size={20} color="inherit" /> : null}
                    sx={{ mr: 2 }}
                  >
                    Uložit aktuální model
                  </Button>
                  
                  <Button
                    variant="contained"
                    color="primary"
                    onClick={handleCompare}
                    disabled={loading || (modelA === 'saved' && !modelAId) || (modelB === 'saved' && !modelBId)}
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
                    {loading ? "Porovnávam..." : "Porovnat modely"}
                  </Button>
                </Box>
                
                {error && (
                  <Alert 
                    severity="error" 
                    variant="filled"
                    sx={{ borderRadius: 2, mt: 2 }}
                  >
                    {error}
                  </Alert>
                )}
              </Grid>
            </Grid>
          </Box>

          {/* Výsledek porovnání - zobrazuje se pouze když máme výsledek */}
          {comparisonResult ? (
            <>
              {/* Model summary boxes */}
              <Box sx={{ mb: 3 }}>
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
                  <FactCheckIcon sx={{ mr: 1, color: '#90caf9' }} />
                  Výsledek porovnání
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Paper
                      variant="outlined"
                      sx={{
                        p: 2,
                        borderRadius: 2,
                        bgcolor: alpha('#fff', 0.05),
                        borderColor: alpha('#fff', 0.1)
                      }}
                    >
                      <Typography variant="h6" sx={{ color: '#90caf9', mb: 1 }}>
                        Model A: {comparisonResult.model_a.name}
                      </Typography>
                      <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                        {comparisonResult.model_a.pl1_representation || 'Žádná formula k dispozici'}
                      </Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Paper
                      variant="outlined"
                      sx={{
                        p: 2,
                        borderRadius: 2,
                        bgcolor: alpha('#fff', 0.05),
                        borderColor: alpha('#fff', 0.1)
                      }}
                    >
                      <Typography variant="h6" sx={{ color: '#90caf9', mb: 1 }}>
                        Model B: {comparisonResult.model_b.name}
                      </Typography>
                      <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                        {comparisonResult.model_b.pl1_representation || 'Žádná formula k dispozici'}
                      </Typography>
                    </Paper>
                  </Grid>
                </Grid>
              </Box>

              {/* Statistika */}
              <Paper
                variant="outlined"
                sx={{ 
                  p: 3,
                  borderRadius: 2,
                  bgcolor: alpha('#000', 0.2),
                  borderColor: alpha('#fff', 0.1),
                  mb: 3
                }}
              >
                <Typography variant="h6" sx={{ mb: 2, color: 'white' }}>
                  Statistika
                </Typography>
                <Box sx={{ mb: 2, p: 2, bgcolor: 'rgba(0, 0, 0, 0.2)', borderRadius: 1 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Přehled pravidel
                  </Typography>
                  
                  {/* Model A Stats */}
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
                    <Box sx={{ width: '25%', mr: 2 }}>
                      <Typography variant="body2" sx={{ color: '#90caf9' }}>
                        Model A: {comparisonResult.differences.links.count_a}
                      </Typography>
                    </Box>
                    <Box sx={{ width: '75%', display: 'flex' }}>
                      <Box 
                        sx={{ 
                          height: 20, 
                          bgcolor: '#90caf9', 
                          width: `${((comparisonResult.differences.links.count_a - (comparisonResult.differences.links.only_in_a.length)) / Math.max(comparisonResult.differences.links.count_a, comparisonResult.differences.links.count_b)) * 100}%`,
                          borderRadius: '4px 0 0 4px'
                        }} 
                      />
                      <Box 
                        sx={{ 
                          height: 20, 
                          bgcolor: '#4fc3f7',
                          width: `${(comparisonResult.differences.links.only_in_a.length / Math.max(comparisonResult.differences.links.count_a, comparisonResult.differences.links.count_b)) * 100}%`,
                          borderRadius: '0 4px 4px 0',
                          borderLeft: '2px solid rgba(0,0,0,0.3)'
                        }} 
                      />
                    </Box>
                  </Box>
                  
                  {/* Model B Stats */}
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
                    <Box sx={{ width: '25%', mr: 2 }}>
                      <Typography variant="body2" sx={{ color: '#ce93d8' }}>
                        Model B: {comparisonResult.differences.links.count_b}
                      </Typography>
                    </Box>
                    <Box sx={{ width: '75%', display: 'flex' }}>
                      <Box 
                        sx={{ 
                          height: 20, 
                          bgcolor: '#ce93d8', 
                          width: `${((comparisonResult.differences.links.count_b - (comparisonResult.differences.links.only_in_b.length)) / Math.max(comparisonResult.differences.links.count_a, comparisonResult.differences.links.count_b)) * 100}%`,
                          borderRadius: '4px 0 0 4px'
                        }} 
                      />
                      <Box 
                        sx={{ 
                          height: 20, 
                          bgcolor: '#ba68c8',
                          width: `${(comparisonResult.differences.links.only_in_b.length / Math.max(comparisonResult.differences.links.count_a, comparisonResult.differences.links.count_b)) * 100}%`,
                          borderRadius: '0 4px 4px 0',
                          borderLeft: '2px solid rgba(0,0,0,0.3)'
                        }} 
                      />
                    </Box>
                  </Box>
                  
                  {/* Legend */}
                  <Box sx={{ mt: 2, display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <Box sx={{ width: 12, height: 12, bgcolor: '#90caf9', mr: 1, borderRadius: 1 }} />
                      <Typography variant="caption">Společná A ({comparisonResult.differences.links.count_a - comparisonResult.differences.links.only_in_a.length})</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <Box sx={{ width: 12, height: 12, bgcolor: '#4fc3f7', mr: 1, borderRadius: 1 }} />
                      <Typography variant="caption">Pouze v A ({comparisonResult.differences.links.only_in_a.length})</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <Box sx={{ width: 12, height: 12, bgcolor: '#ce93d8', mr: 1, borderRadius: 1 }} />
                      <Typography variant="caption">Společná B ({comparisonResult.differences.links.count_b - comparisonResult.differences.links.only_in_b.length})</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <Box sx={{ width: 12, height: 12, bgcolor: '#ba68c8', mr: 1, borderRadius: 1 }} />
                      <Typography variant="caption">Pouze v B ({comparisonResult.differences.links.only_in_b.length})</Typography>
                    </Box>
                  </Box>
                </Box>

                <Box sx={{ mb: 3 }}>
                  <Typography variant="body2" fontWeight="bold">
                    Shrnutí:
                  </Typography>
                  <Box sx={{ pl: 2, mt: 1 }}>
                    <Typography variant="body2">
                      Počet pravidel v modelu A: <strong>{comparisonResult.differences.links.count_a}</strong>
                    </Typography>
                    <Typography variant="body2">
                      Počet pravidel v modelu B: <strong>{comparisonResult.differences.links.count_b}</strong>
                    </Typography>
                    <Typography variant="body2">
                      Počet společných pravidel: <strong>{comparisonResult.differences.links.common_count}</strong>
                    </Typography>
                    <Typography variant="body2">
                      Pravidla pouze v A: <strong>{comparisonResult.differences.links.only_in_a.length}</strong>
                    </Typography>
                    <Typography variant="body2">
                      Pravidla pouze v B: <strong>{comparisonResult.differences.links.only_in_b.length}</strong>
                    </Typography>
                  </Box>
                </Box>
              </Paper>

              {/* Rozdíly v modelech */}
              <Paper
                variant="outlined"
                sx={{
                  p: 3,
                  borderRadius: 2,
                  bgcolor: alpha('#000', 0.2),
                  borderColor: alpha('#fff', 0.1),
                  mb: 3
                }}
              >
                <Typography variant="h6" sx={{ mb: 2, color: 'white' }}>
                  Rozdíly v modelech
                </Typography>
                
                {/* Detailní seznam rozdílných spojení mezi modely */}
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
                    Rozdíly ve vztazích
                  </Typography>
                  
                  {/* Links pouze v modelu A */}
                  {comparisonResult.differences.links.only_in_a.length > 0 ? (
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="h6" sx={{ color: '#90caf9', fontWeight: 600, mb: 1 }}>
                        Vztahy pouze v modelu A ({comparisonResult.model_a.name}):
                      </Typography>
                      <List dense sx={{ bgcolor: 'rgba(0, 0, 0, 0.2)', borderRadius: 1 }}>
                        {comparisonResult.differences.links.only_in_a.map((link, index) => (
                          <ListItem key={`link-a-${index}`}>
                            <ListItemIcon sx={{ minWidth: 36 }}>
                              <span style={{ color: '#90caf9', fontSize: '20px' }}>ⓘ</span>
                            </ListItemIcon>
                            <ListItemText 
                              primary={convertToPl1Notation(link)} 
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
                  
                  {/* Links pouze v modelu B */}
                  {comparisonResult.differences.links.only_in_b.length > 0 ? (
                    <Box>
                      <Typography variant="h6" sx={{ color: '#ce93d8', fontWeight: 600, mb: 1 }}>
                        Vztahy pouze v modelu B ({comparisonResult.model_b.name}):
                      </Typography>
                      <List dense sx={{ bgcolor: 'rgba(0, 0, 0, 0.2)', borderRadius: 1 }}>
                        {comparisonResult.differences.links.only_in_b.map((link, index) => (
                          <ListItem key={`link-b-${index}`}>
                            <ListItemIcon sx={{ minWidth: 36 }}>
                              <span style={{ color: '#ce93d8', fontSize: '20px' }}>ⓘ</span>
                            </ListItemIcon>
                            <ListItemText 
                              primary={convertToPl1Notation(link)} 
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
                  
                  {/* Pokud nejsou žádné rozdíly ve vztazích */}
                  {comparisonResult.differences.links.only_in_a.length === 0 && comparisonResult.differences.links.only_in_b.length === 0 && (
                    <Typography variant="body2" color="text.secondary">
                      Mezi modely nejsou žádné rozdíly ve vztazích.
                    </Typography>
                  )}
                </Box>
                
                <Divider sx={{ my: 2, bgcolor: alpha('#fff', 0.1) }} />
                
                {/* Společná pravidla mezi modely */}
                <Box sx={{ mb: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                      Společná pravidla mezi modely ({comparisonResult.differences.links.common_count})
                    </Typography>
                    <Button 
                      size="small" 
                      onClick={() => setShowCommonRules(!showCommonRules)}
                      sx={{ fontSize: '0.75rem' }}
                    >
                      {showCommonRules ? 'SKRÝT' : 'ZOBRAZIT'}
                    </Button>
                  </Box>
                  
                  {showCommonRules && comparisonResult.differences.links.common_count > 0 ? (
                    <Box>
                      <Box sx={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        mb: 2, 
                        backgroundColor: 'rgba(0, 0, 0, 0.3)',
                        p: 2,
                        borderRadius: 1
                      }}>
                        <span style={{ color: '#2196f3', fontSize: '24px', marginRight: '12px' }}>ⓘ</span>
                        <Typography variant="body2" color="text.secondary">
                          Společná pravidla jsou přítomna v obou modelech a představují sdílené vlastnosti modelů.
                        </Typography>
                      </Box>
                      
                      {/* Seznam společných pravidel */}
                      {comparisonResult.differences.links.common_links ? (
                        <Box sx={{ pl: 2 }}>
                          {comparisonResult.differences.links.common_links.map((link, index) => (
                            <Typography key={index} variant="body2" sx={{ color: '#9e9e9e', my: 0.5 }}>
                              <span style={{ marginRight: '8px', color: '#66bb6a' }}>✓</span>
                              {link}
                            </Typography>
                          ))}
                        </Box>
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          Detailní informace o společných pravidlech nejsou k dispozici.
                        </Typography>
                      )}
                    </Box>
                  ) : (
                    !showCommonRules && comparisonResult.differences.links.common_count > 0 && (
                      <Typography variant="body2" color="text.secondary">
                        Klikněte na "ZOBRAZIT" pro zobrazení {comparisonResult.differences.links.common_count} společných pravidel.
                      </Typography>
                    )
                  )}
                </Box>

                {/* Grafické zobrazení bude přidáno později */}
              </Paper>
            </>
          ) : (
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '300px' }}>
              <Typography variant="body1" sx={{ color: 'text.secondary' }}>
                Vyberte modely a klikněte na "Porovnat modely" pro zobrazení výsledků
              </Typography>
            </Box>
          )}
        </Box>
      </Paper>
    </Container>
  );
};

export default CompareModels; 