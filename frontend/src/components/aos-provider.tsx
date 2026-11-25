"use client";
import { useEffect } from "react";
import AOS from "aos";
import "aos/dist/aos.css";
export function AOSProvider(){useEffect(()=>{AOS.init({duration:500,once:true,offset:18,disable:()=>window.matchMedia("(prefers-reduced-motion: reduce)").matches});},[]);return null;}
