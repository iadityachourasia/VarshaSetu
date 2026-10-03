// Mirrors src/lib/features.ts for the test process: the same variable that was used to build the app under test must be set when running the tests.
export const COMPLIANCE_PAGE = process.env.NEXT_PUBLIC_SHOW_COMPLIANCE_PAGE === "1";
export const COMPLIANCE_HIDDEN_REASON = "the requirement-coverage page is hidden by default (build with NEXT_PUBLIC_SHOW_COMPLIANCE_PAGE=1 to show it)";
