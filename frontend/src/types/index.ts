// Types for examples and dataset
export interface Example {
  id: number;
  name: string;
  formula: string;
  isPositive: boolean;
  selected: boolean;
  usedInTraining?: boolean;
}

export interface TrainingResult {
  success: boolean;
  message: string;
  model_updated: boolean;
  model_hypothesis?: string; // Textová reprezentácia hypotézy modelu
  model_visualization?: {
    nodes: Array<NetworkNode>;
    links: Array<NetworkLink>;
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
  time_elapsed?: number;
}

// Types for API responses
export interface ApiExample {
  id: number;
  formula: string;
  is_positive: boolean;
  name: string;
  used_in_training?: boolean;
}

export interface ApiDatasetResponse {
  examples: ApiExample[];
}

// Define types for the SigmaNetwork component
export interface NetworkNode {
  id: string;
  name: string;
  class: string;
  category: string;
  attributes?: Record<string, any>;
}

export interface NetworkLink {
  source: string;
  target: string;
  type: string;
}

export interface SigmaNetworkProps {
  nodes: NetworkNode[];
  links: NetworkLink[];
}

export interface InfoPanelProps {
  hoveredNode: string | null;
  nodes: NetworkNode[];
  links: NetworkLink[];
}

export interface ModelHistory {
  current_index: number;
  total_entries: number;
} 