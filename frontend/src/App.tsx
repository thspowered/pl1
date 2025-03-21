import { useState, useEffect } from 'react';
import { 
  Box, 
  Container, 
  Typography, 
  Paper, 
  Button, 
  ThemeProvider, 
  createTheme, 
  CssBaseline,
  Snackbar,
  Alert,
  Grid,
  Divider,
  CircularProgress,
  Card,
  CardContent,
  Chip,
  FormControlLabel,
  Checkbox,
  Switch
} from '@mui/material';
import { useApi } from './hooks/useApi';
import { useExamples } from './hooks/useExamples';
import { useNotification } from './hooks/useNotification';
import SigmaNetwork from './components/SigmaNetwork';
import FileUploader from './components/FileUploader';
import ExampleList from './components/ExampleList';
import TrainingPanel from './components/TrainingPanel';
import TrainingResultDisplay from './components/TrainingResult';
import ModelControls from './components/ModelControls';
import LandingPage from './components/LandingPage';
import { TrainingResult, NetworkNode, NetworkLink } from './types';

// Vytvorenie tmavého motívu
const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#90caf9', // svetlomodrá
    },
    secondary: {
      main: '#ce93d8', // svetlofialová
    },
    success: {
      main: '#66bb6a', // zelená
    },
    error: {
      main: '#f44336', // červená
    }
  },
});

function App() {
  const { 
    isLoading: apiLoading, 
    error: apiError, 
    fetchModelStatus, 
    fetchDataset, 
    uploadDataset, 
    trainModel, 
    resetModel, 
    stepBack, 
    stepForward 
  } = useApi();
  
  const {
    examples,
    setExamples,
    showExamples,
    setShowExamples,
    processExamples,
    updateExamplesFromApi,
    toggleExampleSelection,
    selectAll,
    resetExamples,
    markExamplesAsUsed,
    getSelectedCounts
  } = useExamples();
  
  const {
    notification,
    closeNotification,
    showSuccess,
    showError,
    showInfo,
    showWarning
  } = useNotification();
  
  const [file, setFile] = useState<File | null>(null);
  const [fileContent, setFileContent] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isTraining, setIsTraining] = useState<boolean>(false);
  const [isUpdatingModel, setIsUpdatingModel] = useState<boolean>(false);
  const [trainingResult, setTrainingResult] = useState<TrainingResult | null>(null);
  const [modelStatus, setModelStatus] = useState<{
    model_initialized: boolean;
    used_examples_count: number;
    total_examples_count: number;
    objects_count: number;
    links_count: number;
    positive_examples_count: number;
    negative_examples_count: number;
  } | null>(null);
  const [modelHistory, setModelHistory] = useState<Array<any>>([]);
  const [historyIndex, setHistoryIndex] = useState<number>(-1);
  
  // State for model visualization
  const [nodes, setNodes] = useState<NetworkNode[]>([]);
  const [links, setLinks] = useState<NetworkLink[]>([]);
  const [trainingSteps, setTrainingSteps] = useState<any[]>([]);

  // Handle file upload
  const handleFileUpload = (content: string) => {
          setFileContent(content);
    setFile(new File([content], "uploaded-file.txt"));
    showSuccess('Súbor bol úspešne nahraný.');
  };

  // Process dataset
  const processDataset = async () => {
    if (!fileContent) {
      showWarning('Najprv nahrajte súbor s datasetom.');
      return;
    }
    
    setIsProcessing(true);
    
    try {
      // Process the file content to extract examples
      const parsedExamples = processExamples(fileContent);
      setExamples(parsedExamples);
      setShowExamples(true);
      
      showInfo(`Dataset bol úspešne spracovaný. Nájdených ${parsedExamples.length} príkladov. Získavam informácie o modeli...`);
      
      // Update model status and dataset
      setIsUpdatingModel(true);
      
      try {
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        const modelStatusResult = await fetchModelStatus();
        if (modelStatusResult.success && modelStatusResult.data) {
          setModelStatus(modelStatusResult.data);
        }
        
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        const datasetResult = await fetchDataset();
        if (datasetResult.success && datasetResult.data?.examples) {
          updateExamplesFromApi(datasetResult.data.examples);
        }
        
        showSuccess(`Dataset bol úspešne spracovaný. Nájdených ${parsedExamples.length} príkladov.`);
      } catch (error) {
        console.error('Chyba pri získavaní informácií o modeli:', error);
        showWarning(`Dataset bol spracovaný, ale nastala chyba pri získavaní informácií o modeli. Skúste obnoviť stránku.`);
      } finally {
        setIsUpdatingModel(false);
      }
    } catch (error) {
      console.error('Chyba pri spracovaní datasetu:', error);
      showError('Nastala chyba pri spracovaní datasetu.');
    } finally {
      setIsProcessing(false);
    }
  };

  // Update model after training
  const updateModelAfterTraining = async () => {
    try {
      const datasetResult = await fetchDataset();
      if (datasetResult.success && datasetResult.data?.examples) {
        updateExamplesFromApi(datasetResult.data.examples);
      }
      
      const modelStatusResult = await fetchModelStatus();
      if (modelStatusResult.success && modelStatusResult.data) {
        setModelStatus(modelStatusResult.data);
      }
    } catch (error) {
      console.error('Chyba pri aktualizácii stavu modelu:', error);
    }
  };

  // Train model
  const handleTrainModel = async (retrainAll: boolean) => {
    const selectedExamples = examples.filter(example => example.selected);
    
    if (selectedExamples.length === 0) {
      showWarning('Vyberte aspoň jeden príklad na trénovanie.');
      return;
    }
    
    // Check if we have at least one new example (not used in training)
    if (!retrainAll) {
      const newExamples = selectedExamples.filter(ex => !ex.usedInTraining);
      if (newExamples.length === 0) {
        showWarning('Všetky vybrané príklady už boli použité v trénovaní. Vyberte aspoň jeden nový príklad alebo zvoľte režim pretrénovania.');
        return;
      }
    }
    
    // Check if we have at least one positive and one negative example
    const hasPositive = selectedExamples.some(ex => ex.isPositive);
    const hasNegative = selectedExamples.some(ex => !ex.isPositive);
    
    // If model hasn't been initialized, check if we have at least one positive example
    if (!modelStatus?.model_initialized && !hasPositive) {
      showWarning('Pre inicializáciu modelu je potrebný aspoň jeden pozitívny príklad.');
      return;
    }
    
    // If model has been initialized, check if we have negative examples
    if (modelStatus?.model_initialized && !hasNegative && modelStatus.negative_examples_count === 0) {
      showWarning('Pre trénovanie modelu je potrebný aspoň jeden negatívny príklad.');
      return;
    }
    
    setIsTraining(true);
    
    try {
      // STEP 1: Upload dataset
      showInfo("1/4 Nahrávam dataset na server...");
      
      // Prepare data for API
      const apiExamples = selectedExamples.map(example => ({
        formula: example.formula,
        is_positive: example.isPositive,
        name: example.name
      }));
      
      const uploadResult = await uploadDataset(apiExamples);
      if (!uploadResult.success) {
        throw new Error(uploadResult.error || 'Chyba pri nahrávaní datasetu');
      }
      
      // STEP 2: Get dataset for example IDs
      showInfo("2/4 Získavam ID príkladov...");
      
      // Wait a moment for the server to process the dataset
      await new Promise(resolve => setTimeout(resolve, 500));
      
      const datasetResult = await fetchDataset();
      if (!datasetResult.success || !datasetResult.data?.examples) {
        throw new Error('Chyba pri získavaní datasetu zo servera');
      }
      
      // Get IDs of selected examples
      const selectedIds = selectedExamples.map(ex => {
        const apiExample = datasetResult.data.examples.find(e => 
          e.name === ex.name && e.formula === ex.formula && e.is_positive === ex.isPositive
        );
        return apiExample?.id;
      }).filter(id => id !== undefined) as number[];
      
      if (selectedIds.length === 0) {
        throw new Error('Nepodarilo sa nájsť ID vybraných príkladov v datasete');
      }
      
      // STEP 3: Train model
      const trainingMode = retrainAll ? 'úplné pretrénovanie' : 'inkrementálne dotrénovanie';
      showInfo(`3/4 Trénujem model s ${selectedIds.length} príkladmi (${trainingMode})...`);
      
      const trainingResults = await trainModel(selectedIds, retrainAll);
      if (!trainingResults.success || !trainingResults.data) {
        throw new Error(trainingResults.error || 'Chyba pri trénovaní modelu');
      }
      
      setTrainingResult(trainingResults.data);
      
      // STEP 4: Update local state
      showSuccess("4/4 Trénovanie dokončené! Aktualizujem rozhranie...");
      
      // Mark examples as used in training
      markExamplesAsUsed(selectedExamples);
      
      // STEP 5: Update model status and dataset
      setIsUpdatingModel(true);
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      try {
        await updateModelAfterTraining();
      } catch (error) {
        console.error('Chyba pri aktualizácii stavu po trénovaní:', error);
      } finally {
        setIsUpdatingModel(false);
      }
      
      // Add current model to history
      const newModelState = {
        model_visualization: trainingResults.data.model_visualization,
        training_steps: trainingResults.data.training_steps,
        used_examples_count: trainingResults.data.used_examples_count
      };
      
      // Remove states ahead if we've gone back and then trained
      const newHistory = modelHistory.slice(0, historyIndex + 1);
      setModelHistory([...newHistory, newModelState]);
      setHistoryIndex(newHistory.length);
      
      showSuccess(trainingResults.data.message || 'Model bol úspešne natrénovaný.');
    } catch (error) {
      console.error('Chyba pri trénovaní modelu:', error);
      setTrainingResult({
        success: false,
        message: error instanceof Error ? error.message : 'Nastala chyba pri trénovaní modelu.',
        model_updated: false,
        model_hypothesis: undefined,
        model_visualization: undefined,
        training_steps: undefined
      });
      
      showError(error instanceof Error ? error.message : 'Nastala chyba pri trénovaní modelu.');
    } finally {
      setIsTraining(false);
    }
  };

  // Reset app
  const handleReset = async () => {
    try {
      setIsLoading(true);
      const result = await resetModel();
      
      if (result.success) {
        // Reset visualization
        setNodes([]);
        setLinks([]);
        
        // Reset history
        setModelHistory([]);
        setHistoryIndex(-1);
        
        // Reset training steps
        setTrainingSteps([]);
        
        // Reset training result
    setTrainingResult(null);
        
        // Reset all examples - set usedInTraining to false
        resetExamples();
        
        showSuccess("Hypotéza bola vymazaná");
        
        // Update model status
        await fetchModelStatus(true);
      } else {
        showError("Nepodarilo sa vymazať hypotézu: " + (result.data?.message || "Neznáma chyba"));
      }
    } catch (error) {
      console.error("Chyba pri mazání hypotézy:", error);
      showError("Nastala chyba pri mazaní hypotézy");
    } finally {
      setIsLoading(false);
    }
  };

  // Step back in model history
  const handleStepBack = async () => {
    if (historyIndex > 0 || modelHistory.length === 0) {
      try {
        setIsLoading(true);
        const response = await stepBack();
        
        if (response.success && response.data) {
          // Set new history index
          setHistoryIndex(response.data.current_index);
          
          // Update application state from response
          if (response.data.model_visualization) {
            setNodes(response.data.model_visualization.nodes || []);
            setLinks(response.data.model_visualization.links || []);
          }
          
          // Update other relevant states
          if (response.data.training_steps) {
            setTrainingSteps(response.data.training_steps);
            // Update trainingResult to show history steps
            if (trainingResult) {
              setTrainingResult({
                ...trainingResult,
                training_steps: response.data.training_steps,
                model_visualization: response.data.model_visualization
              });
            } else {
              setTrainingResult({
                success: true,
                message: "Model obnovený na predchádzajúci krok",
                model_updated: true,
                training_steps: response.data.training_steps,
                model_visualization: response.data.model_visualization
              });
            }
          }
          
          // Update dataset to show used examples
          await fetchDataset(true);
          
          // Update model status
          await fetchModelStatus(true);
          
          showSuccess("Model obnovený na predchádzajúci krok");
        } else {
          showWarning(response.data?.message || "Nepodarilo sa vrátiť o krok späť");
        }
      } catch (error) {
        console.error("Chyba pri kroku späť:", error);
        showError("Nastala chyba pri kroku späť");
      } finally {
        setIsLoading(false);
      }
    }
  };

  // Step forward in model history
  const handleStepForward = async () => {
    if (historyIndex < modelHistory.length - 1 || modelHistory.length === 0) {
      try {
        setIsLoading(true);
        const response = await stepForward();
        
        if (response.success && response.data) {
          // Set new history index
          setHistoryIndex(response.data.current_index);
          
          // Update application state from response
          if (response.data.model_visualization) {
            setNodes(response.data.model_visualization.nodes || []);
            setLinks(response.data.model_visualization.links || []);
          }
          
          // Update other relevant states
          if (response.data.training_steps) {
            setTrainingSteps(response.data.training_steps);
            // Update trainingResult to show history steps
            if (trainingResult) {
              setTrainingResult({
                ...trainingResult,
                training_steps: response.data.training_steps,
                model_visualization: response.data.model_visualization
              });
            } else {
              setTrainingResult({
                success: true,
                message: "Model posunutý na nasledujúci krok",
                model_updated: true,
                training_steps: response.data.training_steps,
                model_visualization: response.data.model_visualization
              });
            }
          }
          
          // Update dataset to show used examples
          await fetchDataset(true);
          
          // Update model status
          await fetchModelStatus(true);
          
          showSuccess("Model posunutý na nasledujúci krok");
        } else {
          showWarning(response.data?.message || "Nepodarilo sa posunúť o krok vpred");
        }
      } catch (error) {
        console.error("Chyba pri kroku vpred:", error);
        showError("Nastala chyba pri kroku vpred");
      } finally {
        setIsLoading(false);
      }
    }
  };

  // Return to upload screen
  const goToUploadScreen = () => {
    setFile(null);
    setFileContent('');
    setExamples([]);
    setShowExamples(false);
        setTrainingResult(null);
    setModelStatus(null);
  };

  // Refresh graph
  const handleRefreshGraph = () => {
    if (trainingResult && trainingResult.model_visualization) {
      const modifiedVisualization = {
        nodes: [...trainingResult.model_visualization.nodes],
        links: [...trainingResult.model_visualization.links]
      };
      
      setTrainingResult(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          model_visualization: modifiedVisualization
        };
      });
    }
  };
  
  // Additional loading state for UI operations
  const [isLoading, setIsLoading] = useState<boolean>(false);

  useEffect(() => {
    // If examples are shown, get model status and dataset
    if (showExamples) {
      updateModelAfterTraining();
    }
  }, [showExamples]);

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Box
        sx={{
          minHeight: '100vh',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          background: 'linear-gradient(to bottom, #121212, #1e1e1e)',
          margin: 0,
          padding: 0,
          overflowX: 'hidden'
        }}
      >
        {/* Global loading indicator */}
        {(isTraining || isUpdatingModel) && (
          <Box
            sx={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              zIndex: 9999,
              height: '4px',
              backgroundColor: 'transparent',
              overflow: 'hidden'
            }}
          >
            <Box
              sx={{
                width: '100%',
                height: '100%',
                backgroundColor: 'primary.main',
                animation: 'progress 2s infinite linear',
                '@keyframes progress': {
                  '0%': {
                    transform: 'translateX(-100%)',
                  },
                  '100%': {
                    transform: 'translateX(100%)',
                  },
                },
              }}
            />
          </Box>
        )}
        
        {/* Training modal */}
        {isTraining && (
          <Box 
            sx={{ 
              position: 'fixed',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              zIndex: 9998,
              backgroundColor: 'background.paper',
              padding: 3,
              borderRadius: 2,
              boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
              width: '90%',
              maxWidth: '500px',
              textAlign: 'center'
            }}
          >
            <CircularProgress size={50} sx={{ mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              Trénovanie modelu...
            </Typography>
            <Typography variant="body1" gutterBottom sx={{ mb: 2 }}>
              Spracovávanie príkladov, prosím čakajte. Táto operácia môže trvať niekoľko sekúnd až minút v závislosti od počtu príkladov.
            </Typography>
            <Box sx={{ width: '100%' }}>
              <CircularProgress size={24} sx={{ mb: 2 }} />
            </Box>
          </Box>
        )}
        
        {/* App header - zobrazí sa len ak je showExamples true */}
        {showExamples && (
          <>
        <Box 
          sx={{ 
            p: 2, 
            borderBottom: '1px solid #333',
            display: 'flex',
            flexDirection: { xs: 'column', md: 'row' },
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 2
          }}
        >
          <Typography variant="h5" component="h1" sx={{ fontWeight: 700 }}>
            PL1-Winston Learner
          </Typography>
          
              {/* Model history navigation buttons */}
              {modelHistory.length > 0 && (
                <ModelControls 
                  historyIndex={historyIndex}
                  historyLength={modelHistory.length}
                  isLoading={isLoading || apiLoading}
                  onStepBack={handleStepBack}
                  onStepForward={handleStepForward}
                  onReset={handleReset}
                />
          )}
        </Box>
        
        <Container 
          sx={{ 
            py: 6, 
            width: '100%', 
            maxWidth: '100% !important',
            px: { xs: 2, sm: 4, md: 6 }
          }}
        >
          <Typography variant="h3" align="center" gutterBottom>
            PL1 Learning System
          </Typography>
          <Typography variant="h5" align="center" color="text.secondary" paragraph>
            Systém pre učenie konceptov pomocou symbolickej notácie predikátovej logiky prvého rádu
          </Typography>
        </Container>
          </>
        )}
        
        {/* Conditional rendering of content */}
        {!showExamples ? (
          // Use the new LandingPage component
          <LandingPage 
            file={file}
            isProcessing={isProcessing}
            onFileUpload={handleFileUpload}
            onProcessDataset={processDataset}
          />
        ) : (
          // Examples and training interface
          <Grid container spacing={4} sx={{ mt: 4, width: '100%', mx: 0 }}>
            <Grid item xs={12}>
              <Paper elevation={3} sx={{ 
                p: { xs: 2, sm: 3, md: 4 },
                height: 'auto',
                overflow: 'visible'
              }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                  <Typography variant="h5">
                    Príklady v datasete
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 2 }}>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Button 
                        variant="outlined" 
                        color="primary" 
                        onClick={goToUploadScreen}
                        startIcon={<span style={{ fontSize: '1.2rem' }}>📁</span>}
                        size="small"
                      >
                        Nahrať nový dataset
                      </Button>
                    </Box>
                  </Box>
                </Box>
                
                <Box sx={{ mb: 2 }}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={examples.every(ex => ex.selected)}
                        indeterminate={examples.some(ex => ex.selected) && !examples.every(ex => ex.selected)}
                        onChange={(e) => selectAll(e.target.checked)}
                      />
                    }
                    label="Vybrať všetky príklady"
                  />
                </Box>
                
                <Divider sx={{ mb: 2 }} />
                
                <Box sx={{ 
                  maxHeight: '65vh',
                  overflow: 'auto',
                  pr: 1
                }}>
                  {examples.map((example) => (
                    <Card key={example.id} sx={{ 
                      mb: 1.5, 
                      backgroundColor: example.usedInTraining ? 'rgba(25, 118, 210, 0.08)' : 'background.paper',
                      boxShadow: example.usedInTraining 
                        ? '0 0 0 1px rgba(25, 118, 210, 0.5), 0 2px 4px rgba(0,0,0,0.2)'
                        : '0 2px 4px rgba(0,0,0,0.2)',
                      position: 'relative',
                      transition: 'all 0.2s ease',
                      opacity: example.usedInTraining ? 0.9 : 1,
                      '&:hover': {
                        boxShadow: example.usedInTraining 
                          ? '0 0 0 1px rgba(25, 118, 210, 0.7), 0 4px 8px rgba(0,0,0,0.3)'
                          : '0 4px 8px rgba(0,0,0,0.3)',
                      }
                    }}>
                      {example.usedInTraining && (
                        <Box sx={{ 
                          position: 'absolute', 
                          top: 0, 
                          right: 0, 
                          backgroundColor: 'primary.main', 
                          color: 'white',
                          px: 1,
                          py: 0.5,
                          borderBottomLeftRadius: 8,
                          fontSize: '0.7rem',
                          fontWeight: 'bold',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 0.5
                        }}>
                          <span style={{ fontSize: '1rem' }}>✓</span> Použité v trénovaní
                        </Box>
                      )}
                      <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                        <Box sx={{ display: 'flex', alignItems: 'flex-start' }}>
                          <Checkbox
                            checked={example.selected}
                            onChange={() => toggleExampleSelection(example.id)}
                            disabled={example.usedInTraining}
                            sx={{ 
                              pt: 0, 
                              mt: 0, 
                              mr: 1,
                              '&.Mui-checked': {
                                color: example.usedInTraining ? 'primary.dark' : 'primary.main',
                              },
                              '&.Mui-disabled': {
                                color: example.usedInTraining ? 'primary.main' : 'text.disabled',
                              }
                            }}
                          />
                          <Box sx={{ width: '100%' }}>
                            <Box sx={{ 
                              display: 'flex', 
                              justifyContent: 'space-between', 
                              alignItems: 'center', 
                              mb: 0.5 
                            }}>
                              <Typography 
                                variant="subtitle1" 
                                sx={{ 
                                  fontWeight: 'bold', 
                                  fontSize: '0.95rem',
                                  color: example.usedInTraining ? 'primary.main' : 'text.primary'
                                }}
                              >
                                {example.name}
                                <Chip 
                                  label={example.isPositive ? "Pozitívny" : "Negatívny"} 
                                  color={example.isPositive ? "success" : "error"}
                                  size="small"
                                  sx={{ ml: 1, height: '20px', '& .MuiChip-label': { px: 1, py: 0.5, fontSize: '0.7rem' } }}
                                />
                              </Typography>
                            </Box>
                            <Typography 
                              variant="body2" 
                              sx={{ 
                                whiteSpace: 'pre-wrap', 
                                backgroundColor: example.usedInTraining ? 'rgba(25, 118, 210, 0.05)' : 'rgba(0, 0, 0, 0.2)', 
                                p: 1.5, 
                                borderRadius: 1,
                                fontFamily: 'monospace',
                                fontSize: '0.85rem',
                                width: '100%',
                                overflowX: 'hidden',
                                lineHeight: 1.4,
                                border: example.usedInTraining ? '1px solid rgba(25, 118, 210, 0.2)' : 'none'
                              }}
                            >
                              {example.formula}
                            </Typography>
                          </Box>
                        </Box>
                      </CardContent>
                    </Card>
                  ))}
                </Box>
                
                <Box sx={{ mt: 2, mb: 2 }}>
                  <TrainingPanel 
                    isTraining={isTraining}
                    onTrain={handleTrainModel}
                    selectedExamplesCount={getSelectedCounts().selectedCount}
                    usedInTrainingCount={getSelectedCounts().usedSelectedCount}
                  />
                </Box>
                
                {isUpdatingModel && (
                  <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
                    <Alert severity="info" sx={{ width: 'auto' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <CircularProgress size={20} sx={{ mr: 2 }} />
                        <Typography variant="body2">
                          Aktualizujem informácie o modeli a použitých príkladoch...
                        </Typography>
                      </Box>
                    </Alert>
                  </Box>
                )}
                
                <TrainingResultDisplay 
                  result={trainingResult}
                  onRefreshGraph={handleRefreshGraph}
                />
              </Paper>
            </Grid>
          </Grid>
        )}
      </Box>
      
      {/* Notifications */}
      <Snackbar
        open={notification.open}
        autoHideDuration={6000}
        onClose={closeNotification}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
        sx={{ 
          zIndex: 9999,
          '& .MuiAlert-root': {
            width: '100%',
            boxShadow: '0 4px 20px rgba(0,0,0,0.25)',
            fontSize: '1rem',
            alignItems: 'center'
          }
        }}
      >
        <Alert 
          onClose={closeNotification} 
          severity={notification.severity}
          variant="filled"
          sx={{ 
            width: '100%',
            minWidth: '300px',
            boxShadow: '0 4px 20px rgba(0,0,0,0.25)',
            '& .MuiAlert-message': {
              display: 'flex',
              alignItems: 'center',
              gap: 1
            }
          }}
        >
          {isTraining && notification.severity === 'info' && (
            <CircularProgress size={20} sx={{ mr: 1 }} color="inherit" />
          )}
          {notification.message}
        </Alert>
      </Snackbar>
  </ThemeProvider>
);
}

export default App;