import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "semanticut",
  description: "Recherche sémantique sur vidéo",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr">
      <body className="font-sans">{children}</body>
    </html>
  );
}
