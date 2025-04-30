import { useState } from 'react';
import axios from 'axios';
import { 
  ApiDatasetResponse, 
  TrainingResult 
} from '../types';

const API_BASE_URL = 'http://localhost:8000';

export const useApi = () => {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchModelStatus = async (force = false) => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await fetch(`${API_BASE_URL}/api/model-status`);
      if (response.ok) {
        const data = await response.json();

        return {
          success: true,
          data: {
            model_initialized: data.object_count > 0,
            used_examples_count: data.used_examples,
            total_examples_count: data.total_examples,
            objects_count: data.object_count,
            links_count: data.link_count,
            positive_examples_count: data.positive_examples?.used || 0,
            negative_examples_count: data.negative_examples?.used || 0
          }
        };
      } else {
        setError('Chyba pri získavaní stavu modelu: ' + response.statusText);
        return { success: false, error: response.statusText };
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Neznáma chyba';
      setError(`Chyba pri získavaní stavu modelu: ${errorMessage}`);
      return { success: false, error: errorMessage };
    } finally {
      setIsLoading(false);
    }
  };

  const fetchDataset = async (force = false) => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await fetch(`${API_BASE_URL}/api/dataset`);
      if (response.ok) {
        const data = await response.json() as ApiDatasetResponse;
        return { success: true, data };
      } else {
        setError('Chyba pri získavaní datasetu: ' + response.statusText);
        return { success: false, error: response.statusText };
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Neznáma chyba';
      setError(`Chyba pri získavaní datasetu: ${errorMessage}`);
      return { success: false, error: errorMessage };
    } finally {
      setIsLoading(false);
    }
  };

  const uploadDataset = async (examples: { formula: string, is_positive: boolean, name: string }[]) => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await fetch(`${API_BASE_URL}/api/upload-dataset`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(examples),
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = 'Chyba pri nahrávaní datasetu na server';
        
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.message || errorData.detail || errorMessage;
        } catch (e) {
          console.error('Failed to parse error response:', errorText);
        }
        
        setError(errorMessage);
        return { success: false, error: errorMessage };
      }
      
      const data = await response.json();
      
      if (!data.success) {
        setError(data.message || 'Chyba pri nahrávaní datasetu');
        return { success: false, error: data.message || 'Chyba pri nahrávaní datasetu' };
      }
      
      return { success: true, data };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Neznáma chyba';
      setError(`Chyba pri nahrávaní datasetu: ${errorMessage}`);
      return { success: false, error: errorMessage };
    } finally {
      setIsLoading(false);
    }
  };

  const trainModel = async (exampleIds: number[], retrainAll: boolean) => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await fetch(`${API_BASE_URL}/api/train`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          example_ids: exampleIds,
          retrain_all: retrainAll
        }),
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = 'Chyba pri trénovaní modelu';
        
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.message || errorData.detail || errorMessage;
        } catch (e) {
          console.error('Failed to parse error response:', errorText);
        }
        
        setError(errorMessage);
        return { success: false, error: errorMessage };
      }
      
      const data = await response.json();
  
      const trainingResult: TrainingResult = {
        success: data.success || false,
        message: data.message || 'Model bol natrénovaný.',
        model_updated: data.model_updated || false,
        model_hypothesis: data.model_hypothesis,
        model_rules: data.model_rules,
        model_visualization: data.model_visualization || { nodes: [], links: [] },
        training_steps: data.training_steps || [],
        used_examples_count: data.used_examples_count,
        total_examples_count: data.total_examples_count,
        training_mode: retrainAll ? 'retrained' : 'incremental'
      };
      
      console.log('Training result received:', data);
      console.log('Extracted model_rules:', data.model_rules);
      
      return { success: true, data: trainingResult };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Neznáma chyba';
      setError(`Chyba pri trénovaní modelu: ${errorMessage}`);
      return { success: false, error: errorMessage };
    } finally {
      setIsLoading(false);
    }
  };

  const resetModel = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await axios.post(`${API_BASE_URL}/api/model/reset`);
      
      return { success: response.data.success, data: response.data };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Neznáma chyba';
      setError(`Chyba pri resetovaní modelu: ${errorMessage}`);
      return { success: false, error: errorMessage };
    } finally {
      setIsLoading(false);
    }
  };

  const stepBack = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await axios.post(`${API_BASE_URL}/api/model-history/step-back`);
      
      return { success: response.data.success, data: response.data };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Neznáma chyba';
      setError(`Chyba pri kroku späť: ${errorMessage}`);
      return { success: false, error: errorMessage };
    } finally {
      setIsLoading(false);
    }
  };

  const stepForward = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await axios.post(`${API_BASE_URL}/api/model-history/step-forward`);
      
      return { success: response.data.success, data: response.data };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Neznáma chyba';
      setError(`Chyba pri kroku vpred: ${errorMessage}`);
      return { success: false, error: errorMessage };
    } finally {
      setIsLoading(false);
    }
  };

  const compareExample = async (formula: string, validateAttributes: boolean = true) => {
    try {
      setIsLoading(true);
      setError(null);
      
      console.log(`Sending compare request with formula: ${formula}, validate_attributes: ${validateAttributes}`);
      
      const response = await axios.post(`${API_BASE_URL}/api/compare`, {
        formula: formula,
        is_positive: true, 
        name: "Porovnávaný príklad",
        validate_attributes: validateAttributes
      });
      
      console.log("Compare response:", response.data);
      return response.data;
    } catch (error) {
      console.error("Error in compareExample:", error);
      const errorMessage = error instanceof Error ? error.message : 'Neznáma chyba';
      setError(`Chyba pri porovnávaní príkladu: ${errorMessage}`);
      return { 
        is_valid: false, 
        violations: [`Chyba pri validácii príkladu: ${errorMessage}`], 
        satisfied_rules: [],
        model_type: "Unknown"
      };
    } finally {
      setIsLoading(false);
    }
  };

  const fetchHeuristicsHistory = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await axios.get(`${API_BASE_URL}/api/heuristics/history`);
      
      return { success: true, data: response.data };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Neznáma chyba';
      setError(`Chyba pri získavaní histórie heuristík: ${errorMessage}`);
      return { success: false, error: errorMessage };
    } finally {
      setIsLoading(false);
    }
  };

  return {
    isLoading,
    error,
    fetchModelStatus,
    fetchDataset,
    uploadDataset,
    trainModel,
    resetModel,
    stepBack,
    stepForward,
    compareExample,
    fetchHeuristicsHistory
  };
}; 