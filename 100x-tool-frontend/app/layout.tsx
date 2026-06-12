import type { Metadata } from "next";
import { Fraunces, Montserrat, JetBrains_Mono, Cormorant_Garamond, Inter } from "next/font/google";

<<<<<<< Updated upstream
import { AuthProvider } from "@/context/AuthContext";
import { LogoutButton } from "@/components/LogoutButton";
import { TermsGuard } from "@/components/TermsGuard";
=======
>>>>>>> Stashed changes
import "./globals.css";
import { SchedulerProvider } from "@/lib/scheduler/context";

const fraunces = Fraunces({
  subsets: ["latin"],
  style: ["normal", "italic"],
  axes: ["opsz", "SOFT"],
  variable: "--font-serif",
  display: "swap",
});

const montserrat = Montserrat({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700", "800"],
  variable: "--font-sans",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
  display: "swap",
});

const cormorant = Cormorant_Garamond({
  subsets: ["latin"],
  style: ["normal", "italic"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-cormorant",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Schedulr — 100xAI",
  description: "One calendar for your blogs, LinkedIn and Instagram — plan, approve and publish, built on the 100xAI automation stack.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      className={`${fraunces.variable} ${montserrat.variable} ${jetbrains.variable} ${cormorant.variable} ${inter.variable}`}
      lang="en"
    >
      <body>
<<<<<<< Updated upstream
        <AuthProvider>
        <div className="app-shell">
          <header className="topbar">
            <div className="topbar-brand">
              <div className="topbar-logo-mark">AI</div>
              <div>
                <div className="topbar-title">100xAI</div>
                <div className="topbar-status-pulse">
                  <span className="pulse-dot" />
                  <span className="topbar-kicker">Live · Brand OS</span>
                </div>
              </div>
            </div>
            <nav className="topbar-nav">
              <Link className="topbar-link" href="/brands">
                Dashboard
              </Link>
              <Link className="topbar-link" href="/billing">
                Billing
              </Link>
              <Link className="topbar-link primary" href="/brands/new">
                + New Brand
              </Link>
              <LogoutButton />
            </nav>
          </header>
          <main>{children}</main>
          <TermsGuard />
        </div>
        </AuthProvider>
=======
        <SchedulerProvider>{children}</SchedulerProvider>
>>>>>>> Stashed changes
      </body>
    </html>
  );
}
