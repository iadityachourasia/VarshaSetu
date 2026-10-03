import { describe, expect, it } from "vitest";
import { graticule, graticuleStep } from "./chrome";

describe("map graticule", () => {
  it("chooses a spacing that suits the extent", () => {
    expect(graticuleStep([67.875, 9.875, 80.125, 22.125])).toBe(2);
    expect(graticuleStep([55, 5, 95, 30])).toBe(5);
    expect(graticuleStep([70, 10, 74, 14])).toBe(1);
  });
  it("draws a line at every tick and labels only ticks away from the corners", () => {
    const { lines, labels } = graticule([67.875, 9.875, 80.125, 22.125]);
    expect(lines.features).toHaveLength(14);                                  // meridians 68 to 80 and parallels 10 to 22, every 2 degrees
    const texts = labels.features.map((feature) => feature.properties.text);
    expect(texts).toContain("20° N");
    expect(texts).toContain("72° E");
    expect(texts).not.toContain("22° N");
    expect(texts).not.toContain("68° E");
    expect(texts).not.toContain("10° N");
    expect(texts).not.toContain("80° E");
  });
  it("places meridian labels on the south edge and parallel labels on the west edge", () => {
    const { labels } = graticule([67.875, 9.875, 80.125, 22.125]);
    for (const feature of labels.features) {
      const [lon, lat] = feature.geometry.coordinates;
      if (feature.properties.axis === "lon") expect(lat).toBe(9.875);
      else expect(lon).toBe(67.875);
    }
  });
});
