import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "100xAI",
  description: "AI Brand OS for brand onboarding, content generation, and publishing."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
