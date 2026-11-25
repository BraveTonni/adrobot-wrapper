import type { Metadata } from "next";
import "./styles.css";
import { AOSProvider } from "@/components/aos-provider";
export const metadata: Metadata = { title: "Adrobot ? ?????????? ??????????", description: "???????? ? ?????????? ?????????? Keitaro." };
export default function RootLayout({ children }: Readonly<{children: React.ReactNode}>) { return <html lang="ru"><head><link rel="preconnect" href="https://fonts.googleapis.com"/><link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous"/><link href="https://fonts.googleapis.com/icon?family=Material+Icons+Round" rel="stylesheet"/></head><body><AOSProvider/>{children}</body></html>; }
