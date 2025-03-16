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
  List,
  Checkbox,
  FormControlLabel,
  Divider,
  CircularProgress,
  Card,
  CardContent,
  Chip,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  LinearProgress,
  Switch,
  Tooltip,
  ListItem
} from '@mui/material';
import { useDropzone } from 'react-dropzone';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

// Vytvorenie tmavého motívu
const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#90caf9', // svetlomodrá
    },
    secondary: {
      main: '#f48fb1', // ružová
    },
    background: {
      default: '#121212', // tmavé pozadie
      paper: '#1e1e1e',   // tmavé pozadie pre komponenty
    },
  },
  typography: {
    h3: {
      fontWeight: 700,
      marginBottom: '1.5rem',
      fontSize: '2.5rem',
    },
    h5: {
      fontWeight: 600,
      marginBottom: '1rem',
    },
    body1: {
      fontSize: '1rem',
    },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          padding: 24,
          boxShadow: '0 8px 16px rgba(0, 0, 0, 0.4)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          fontWeight: 600,
          padding: '10px 20px',
        },
      },
    },
    MuiContainer: {
      styleOverrides: {
        root: {
          // Zabezpečí, že Container bude využívať maximálnu šírku
          maxWidth: '100% !important',
          padding: '0 24px',
        },
      },
    },
  },
});

// Typy pre príklady a dataset
interface Example {
  id: number;
  name: string;
  formula: string;
  isPositive: boolean;
  selected: boolean;
  usedInTraining?: boolean;
}

interface TrainingResult {
  success: boolean;
  message: string;
  model_updated: boolean;
  model_hypothesis?: string; // Textová reprezentácia hypotézy modelu
  model_visualization?: {
    nodes: Array<{
      id: string;
      name: string;
      class: string;
      category: string;
      attributes: Record<string, any>;
    }>;
    links: Array<{
      source: string;
      target: string;
      type: string;
    }>;
  };
  training_steps?: Array<{
    step: string;
    description: string;
    example_name?: string;
    is_positive?: boolean;
    positive_example?: string;
    negative_example?: string;
    negative_examples?: string[];
    heuristics?: Array<{
      name: string;
      description: string;
      example_id?: number;
      details?: Record<string, any>;
    }>;
  }>;
  used_examples_count?: number;
  total_examples_count?: number;
  training_mode?: string;
}

// Typy pre API odpovede
interface ApiExample {
  id: number;
  formula: string;
  is_positive: boolean;
  name: string;
  used_in_training?: boolean;
}

interface ApiDatasetResponse {
  examples: ApiExample[];
}

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [fileContent, setFileContent] = useState<string>('');
  const [examples, setExamples] = useState<Example[]>([]);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isTraining, setIsTraining] = useState<boolean>(false);
  const [isUpdatingModel, setIsUpdatingModel] = useState<boolean>(false);
  const [showExamples, setShowExamples] = useState<boolean>(false);
  const [trainingResult, setTrainingResult] = useState<TrainingResult | null>(null);
  const [notification, setNotification] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info' | 'warning';
  }>({
    open: false,
    message: '',
    severity: 'info',
  });
  const [modelStatus, setModelStatus] = useState<{
    model_initialized: boolean;
    used_examples_count: number;
    total_examples_count: number;
    objects_count: number;
    links_count: number;
    positive_examples_count: number;
    negative_examples_count: number;
  } | null>(null);
  const [retrainAll, setRetrainAll] = useState<boolean>(false);

  // Konfigurácia dropzone
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'text/plain': ['.txt', '.pl1'],
    },
    maxFiles: 1,
    onDrop: (acceptedFiles) => {
      if (acceptedFiles.length > 0) {
        const selectedFile = acceptedFiles[0];
        setFile(selectedFile);
        
        // Načítanie obsahu súboru
        const reader = new FileReader();
        reader.onload = (e) => {
          const content = e.target?.result as string;
          setFileContent(content);
        };
        reader.readAsText(selectedFile);
        
        setNotification({
          open: true,
          message: `Súbor "${selectedFile.name}" bol úspešne nahraný.`,
          severity: 'success',
        });
      }
    },
    onDropRejected: () => {
      setNotification({
        open: true,
        message: 'Neplatný formát súboru. Nahrajte súbor .txt alebo .pl1.',
        severity: 'error',
      });
    },
  });

  const handleCloseNotification = () => {
    setNotification({ ...notification, open: false });
  };

  // Spracovanie datasetu
  const processDataset = async () => {
    if (!fileContent) {
      setNotification({
        open: true,
        message: 'Najprv nahrajte súbor s datasetom.',
        severity: 'warning',
      });
      return;
    }
    
    setIsProcessing(true);
    
    try {
      // Rozdelenie obsahu súboru na jednotlivé príklady (oddelené prázdnymi riadkami)
      const exampleBlocks = fileContent.split(/\n\s*\n/);
      const parsedExamples: Example[] = [];
      
      exampleBlocks.forEach((block, index) => {
        if (!block.trim()) return; // Preskočiť prázdne bloky
        
        // Extrakcia názvu príkladu z komentára
        const nameMatch = block.match(/#\s*(.*?)(?:\n|$)/);
        const name = nameMatch ? nameMatch[1].trim() : `Príklad ${index + 1}`;
        
        // Určenie, či je príklad pozitívny alebo negatívny
        const isPositive = name.toLowerCase().includes('pozitívny') || 
                          !name.toLowerCase().includes('negatívny');
        
        // Odstránenie riadku s komentárom z formuly
        const formulaLines = block.trim().split('\n');
        const cleanedFormula = formulaLines.filter(line => !line.trim().startsWith('#')).join('\n');
        
        // Ensure the formula is properly formatted
        const formattedFormula = cleanedFormula
          .replace(/\s+/g, ' ')  // Replace multiple spaces with a single space
          .trim();               // Trim whitespace from the beginning and end
        
        // Normalize special characters
        const normalizedFormula = formattedFormula
          .replace(/\(/g, '(')   // Normalize opening parentheses
          .replace(/\)/g, ')')   // Normalize closing parentheses
          .replace(/,/g, ', ')   // Add space after commas
          .replace(/\s+/g, ' ')  // Clean up any double spaces
          .trim();
        
        if (normalizedFormula) {
          parsedExamples.push({
            id: index,
            name: name,
            formula: normalizedFormula,
            isPositive: isPositive,
            selected: false,
            usedInTraining: false
          });
        }
      });
      
      setExamples(parsedExamples);
      setShowExamples(true);
      
      // Po spracovaní datasetu získaj informácie o stave modelu a použitých príkladoch
      setNotification({
        open: true,
        message: `Dataset bol úspešne spracovaný. Nájdených ${parsedExamples.length} príkladov. Získavam informácie o modeli...`,
        severity: 'info',
      });
      
      // Nastavíme stav aktualizácie modelu
      setIsUpdatingModel(true);
      
      try {
        // Počkaj 1 sekundu pred aktualizáciou stavu modelu
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Získaj stav modelu
        const modelStatusSuccess = await fetchModelStatus();
        
        // Počkaj ďalšiu sekundu pred aktualizáciou datasetu
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Získaj dataset
        const datasetSuccess = await fetchDataset();
        
        if (modelStatusSuccess && datasetSuccess) {
          setNotification({
            open: true,
            message: `Dataset bol úspešne spracovaný. Nájdených ${parsedExamples.length} príkladov.`,
            severity: 'success',
          });
        } else {
          setNotification({
            open: true,
            message: `Dataset bol spracovaný, ale nastala chyba pri získavaní informácií o modeli. Skúste obnoviť stránku.`,
            severity: 'warning',
          });
        }
      } catch (error) {
        console.error('Chyba pri získavaní informácií o modeli:', error);
        setNotification({
          open: true,
          message: `Dataset bol spracovaný, ale nastala chyba pri získavaní informácií o modeli. Skúste obnoviť stránku.`,
          severity: 'warning',
        });
      } finally {
        setIsUpdatingModel(false);
      }
    } catch (error) {
      console.error('Chyba pri spracovaní datasetu:', error);
      setNotification({
        open: true,
        message: 'Nastala chyba pri spracovaní datasetu.',
        severity: 'error',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  // Zmena výberu príkladu
  const handleExampleSelection = (id: number) => {
    const example = examples.find(ex => ex.id === id);
    
    // Ak príklad už bol použitý v trénovaní, nemôžeme ho odznačiť
    if (example && example.usedInTraining) {
      setNotification({
        open: true,
        message: 'Príklad použitý v trénovaní nemôže byť odznačený.',
        severity: 'info',
      });
      return;
    }
    
    setExamples(prevExamples => 
      prevExamples.map(example => 
        example.id === id ? { ...example, selected: !example.selected } : example
      )
    );
  };

  // Výber všetkých príkladov
  const handleSelectAll = (selected: boolean) => {
    setExamples(examples.map(example => {
      // Ak príklad už bol použitý v trénovaní, nechaj ho označený
      if (example.usedInTraining) {
        return { ...example, selected: true };
      }
      return { ...example, selected };
    }));
  };

  // Získanie stavu modelu
  const fetchModelStatus = async (force = false) => {
    try {
      const response = await fetch('http://localhost:8000/api/model-status');
      if (response.ok) {
        const data = await response.json();
        console.log("Model status fetched:", data);
        
        // Upravené mapovanie údajov z API na formát používaný v UI
        setModelStatus({
          model_initialized: data.object_count > 0,
          used_examples_count: data.used_examples,
          total_examples_count: data.total_examples,
          objects_count: data.object_count,
          links_count: data.link_count,
          positive_examples_count: data.positive_examples?.used || 0,
          negative_examples_count: data.negative_examples?.used || 0
        });
        
        // Ak je force true, aktualizuj aj dataset
        if (force) {
          await fetchDataset(true);
        }
        return true;
      } else {
        console.error('Chyba pri získavaní stavu modelu:', response.statusText);
        return false;
      }
    } catch (error) {
      console.error('Chyba pri získavaní stavu modelu:', error);
      return false;
    }
  };

  // Získanie datasetu
  const fetchDataset = async (force = false) => {
    try {
      const response = await fetch('http://localhost:8000/api/dataset');
      if (response.ok) {
        const data = await response.json() as ApiDatasetResponse;
        
        console.log('Dataset response:', data);
        
        // Aktualizuj príklady s informáciou o tom, či boli použité v trénovaní
        setExamples(prevExamples => {
          // Ak nemáme žiadne príklady, vráť pôvodný stav
          if (!prevExamples || prevExamples.length === 0) {
            return prevExamples;
          }
          
          // Vytvor mapu pre rýchle vyhľadávanie príkladov podľa názvu, formuly a typu
          const apiExamplesMap = new Map<string, ApiExample>();
          data.examples.forEach(apiExample => {
            const key = `${apiExample.name}|${apiExample.formula}|${apiExample.is_positive}`;
            apiExamplesMap.set(key, apiExample);
          });
          
          const updatedExamples = prevExamples.map(example => {
            // Vytvor kľúč pre vyhľadávanie v mape
            const key = `${example.name}|${example.formula}|${example.isPositive}`;
            const apiExample = apiExamplesMap.get(key);
            
            // Ak sa našiel príklad a má nastavené used_in_training, použi túto hodnotu
            if (apiExample && apiExample.used_in_training !== undefined) {
              return {
                ...example, // Zachovaj pôvodné ID a ostatné vlastnosti
                usedInTraining: apiExample.used_in_training,
                selected: apiExample.used_in_training ? true : example.selected
              };
            }
            
            return example;
          });
          
          console.log('Updated examples:', updatedExamples.filter(ex => ex.usedInTraining).length);
          
          return updatedExamples;
        });
        return true;
      } else {
        console.error('Chyba pri získavaní datasetu:', response.statusText);
        return false;
      }
    } catch (error) {
      console.error('Chyba pri získavaní datasetu:', error);
      return false;
    }
  };

  // Aktualizácia stavu modelu po trénovaní
  const updateModelAfterTraining = async () => {
    try {
      // Najprv získaj dataset, aby sa aktualizovali informácie o použitých príkladoch
      const datasetResponse = await fetch('http://localhost:8000/api/dataset');
      if (datasetResponse.ok) {
        const data = await datasetResponse.json() as ApiDatasetResponse;
        console.log('Dataset response in updateModelAfterTraining:', data);
        
        // Aktualizuj príklady s informáciou o tom, či boli použité v trénovaní
        setExamples(prevExamples => {
          // Vytvor mapu pre rýchle vyhľadávanie príkladov podľa názvu, formuly a typu
          const apiExamplesMap = new Map<string, ApiExample>();
          data.examples.forEach(apiExample => {
            const key = `${apiExample.name}|${apiExample.formula}|${apiExample.is_positive}`;
            apiExamplesMap.set(key, apiExample);
          });
          
          const updatedExamples = prevExamples.map(example => {
            // Vytvor kľúč pre vyhľadávanie v mape
            const key = `${example.name}|${example.formula}|${example.isPositive}`;
            const apiExample = apiExamplesMap.get(key);
            
            // Ak sa našiel príklad a má nastavené used_in_training, použi túto hodnotu
            if (apiExample && apiExample.used_in_training !== undefined) {
              return {
                ...example, // Zachovaj pôvodné ID a ostatné vlastnosti
                usedInTraining: apiExample.used_in_training,
                selected: apiExample.used_in_training ? true : example.selected
              };
            }
            
            return example;
          });
          
          console.log('Updated examples in updateModelAfterTraining:', updatedExamples.filter(ex => ex.usedInTraining).length);
          
          return updatedExamples;
        });
      }
      
      // Potom získaj stav modelu
      const modelResponse = await fetch('http://localhost:8000/api/model-status');
      if (modelResponse.ok) {
        const modelData = await modelResponse.json();
        console.log('Model status response in updateModelAfterTraining:', modelData);
        
        // Aktualizuj stav modelu
        setModelStatus(modelData);
      }
    } catch (error) {
      console.error('Chyba pri aktualizácii stavu modelu:', error);
    }
  };

  // Pridám funkciu na získanie počtu vybraných príkladov
  const getSelectedExamplesCount = () => {
    const selectedCount = examples.filter(ex => ex.selected).length;
    const newSelectedCount = examples.filter(ex => ex.selected && !ex.usedInTraining).length;
    const usedSelectedCount = selectedCount - newSelectedCount;
    
    return { selectedCount, newSelectedCount, usedSelectedCount };
  };

  // Trénovanie modelu
  const trainModel = async () => {
    const selectedExamples = examples.filter(example => example.selected);
    
    if (selectedExamples.length === 0) {
      setNotification({
        open: true,
        message: 'Vyberte aspoň jeden príklad na trénovanie.',
        severity: 'warning',
      });
      return;
    }
    
    // Skontroluj, či máme aspoň jeden nový príklad (ktorý ešte nebol použitý v trénovaní)
    // Táto kontrola je potrebná len v režime inkrementálneho trénovania
    if (!retrainAll) {
      const newExamples = selectedExamples.filter(ex => !ex.usedInTraining);
      if (newExamples.length === 0) {
        setNotification({
          open: true,
          message: 'Všetky vybrané príklady už boli použité v trénovaní. Vyberte aspoň jeden nový príklad alebo zvoľte režim pretrénovania.',
          severity: 'warning',
        });
        return;
      }
    }
    
    // Skontroluj, či máme aspoň jeden pozitívny a jeden negatívny príklad
    const hasPositive = selectedExamples.some(ex => ex.isPositive);
    const hasNegative = selectedExamples.some(ex => !ex.isPositive);
    
    // Ak model ešte nebol inicializovaný, skontroluj, či máme aspoň jeden pozitívny príklad
    if (!modelStatus?.model_initialized && !hasPositive) {
      setNotification({
        open: true,
        message: 'Pre inicializáciu modelu je potrebný aspoň jeden pozitívny príklad.',
        severity: 'warning',
      });
      return;
    }
    
    // Ak model už bol inicializovaný, skontroluj, či máme aspoň jeden negatívny príklad
    // alebo či už máme nejaké negatívne príklady v histórii
    if (modelStatus?.model_initialized && !hasNegative && modelStatus.negative_examples_count === 0) {
      setNotification({
        open: true,
        message: 'Pre trénovanie modelu je potrebný aspoň jeden negatívny príklad.',
        severity: 'warning',
      });
      return;
    }
    
    setIsTraining(true);
    
    try {
      // KROK 1: Nahratie datasetu
      setNotification({
        open: true,
        message: "1/4 Nahrávam dataset na server...",
        severity: 'info',
      });
      
      // Príprava dát pre API
      const apiExamples = selectedExamples.map(example => ({
        formula: example.formula,
        is_positive: example.isPositive,
        name: example.name
      }));
      
      console.log('Sending examples to server:', JSON.stringify(apiExamples, null, 2));
      
      const uploadResponse = await fetch('http://localhost:8000/api/upload-dataset', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(apiExamples),
      });
      
      if (!uploadResponse.ok) {
        const errorText = await uploadResponse.text();
        let errorMessage = 'Chyba pri nahrávaní datasetu na server';
        
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.message || errorData.detail || errorMessage;
        } catch (e) {
          console.error('Failed to parse error response:', errorText);
        }
        
        throw new Error(errorMessage);
      }
      
      const uploadData = await uploadResponse.json();
      
      if (!uploadData.success) {
        throw new Error(uploadData.message || 'Chyba pri nahrávaní datasetu');
      }
      
      // KROK 2: Získanie datasetu pre ID príkladov
      setNotification({
        open: true,
        message: "2/4 Získavam ID príkladov...",
        severity: 'info',
      });
      
      // Počkaj chvíľu, aby mal server čas spracovať dataset
      await new Promise(resolve => setTimeout(resolve, 500));
      
      const datasetResponse = await fetch('http://localhost:8000/api/dataset');
      
      if (!datasetResponse.ok) {
        throw new Error('Chyba pri získavaní datasetu zo servera');
      }
      
      const datasetData = await datasetResponse.json() as ApiDatasetResponse;
      
      // Získaj ID vybraných príkladov
      const selectedIds = selectedExamples.map(ex => {
        const apiExample = datasetData.examples.find(e => 
          e.name === ex.name && e.formula === ex.formula && e.is_positive === ex.isPositive
        );
        return apiExample?.id;
      }).filter(id => id !== undefined) as number[];
      
      console.log('Selected IDs for training:', selectedIds);
      
      if (selectedIds.length === 0) {
        throw new Error('Nepodarilo sa nájsť ID vybraných príkladov v datasete');
      }
      
      // KROK 3: Trénovanie modelu
      const trainingMode = retrainAll ? 'úplné pretrénovanie' : 'inkrementálne dotrénovanie';
      setNotification({
        open: true,
        message: `3/4 Trénujem model s ${selectedIds.length} príkladmi (${trainingMode})...`,
        severity: 'info',
      });
      
      const trainingResponse = await fetch('http://localhost:8000/api/train', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          example_ids: selectedIds,
          retrain_all: retrainAll
        }),
      });
      
      if (!trainingResponse.ok) {
        const errorText = await trainingResponse.text();
        let errorMessage = 'Chyba pri trénovaní modelu';
        
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.message || errorData.detail || errorMessage;
        } catch (e) {
          console.error('Failed to parse error response:', errorText);
        }
        
        throw new Error(errorMessage);
      }
      
      const trainingData = await trainingResponse.json();
      
      console.log('Training response:', trainingData);
      
      // KROK 4: Aktualizácia lokálneho stavu
      setTrainingResult({
        success: trainingData.success,
        message: trainingData.message,
        model_updated: trainingData.model_updated,
        model_hypothesis: trainingData.model_hypothesis,
        model_visualization: trainingData.model_visualization,
        training_steps: trainingData.training_steps,
        used_examples_count: trainingData.used_examples_count,
        total_examples_count: trainingData.total_examples_count,
        training_mode: retrainAll ? 'retrained' : 'incremental'
      });
      
      // Zobraz notifikáciu o dokončení trénovania
      setNotification({
        open: true,
        message: "4/4 Trénovanie dokončené! Aktualizujem rozhranie...",
        severity: 'success',
      });
      
      // Aktualizuj príklady použité v trénovaní
      setExamples(prevExamples => {
        return prevExamples.map(example => {
          // Ak je príklad medzi vybranými, označ ho ako použitý v trénovaní
          if (selectedExamples.some(selected => 
            selected.name === example.name && 
            selected.formula === example.formula && 
            selected.isPositive === example.isPositive
          )) {
            return {
              ...example,
              usedInTraining: true,
              selected: true // Ponechaj ho označený
            };
          }
          return example;
        });
      });
      
      // KROK 5: Aktualizácia stavu modelu a datasetu
      setIsUpdatingModel(true);
      
      // Počkaj trochu dlhší čas, aby server mal čas spracovať všetky zmeny
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      try {
        // Aktualizuj stav modelu
        const modelResponse = await fetch('http://localhost:8000/api/model-status');
        if (modelResponse.ok) {
          const modelData = await modelResponse.json();
          setModelStatus(modelData);
          console.log("Model status updated:", modelData);
        } else {
          console.error('Chyba pri získavaní stavu modelu:', modelResponse.statusText);
        }
        
        // Aktualizuj dataset
        const finalDatasetResponse = await fetch('http://localhost:8000/api/dataset');
        if (finalDatasetResponse.ok) {
          const finalDatasetData = await finalDatasetResponse.json() as ApiDatasetResponse;
          
          // Aktualizuj príklady s informáciou o tom, či boli použité v trénovaní
          setExamples(prevExamples => {
            // Vytvor mapu pre rýchle vyhľadávanie príkladov podľa názvu, formuly a typu
            const apiExamplesMap = new Map<string, ApiExample>();
            finalDatasetData.examples.forEach(apiExample => {
              const key = `${apiExample.name}|${apiExample.formula}|${apiExample.is_positive}`;
              apiExamplesMap.set(key, apiExample);
            });
            
            const updatedExamples = prevExamples.map(example => {
              // Vytvor kľúč pre vyhľadávanie v mape
              const key = `${example.name}|${example.formula}|${example.isPositive}`;
              const apiExample = apiExamplesMap.get(key);
              
              // Ak sa našiel príklad a má nastavené used_in_training, použi túto hodnotu
              if (apiExample && apiExample.used_in_training !== undefined) {
                return {
                  ...example, // Zachovaj pôvodné ID a ostatné vlastnosti
                  usedInTraining: apiExample.used_in_training,
                  selected: apiExample.used_in_training ? true : example.selected
                };
              }
              
              return example;
            });
            
            console.log('Updated examples after training:', updatedExamples.filter(ex => ex.usedInTraining).length);
            
            return updatedExamples;
          });
        } else {
          console.error('Chyba pri získavaní datasetu:', finalDatasetResponse.statusText);
        }
      } catch (error) {
        console.error('Chyba pri aktualizácii stavu po trénovaní:', error);
      } finally {
        setIsUpdatingModel(false);
      }
      
      // Finálna notifikácia
      setNotification({
        open: true,
        message: trainingData.message || 'Model bol úspešne natrénovaný.',
        severity: 'success',
      });
      
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
      
      setNotification({
        open: true,
        message: error instanceof Error ? error.message : 'Nastala chyba pri trénovaní modelu.',
        severity: 'error',
      });
    } finally {
      setIsTraining(false);
    }
  };

  // Resetovanie aplikácie
  const resetApp = async () => {
    try {
      // Resetuj model na serveri
      await fetch('http://localhost:8000/api/reset', { method: 'POST' });
      
      // Resetuj stav aplikácie
      setTrainingResult(null);
      setModelStatus(null);
      
      // Odznač všetky príklady a nastav ich ako nepoužité v trénovaní
      setExamples(examples.map(example => ({
        ...example,
        selected: false,
        usedInTraining: false
      })));
      
      setNotification({
        open: true,
        message: 'Model bol úspešne resetovaný.',
        severity: 'success',
      });
      
      // Aktualizuj stav modelu
      await updateModelAfterTraining();
    } catch (error) {
      console.error('Chyba pri resetovaní modelu:', error);
      setNotification({
        open: true,
        message: 'Nastala chyba pri resetovaní modelu.',
        severity: 'error',
      });
    }
  };

  // Návrat na obrazovku nahrávania datasetu
  const goToUploadScreen = () => {
    setFile(null);
    setFileContent('');
    setExamples([]);
    setShowExamples(false);
    setTrainingResult(null);
    setModelStatus(null);
  };

  useEffect(() => {
    // Ak sú zobrazené príklady, získaj stav modelu a dataset
    if (showExamples) {
      updateModelAfterTraining();
    }
  }, [showExamples]);

  // Pridám useEffect, ktorý bude reagovať na zmeny v examples
  useEffect(() => {
    // Aktualizuj počty vybraných príkladov
    if (modelStatus) {
      const usedExamplesCount = examples.filter(ex => ex.usedInTraining).length;
      const positiveUsedCount = examples.filter(ex => ex.usedInTraining && ex.isPositive).length;
      const negativeUsedCount = examples.filter(ex => ex.usedInTraining && !ex.isPositive).length;
      
      // Aktualizuj modelStatus len ak sa počty zmenili
      if (usedExamplesCount !== modelStatus.used_examples_count ||
          positiveUsedCount !== modelStatus.positive_examples_count ||
          negativeUsedCount !== modelStatus.negative_examples_count) {
        
        setModelStatus(prevStatus => {
          if (!prevStatus) return null;
          
          return {
            ...prevStatus,
            used_examples_count: usedExamplesCount,
            positive_examples_count: positiveUsedCount,
            negative_examples_count: negativeUsedCount
          };
        });
      }
    }
  }, [examples]);

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
        {/* Globálny indikátor načítavania */}
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
        
        {/* Modálne okno s informáciou o trénovaní */}
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
            <LinearProgress />
          </Box>
        )}
        
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

          {!showExamples ? (
            // Zobrazenie nahrávacieho rozhrania
            <Grid container spacing={4} sx={{ mt: 4, width: '100%', mx: 0 }}>
              <Grid item xs={12} md={6}>
                <Paper elevation={3} sx={{ height: '100%', p: { xs: 2, sm: 3, md: 4 } }}>
                  <Typography variant="h5" gutterBottom>
                    Nahrať dataset
                  </Typography>
                  <Typography variant="body1" paragraph>
                    Nahrajte súbor s datasetom vo formáte PL1. Súbor by mal obsahovať pozitívne a negatívne príklady v symbolickej notácii.
                  </Typography>
                  
                  <Box
                    {...getRootProps()}
                    sx={{
                      border: '2px dashed',
                      borderColor: isDragActive ? 'primary.main' : 'grey.500',
                      borderRadius: 2,
                      p: { xs: 2, sm: 3, md: 4 },
                      mt: 2,
                      textAlign: 'center',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                      backgroundColor: isDragActive ? 'rgba(144, 202, 249, 0.1)' : 'transparent',
                      '&:hover': {
                        borderColor: 'primary.main',
                        backgroundColor: 'rgba(144, 202, 249, 0.05)',
                      },
                      width: '100%',
                    }}
                  >
                    <input {...getInputProps()} />
                    <CloudUploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
                    {isDragActive ? (
                      <Typography>Pustite súbor sem...</Typography>
                    ) : (
                      <Typography>
                        Pretiahnite sem súbor alebo kliknite pre výber súboru
                      </Typography>
                    )}
                    {file && (
                      <Typography variant="body2" sx={{ mt: 2, fontWeight: 'bold' }}>
                        Vybraný súbor: {file.name}
                      </Typography>
                    )}
                  </Box>
                  
                  <Button
                    variant="contained"
                    color="primary"
                    fullWidth
                    sx={{ mt: 3 }}
                    disabled={!file || isProcessing}
                    onClick={processDataset}
                  >
                    {isProcessing ? (
                      <>
                        <CircularProgress size={24} color="inherit" sx={{ mr: 1 }} />
                        Spracovávam...
                      </>
                    ) : (
                      'Spracovať dataset'
                    )}
                  </Button>
                </Paper>
              </Grid>
              
              <Grid item xs={12} md={6}>
                <Paper elevation={3} sx={{ height: '100%', p: { xs: 2, sm: 3, md: 4 } }}>
                  <Typography variant="h5" gutterBottom>
                    O projekte
                  </Typography>
                  <Typography variant="body1" paragraph>
                    Tento projekt implementuje systém pre učenie konceptov na základe pozitívnych a negatívnych príkladov. 
                    Využíva Winstonov algoritmus učenia konceptov a reprezentuje znalosti pomocou symbolickej notácie predikátovej logiky prvého rádu (PL1).
                  </Typography>
                  <Typography variant="body1" paragraph>
                    Hlavné funkcie systému:
                  </Typography>
                  <ul>
                    <li>
                      <Typography variant="body1">
                        Parsovanie a spracovanie príkladov v symbolickej notácii PL1
                      </Typography>
                    </li>
                    <li>
                      <Typography variant="body1">
                        Učenie konceptov pomocou Winstonovho algoritmu
                      </Typography>
                    </li>
                    <li>
                      <Typography variant="body1">
                        Porovnávanie nových príkladov s naučeným modelom
                      </Typography>
                    </li>
                    <li>
                      <Typography variant="body1">
                        Vizualizácia naučeného modelu ako sémantickej siete
                      </Typography>
                    </li>
                  </ul>
                </Paper>
              </Grid>
            </Grid>
          ) : (
            // Zobrazenie príkladov a trénovacieho rozhrania
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
                      {modelStatus && modelStatus.model_initialized && (
                        <Chip 
                          label={`Použité príklady: ${examples.filter(ex => ex.usedInTraining).length}/${examples.length}`}
                          color="primary"
                        />
                      )}
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
                        {modelStatus && modelStatus.model_initialized && (
                          <Button 
                            variant="outlined" 
                            color="error" 
                            onClick={resetApp}
                            startIcon={<span style={{ fontSize: '1.2rem' }}>🔄</span>}
                            size="small"
                          >
                            Resetovať model
                          </Button>
                        )}
                      </Box>
                    </Box>
                  </Box>
                  
                  {modelStatus && modelStatus.model_initialized && (
                    <Alert severity="info" sx={{ mb: 2 }}>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        <Typography variant="body2" fontWeight="bold">
                          Stav modelu:
                        </Typography>
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                          <Chip 
                            icon={<span style={{ fontSize: '1.2rem', marginRight: '4px' }}>🔄</span>}
                            label={`Použité príklady: ${modelStatus.used_examples_count}/${modelStatus.total_examples_count}`}
                            color="primary"
                            variant="outlined"
                            size="small"
                          />
                          <Chip 
                            icon={<span style={{ fontSize: '1.2rem', marginRight: '4px' }}>📊</span>}
                            label={`Objekty: ${modelStatus.objects_count}, Spojenia: ${modelStatus.links_count}`}
                            color="default"
                            variant="outlined"
                            size="small"
                          />
                          <Chip 
                            icon={<span style={{ fontSize: '1.2rem', marginRight: '4px' }}>✅</span>}
                            label={`Pozitívne príklady: ${modelStatus.positive_examples_count}`}
                            color="success"
                            variant="outlined"
                            size="small"
                          />
                          <Chip 
                            icon={<span style={{ fontSize: '1.2rem', marginRight: '4px' }}>❌</span>}
                            label={`Negatívne príklady: ${modelStatus.negative_examples_count}`}
                            color="error"
                            variant="outlined"
                            size="small"
                          />
                        </Box>
                        <Typography variant="body2" sx={{ mt: 1 }}>
                          Zostáva {modelStatus.total_examples_count - modelStatus.used_examples_count} nepoužitých príkladov.
                          {modelStatus.used_examples_count > 0 && ' Príklady použité v trénovaní sú automaticky označené a nemôžu byť odznačené.'}
                        </Typography>
                      </Box>
                    </Alert>
                  )}
                  
                  <Box sx={{ mb: 2 }}>
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={examples.every(ex => ex.selected)}
                          indeterminate={examples.some(ex => ex.selected) && !examples.every(ex => ex.selected)}
                          onChange={(e) => handleSelectAll(e.target.checked)}
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
                              onChange={() => handleExampleSelection(example.id)}
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
                    <Paper sx={{ p: 2 }}>
                      <Typography variant="h6" gutterBottom>
                        Trénovanie modelu
                      </Typography>
                      
                      {/* Pridaj prepínač režimu trénovania */}
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                        <Typography variant="body2">Inkrementálne dotrénovanie</Typography>
                        <Tooltip title={
                          retrainAll 
                            ? "Model sa natrénuje od začiatku na všetkých príkladoch (pôvodných + nových)" 
                            : "Model sa dotrénuje len na nových príkladoch"
                        }>
                          <Switch
                            checked={retrainAll}
                            onChange={(e) => setRetrainAll(e.target.checked)}
                            color="primary"
                          />
                        </Tooltip>
                        <Typography variant="body2">Úplné pretrénovanie</Typography>
                      </Box>
                      
                      <Button
                        variant="contained"
                        color="primary"
                        onClick={trainModel}
                        disabled={isTraining || examples.filter(ex => ex.selected).length === 0}
                        startIcon={isTraining ? <CircularProgress size={20} color="inherit" /> : null}
                      >
                        {isTraining 
                          ? 'Trénujem...' 
                          : retrainAll 
                            ? 'Pretrénovať model od začiatku' 
                            : 'Dotrénovať model'
                        }
                      </Button>
                    </Paper>
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
                  
                  {examples.filter(ex => ex.selected && ex.usedInTraining).length > 0 && !isUpdatingModel && (
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block', textAlign: 'center' }}>
                      ({examples.filter(ex => ex.selected && ex.usedInTraining).length} príkladov už bolo použitých v trénovaní)
                    </Typography>
                  )}
                  
                  {trainingResult && (
                    <Paper sx={{ p: 2, mt: 3, bgcolor: trainingResult.success ? 'success.dark' : 'error.dark' }}>
                      <Typography variant="h6" gutterBottom>
                        {trainingResult.success ? 'Trénovanie úspešné' : 'Chyba trénovania'}
                      </Typography>
                      <Typography variant="body1">{trainingResult.message}</Typography>
                      
                      {trainingResult.success && (
                        <Box sx={{ mt: 1 }}>
                          <Typography variant="body2" sx={{ mt: 1 }}>
                            Použitých {trainingResult.used_examples_count || 0} z {trainingResult.total_examples_count || 0} príkladov
                          </Typography>
                          <Typography variant="body2" sx={{ mt: 1 }}>
                            Režim trénovania: {trainingResult.training_mode === 'retrained' ? 'Úplné pretrénovanie' : 'Inkrementálne dotrénovanie'}
                          </Typography>
                        </Box>
                      )}
                    </Paper>
                  )}
                  
                  {trainingResult && trainingResult.training_steps && trainingResult.training_steps.length > 0 && (
                    <Box sx={{ mt: 4, mb: 4 }}>
                      <Typography variant="h6" gutterBottom>
                        Kroky trénovania
                      </Typography>
                      <Stepper orientation="vertical">
                        {trainingResult.training_steps.map((step, index) => (
                          <Step key={index} active={true} completed={true}>
                            <StepLabel>
                              {step.step === 'initialize' && 'Inicializácia modelu'}
                              {step.step === 'update' && 'Aktualizácia modelu'}
                              {step.step === 'update_multi' && 'Hromadná aktualizácia modelu'}
                              {step.step === 'error' && 'Chyba pri trénovaní'}
                            </StepLabel>
                            <StepContent>
                              <Typography variant="body1">{step.description}</Typography>
                              
                              {/* Zobrazenie detailov o použitých príkladoch */}
                              {step.example_name && (
                                <Box sx={{ mt: 1, mb: 1 }}>
                                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                                    Použitý príklad: {step.example_name} ({step.is_positive ? 'pozitívny' : 'negatívny'})
                                  </Typography>
                                </Box>
                              )}
                              
                              {step.negative_examples && step.negative_examples.length > 0 && (
                                <Box sx={{ mt: 1, mb: 1 }}>
                                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                                    Negatívne príklady:
                                  </Typography>
                                  <ul style={{ margin: '4px 0', paddingLeft: '20px' }}>
                                    {step.negative_examples.map((name, i) => (
                                      <li key={i}>
                                        <Typography variant="body2">{name}</Typography>
                                      </li>
                                    ))}
                                  </ul>
                                </Box>
                              )}
                              
                              {/* Zobrazenie použitých heuristík */}
                              {step.heuristics && step.heuristics.length > 0 && (
                                <Box sx={{ mt: 2 }}>
                                  <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'info.main' }}>
                                    Použité heuristiky, ktoré vykonali zmeny v modeli:
                                  </Typography>
                                  <Accordion sx={{ mt: 1, bgcolor: 'background.paper' }}>
                                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                      <Typography variant="body2">
                                        {step.heuristics.length} aplikovaných heuristík v tomto kroku
                                      </Typography>
                                    </AccordionSummary>
                                    <AccordionDetails>
                                      <List dense>
                                        {step.heuristics.map((heuristic, hIndex) => (
                                          <ListItem key={hIndex} sx={{ mb: 1, flexDirection: 'column', alignItems: 'flex-start' }}>
                                            <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'info.main' }}>
                                              {heuristic.description}
                                            </Typography>
                                            {heuristic.details && (
                                              <Box sx={{ mt: 0.5, ml: 2 }}>
                                                <Typography variant="caption" component="div" sx={{ color: 'text.secondary' }}>
                                                  Spracované objekty: {heuristic.details.good_objects} (pozitívny príklad) 
                                                  {heuristic.details.near_miss_objects !== undefined && `, ${heuristic.details.near_miss_objects} (negatívny príklad)`}
                                                </Typography>
                                                {heuristic.details.changes_made && (
                                                  <Typography variant="caption" component="div" sx={{ color: 'success.main' }}>
                                                    Pridaných spojení: {heuristic.details.changes_made}
                                                  </Typography>
                                                )}
                                                {heuristic.details.links_removed && (
                                                  <Typography variant="caption" component="div" sx={{ color: 'success.main' }}>
                                                    Odstránených spojení: {heuristic.details.links_removed}
                                                  </Typography>
                                                )}
                                              </Box>
                                            )}
                                          </ListItem>
                                        ))}
                                      </List>
                                    </AccordionDetails>
                                  </Accordion>
                                </Box>
                              )}
                            </StepContent>
                          </Step>
                        ))}
                      </Stepper>
                    </Box>
                  )}
                  
                  {trainingResult && trainingResult.model_hypothesis && (
                    <Accordion sx={{ mt: 3 }}>
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="h6">
                          Naučená hypotéza modelu
                        </Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Box sx={{ p: 2, backgroundColor: '#112', borderRadius: 1, overflow: 'auto' }}>
                          <Typography 
                            variant="body2" 
                            component="pre" 
                            sx={{ 
                              whiteSpace: 'pre-wrap', 
                              fontFamily: 'monospace',
                              fontSize: '0.85rem',
                              color: '#66f'
                            }}
                          >
                            {trainingResult.model_hypothesis}
                          </Typography>
                        </Box>
                        <Typography variant="body2" sx={{ mt: 2, color: 'text.secondary' }}>
                          Toto je formálny zápis odvodenej hypotézy. Vyjadruje, čo sa model naučil o koncepte na základe poskytnutých príkladov.
                        </Typography>
                      </AccordionDetails>
                    </Accordion>
                  )}
                  
                  {trainingResult && trainingResult.model_visualization && (
                    <Accordion sx={{ mt: 3 }}>
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="h6">
                          Vizualizácia naučeného modelu
                        </Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Typography variant="body2" gutterBottom>
                          Model obsahuje {trainingResult.model_visualization.nodes.length} objektov a {trainingResult.model_visualization.links.length} spojení.
                        </Typography>
                        
                        <Typography variant="subtitle1" sx={{ mt: 2, mb: 1 }}>
                          Objekty:
                        </Typography>
                        <List dense>
                          {trainingResult.model_visualization.nodes.map((node, index) => (
                            <li key={index}>
                              <Chip 
                                label={`${node.name} (${node.class})`} 
                                color={node.category === 'attribute' ? 'secondary' : 'primary'} 
                                size="small"
                                sx={{ m: 0.5 }}
                              />
                            </li>
                          ))}
                        </List>
                        
                        <Typography variant="subtitle1" sx={{ mt: 2, mb: 1 }}>
                          Spojenia:
                        </Typography>
                        <List dense>
                          {trainingResult.model_visualization.links.map((link, index) => (
                            <li key={index}>
                              <Chip 
                                label={`${link.source} → ${link.target} (${link.type})`} 
                                variant="outlined"
                                size="small"
                                sx={{ m: 0.5 }}
                              />
                            </li>
                          ))}
                        </List>
                      </AccordionDetails>
                    </Accordion>
                  )}
                </Paper>
              </Grid>
            </Grid>
          )}
        </Container>
        
        {/* Notifikácie */}
        <Snackbar
          open={notification.open}
          autoHideDuration={6000}
          onClose={handleCloseNotification}
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
            onClose={handleCloseNotification} 
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
      </Box>
    </ThemeProvider>
  );
}

export default App;