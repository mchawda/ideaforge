import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "ideaForge",
  description: "From idea to live product in minutes. Browse on IdeaBrowser. Build on IdeaForge.",
  metadataBase: new URL("https://idea-forge-eta-six.vercel.app"),
  icons: {
    icon: "/logo.svg",
    apple: "/logo-480.jpg",
  },
  openGraph: {
    title: "ideaForge",
    description: "From idea to live product in minutes.",
    url: "https://idea-forge-eta-six.vercel.app",
    siteName: "IdeaForge",
    images: [{ url: "/logo-480.jpg", width: 480, height: 480, alt: "IdeaForge" }],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} h-full`}>
      <body className="min-h-full flex flex-col bg-background text-foreground">
        {children}
        <Toaster closeButton />
      </body>
    </html>
  );
}
