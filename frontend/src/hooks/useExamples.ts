import { useState } from 'react';
import { Example, ApiExample, ApiDatasetResponse } from '../types';

export const useExamples = () => {
  const [examples, setExamples] = useState<Example[]>([]);
  const [showExamples, setShowExamples] = useState<boolean>(false);

  // Process file content into examples
  const processExamples = (fileContent: string): Example[] => {
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
    
    return parsedExamples;
  };

  // Update examples from API response
  const updateExamplesFromApi = (apiExamples: ApiExample[]) => {
    setExamples(prevExamples => {
      // If we have no examples, return
      if (!prevExamples || prevExamples.length === 0) {
        return prevExamples;
      }
      
      // Create map for fast lookups
      const apiExamplesMap = new Map<string, ApiExample>();
      apiExamples.forEach(apiExample => {
        const key = `${apiExample.name}|${apiExample.formula}|${apiExample.is_positive}`;
        apiExamplesMap.set(key, apiExample);
      });
      
      const updatedExamples = prevExamples.map(example => {
        const key = `${example.name}|${example.formula}|${example.isPositive}`;
        const apiExample = apiExamplesMap.get(key);
        
        if (apiExample && apiExample.used_in_training !== undefined) {
          return {
            ...example,
            usedInTraining: apiExample.used_in_training,
            selected: apiExample.used_in_training ? true : example.selected
          };
        }
        
        return example;
      });
      
      return updatedExamples;
    });
  };

  // Toggle example selection
  const toggleExampleSelection = (id: number, selected?: boolean) => {
    setExamples(prevExamples => 
      prevExamples.map(example => {
        if (example.id === id) {
          // Ak je príklad už použitý v trénovaní, nemôžeme ho odznačiť
          if (example.usedInTraining && selected === false) {
            return example;
          }
          // Použijeme explicitne zadanú hodnotu alebo negáciu existujúcej
          return { ...example, selected: selected !== undefined ? selected : !example.selected };
        }
        return example;
      })
    );
    
    return true;
  };

  // Select or deselect all examples
  const selectAll = (selected: boolean) => {
    setExamples(examples.map(example => {
      // If example was already used in training, keep it selected
      if (example.usedInTraining) {
        return { ...example, selected: true };
      }
      return { ...example, selected };
    }));
  };

  // Reset all examples (used when clearing the model)
  const resetExamples = () => {
    setExamples(prevExamples => 
      prevExamples.map(example => ({
        ...example,
        selected: false,
        usedInTraining: false
      }))
    );
  };

  // Mark examples as used in training
  const markExamplesAsUsed = (selectedExamples: Example[]) => {
    setExamples(prevExamples => {
      return prevExamples.map(example => {
        if (selectedExamples.some(selected => 
          selected.name === example.name && 
          selected.formula === example.formula && 
          selected.isPositive === example.isPositive
        )) {
          return {
            ...example,
            usedInTraining: true,
            selected: true
          };
        }
        return example;
      });
    });
  };

  // Get counts of selected examples
  const getSelectedCounts = () => {
    const selectedCount = examples.filter(ex => ex.selected).length;
    const newSelectedCount = examples.filter(ex => ex.selected && !ex.usedInTraining).length;
    const usedSelectedCount = selectedCount - newSelectedCount;
    
    return { 
      selectedCount, 
      newSelectedCount, 
      usedSelectedCount 
    };
  };

  return {
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
  };
}; 