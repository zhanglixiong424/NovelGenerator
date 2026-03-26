import { cn } from "@/lib/utils";
import type { HTMLAttributes } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  glow?: "orange" | "cyan" | "none";
}

export function Card({ className, glow = "orange", children, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-lg bg-bg-card",
        glow === "orange" && "border border-accent-orange/20 shadow-[0_4px_20px_rgba(0,0,0,0.5)]",
        glow === "cyan" && "border border-accent-cyan/20 shadow-[0_4px_20px_rgba(0,0,0,0.5)]",
        glow === "none" && "border border-bg-hover",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("px-5 py-4 border-b border-bg-hover", className)} {...props}>
      {children}
    </div>
  );
}

export function CardContent({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("px-5 py-4", className)} {...props}>
      {children}
    </div>
  );
}
