import type { Metadata } from "next";
import { AOSProvider } from "@/components/aos-provider";
import "./styles.css";

export const metadata: Metadata = {
  title: "Adrobot — управление кампаниями",
  description: "Создание кампаний Keitaro и управление офферами.",
};

type RootLayoutProps = Readonly<{ children: React.ReactNode }>;

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="ru">
      <head>
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/icon?family=Material+Icons+Round"
        />
      </head>
      <body>
        <AOSProvider />
        {children}
      </body>
    </html>
  );
}
