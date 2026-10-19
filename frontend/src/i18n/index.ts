import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import { en } from "./en";
import { es } from "./es";

// The API never translates (§1): every UI text lives here. Until the user signs in,
// follow the browser; after that, AuthContext switches to `preferred_language`.
const browser = typeof navigator !== "undefined" && navigator.language?.startsWith("en") ? "en" : "es";

void i18n.use(initReactI18next).init({
  resources: { es: { translation: es }, en: { translation: en } },
  lng: browser,
  fallbackLng: "es",
  interpolation: { escapeValue: false },
});

i18n.on("languageChanged", (language) => document.documentElement.setAttribute("lang", language));

export default i18n;
