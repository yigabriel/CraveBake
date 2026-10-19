import { api, apiWithStatus } from "./client";
import type {
  ConversionResult,
  CreateRecipeInput,
  Difficulty,
  DiscoverySession,
  DisplayUnitSystem,
  Equipment,
  EquipmentType,
  FavoriteStatus,
  Ingredient,
  IngredientCategory,
  Language,
  NamedRef,
  Page,
  PantryItem,
  PortfolioItem,
  PortfolioKind,
  PortfolioSummary,
  PreparationDetail,
  PreparationStatus,
  PreparationSummary,
  Recommendation,
  RecipeBasics,
  RecipeDetail,
  RecipeEquipmentInput,
  RecipeIngredientInput,
  RecipePhoto,
  RecipeStepInput,
  RecipeSummary,
  RecipeTag,
  Swipe,
  SwipeAction,
  TokenResponse,
  Unit,
  UnitSystem,
  User,
  UserEquipment,
} from "./types";

// --- Auth & profile ------------------------------------------------------------------

export const authApi = {
  register: (body: { email: string; password: string; full_name: string }) =>
    api<User>("/auth/register", { method: "POST", json: body }),
  // OAuth2 password form: `username` is the email.
  login: (email: string, password: string) =>
    api<TokenResponse>("/auth/login", { method: "POST", form: { username: email, password } }),
};

export const usersApi = {
  me: () => api<User>("/users/me"),
  updateProfile: (body: { full_name?: string; avatar_url?: string | null }) =>
    api<User>("/users/me/profile", { method: "PATCH", json: body }),
  setUnitSystem: (preferred_unit_system: UnitSystem) =>
    api<User>("/users/me/unit-preference", { method: "PATCH", json: { preferred_unit_system } }),
  setLanguage: (preferred_language: Language) =>
    api<User>("/users/me/language", { method: "PATCH", json: { preferred_language } }),
  changePassword: (current_password: string, new_password: string) =>
    api<User>("/users/me/change-password", { method: "PATCH", json: { current_password, new_password } }),
};

// --- Catalogs ------------------------------------------------------------------------

export const catalogApi = {
  units: () => api<Unit[]>("/units"),
  recipeCategories: () => api<NamedRef[]>("/recipe-categories"),
  difficulties: () => api<Difficulty[]>("/difficulties"),
  tags: () => api<RecipeTag[]>("/recipe-tags"),
  ingredientCategories: () => api<IngredientCategory[]>("/categories"),
  searchIngredients: (q: string, limit = 10) => api<Page<Ingredient>>("/ingredients", { query: { q, limit } }),
  getIngredient: (id: string) => api<Ingredient>(`/ingredients/${id}`),
  ingredientsByCategory: (category: string) =>
    api<Page<Ingredient>>(`/categories/${encodeURIComponent(category)}/ingredients`, { query: { limit: 100 } }),
  createIngredient: (body: { name: string; default_category?: string | null }) =>
    api<Ingredient>("/ingredients", { method: "POST", json: body }),
  searchEquipment: (q: string, equipment_type?: EquipmentType, limit = 20) =>
    api<Page<Equipment>>("/equipment", { query: { q, equipment_type, limit } }),
  createEquipment: (body: { name: string; equipment_type: EquipmentType; description?: string | null }) =>
    api<Equipment>("/equipment", { method: "POST", json: body }),
  convert: (body: { quantity: string; from_unit_id: string; to_unit_id: string; ingredient_id?: string | null }) =>
    api<ConversionResult>("/converter", { method: "POST", json: body }),
};

// --- Pantry & kitchen ----------------------------------------------------------------

export const pantryApi = {
  list: () => api<PantryItem[]>("/pantry"),
  upsert: (body: { ingredient_id: string; quantity?: string | null; unit_id?: string | null }) =>
    api<PantryItem>("/pantry", { method: "PUT", json: body }),
  remove: (ingredientId: string) => api<void>(`/pantry/${ingredientId}`, { method: "DELETE" }),
};

export const kitchenApi = {
  list: () => api<UserEquipment[]>("/equipment/mine"),
  upsert: (body: { equipment_id: string; quantity: number; notes?: string | null }) =>
    api<UserEquipment>("/equipment/mine", { method: "PUT", json: body }),
  remove: (equipmentId: string) => api<void>(`/equipment/mine/${equipmentId}`, { method: "DELETE" }),
};

// --- Recipes -------------------------------------------------------------------------

export interface RecipeSearch {
  q?: string;
  category_id?: string;
  difficulty_id?: string;
  max_prep_time?: number;
  ingredient_ids?: string[];
  tag_ids?: string[];
  limit?: number;
  offset?: number;
}

export const recipesApi = {
  search: (params: RecipeSearch) => api<Page<RecipeSummary>>("/recipes", { query: { ...params } }),
  mine: (kind?: "original" | "personalized") => api<Page<RecipeSummary>>("/recipes/mine", { query: { kind, limit: 100 } }),
  get: (id: string, unit_system?: DisplayUnitSystem) => api<RecipeDetail>(`/recipes/${id}`, { query: { unit_system } }),
  create: (body: CreateRecipeInput) => api<RecipeDetail>("/recipes", { method: "POST", json: body }),
  update: (id: string, changes: Partial<RecipeBasics>) =>
    api<RecipeDetail>(`/recipes/${id}`, { method: "PATCH", json: changes }),
  replaceIngredients: (id: string, ingredients: RecipeIngredientInput[]) =>
    api<RecipeDetail>(`/recipes/${id}/ingredients`, { method: "PUT", json: { ingredients } }),
  replaceEquipment: (id: string, equipment: RecipeEquipmentInput[]) =>
    api<RecipeDetail>(`/recipes/${id}/equipment`, { method: "PUT", json: { equipment } }),
  replaceTags: (id: string, tag_ids: string[]) =>
    api<RecipeDetail>(`/recipes/${id}/tags`, { method: "PUT", json: { tag_ids } }),
  replaceSteps: (id: string, steps: RecipeStepInput[]) =>
    api<RecipeDetail>(`/recipes/${id}/steps`, { method: "PUT", json: { steps } }),
  remove: (id: string) => api<void>(`/recipes/${id}`, { method: "DELETE" }),
  personalize: (id: string, title?: string) =>
    api<RecipeDetail>(`/recipes/${id}/personalizations`, { method: "POST", json: title ? { title } : {} }),
  personalizations: (id: string) => api<Page<RecipeSummary>>(`/recipes/${id}/personalizations`),
  addPhoto: (id: string, body: { photo_type: "cover" | "step"; photo_url: string; step_id?: string }) =>
    api<RecipePhoto>(`/recipes/${id}/photos`, { method: "POST", json: body }),
  removePhoto: (id: string, photoId: string) => api<void>(`/recipes/${id}/photos/${photoId}`, { method: "DELETE" }),
  reorderCovers: (id: string, photo_ids: string[]) =>
    api<RecipePhoto[]>(`/recipes/${id}/photos/cover-order`, { method: "PUT", json: { photo_ids } }),
};

// --- Portfolio -----------------------------------------------------------------------

export interface PortfolioFilters {
  kind?: PortfolioKind;
  q?: string;
  category_id?: string;
  tag_ids?: string[];
  limit?: number;
  offset?: number;
}

export const portfolioApi = {
  list: (filters: PortfolioFilters) => api<Page<PortfolioItem>>("/portfolio", { query: { ...filters } }),
  summary: () => api<PortfolioSummary>("/portfolio/summary"),
  favoriteStatus: (recipe_ids: string[]) =>
    api<FavoriteStatus[]>("/portfolio/favorites/status", { query: { recipe_ids } }),
  save: (recipeId: string) => api<PortfolioItem>(`/portfolio/favorites/${recipeId}`, { method: "PUT" }),
  unsave: (recipeId: string) => api<void>(`/portfolio/favorites/${recipeId}`, { method: "DELETE" }),
};

// --- Discovery (swipe) ---------------------------------------------------------------

export const discoveryApi = {
  start: (body: { ingredient_ids: string[]; min_score: number; category_id?: string | null; tag_ids?: string[] }) =>
    api<DiscoverySession>("/recommendations/sessions", { method: "POST", json: body }),
  get: (id: string) => api<DiscoverySession>(`/recommendations/sessions/${id}`),
  // Swiped cards leave the deck, so callers always ask from offset 0.
  deck: (id: string, limit = 10) =>
    api<Page<Recommendation>>(`/recommendations/sessions/${id}/deck`, { query: { limit, offset: 0 } }),
  swipe: (id: string, recipe_id: string, action: SwipeAction) =>
    api<Swipe>(`/recommendations/sessions/${id}/swipes`, { method: "POST", json: { recipe_id, action } }),
  swipes: (id: string, action?: SwipeAction) =>
    api<Page<Swipe>>(`/recommendations/sessions/${id}/swipes`, { query: { action, limit: 100 } }),
};

// --- Preparation (cooking mode) -------------------------------------------------------

type Units = DisplayUnitSystem | undefined;

export const preparationApi = {
  // 201 = new, 200 = resumed: the caller learns which through `resumed`.
  start: async (recipe_id: string, unit_system?: Units) => {
    const { data, status } = await apiWithStatus<PreparationDetail>("/preparations", {
      method: "POST",
      json: { recipe_id },
      query: { unit_system },
    });
    return { detail: data, resumed: status === 200 };
  },
  list: (params: { status?: PreparationStatus; recipe_id?: string; limit?: number; offset?: number }) =>
    api<Page<PreparationSummary>>("/preparations", { query: { ...params } }),
  get: (id: string, unit_system?: Units) => api<PreparationDetail>(`/preparations/${id}`, { query: { unit_system } }),
  goTo: (id: string, step_number: number, unit_system?: Units) =>
    api<PreparationDetail>(`/preparations/${id}/current-step`, { method: "PUT", json: { step_number }, query: { unit_system } }),
  complete: (id: string, step: number, unit_system?: Units) =>
    api<PreparationDetail>(`/preparations/${id}/steps/${step}/complete`, { method: "POST", query: { unit_system } }),
  uncomplete: (id: string, step: number, unit_system?: Units) =>
    api<PreparationDetail>(`/preparations/${id}/steps/${step}/complete`, { method: "DELETE", query: { unit_system } }),
  startTimer: (id: string, step: number, unit_system?: Units) =>
    api<PreparationDetail>(`/preparations/${id}/steps/${step}/timer`, { method: "POST", query: { unit_system } }),
  finish: (id: string, unit_system?: Units) =>
    api<PreparationDetail>(`/preparations/${id}/finish`, { method: "POST", query: { unit_system } }),
  abandon: (id: string, unit_system?: Units) =>
    api<PreparationDetail>(`/preparations/${id}/abandon`, { method: "POST", query: { unit_system } }),
};
