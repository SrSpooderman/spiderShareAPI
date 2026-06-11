import { clsx } from "clsx";
import { ReactNode } from "react";

type BadgeProps = {
  tone?: "neutral" | "blue" | "green" | "yellow" | "red";
  children: ReactNode;
};

export function Badge({ tone = "neutral", children }: BadgeProps) {
  return <span className={clsx("badge", `badge-${tone}`)}>{children}</span>;
}
