/**
 * "  Azúcar " -> "azucar": what two spellings of the same word have in common, so a
 * name typed without accents is recognised as the one that has them. The API folds
 * its searches the same way (backend/app/shared/database/text_search.py).
 */
export const fold = (text: string): string => text.normalize("NFD").replace(/[̀-ͯ]/g, "").trim().toLowerCase();
