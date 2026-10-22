/**
 * Recipe sections ("Masa choux", "Manjar"): groups of ingredient lines and steps.
 *
 * The API lists lines without a section first and then each section's lines
 * together, so a client only has to start a new heading when the section changes.
 * In the editor the same shape is a flat list where a heading item owns the rows
 * below it, which makes an invalid grouping impossible to build.
 */

export interface Group<T> {
  /** null for the lines that belong to no section. */
  section: string | null;
  items: T[];
}

/** Consecutive runs of the same section, in order. */
export function groupBySection<T>(items: T[], sectionOf: (item: T) => string | null): Group<T>[] {
  const groups: Group<T>[] = [];
  for (const item of items) {
    const section = sectionOf(item);
    const last = groups[groups.length - 1];
    if (last && last.section === section) last.items.push(item);
    else groups.push({ section, items: [item] });
  }
  return groups;
}

/**
 * Lines without a section first, then each section's lines together, in order of first appearance.
 * The API already answers that way; an imported draft is reordered here too, because a list that
 * has a section-less line after a section would silently make it part of that section.
 */
export function inStorageOrder<T>(items: T[], sectionOf: (item: T) => string | null): T[] {
  const key = (item: T) => sectionOf(item)?.trim().replace(/\s+/g, " ").toLowerCase() ?? null;
  const order = new Map<string, number>();
  for (const item of items) {
    const k = key(item);
    if (k !== null && !order.has(k)) order.set(k, order.size);
  }
  return [...items].sort((a, b) => (key(a) === null ? -1 : order.get(key(a)!)!) - (key(b) === null ? -1 : order.get(key(b)!)!));
}

// --- Editor ---------------------------------------------------------------------------

/** A group heading inside an editable list. */
export interface Heading {
  key: string;
  heading: string;
}

export type Sectioned<T> = T | Heading;

export const isHeading = <T extends object>(item: Sectioned<T>): item is Heading => "heading" in item;

/** Rows only, without the headings. */
export const rowsOf = <T extends object>(items: Sectioned<T>[]): T[] => items.filter((item): item is T => !isHeading(item));

/** From the API order (each line knows its section) to a list with a heading before each group. */
export function withHeadings<L, T extends object>(
  lines: L[],
  sectionOf: (line: L) => string | null,
  toRow: (line: L) => T,
  newKey: () => string,
): Sectioned<T>[] {
  return groupBySection(lines, sectionOf).flatMap<Sectioned<T>>((group) => {
    const rows = group.items.map(toRow);
    return group.section === null ? rows : [{ key: newKey(), heading: group.section }, ...rows];
  });
}

/** Back to what the API takes: every row with the name of the heading above it (blank before any). */
export function withSections<T extends object>(items: Sectioned<T>[]): (T & { section: string | null })[] {
  let section: string | null = null;
  const rows: (T & { section: string | null })[] = [];
  for (const item of items) {
    if (isHeading(item)) section = item.heading.trim() || null;
    else rows.push({ ...item, section });
  }
  return rows;
}

export type HeadingProblem = "blank" | "duplicate";

/** Headings the API would reject or merge by surprise: a blank name, or the same name twice. */
export function headingProblems<T extends object>(items: Sectioned<T>[]): Record<string, HeadingProblem> {
  const problems: Record<string, HeadingProblem> = {};
  const seen = new Set<string>();
  for (const item of items) {
    if (!isHeading(item)) continue;
    const name = item.heading.trim().replace(/\s+/g, " ").toLowerCase();
    if (!name) problems[item.key] = "blank";
    else if (seen.has(name)) problems[item.key] = "duplicate";
    seen.add(name);
  }
  return problems;
}
