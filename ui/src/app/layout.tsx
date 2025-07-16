"use client";
import "@/lib/client";
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
import React from "react";
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
            <div className="grid grid-rows-[auto_1fr] h-screen">
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
  const { buttons, breadcrumbs } = useToolbar();
  
  return (
    <header className="sticky top-0 z-50 flex h-16 shrink-0 items-center gap-2 border-b px-4 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/60">
      <Breadcrumb>
        <BreadcrumbList>
          {breadcrumbs.map((item, index) => (
            <React.Fragment key={index}>
              {index > 0 && <BreadcrumbSeparator />}
              <BreadcrumbItem>
                {item.href && !item.isCurrentPage ? (
                  <Link href={item.href} className="font-medium text-base">
                    {item.label}
                  </Link>
                ) : (
                  <span className={`font-medium ${index === 0 ? 'text-base' : ''}`}>
                    {item.label}
                  </span>
                )}
              </BreadcrumbItem>
            </React.Fragment>
          ))}
        </BreadcrumbList>
      </Breadcrumb>
      {buttons}
    </header>
  );
};
