import { useState } from 'react';
import { Example, ApiExample, ApiDatasetResponse } from '../types';

export const useExamples = () => {
  const [examples, setExamples] = useState<Example[]>([]);
  const [showExamples, setShowExamples] = useState<boolean>(false);


  const processExamples = (fileContent: string): Example[] => {
    const exampleBlocks = fileContent.split(/\n\s*\n/);
    const parsedExamples: Example[] = [];
    
    exampleBlocks.forEach((block, index) => {
      if (!block.trim()) return; 
      
      const nameMatch = block.match(/#\s*(.*?)(?:\n|$)/);
      const name = nameMatch ? nameMatch[1].trim() : `Príklad ${index + 1}`;
      
      const isPositive = name.toLowerCase().includes('pozitívny') || 
                        !name.toLowerCase().includes('negatívny');
      
      const formulaLines = block.trim().split('\n');
      const cleanedFormula = formulaLines.filter(line => !line.trim().startsWith('#')).join('\n');
     
      const formattedFormula = cleanedFormula
        .replace(/\s+/g, ' ')  
        .trim();              
      
      const normalizedFormula = formattedFormula
        .replace(/\(/g, '(')   
        .replace(/\)/g, ')')   
        .replace(/,/g, ', ')   
        .replace(/\s+/g, ' ')  
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


  const updateExamplesFromApi = (apiExamples: ApiExample[]) => {
    setExamples(prevExamples => {
      if (!prevExamples || prevExamples.length === 0) {
        return prevExamples;
      }
      
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

  const toggleExampleSelection = (id: number, selected?: boolean) => {
    setExamples(prevExamples => 
      prevExamples.map(example => {
        if (example.id === id) {
          if (example.usedInTraining && selected === false) {
            return example;
          }
          return { ...example, selected: selected !== undefined ? selected : !example.selected };
        }
        return example;
      })
    );
    
    return true;
  };

  const selectAll = (selected: boolean) => {
    setExamples(examples.map(example => {
      if (example.usedInTraining) {
        return { ...example, selected: true };
      }
      return { ...example, selected };
    }));
  };

  const resetExamples = () => {
    setExamples(prevExamples => 
      prevExamples.map(example => ({
        ...example,
        selected: false,
        usedInTraining: false
      }))
    );
  };

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