import type { Metadata } from "next";
import { Inter, Playfair_Display, JetBrains_Mono } from "next/font/google";
import { Providers } from "@/components/providers";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const playfair = Playfair_Display({
  subsets: ["latin"],
  variable: "--font-playfair",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "BullSutra | Multi-Agent NEPSE Stock Research & Backtesting",
  description:
    "Four specialist agents (News, Fundamentals, Technicals, Risk) analyze and cross-examine NEPSE equities to deliver calibrated consensus research and walk-forward backtested proof.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${inter.variable} ${playfair.variable} ${jetbrainsMono.variable}`}
    >
      <body className="antialiased min-h-screen bg-background text-foreground font-sans selection:bg-gold-500/20 selection:text-gold-300">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
