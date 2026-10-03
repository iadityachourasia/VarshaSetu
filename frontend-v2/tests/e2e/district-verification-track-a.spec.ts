import { expect, test } from "@playwright/test";

// Track A (2017-2019 reforecast) district-level verification (protocol A v1, docs/135) against the REAL backend and hash-verified evidence.

const fixed = (value: number | null, digits: number) => (value == null ? "undefined" : value.toFixed(digits));

test("the Track A district panel shows the post-hoc 2019 label, its own protocol and numbers equal to the evidence API", async ({ page }) => {
  const api = await (await page.request.get("/api/science/evidence/district-verification?year=2019")).json();
  expect(api.track).toBe("A");
  await page.goto("/verification");
  const block = page.getByTestId("track-a-district-verification");
  await expect(block).toBeVisible();
  const panel = block.locator(".district-verification");
  await expect(panel.getByText("POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST")).toBeVisible();
  await expect(panel).toContainText("Track A · 2019");
  await expect(panel.getByText(`approved and frozen (SHA-256 ${api.protocol_sha256.slice(0, 12)}`)).toBeVisible();
  await expect(panel.getByText(/169 of 188 districts included/)).toBeVisible();
  const pooled = panel.getByRole("table", { name: /Pooled district-mean RMSE, MAE and bias/ });
  const cells = await pooled.locator("tbody tr").nth(2).locator("td").allTextContents();
  const m2 = api.continuous.pooled.all.M2;
  expect(cells.slice(0, 3)).toEqual([fixed(m2.rmse_mm, 2), fixed(m2.mae_mm, 2), fixed(m2.bias_mm, 2)]);
  const event = panel.getByRole("table", { name: /CSI for E1 heavy district events, pooled/ });
  const csi = (await event.locator("tbody tr").first().locator("td").allTextContents()).map((c) => c.trim());
  expect(csi).toEqual(["M0", "M1", "M2", "M3", "M4"].map((m) => fixed(api.categorical.E1.heavy.pooled.all[m].CSI, 3)));
});

test("switching to 2018 relabels the evidence as development and changes the numbers to the 2018 evidence", async ({ page }) => {
  const api2018 = await (await page.request.get("/api/science/evidence/district-verification?year=2018")).json();
  await page.goto("/verification");
  const block = page.getByTestId("track-a-district-verification");
  await block.getByRole("combobox", { name: "Population" }).selectOption("2018");
  const panel = block.locator(".district-verification");
  await expect(panel).toContainText("Track A · 2018");
  await expect(panel.getByText(/Track A 2018 validation year: development evidence/)).toBeVisible();
  await expect(panel.getByText("POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST")).toHaveCount(0);
  const pooled = panel.getByRole("table", { name: /Pooled district-mean RMSE, MAE and bias/ });
  const cells = await pooled.locator("tbody tr").nth(0).locator("td").allTextContents();
  expect(cells[0]).toBe(fixed(api2018.continuous.pooled.all.M0.rmse_mm, 2));
});

test("the Track A report downloads are labelled for their track", async ({ page }) => {
  await page.goto("/verification");
  const block = page.getByTestId("track-a-district-verification");
  const href = await block.getByRole("link", { name: "CSV" }).getAttribute("href");
  expect(href).toContain("district-verification/report?year=2019&format=csv");
  const response = await page.request.get(href!);
  expect(response.ok()).toBeTruthy();
  expect(response.headers()["content-disposition"]).toContain("varshasetu_district_verification_A_2019.csv");
});
