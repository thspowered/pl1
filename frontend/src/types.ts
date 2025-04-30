export interface CategorizedViolations {
  must_violations?: string[];
  must_not_violations?: string[];
  component_violations?: string[];
  attribute_violations?: string[];
  extra_components?: string[];
}

export interface ComparisonResult {
  is_valid: boolean;
  model_type: string | null;
  violations: string[];
  satisfied_rules: string[];
  formula: string;
  validate_attributes: boolean;
  allowed_alternatives?: {
    engines?: string[];
    transmissions?: string[];
    drives?: string[];
  };
  categorized_violations?: CategorizedViolations;
  highlighted_formula?: any;
  model_formula?: string;
  extra_components?: string[];
} 