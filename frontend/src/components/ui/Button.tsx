import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "danger" | "ghost";
type Size = "sm" | "md" | "lg" | "icon";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

const variantStyles: Record<Variant, string> = {
  primary:
    "bg-accent-orange text-white border border-accent-orange/60 shadow-[0_0_15px_rgba(255,77,0,0.4)] hover:brightness-110 hover:shadow-[0_0_25px_rgba(255,77,0,0.6)]",
  secondary:
    "bg-transparent text-accent-cyan border border-accent-cyan/40 shadow-[0_0_10px_rgba(0,212,255,0.2)] hover:bg-accent-cyan/10 hover:shadow-[0_0_15px_rgba(0,212,255,0.3)]",
  danger:
    "bg-accent-red text-white border-none shadow-[0_0_15px_rgba(255,0,64,0.4)] hover:brightness-110 hover:shadow-[0_0_25px_rgba(255,0,64,0.6)]",
  ghost:
    "bg-transparent text-text-secondary border border-transparent hover:bg-bg-hover hover:text-text-primary",
};

const sizeStyles: Record<Size, string> = {
  sm: "h-8 px-3 text-sm rounded-md",
  md: "h-10 px-4 text-sm rounded-lg",
  lg: "h-12 px-6 text-base rounded-lg",
  icon: "h-10 w-10 rounded-lg",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", loading, disabled, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center gap-2 font-medium transition-all duration-200 ease-out",
          "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-orange",
          "disabled:opacity-40 disabled:pointer-events-none",
          "hover:-translate-y-0.5 active:translate-y-0",
          variantStyles[variant],
          sizeStyles[size],
          className
        )}
        disabled={disabled || loading}
        {...props}
      >
        {loading && (
          <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        )}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";
