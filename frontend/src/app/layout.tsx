import type { Metadata } from "next";
import { IBM_Plex_Sans, JetBrains_Mono, Syne } from "next/font/google";
import "./globals.css";

const plex = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
});

const syne = Syne({
  subsets: ["latin"],
  weight: ["600", "700", "800"],
  variable: "--font-display",
});

export const metadata: Metadata = {
  title: "AutoPatch",
  description: "Autonomous sandboxed code remediation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${plex.variable} ${mono.variable} ${syne.variable} antialiased`}>
        {children}
      </body>
    </html>
  );
}
