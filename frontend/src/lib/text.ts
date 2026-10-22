/**
 * "  Azúcar " -> "azucar": what two spellings of the same word have in common, so a
 * name typed without accents is recognised as the one that has them. The API folds
 * its searches the same way (backend/app/shared/database/text_search.py).
 */
export const fold = (text: string): string => text.normalize("NFD").replace(/[̀-ͯ]/g, "").trim().toLowerCase();

/**
 * A name may list synonyms separated by " / " ("Mantequilla / Manteca"): typing any of them
 * is the same ingredient. Mirrors `matches_name` in the API.
 */
export const isSameName = (existing: string, typed: string): boolean =>
  existing.split(" / ").some((word) => fold(word) === fold(typed)) || fold(existing) === fold(typed);
