import type { Metadata } from "next";
import { Inter, Plus_Jakarta_Sans } from "next/font/google";
import { BuildProvider } from "@/context/BuildContext";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { ThemeProvider } from "@/components/ThemeProvider";
import ThemeToggle from "@/components/ThemeToggle";
import CursorAndBackground from "@/components/CursorAndBackground";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const jakarta = Plus_Jakarta_Sans({
  variable: "--font-jakarta",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Loop PC Builder",
  description: "Build your dream PC with real-time compatibility checks and pricing.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${jakarta.variable} antialiased bg-background text-foreground flex flex-col min-h-screen relative`}>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <CursorAndBackground />
          <BuildProvider>
            <Navbar />
            <main className="flex-grow z-10">
              {children}
            </main>
            <Footer />
          </BuildProvider>
          <ThemeToggle />
        </ThemeProvider>
      </body>
    </html>
  );
}
