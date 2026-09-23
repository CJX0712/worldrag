/**
 * Project-locked icon set: inline SVG, uniform 1.8px stroke, 16/20/24px.
 * P0 rule: no emoji as functional icons anywhere in the product.
 *
 * Author: 晨星
 */
import type { ReactElement, ReactNode } from "react";

type IconProps = { size?: 16 | 20 | 24; className?: string };

function base(
  size: number,
  className: string | undefined,
  children: ReactNode,
): ReactElement {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export const LogoIcon = ({ size = 24, className }: IconProps) =>
  base(size, className, (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M8 12h8M12 8v8" />
    </>
  ));

export const SendIcon = ({ size = 20, className }: IconProps) =>
  base(size, className, <path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7z" />);

export const ChartIcon = ({ size = 20, className }: IconProps) =>
  base(size, className, (
    <>
      <path d="M3 3v18h18" />
      <path d="M7 15l4-6 4 3 5-8" />
    </>
  ));

export const DatabaseIcon = ({ size = 20, className }: IconProps) =>
  base(size, className, (
    <>
      <ellipse cx="12" cy="5" rx="8" ry="3" />
      <path d="M4 5v14c0 1.66 3.58 3 8 3s8-1.34 8-3V5" />
      <path d="M4 12c0 1.66 3.58 3 8 3s8-1.34 8-3" />
    </>
  ));
