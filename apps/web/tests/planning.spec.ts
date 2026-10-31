import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { randomUUID } from "node:crypto";

test.beforeEach(() =>
  test.skip(
    process.env.E2E_AI_FIXTURE !== "true",
    "Requires the explicitly isolated fixture-provider test server.",
  ),
);

async function setup(page: Page, baseURL: string) {
  const registration = await page.request.post("/api/v1/auth/register", {
    headers: { Origin: baseURL, "X-Requested-With": "Eventora" },
    data: {
      username: `ai_${randomUUID().replaceAll("-", "").slice(0, 20)}`,
      display_name: "Planning host",
      password: "synthetic planning passphrase 2030",
    },
  });
  expect(registration.status()).toBe(201);
  const identity = await registration.json();
  const created = await page.request.post("/api/v1/events", {
    headers: {
      Origin: baseURL,
      "X-Requested-With": "Eventora",
      "X-CSRF-Token": identity.csrf_token,
    },
    data: { title: "Our birthday", event_type: "birthday" },
  });
  expect(created.status()).toBe(201);
  const event = await created.json();
  await page.goto(`/events/${event.id}/planning`);
  await expect(page.getByLabel("Describe your event")).toBeVisible();
  return event;
}

async function accessible(page: Page) {
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(page.viewportSize()!.width);
}

test("extract, clarify, generate, edit, save and reload a structured plan", async ({
  page,
  baseURL,
}) => {
  const event = await setup(page, baseURL!);
  await page
    .getByLabel("Describe your event")
    .fill(
      "An incomplete birthday idea with a vegetarian menu and step-free access.",
    );
  await page.getByRole("checkbox", { name: /Send this description/ }).check();
  await page
    .getByRole("button", { name: "Extract event details", exact: true })
    .click();
  await expect(
    page.getByText("How many guests should the plan accommodate?", {
      exact: true,
    }),
  ).toBeVisible();
  await page.getByLabel("Location", { exact: false }).fill("Community garden");
  await page.getByLabel("Guest count", { exact: false }).fill("30");
  await page.getByLabel("Budget ceiling", { exact: false }).fill("30000.01");
  await page.getByLabel("Duration in minutes", { exact: false }).fill("180");
  await accessible(page);
  await page.getByRole("checkbox", { name: /I have checked/ }).check();
  await page
    .getByRole("button", { name: "Generate and save draft", exact: true })
    .click();
  await expect(
    page.getByLabel("Event summary", { exact: false }),
  ).toBeVisible();
  await expect(page.getByText("INR 30,000.01", { exact: true })).toBeVisible();
  await page
    .getByLabel("Event summary", { exact: false })
    .fill("Reviewed garden birthday, with quiet games and vegetarian food.");
  await page.getByLabel("Estimated amount 1 (INR)").fill("21000.01");
  await page
    .getByLabel("Menu ideas", { exact: false })
    .fill("Vegetarian dishes with allergen labels");
  await page
    .getByRole("button", { name: "Save reviewed plan", exact: true })
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "Plan saved" }),
  ).toBeVisible();
  await expect(page.getByText("INR 31,000.01", { exact: true })).toBeVisible();
  await expect(
    page.getByText(/These estimates exceed the budget/),
  ).toBeVisible();
  await accessible(page);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `test-results/planning-${test.info().project.name}.png`,
    fullPage: true,
  });
  await page.reload();
  await page.getByRole("link", { name: /A garden birthday.*Draft 1/ }).click();
  await expect(page.getByLabel("Event summary", { exact: false })).toHaveValue(
    "Reviewed garden birthday, with quiet games and vegetarian food.",
  );
  await expect(page.getByLabel("Menu ideas", { exact: false })).toHaveValue(
    "Vegetarian dishes with allergen labels",
  );
  await page.setViewportSize({ width: 320, height: 800 });
  await page.addStyleTag({ content: "html { font-size: 200% !important; }" });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(320);
  expect(
    (await page.request.get(`/api/v1/events/${event.id}/plans`)).status(),
  ).toBe(200);

  // Exercise the real owner-scoped API through the web controls and proxy.
  await page.goto(`/events/${event.id}/budget`);
  expect(
    (
      await page.request.get(`/api/v1/events/${event.id}/budget?format=json`)
    ).status(),
  ).toBe(422);
  await page
    .getByRole("textbox", { name: "Category (required)", exact: true })
    .fill("Venue");
  await page
    .getByRole("textbox", { name: "Description (required)", exact: true })
    .fill("Room rental");
  await page.getByLabel("Planned", { exact: true }).fill("1250.50");
  await page
    .getByRole("button", { name: "Add budget line", exact: true })
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "Budget line saved" }),
  ).toBeVisible();
  await page
    .getByRole("textbox", { name: "Task (required)", exact: true })
    .fill("Confirm venue");
  await page.getByLabel("Owner", { exact: true }).fill("Host");
  await page.getByRole("button", { name: "Add task", exact: true }).click();
  const progress = page.getByLabel("Progress for Confirm venue");
  await progress.selectOption("done");
  await expect(
    page.getByRole("status").filter({ hasText: "Task progress saved" }),
  ).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Progress for Confirm venue")).toHaveValue(
    "done",
  );
  await accessible(page);
  await expect(page.getByRole("main")).toHaveCount(1);
  await expect(page.locator(".budget-bar-fill")).not.toHaveCSS(
    "background-color",
    "rgba(0, 0, 0, 0)",
  );
  await page.screenshot({
    path: `test-results/budget-${test.info().project.name}.png`,
    fullPage: true,
  });
  await page.addStyleTag({ content: "html { font-size: 200% !important; }" });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(320);
  await page.goto(`/events/${event.id}/replan`);
  await page.getByLabel("Change detail").fill("40");
  await page.getByRole("button", { name: "Analyse impact" }).click();
  await expect(
    page.getByRole("heading", { name: "Before and after review" }),
  ).toBeVisible();
  await accessible(page);
  await page.getByRole("button", { name: "Reject proposal" }).click();
  await expect(page.getByText("Status: rejected")).toBeVisible();
  await page.goto(`/events/${event.id}/vendors`);
  await expect(
    page.getByRole("heading", { name: "Vendors and requirements" }),
  ).toBeVisible();
  await accessible(page);
});

test("a provider failure is recoverable and never fabricates a draft", async ({
  page,
  baseURL,
}) => {
  const event = await setup(page, baseURL!);
  await page
    .getByLabel("Describe your event")
    .fill("Please simulate failure for this isolated test request.");
  await page.getByRole("checkbox", { name: /Send this description/ }).check();
  await page
    .getByRole("button", { name: "Extract event details", exact: true })
    .click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "The model took too long",
  );
  expect(
    (await (await page.request.get(`/api/v1/events/${event.id}/plans`)).json())
      .items,
  ).toEqual([]);
  await page
    .getByLabel("Describe your event")
    .fill(
      "A relaxed birthday gathering with vegetarian food and step-free access.",
    );
  await page
    .getByRole("button", { name: "Extract event details", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Make the details yours." }),
  ).toBeVisible();
  await expect(page.getByLabel("Guest count", { exact: false })).toHaveValue(
    "30",
  );
});
