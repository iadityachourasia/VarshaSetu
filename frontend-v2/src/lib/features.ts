// Build-time switches for parts of the site that exist but are not shown by default. A NEXT_PUBLIC_ variable is inlined at build, so changing one needs a rebuild.

/**
 * The SIH26080 requirement-coverage page (/compliance) and the presentation scene that summarises it. Hidden by default: the page, its data, its API endpoint and its tests
 * are all kept, so showing it again is only a matter of building with NEXT_PUBLIC_SHOW_COMPLIANCE_PAGE=1.
 */
export const SHOW_COMPLIANCE_PAGE = process.env.NEXT_PUBLIC_SHOW_COMPLIANCE_PAGE === "1";
