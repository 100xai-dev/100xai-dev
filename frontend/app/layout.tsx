import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "100xAI Admin",
  description: "Internal onboarding admin panel"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

