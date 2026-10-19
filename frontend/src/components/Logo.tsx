import { useId } from "react";

/**
 * Crave Bake isotype: the cookie is the C, the bite is a mirrored B, and the two
 * crumbs sit where the B's counters would be. Source: public/logo-concepts/galleta-cb-migas-clasica.svg.
 */
export function LogoMark({ size = 32, className = "" }: { size?: number; className?: string }) {
  // Unique per instance: two marks on one page must not share a <mask> id.
  const mask = `bite-${useId().replace(/:/g, "")}`;
  return (
    <svg viewBox="0 0 128 128" width={size} height={size} className={className} role="img" aria-label="Crave Bake">
      <defs>
        <mask id={mask}>
          <rect width="128" height="128" fill="white" />
          <circle cx="95" cy="46" r="19" fill="black" />
          <circle cx="95" cy="82" r="19" fill="black" />
          <rect x="95" y="46" width="40" height="36" fill="black" />
        </mask>
      </defs>
      <circle cx="58" cy="64" r="50" fill="#E9A84C" mask={`url(#${mask})`} />
      <g fill="#3A1F14">
        <circle cx="36" cy="44" r="7" />
        <circle cx="60" cy="32" r="5" />
        <circle cx="32" cy="78" r="6" />
        <circle cx="58" cy="94" r="7" />
        <circle cx="64" cy="62" r="6" />
      </g>
      <g fill="#E9A84C">
        <path d="M91.5 46c0-3.9 3.2-6.5 6.5-6.5s6.5 3.2 6.5 7.2-2.6 5.9-6.8 5.9-6.5-1.9-6.5-5.9z" />
        <path d="M91.5 82c0-3.9 3.2-6.5 6.5-6.5s6.5 3.2 6.5 7.2-2.6 5.9-6.8 5.9-6.5-1.9-6.5-5.9z" />
      </g>
    </svg>
  );
}

/** Mark + wordmark, for headers and footers. */
export function Logo({ size = 32, className = "" }: { size?: number; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-xs ${className}`}>
      <LogoMark size={size} />
      <span className="font-bold tracking-tight text-[#3A1F14]" style={{ fontSize: size * 0.62 }}>
        Crave <span className="text-primary">Bake</span>
      </span>
    </span>
  );
}
