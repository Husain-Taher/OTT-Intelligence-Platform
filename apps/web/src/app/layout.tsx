import type { Metadata, Viewport } from "next";
import { UserProvider } from "@auth0/nextjs-auth0/client";
import "./globals.css";

export const metadata: Metadata = {
  title: "OTT Intelligence | Pick what to watch by mood",
  description: "Set the lights to your mood and get picks that learn what you love in each one.",
};

export const viewport: Viewport = { themeColor: "#0E0B0A", viewportFit: "cover" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400..700;1,9..144,400..600&family=Instrument+Sans:wght@400..700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen bg-pit font-sans">
        <UserProvider>{children}</UserProvider>
      </body>
    </html>
  );
}
