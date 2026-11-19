import {expect, test} from "@playwright/test";

for (const width of [320, 375, 768, 1024, 1440]) {
  test("consulta y cita en " + width + " px", async ({page}) => {
    await page.setViewportSize({width, height: 860});
    await page.goto("/");
    await page.getByLabel("Tu pregunta").fill("¿Cuánto asciende la reserva de crédito Faro?");
    await page.getByRole("button", {name: "Consultar"}).click();
    await expect(page.getByText(/731 millones/)).toBeVisible();
    const cite = page.getByRole("button", {name: /ensayo.pdf.*Página 2/});
    await cite.focus();
    await page.keyboard.press("Enter");
    const modal = page.getByRole("dialog");
    await expect(modal.getByAltText("Página original 2")).toBeVisible();
    await expect.poll(() => modal.locator("img").evaluate((el: HTMLImageElement) => el.naturalWidth)).toBeGreaterThan(0);
    await page.keyboard.press("Escape");
    await expect(modal).toHaveCount(0);
    await expect(cite).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
  });
}

test("abstención, caída y reintento conservan la conversación", async ({page}) => {
  await page.goto("/");
  await page.getByLabel("Tu pregunta").fill("Combustible de la sonda Voyager");
  await page.getByRole("button", {name: "Consultar"}).click();
  await expect(page.getByText("EVIDENCIA INSUFICIENTE", {exact: true})).toBeVisible();
  await page.route("**/api/chat", route => route.fulfill({status: 503, contentType:"application/json",
    body: JSON.stringify({detail:"Proveedor no disponible."})}));
  await page.getByLabel("Tu pregunta").fill("reserva Faro");
  await page.getByRole("button", {name: "Consultar"}).click();
  await expect(page.getByRole("alert")).toContainText("Proveedor no disponible");
  await page.unroute("**/api/chat");
  await page.getByRole("button", {name:"Reintentar"}).click();
  await expect(page.getByText(/731 millones/)).toBeVisible();
  const citation = page.getByRole("button", {name:/ensayo.pdf.*Página 2/});
  await page.route("**/image?*", route => route.fulfill({status:404}));
  await citation.click();
  await expect(page.getByRole("alert")).toContainText("No se pudo abrir");
  await page.unroute("**/image?*");
  await page.getByRole("button", {name:"Reintentar"}).click();
  await expect.poll(() => page.locator("dialog img").evaluate((el: HTMLImageElement) => el.naturalWidth)).toBeGreaterThan(0);
});
