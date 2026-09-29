import { expect, test } from "@playwright/test";

test("Ensemble navigation opens its supported 2025 experiment from a 2019 context", async ({ page }) => {
  await page.goto("/forecast?experiment=reforecast&year=2019");
  const link = page.getByRole("navigation", { name: "Primary" }).getByRole("link", { name: "Ensemble & Uncertainty" });
  await expect(link).toHaveAttribute("href", "/ensemble?experiment=operational&year=2025");
  await link.click();
  await expect(page).toHaveURL(/\/ensemble\?experiment=operational&year=2025$/);
  await expect(page.getByRole("heading", { name: "Ensemble & Uncertainty" })).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Experiment and year" })).toHaveValue("operational:2025");
  await expect(page.getByText("Data unavailable")).toHaveCount(0);
});

test("unsupported direct Ensemble URLs redirect to the supported view", async ({ page }) => {
  await page.goto("/ensemble?experiment=reforecast&year=2019");
  await expect(page).toHaveURL(/\/ensemble\?experiment=operational&year=2025$/);
  await expect(page.getByRole("heading", { name: "Ensemble & Uncertainty" })).toBeVisible();
});
