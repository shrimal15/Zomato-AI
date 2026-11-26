import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "Find a restaurant · Zomato AI",
  description: "A short list of restaurants that match location, budget, cuisine, and rating.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="topbar">
          <div className="brand">
            <a className="logo" href="/">
              zomato
            </a>
            <nav className="crumb" aria-label="Breadcrumb">
              <a href="/">Home</a>
              <span aria-hidden="true">/</span>
              <a href="/" aria-current="page">
                AI Recommendations
              </a>
            </nav>
          </div>
          <svg className="avatar" viewBox="0 0 32 32" aria-hidden="true">
            <circle cx="16" cy="16" r="15" fill="#f3f3f3" stroke="#e4e4e4" />
            <circle cx="16" cy="13" r="4.5" fill="#b5b5b5" />
            <path d="M7 26c1.8-4.2 5-6.2 9-6.2s7.2 2 9 6.2" fill="#b5b5b5" />
          </svg>
        </header>
        {children}
      </body>
    </html>
  );
}
