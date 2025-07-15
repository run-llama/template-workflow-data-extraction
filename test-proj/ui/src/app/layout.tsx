"use client";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Theme } from "@radix-ui/themes";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbSeparator,
} from "@llamaindex/components/ui";
import Link from "next/link";
import { useParams } from "next/navigation";
import "../lib/client";
import { Toaster } from "@llamaindex/components/ui";
import { useToolbar, ToolbarProvider } from "@/lib/ToolbarContext";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable}`}>
        <Theme>
          <ToolbarProvider>
            <div className="grid grid-rows-[auto_1fr] min-h-screen">
              <Toolbar />
              <main className="overflow-auto">{children}</main>
            </div>
            <Toaster />
          </ToolbarProvider>
        </Theme>
      </body>
    </html>
  );
}

const Toolbar = () => {
  const { fileId } = useParams();
  const { buttons, setButtons } = useToolbar();
  return (
    <header className="sticky top-0 z-50 flex h-16 shrink-0 items-center gap-2 border-b px-4 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/60">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <Link href="/" className="font-medium text-base">
              Invoice Extraction
            </Link>
          </BreadcrumbItem>
          {fileId && (
            <>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <span className="font-medium">{fileId}</span>
              </BreadcrumbItem>
            </>
          )}
        </BreadcrumbList>
      </Breadcrumb>
      {buttons}
    </header>
  );
};
