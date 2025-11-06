import React from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/Button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/DropdownMenu";
import { Globe, Settings, Sun, Moon, ChevronDown, User, LogOut } from "lucide-react";
import { useTranslation } from "react-i18next";

// --- Theme hook --- //
function getInitialTheme(): "light" | "dark" {
  if (typeof window !== "undefined") {
    return "light";
  }

  const savedTheme = localStorage.getItem("theme");
  if (savedTheme === "light" || savedTheme === "dark") {
    return savedTheme;
  }

  const prefersDark = typeof window !== "undefined" && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  return prefersDark ? "dark" : "light";
}

function applyTheme(theme: "light" | "dark") {
  const root = document.documentElement;
  if (theme === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
  localStorage.setItem("theme", theme);
}

function useTheme() {
  const [theme, setTheme] = React.useState<"light" | "dark">(getInitialTheme());
  React.useEffect(() => {
    applyTheme(theme);
  }, [theme]);
  const toggleTheme = () => {
    setTheme(() => (theme === "light" ? "dark" : "light"));
  }
  return { theme, setTheme, toggleTheme };
}

// --- TopBar Props --- //
interface TopBarProps {
  projectName?: string,
  logo?: React.ReactNode,
  onLogoClick?: () => void,
  onNavigateHomeHref?: string,
  onOpenSettings?: () => void,
  languages?: { code: string, label?: string }[],
}

interface LogoProps {
  homeName: string,
  logo: React.ReactNode,
  onLogoClick: () => void,
  onNavigateHomeHref?: string,
}

// --- TopBar Components --- //
function TopBarLogo({ homeName, logo, onLogoClick, onNavigateHomeHref }: LogoProps) {
  return onNavigateHomeHref ? (
    <a href={onNavigateHomeHref} className="hover:opacity-80 active:opacity-60" aria-label={homeName}>
      {logo}
    </a>
  ) : (
    <button onClick={onLogoClick} className="hover:opacity-80 active:opacity-60" aria-label={homeName}>
      {logo}
    </button>
  )
}

function TopBarProjectName()

// --- TopBar --- //
function TopBar({
  projectName,
  logo,
  onLogoClick,
  onNavigateHomeHref,
  onOpenSettings,
  languages
}: TopBarProps) {
  const { theme, toggleTheme } = useTheme();

  // Language setup
  const { t, i18n } = useTranslation(["topbar", "common"]);
  const langOptions = (languages && languages.length > 0) ? languages : [
    { code: "en", label: "English" },
    { code: "zh", label: "中文" },
    { code: "ja", label: "日本語" },
  ];
  const currentLang = (i18n.language || "en").slice(0, 2);

  const handleLanguageChange = async (code: string) => {
    if (i18n.language === code) return;
    await i18n.changeLanguage(code);
    localStorage.setItem('locale', code);
  }

  // Logo setup
  const Logo = (
    <div className="flex items-center gap-2 select-none">
      {logo ?? (
        <div className="h-8 w-8 rounded-xl bg-primary/15 flex items-center justify-center font-bold">
          <span className="text-primary">AAA</span>
        </div>
      )}
    </div>
  );

  return (
    <motion.header
      initial={{ y: -12, opacity: 0}}
      animate={{ y: 0, opacity: 1 }}
      transition={{ type: "spring", stiffness: 280, damping: 22 }}
      className="sticky top-0 z-40 w-full border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60"
    >
      <div className="mx-auto max-w-screen-2xl px-3 sm:px-4 lg:px-6">
        <div className="h-14 flex items-center justify-between gap-2">
          {/*Logo*/}
          <TopBarLogo
            homeName={t("topbar.home")}
            logo={Logo}
            onLogoClick={onLogoClick || (() => {})}
            onNavigateHomeHref={onNavigateHomeHref} />

          {/*Project Name (Use projectName first, else i18n)*/}
          // TODO
        </div>
      </div>
    </motion.header>
  )
}

export default { useTheme, TopBar };