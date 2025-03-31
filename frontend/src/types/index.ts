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
  model_rules?: Record<string, string>; // Identifikačné pravidlá pre jednotlivé modely áut
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
  status?: 'common' | 'only_in_a' | 'only_in_b';  // Status pro vizualizaci rozdílů
  value?: any;  // Hodnota atributu
  value_display?: string;  // Textová reprezentace hodnoty pro zobrazení
}

export interface NetworkLink {
  source: string;
  target: string;
  type: string;
  status?: 'common' | 'only_in_a' | 'only_in_b';  // Status pro vizualizaci rozdílů
}

export interface SigmaNetworkProps {
  nodes: NetworkNode[];
  links: NetworkLink[];
  showDifferences?: boolean;  // Příznak pro zobrazení rozdílů
  modelA?: string;  // Název prvního modelu
  modelB?: string;  // Název druhého modelu
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

// Výsledok porovnania príkladu s natrénovaným modelom
export interface ComparisonResult {
  is_valid: boolean;
  explanation: string;
  symbolic_differences: string[];
}

// Typy pro uložené modely a porovnávání hypotéz
export interface SavedModel {
  id: number;
  name: string;
  timestamp: string;
}

export interface SavedModelDetail extends SavedModel {
  pl1_representation: string;
  model_state: any;
}

export interface ModelComparisonRequest {
  model_a_type: 'current' | 'saved';
  model_a_id?: number;
  model_b_type: 'current' | 'saved';
  model_b_id?: number;
}

export interface ModelComparisonResult {
  success: boolean;
  model_a: {
    name: string;
    type: string;
    id?: number;
    pl1_representation: string;
  };
  model_b: {
    name: string;
    type: string;
    id?: number;
    pl1_representation: string;
  };
  differences: {
    objects: {
      only_in_a: string[];
      only_in_b: string[];
      common: string[];
    };
    links: {
      only_in_a: string[];
      only_in_b: string[];
      count_a: number;
      count_b: number;
      common_count: number;
    };
    model_types: {
      [model_type: string]: {
        only_in_a: {
          must: string[];
          must_not: string[];
        };
        only_in_b: {
          must: string[];
          must_not: string[];
        };
        different: Record<string, any>;
      };
    };
  };
  visualization?: {
    nodes: NetworkNode[];
    links: NetworkLink[];
  };
  visualization_stats?: {
    node_count: number;
    link_count: number;
    nodes_only_in_a: number;
    nodes_only_in_b: number;
    nodes_common: number;
    links_only_in_a: number;
    links_only_in_b: number;
    links_common: number;
  };
} 