import type { Metadata } from "next";
import { AOSProvider } from "@/components/aos-provider";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import "./styles/globals.css";

export const metadata: Metadata = {
  title: "Adrobot — управление кампаниями",
  description: "Создание кампаний Keitaro и управление офферами.",
};

export const dynamic = "force-dynamic";

type RootLayoutProps = Readonly<{ children: React.ReactNode }>;

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="ru">
      <body>
        <AOSProvider />
        {children}
        <ToastContainer
          position="top-right"
          autoClose={4000}
          newestOnTop
          closeOnClick
          pauseOnFocusLoss
          draggable
          pauseOnHover
        />
      </body>
    </html>
  );
}
