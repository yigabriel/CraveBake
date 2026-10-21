// Mirrors backend/app/*/presentation/http/schemas. Decimals arrive as strings ("2.50").

export type Decimalish = string;
export type UnitSystem = "metric" | "us";
export type DisplayUnitSystem = UnitSystem | "original";
export type Language = "en" | "es";

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface ApiErrorBody {
  detail: string;
  code: string;
  errors?: { field: string; message: string }[];
}

// --- IAM -----------------------------------------------------------------------------

export interface User {
  id: string;
  email: string;
  full_name: string;
  avatar_url: string | null;
  preferred_unit_system: UnitSystem;
  preferred_language: Language;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  user: User;
}

// --- Ingredients ---------------------------------------------------------------------

export interface Unit {
  id: string;
  name: string;
  abbreviation: string;
  unit_type: "weight" | "volume" | "count";
  base_factor: Decimalish;
  unit_system: "metric" | "us" | "neutral";
}

export interface Ingredient {
  id: string;
  name: string;
  description: string | null;
  default_category: string | null; // stable code, e.g. "flour"
  category_name: string | null; // its name in the user's language
}

export interface IngredientCategory {
  name: string; // stable code
  label: string;
  ingredient_count: number;
}

export interface PantryItem {
  id: string;
  ingredient: Ingredient;
  quantity: Decimalish | null;
  unit: Unit | null;
  updated_at: string;
}

export interface ConversionResult {
  original_quantity: Decimalish;
  from_unit: Unit;
  to_unit: Unit;
  converted_quantity: Decimalish;
}

// --- Equipment -----------------------------------------------------------------------

export type EquipmentType = "mold" | "utensil" | "appliance" | "other";

export interface Equipment {
  id: string;
  name: string;
  equipment_type: EquipmentType;
  description: string | null;
}

export interface UserEquipment {
  id: string;
  equipment: Equipment;
  quantity: number;
  notes: string | null;
  updated_at: string;
}

// --- Recipes -------------------------------------------------------------------------

export interface NamedRef {
  id: string;
  name: string;
}

export interface Difficulty extends NamedRef {
  level_order: number;
}

export type TagGroup = "flavor" | "diet" | "technique" | "time" | "celebrations";

export interface RecipeTag extends NamedRef {
  group: TagGroup;
  group_name: string;
}

export interface RecipePhoto {
  id: string;
  photo_type: "cover" | "step";
  photo_url: string;
  position: number;
  step_id: string | null;
}

export interface RecipeIngredient {
  id: string;
  ingredient_id: string;
  ingredient_name: string | null;
  // As the author wrote it (what the editor sends back).
  quantity: Decimalish;
  unit_id: string;
  unit_abbreviation: string | null;
  notes: string | null;
  position: number;
  // The group it belongs to ("Masa choux"); null when it has none.
  section_id: string | null;
  section: string | null;
  // In the response's unit_system (what the detail shows).
  display_quantity: Decimalish;
  display_unit_abbreviation: string | null;
  converted: boolean;
}

export interface RecipeEquipment {
  id: string;
  equipment_id: string;
  equipment_name: string | null;
  notes: string | null;
}

export interface RecipeStep {
  id: string;
  step_number: number;
  title: string | null;
  instructions: string;
  timer_seconds: number | null;
  photo: RecipePhoto | null;
  section_id: string | null;
  section: string | null;
}

interface RecipeCommon {
  id: string;
  title: string;
  description: string | null;
  category: NamedRef | null;
  difficulty: Difficulty | null;
  tags: RecipeTag[];
  prep_time_minutes: number | null;
  servings: number | null;
  is_public: boolean;
  is_personalization: boolean;
  source_recipe_id: string | null;
  source_recipe_title: string | null;
  source_updated_since_personalized: boolean | null;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
}

export interface RecipeSummary extends RecipeCommon {
  cover_photo_url: string | null;
}

export interface RecipeDetail extends RecipeCommon {
  video_url: string | null;
  is_owner: boolean;
  cover_photos: RecipePhoto[];
  ingredients: RecipeIngredient[];
  equipment: RecipeEquipment[];
  steps: RecipeStep[];
  unit_system: DisplayUnitSystem;
}

export interface RecipeIngredientInput {
  ingredient_id: string;
  quantity: string;
  unit_id: string;
  notes?: string | null;
  /** Name of the group; lines without one come first, then each group's lines together. */
  section?: string | null;
}

export interface RecipeEquipmentInput {
  equipment_id: string;
  notes?: string | null;
}

export interface RecipeStepInput {
  id?: string | null;
  instructions: string;
  title?: string | null;
  timer_seconds?: number | null;
  section?: string | null;
}

export interface RecipeBasics {
  title: string;
  description: string | null;
  video_url: string | null;
  category_id: string | null;
  difficulty_id: string | null;
  prep_time_minutes: number | null;
  servings: number | null;
  is_public: boolean;
}

export interface CreateRecipeInput extends RecipeBasics {
  ingredients: RecipeIngredientInput[];
  equipment: RecipeEquipmentInput[];
  tag_ids: string[];
  steps: RecipeStepInput[];
}

// --- Portfolio -----------------------------------------------------------------------

export type PortfolioKind = "original" | "personalized" | "saved";

export interface PortfolioItem {
  kind: PortfolioKind;
  recipe_id: string;
  title: string;
  description: string | null;
  cover_photo_url: string | null;
  category_name: string | null;
  tags: string[];
  difficulty_name: string | null;
  prep_time_minutes: number | null;
  servings: number | null;
  is_public: boolean;
  created_by_user_id: string;
  source_recipe_id: string | null;
  source_recipe_title: string | null;
  source_updated_since_personalized: boolean | null;
  added_at: string;
}

export interface PortfolioSummary {
  original_count: number;
  personalized_count: number;
  saved_count: number;
  total: number;
}

export interface FavoriteStatus {
  recipe_id: string;
  is_saved: boolean;
  saved_at: string | null;
}

// --- Recommendations -----------------------------------------------------------------

export interface DiscoverySession {
  id: string;
  ingredient_source: "selection" | "pantry";
  ingredients: NamedRef[];
  category: NamedRef | null;
  tags: NamedRef[];
  min_score: number;
  discarded_count: number;
  saved_count: number;
  selected_count: number;
  created_at: string;
}

export interface Recommendation {
  recipe_id: string;
  title: string;
  description: string | null;
  cover_photo_url: string | null;
  category_name: string | null;
  difficulty_name: string | null;
  tags: string[];
  prep_time_minutes: number | null;
  servings: number | null;
  is_own: boolean;
  is_personalization: boolean;
  source_recipe_title: string | null;
  compatibility_score: number;
  equipment_score: number;
  rank_score: number;
  matched_ingredients: NamedRef[];
  missing_ingredients: NamedRef[];
  missing_equipment: NamedRef[];
  has_all_equipment: boolean;
  is_saved: boolean;
}

export type SwipeAction = "discarded" | "saved" | "selected";

export interface Swipe {
  id: string;
  recipe_id: string;
  action: SwipeAction;
  compatibility_score: number;
  created_at: string;
}

// --- Preparation ---------------------------------------------------------------------

export type PreparationStatus = "in_progress" | "completed" | "abandoned";

export interface PreparedIngredient {
  ingredient_id: string;
  ingredient_name: string | null;
  quantity: Decimalish;
  unit_abbreviation: string | null;
  original_quantity: Decimalish;
  original_unit_abbreviation: string | null;
  converted: boolean;
  notes: string | null;
  section: string | null;
}

export interface PreparedStep {
  step_number: number;
  title: string | null;
  instructions: string;
  photo_url: string | null;
  timer_seconds: number | null;
  timer_started_at: string | null;
  timer_remaining_seconds: number | null;
  is_completed: boolean;
  completed_at: string | null;
  is_current: boolean;
  section: string | null;
}

export interface PreparationSummary {
  id: string;
  recipe_id: string;
  recipe_title: string;
  cover_photo_url: string | null;
  status: PreparationStatus;
  completed_steps: number;
  total_steps: number;
  started_at: string;
  finished_at: string | null;
}

export interface PreparationDetail extends PreparationSummary {
  servings: number | null;
  unit_system: DisplayUnitSystem;
  current_step_number: number | null;
  ingredients: PreparedIngredient[];
  steps: PreparedStep[];
}
