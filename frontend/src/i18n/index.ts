import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import type { Language } from "../api/types";
import { en } from "./en";
import { es } from "./es";

/** The first of the browser's preferred languages that the app speaks; English otherwise (the base language). */
export function browserLanguage(): Language {
  const preferred = typeof navigator === "undefined" ? [] : navigator.languages?.length ? navigator.languages : [navigator.language];
  for (const tag of preferred) {
    const language = tag?.toLowerCase().split("-")[0];
    if (language === "es" || language === "en") return language;
  }
  return "en";
}

// The API never translates (§1): every UI text lives here. Until the user signs in,
// follow the browser; after that, AuthContext switches to `preferred_language`.
const browser = browserLanguage();

void i18n.use(initReactI18next).init({
  resources: { es: { translation: es }, en: { translation: en } },
  lng: browser,
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

// The page's language and its description (what search engines and link previews show) follow the UI.
function followLanguage(language: string) {
  document.documentElement.setAttribute("lang", language);
  const description = i18n.t("meta.description");
  for (const selector of ['meta[name="description"]', 'meta[property="og:description"]'])
    document.querySelector(selector)?.setAttribute("content", description);
}
i18n.on("languageChanged", followLanguage);
followLanguage(i18n.language); // init already chose the language before this listener existed

export default i18n;
