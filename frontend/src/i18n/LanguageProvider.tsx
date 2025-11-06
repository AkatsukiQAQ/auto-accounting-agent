import React from 'react';
import { I18nextProvider } from "react-i18next";
import { setupI18n, type Locale } from "./createI18n";

interface LanguageProviderProps {
  children: React.ReactNode;
  initalLocale?: Locale;
}

function LanguageProvider ({ children, initalLocale }: LanguageProviderProps){{
  const [i18n] = React.useState(() => setupI18n(initalLocale));
  React.useEffect(() => {
    if (initalLocale) i18n.changeLanguage(initalLocale);
  }, [initalLocale, i18n]);
  return <I18nextProvider i18n={i18n}>{children}</I18nextProvider>;
}

export default LanguageProvider;
