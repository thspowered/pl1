import { useState, useEffect, useCallback } from "react";
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
import { ModelControls } from './components/ModelControls';
import LandingPage from './components/LandingPage';
import ExamplesTrainingView from './components/ExamplesTrainingView';
import TrainingResult from './components/TrainingResult';
import { NetworkNode, NetworkLink, ApiExample, Example, ModelHistory, TrainingResult as TrainingResultType } from './types';
import axios from "axios";

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
  const [trainingResult, setTrainingResult] = useState<TrainingResultType | null>(null);
  const [modelStatus, setModelStatus] = useState<{
    model_initialized: boolean;
    used_examples_count: number;
    total_examples_count: number;
    objects_count: number;
    links_count: number;
    positive_examples_count: number;
    negative_examples_count: number;
  } | null>(null);
  const [modelHistory, setModelHistory] = useState<ModelHistory>({ current_index: -1, total_entries: 0 });
  const [graphUpdateKey, setGraphUpdateKey] = useState(0);
  
  // State for model visualization
  const [nodes, setNodes] = useState<NetworkNode[]>([]);
  const [links, setLinks] = useState<NetworkLink[]>([]);
  const [trainingSteps, setTrainingSteps] = useState<any[]>([]);

  const fetchExamples = useCallback(async () => {
    try {
      setIsUpdatingModel(true);
      const response = await axios.get<{ examples: ApiExample[] }>("/api/examples");
      const apiExamples = response.data.examples || [];
      
      if (apiExamples.length > 0) {
        const mappedExamples: Example[] = apiExamples.map((ex) => ({
          id: ex.id,
          name: ex.name,
          formula: ex.formula,
          isPositive: ex.is_positive,
          selected: false,
          usedInTraining: ex.used_in_training,
        }));
        setExamples(mappedExamples);
        console.log("Loaded examples:", mappedExamples.length);
      } else {
        console.log("No examples found in API response");
      }
    } catch (error) {
      console.error("Error fetching examples:", error);
      showWarning("Nastala chyba pri načítaní príkladov");
    } finally {
      setIsUpdatingModel(false);
    }
  }, []);

  const fetchModelInfo = useCallback(async () => {
    try {
      setIsUpdatingModel(true);
      const response = await axios.get("/api/model/info");
      const history = response.data.history || { current_index: -1, total_entries: 0 };
      setModelHistory(history);
    } catch (error) {
      console.error("Error fetching model info:", error);
    } finally {
      setIsUpdatingModel(false);
    }
  }, []);

  useEffect(() => {
    if (showExamples) {
      fetchExamples();
      fetchModelInfo();
    }
  }, [showExamples, fetchExamples, fetchModelInfo]);

  // Načítaj príklady pri prvom otvorení
  useEffect(() => {
    const checkForExamples = async () => {
      try {
        // Len kontrola, či existujú príklady na serveri
        const response = await axios.get<{ examples: ApiExample[] }>("/api/examples");
        const apiExamples = response.data.examples || [];
        
        if (apiExamples.length > 0) {
          // Ak existujú príklady, nastav showExamples na true a načítaj ich
          setShowExamples(true);
        }
      } catch (error) {
        console.error("Error checking for examples:", error);
      }
    };
    
    checkForExamples();
  }, []);

  // Handle file upload
  const handleFileUpload = (content: string) => {
    setFileContent(content);
    setFile(new File([content], "uploaded-file.txt"));
    showSuccess('Súbor bol úspešne nahraný.');
    
    // Skúsime hneď spracovať príklady pre lepšiu odozvu
    if (content) {
      processDataset();
    }
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
      
      if (parsedExamples.length === 0) {
        showWarning('Nenašli sa žiadne príklady v súbore. Skontrolujte formát súboru.');
        setIsProcessing(false);
        return;
      }
      
      setExamples(parsedExamples);
      setShowExamples(true);
      
      showInfo(`Dataset bol úspešne spracovaný. Nájdených ${parsedExamples.length} príkladov. Získavam informácie o modeli...`);
      
      // Update model status and dataset
      setIsUpdatingModel(true);
      
      try {
        await new Promise(resolve => setTimeout(resolve, 500));
        
        const modelStatusResult = await fetchModelStatus();
        if (modelStatusResult.success && modelStatusResult.data) {
          setModelStatus(modelStatusResult.data);
        }
        
        await new Promise(resolve => setTimeout(resolve, 500));
        
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
      
      // Update model history via API will handle history changes
      await fetchModelInfo();
      
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
      setIsUpdatingModel(true);
      
      // Informujeme používateľa, že začíname resetovať model
      showInfo("Prebieha resetovanie modelu a histórie...");
      
      // Resetujeme model na serveri
      await axios.post("/api/model/reset");
      await fetchModelInfo();
      setGraphUpdateKey(prev => prev + 1);
      
      // Reset visualization
      setNodes([]);
      setLinks([]);
      
      // Reset history
      setModelHistory({ current_index: -1, total_entries: 0 });
      
      // Reset training steps
      setTrainingSteps([]);
      
      // Reset training result
    setTrainingResult(null);
      
      // Reset all examples - set usedInTraining to false
      resetExamples();
      
      // Update model status
      await fetchModelStatus(true);
      
      // Zobrazíme úspešnú notifikáciu s kompletnou informáciou
      showSuccess("Model a história boli úspešne vymazané. Príklady boli resetované a môžu byť znova použité na trénovanie.");
    } catch (error) {
      console.error("Chyba pri resetovaní modelu:", error);
      showError("Nastala chyba pri resetovaní modelu a histórie. Skúste to znova neskôr.");
    } finally {
      setIsUpdatingModel(false);
    }
  };

  // Step back in model history
  const handleStepBack = async () => {
    if (modelHistory.current_index > 0 || modelHistory.total_entries === 0) {
      try {
        setIsUpdatingModel(true);
        const response = await axios.post("/api/model/history/step_back");
        
        // Aktualizujeme stav použitých príkladov
        if (response.data.success && response.data.used_example_ids) {
          // Vytvoríme nový stav príkladov s aktualizovaným príznakom usedInTraining
          const updatedExamples = examples.map(example => ({
            ...example,
            usedInTraining: response.data.used_example_ids.includes(example.id)
          }));
          setExamples(updatedExamples);
          showInfo(`Model obnovený na stav z histórie (krok ${response.data.current_index + 1}/${modelHistory.total_entries})`);
          
          // Aktualizujeme trénovací výsledok
          if (response.data.model_hypothesis) {
            setTrainingResult(prevResult => ({
              ...prevResult || {},
              success: true,
              message: 'Model obnovený z histórie',
              model_updated: response.data.model_updated,
              model_hypothesis: response.data.model_hypothesis,
              model_visualization: response.data.model_visualization,
              training_steps: response.data.training_steps
            }));
          }
          
          // Aktualizujeme vizualizáciu modelu
          if (response.data.model_visualization) {
            setNodes(response.data.model_visualization.nodes || []);
            setLinks(response.data.model_visualization.links || []);
          }
          
          // Aktualizujeme kroky trénovania
          if (response.data.training_steps) {
            setTrainingSteps(response.data.training_steps);
          }
        }
        
        // Aktualizujeme informácie o modeli a histórii
        await fetchModelInfo();
        setGraphUpdateKey(prev => prev + 1);
      } catch (error) {
        console.error("Chyba pri kroku späť:", error);
        showError("Nastala chyba pri kroku späť");
      } finally {
        setIsUpdatingModel(false);
      }
    }
  };

  // Step forward in model history
  const handleStepForward = async () => {
    if (modelHistory.current_index < modelHistory.total_entries - 1 || modelHistory.total_entries === 0) {
      try {
        setIsUpdatingModel(true);
        const response = await axios.post("/api/model/history/step_forward");
        
        // Aktualizujeme stav použitých príkladov
        if (response.data.success && response.data.used_example_ids) {
          // Vytvoríme nový stav príkladov s aktualizovaným príznakom usedInTraining
          const updatedExamples = examples.map(example => ({
            ...example,
            usedInTraining: response.data.used_example_ids.includes(example.id)
          }));
          setExamples(updatedExamples);
          showInfo(`Model posunutý na stav z histórie (krok ${response.data.current_index + 1}/${modelHistory.total_entries})`);
          
          // Aktualizujeme trénovací výsledok
          if (response.data.model_hypothesis) {
            setTrainingResult(prevResult => ({
              ...prevResult || {},
              success: true,
              message: 'Model obnovený z histórie',
              model_updated: response.data.model_updated,
              model_hypothesis: response.data.model_hypothesis,
              model_visualization: response.data.model_visualization,
              training_steps: response.data.training_steps
            }));
          }
          
          // Aktualizujeme vizualizáciu modelu
          if (response.data.model_visualization) {
            setNodes(response.data.model_visualization.nodes || []);
            setLinks(response.data.model_visualization.links || []);
          }
          
          // Aktualizujeme kroky trénovania
          if (response.data.training_steps) {
            setTrainingSteps(response.data.training_steps);
          }
        }
        
        // Aktualizujeme informácie o modeli a histórii
        await fetchModelInfo();
        setGraphUpdateKey(prev => prev + 1);
      } catch (error) {
        console.error("Chyba pri kroku vpred:", error);
        showError("Nastala chyba pri kroku vpred");
      } finally {
        setIsUpdatingModel(false);
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
    setGraphUpdateKey(prev => prev + 1);
  };
  
  // Additional loading state for UI operations
  const [isLoading, setIsLoading] = useState<boolean>(false);

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
          // Use the new ExamplesTrainingView component with ModelControls
          <ExamplesTrainingView 
            examples={examples}
            isTraining={isTraining}
            isUpdatingModel={isUpdatingModel}
            trainingResult={trainingResult}
            trainingSteps={trainingSteps}
            isLoading={isLoading}
            historyIndex={modelHistory.current_index}
            historyLength={modelHistory.total_entries}
            onExampleSelect={toggleExampleSelection}
            onSelectAll={selectAll}
            onTrain={handleTrainModel}
            onStepBack={handleStepBack}
            onStepForward={handleStepForward}
            onReset={handleReset}
            onFileUpload={goToUploadScreen}
          />
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