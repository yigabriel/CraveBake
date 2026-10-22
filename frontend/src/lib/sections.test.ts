import { describe, expect, it } from "vitest";
import { groupBySection, headingProblems, inStorageOrder, isHeading, rowsOf, withHeadings, withSections, type Sectioned } from "./sections";

interface Row {
  key: string;
  name: string;
}
const row = (name: string): Row => ({ key: `r-${name}`, name });
const section = (name: string, group: string | null) => ({ ...row(name), section: group });

let counter = 0;
const newKey = () => `h-${++counter}`;

describe("groupBySection", () => {
  it("starts a group each time the section changes", () => {
    const lines = [section("sal", null), section("agua", "Masa"), section("manteca", "Masa"), section("leche", "Manjar")];
    const groups = groupBySection(lines, (line) => line.section);

    expect(groups.map((g) => [g.section, g.items.map((i) => i.name)])).toEqual([
      [null, ["sal"]],
      ["Masa", ["agua", "manteca"]],
      ["Manjar", ["leche"]],
    ]);
  });

  it("has one group for a recipe without sections, and none for an empty one", () => {
    expect(groupBySection([section("a", null), section("b", null)], (l) => l.section)).toHaveLength(1);
    expect(groupBySection([], () => null)).toEqual([]);
  });
});

describe("editor list", () => {
  const lines = [section("sal", null), section("agua", "Masa"), section("manteca", "Masa"), section("leche", "Manjar")];

  it("puts a heading before each group and none before the ungrouped lines", () => {
    const items = withHeadings(lines, (l) => l.section, ({ name }) => row(name), newKey);

    expect(items.map((i) => (isHeading(i) ? `# ${i.heading}` : i.name))).toEqual(["sal", "# Masa", "agua", "manteca", "# Manjar", "leche"]);
  });

  it("round-trips: every row gets the heading above it", () => {
    const items = withHeadings(lines, (l) => l.section, ({ name }) => row(name), newKey);

    expect(withSections(items).map((r) => [r.name, r.section])).toEqual(lines.map((l) => [l.name, l.section]));
  });

  it("moving a row across a heading changes its group", () => {
    const items: Sectioned<Row>[] = [{ key: "h", heading: "Masa" }, row("agua"), { key: "h2", heading: "Manjar" }, row("leche")];
    // leche goes up past the "Manjar" heading, into "Masa".
    [items[2], items[3]] = [items[3], items[2]];

    expect(withSections(items).map((r) => [r.name, r.section])).toEqual([["agua", "Masa"], ["leche", "Masa"]]);
  });

  it("a blank heading means no section", () => {
    expect(withSections<Row>([{ key: "h", heading: "  " }, row("agua")])[0].section).toBeNull();
  });

  it("rowsOf drops the headings", () => {
    expect(rowsOf<Row>([{ key: "h", heading: "Masa" }, row("agua")])).toEqual([row("agua")]);
  });
});

describe("headingProblems", () => {
  it("flags blank names and a name used twice (ignoring case and spacing)", () => {
    const items: Sectioned<Row>[] = [
      { key: "a", heading: "Masa choux" },
      row("x"),
      { key: "b", heading: "  masa   CHOUX " },
      { key: "c", heading: " " },
      { key: "d", heading: "Manjar" },
    ];

    expect(headingProblems(items)).toEqual({ b: "duplicate", c: "blank" });
  });

  it("is empty when every heading is fine", () => {
    expect(headingProblems<Row>([{ key: "a", heading: "Masa" }, { key: "b", heading: "Manjar" }])).toEqual({});
  });
});

describe("inStorageOrder", () => {
  it("puts section-less lines first and keeps each section together, in order of appearance", () => {
    const lines = [section("a", "Filling"), section("b", "Dough"), section("c", null), section("d", " filling "), section("e", null)];

    expect(inStorageOrder(lines, (l) => l.section).map((l) => l.name)).toEqual(["c", "e", "a", "d", "b"]);
  });

  it("changes nothing when the order is already right, and does not mutate its input", () => {
    const lines = [section("a", null), section("b", "Dough"), section("c", "Dough")];
    const before = [...lines];

    expect(inStorageOrder(lines, (l) => l.section)).toEqual(before);
    expect(lines).toEqual(before);
  });
});
