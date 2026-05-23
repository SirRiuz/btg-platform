import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function svgProps({
  size = 16,
  ...rest
}: IconProps): SVGProps<SVGSVGElement> {
  return {
    width: size,
    height: size,
    viewBox: "0 0 20 20",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.5,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    "aria-hidden": true,
    focusable: false,
    ...rest,
  };
}

export function EyeIcon(props: IconProps) {
  return (
    <svg {...svgProps(props)}>
      <path d="M1.667 10S4.583 4.583 10 4.583 18.333 10 18.333 10 15.417 15.417 10 15.417 1.667 10 1.667 10z" />
      <circle cx="10" cy="10" r="2.5" />
    </svg>
  );
}

export function EyeOffIcon(props: IconProps) {
  return (
    <svg {...svgProps(props)}>
      <path d="M3.333 3.333 16.667 16.667" />
      <path d="M8.232 8.232a2.5 2.5 0 0 0 3.536 3.536" />
      <path d="M5.834 6.066C3.55 7.4 1.667 10 1.667 10S4.583 15.417 10 15.417c1.357 0 2.555-.34 3.585-.85" />
      <path d="M16.5 12.6c1.13-1.1 1.833-2.6 1.833-2.6S15.417 4.583 10 4.583c-.582 0-1.13.066-1.645.187" />
    </svg>
  );
}

export function AlertIcon(props: IconProps) {
  return (
    <svg {...svgProps(props)}>
      <circle cx="10" cy="10" r="7.5" />
      <path d="M10 6.667v3.75" />
      <path d="M10 13.333h.008" />
    </svg>
  );
}

export function CheckIcon(props: IconProps) {
  return (
    <svg {...svgProps(props)}>
      <path d="m4.167 10.417 3.75 3.75 8.333-8.334" />
    </svg>
  );
}

export function ArrowRightIcon(props: IconProps) {
  return (
    <svg {...svgProps(props)}>
      <path d="M4.167 10h11.667" />
      <path d="M10 4.167 15.833 10 10 15.833" />
    </svg>
  );
}

export function CloseIcon(props: IconProps) {
  return (
    <svg {...svgProps(props)}>
      <path d="M5 5l10 10" />
      <path d="M15 5L5 15" />
    </svg>
  );
}

export function ChevronDownIcon(props: IconProps) {
  return (
    <svg {...svgProps(props)}>
      <path d="M5 7.5l5 5 5-5" />
    </svg>
  );
}
