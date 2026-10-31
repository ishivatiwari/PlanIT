import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("live connection states, navigation, and accessibility", async ({
  page,
}) => {
  // Explicit browser fixture; the unmocked integration test below verifies the real API.
  await page.route("**/api/v1/health/*", async (route) => {
    await route.fulfill({
      json: { status: route.request().url().endsWith("live") ? "ok" : "ready" },
    });
  });
  await page.goto("/system-status");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Connection status",
  );
  await expect(page.getByRole("status")).toHaveText(
    "Your foundation is connected.",
  );
  await expect(
    page.getByText("Sign in to check", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Check again" }).click();
  await expect(page.getByRole("status")).toHaveText(
    "Your foundation is connected.",
  );
  const accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(accessibility.violations).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("unavailable API is honest and can recover", async ({ page }) => {
  let healthy = false;
  await page.route("**/api/v1/health/*", async (route) => {
    if (!healthy)
      return route.fulfill({
        status: 503,
        json: { error: { code: "UNAVAILABLE" } },
      });
    return route.fulfill({
      json: { status: route.request().url().endsWith("live") ? "ok" : "ready" },
    });
  });
  await page.goto("/system-status");
  await expect(page.getByRole("status")).toHaveText(
    "A connection needs attention.",
  );
  await expect(page.getByText("Unavailable", { exact: true })).toBeVisible();
  await expect(page.getByText("Unverified", { exact: true })).toBeVisible();
  healthy = true;
  await page.getByRole("button", { name: "Check again" }).click();
  await expect(page.getByRole("status")).toHaveText(
    "Your foundation is connected.",
  );
});

test("API live with database unready is distinguished", async ({ page }) => {
  await page.route("**/api/v1/health/*", async (route) =>
    route.fulfill(
      route.request().url().endsWith("live")
        ? { json: { status: "ok" } }
        : { status: 503, json: {} },
    ),
  );
  await page.goto("/system-status");
  await expect(page.getByText("Connected", { exact: true })).toBeVisible();
  await expect(page.getByText("Not ready", { exact: true })).toBeVisible();
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2aa", "wcag21aa"]).analyze())
      .violations,
  ).toEqual([]);
});

test("keyboard skip link and visible focus", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to content" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("main")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Choose a celebration" }),
  ).toBeFocused();
});

test("actual API and database through the web origin", async ({
  page,
  request,
}) => {
  test.skip(
    process.env.E2E_INTEGRATION !== "true",
    "Requires the running FastAPI/PostgreSQL stack.",
  );
  const live = await request.get("/api/v1/health/live");
  const ready = await request.get("/api/v1/health/ready");
  expect(live.status()).toBe(200);
  expect(live.headers()["x-request-id"]).toMatch(/^[0-9a-f-]{36}$/);
  expect(await live.json()).toEqual({ status: "ok" });
  expect(ready.status()).toBe(200);
  expect(await ready.json()).toEqual({ status: "ready" });
  await page.goto("/system-status");
  await expect(page.getByRole("status")).toHaveText(
    "Your foundation is connected.",
  );
  await page.screenshot({
    path: `test-results/status-${test.info().project.name}.png`,
    fullPage: true,
  });
  const unknown = await request.get("/api/v1/health/arbitrary");
  expect(unknown.status()).toBe(404);
  expect((await unknown.json()).request_id).toBe(
    unknown.headers()["x-request-id"],
  );
});
