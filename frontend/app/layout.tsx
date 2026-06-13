import type { Metadata } from "next";
import { Fraunces, Montserrat, JetBrains_Mono, Cormorant_Garamond, Inter } from "next/font/google";

import { AuthProvider } from "@/context/AuthContext";
import { TermsGuard } from "@/components/TermsGuard";
import "./globals.css";

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
        <AuthProvider>
          {children}
          <TermsGuard />
        </AuthProvider>
      </body>
    </html>
  );
}
