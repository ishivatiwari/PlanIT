import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { randomUUID } from "node:crypto";

const password = "isolated test passphrase 2026";
test.beforeEach(() => {
  test.skip(
    process.env.E2E_INTEGRATION !== "true",
    "Requires the isolated API/PostgreSQL stack.",
  );
});

async function register(page: Page) {
  const username = `test_${randomUUID().replaceAll("-", "").slice(0, 20)}`;
  await page.goto("/register");
  await page.getByLabel("Your name", { exact: false }).fill("Celebration host");
  await page.getByLabel("Username", { exact: false }).fill(username);
  await page.getByLabel("Password", { exact: false }).fill(password);
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "My events", exact: true }),
  ).toBeVisible();
  return username;
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

for (const kind of ["wedding", "birthday", "community"]) {
  test(`${kind}: create, reload, edit, archive, and sign out`, async ({
    page,
  }) => {
    const username = await register(page);
    await page.getByRole("link", { name: "Create event", exact: true }).click();
    await page.getByLabel("Event name", { exact: false }).fill(`Our ${kind}`);
    await page.getByLabel("Event type", { exact: false }).selectOption(kind);
    await page
      .getByLabel("Location", { exact: true })
      .fill("The garden pavilion");
    await page.getByLabel("Start date and time").fill("2027-02-12T18:00");
    await page.getByLabel("End date and time").fill("2027-02-12T21:00");
    await page.getByLabel("Guest count").fill("45");
    await page.getByLabel("Budget ceiling").fill("1000.01");
    await page
      .getByLabel("Dietary needs", { exact: true })
      .selectOption("details");
    await page
      .getByLabel("Dietary details", { exact: false })
      .fill("Vegetarian menu");
    await page
      .getByLabel("Accessibility needs", { exact: true })
      .selectOption("details");
    await page
      .getByLabel("Accessibility details", { exact: false })
      .fill("Step-free entrance");
    await page
      .getByLabel("Preferences", { exact: true })
      .fill("Fresh flowers\nA quiet corner");
    await accessible(page);
    if (kind === "wedding") await page.evaluate(() => window.scrollTo(0, 0));
    if (kind === "wedding")
      await page.screenshot({
        path: `test-results/event-form-${test.info().project.name}.png`,
        fullPage: true,
      });
    const response = page.waitForResponse(
      (res) =>
        res.url().endsWith("/api/v1/events") &&
        res.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: "Create event", exact: true })
      .click();
    const saved = await response;
    expect(saved.status()).toBe(201);
    expect((await saved.json()).budget_ceiling_minor).toBe(100001);
    await expect(
      page.getByRole("heading", { name: `Our ${kind}`, exact: true }),
    ).toBeVisible();
    await expect(page.getByText("INR 1,000.01", { exact: true })).toBeVisible();
    await page.reload();
    await expect(
      page.getByText("Step-free entrance", { exact: true }),
    ).toBeVisible();
    await page.getByRole("link", { name: "Edit event", exact: true }).click();
    await page
      .getByLabel("Event name", { exact: false })
      .fill(`Updated ${kind}`);
    await page.getByLabel("Guest count").fill("50");
    await page.getByRole("button", { name: "Save changes" }).click();
    await expect(
      page.getByRole("heading", { name: `Updated ${kind}`, exact: true }),
    ).toBeVisible();
    await accessible(page);
    if (kind === "wedding")
      await page.screenshot({
        path: `test-results/event-detail-${test.info().project.name}.png`,
        fullPage: true,
      });
    await page.getByRole("button", { name: "Archive", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "Archive this event?" });
    await expect(dialog).toBeVisible();
    await dialog
      .getByRole("button", { name: "Archive event", exact: true })
      .click();
    await expect(
      page.getByText("This event is archived and read-only."),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: `Updated ${kind}`, exact: true }),
    ).toBeFocused();
    await expect(page.getByRole("link", { name: "Edit event" })).toHaveCount(0);
    await page.getByRole("link", { name: "Back to my events" }).click();
    await page.getByLabel("Show events").selectOption("archived");
    await expect(
      page.getByRole("link", { name: `Updated ${kind}`, exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Sign out", exact: true }).click();
    await expect(
      page.getByRole("link", { name: `Updated ${kind}`, exact: true }),
    ).toHaveCount(0);
    await page.reload();
    await expect(
      page.getByRole("heading", { name: "Your celebrations, together." }),
    ).toBeVisible();
    await page
      .getByRole("main")
      .getByRole("link", { name: "Sign in", exact: true })
      .click();
    await page.getByLabel("Username", { exact: false }).fill(username);
    await page.getByLabel("Password", { exact: false }).fill(password);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "My events", exact: true }),
    ).toBeVisible();
    await page.getByLabel("Show events").selectOption("archived");
    await expect(
      page.getByRole("link", { name: `Updated ${kind}`, exact: true }),
    ).toBeVisible();
  });
}

test("invalid money, invalid timezone and incomplete confirmed events preserve input", async ({
  page,
}) => {
  await register(page);
  await page.goto("/events/new");
  await page.getByLabel("Event name", { exact: false }).fill("Still a draft");
  await page.getByLabel("Currency", { exact: true }).selectOption("JPY");
  await page.getByLabel("Budget ceiling").fill("100.50");
  await page.getByRole("button", { name: "Create event", exact: true }).click();
  await expect(page.getByLabel("Budget ceiling")).toHaveAttribute(
    "aria-invalid",
    "true",
  );
  await expect(page.getByLabel("Budget ceiling")).toBeFocused();
  await accessible(page);
  await page.getByLabel("Budget ceiling").fill("100");
  await page.getByLabel("Timezone", { exact: false }).fill("Unknown/Place");
  await page.getByRole("button", { name: "Create event", exact: true }).click();
  await expect(page.getByLabel("Timezone", { exact: false })).toHaveAttribute(
    "aria-invalid",
    "true",
  );
  await expect(page.getByLabel("Event name", { exact: false })).toHaveValue(
    "Still a draft",
  );
  await page.getByLabel("Timezone", { exact: false }).fill("Asia/Kolkata");
  await page.getByLabel("Event status").selectOption("confirmed");
  await page.getByRole("button", { name: "Create event", exact: true }).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "require a start",
  );
  await page.getByLabel("Event status").selectOption("draft");
  await page.getByRole("button", { name: "Create event", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Still a draft" }),
  ).toBeVisible();
  await expect(page.getByText("JPY 100", { exact: true })).toBeVisible();
});

test("a second account cannot access or change the first account's event through the proxy", async ({
  page,
  browser,
  baseURL,
}) => {
  await register(page);
  const me = await (await page.request.get("/api/v1/me")).json();
  const headers = {
    Origin: baseURL!,
    "X-Requested-With": "Eventora",
    "X-CSRF-Token": me.csrf_token,
  };
  const created = await page.request.post("/api/v1/events", {
    headers,
    data: { title: "Private first account event", event_type: "birthday" },
  });
  expect(created.status()).toBe(201);
  const event = await created.json();
  const other = await browser.newContext({ baseURL });
  try {
    const signup = await other.request.post("/api/v1/auth/register", {
      headers: { Origin: baseURL!, "X-Requested-With": "Eventora" },
      data: {
        username: `other_${randomUUID().replaceAll("-", "").slice(0, 18)}`,
        display_name: "Other host",
        password,
      },
    });
    expect(signup.status()).toBe(201);
    const otherHeaders = {
      ...headers,
      "X-CSRF-Token": (await signup.json()).csrf_token,
      "If-Match": '"1"',
    };
    expect(
      (await other.request.get(`/api/v1/events/${event.id}`)).status(),
    ).toBe(404);
    expect(
      (
        await other.request.patch(`/api/v1/events/${event.id}`, {
          headers: otherHeaders,
          data: { title: "Unauthorized edit" },
        })
      ).status(),
    ).toBe(404);
    expect(
      (
        await other.request.post(`/api/v1/events/${event.id}/archive`, {
          headers: otherHeaders,
          data: {},
        })
      ).status(),
    ).toBe(404);
    expect(
      (await (await other.request.get("/api/v1/events")).json()).items,
    ).toEqual([]);
    expect(
      (
        await page.request.patch(`/api/v1/events/${event.id}`, {
          headers: { ...headers, "If-Match": '"1"' },
          data: { title: "Current title" },
        })
      ).status(),
    ).toBe(200);
    expect(
      (
        await page.request.patch(`/api/v1/events/${event.id}`, {
          headers: { ...headers, "If-Match": '"1"' },
          data: { title: "Stale overwrite" },
        })
      ).status(),
    ).toBe(412);
    expect(
      (
        await page.request.post(`/api/v1/events/${event.id}/archive`, {
          headers: {
            Origin: baseURL!,
            "X-Requested-With": "Eventora",
            "If-Match": '"2"',
          },
          data: {},
        })
      ).status(),
    ).toBe(403);
    await page.goto(`/events/${event.id}`);
    await expect(
      page.getByRole("heading", { name: "Current title" }),
    ).toBeVisible();
  } finally {
    await other.close();
  }
});

test("signed-out requests and unknown proxy paths cannot expose protected data", async ({
  page,
  request,
}) => {
  expect((await request.get("/api/v1/events")).status()).toBe(401);
  expect((await request.get("/api/v1/users")).status()).toBe(404);
  expect((await request.get("/api/v1/events?owner_id=anything")).status()).toBe(
    422,
  );
  await page.goto("/events/new");
  await expect(
    page.getByRole("heading", { name: "Your celebrations, together." }),
  ).toBeVisible();
  await expect(page.getByLabel("Event name", { exact: false })).toHaveCount(0);
  await accessible(page);
});

test("signing out clears protected views in another tab", async ({
  page,
  context,
}) => {
  await register(page);
  const second = await context.newPage();
  await second.goto("/events/new");
  await expect(second.getByLabel("Event name", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(second.getByLabel("Event name", { exact: false })).toHaveCount(
    0,
  );
  await expect(
    second.getByRole("heading", { name: "Your celebrations, together." }),
  ).toBeVisible();
  await second.close();
});
