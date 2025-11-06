import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import resourcesToBackend from "i18next-resources-to-backend/index";

// --- i18n Configuration --- //
export const SUPPORTED_LANGUAGES = [
  'en',
  'zh',
  'ja',
] as const;
export type Locale = typeof SUPPORTED_LANGUAGES[number];
export const DEFAULT_LOCALE: Locale = 'en';

export const NAMESPACE = [
  'common',
  'topBar',
]
export type Namespace = typeof NAMESPACE[number];
export const DEFAULT_NS = 'common';

// --- Lazy i18n Initialization --- //
const backend = resourcesToBackend(
  (locale: Locale, namespace: Namespace) => {return import(`./locales/${locale}/${namespace}.json`);
});

function getInitialLocale() : Locale {
  const savedLocale = localStorage.getItem('locale');
  if (savedLocale && SUPPORTED_LANGUAGES.includes(savedLocale as Locale)) {
    return savedLocale as Locale;
  }

  const browserLocale = navigator.language.toLowerCase();
  if (browserLocale.startsWith('zh')) return 'zh' as Locale;
  if (browserLocale.startsWith('ja')) return 'ja' as Locale;
  return DEFAULT_LOCALE;
}

export function setupI18n(initialLocale: Locale = getInitialLocale()) {
  if (!i18n.isInitialized) {
    i18n
      .use(initReactI18next)
      .use(backend)
      .init({
        lng: initialLocale,
        fallbackLng: DEFAULT_LOCALE,
        supportedLngs: SUPPORTED_LANGUAGES as unknown as string[],
        ns: NAMESPACE,
        defaultNS: DEFAULT_NS,
        interpolation: { escapeValue: false },
        debug: import.meta.env.DEV,
      });
  }
}