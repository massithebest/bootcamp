import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "P&T FP agent",
  description: "생산계획 Agent 질의응답 Frontend (POC)",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
