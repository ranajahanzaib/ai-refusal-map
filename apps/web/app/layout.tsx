import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Refusal Map — Research Observatory",
  description: "Mapping the boundaries of artificial intelligence.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
