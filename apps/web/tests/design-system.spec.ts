import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

async function accessible(page: Page) {
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
}

async function noOverflow(page: Page) {
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(page.viewportSize()!.width);
}

test("occasion selection is keyboard accessible, local, and resettable", async ({
  page,
}) => {
  const writes: string[] = [];
  page.on("request", (request) => {
    if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method()))
      writes.push(request.url());
  });
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Good thingsstart with a plan.",
  );
  await page.getByRole("link", { name: "Choose a celebration" }).click();
  await expect(page).toHaveURL(/#occasions$/);
  const wedding = page.getByRole("radio", { name: /Wedding/ });
  await wedding.focus();
  await page.keyboard.press("Space");
  await expect(wedding).toBeChecked();
  await expect(
    page.getByRole("heading", { name: "Wedding preview" }),
  ).toBeVisible();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("radio", { name: /Birthday/ })).toBeChecked();
  await expect(page.getByRole("status")).toHaveText(
    "Birthday selected for preview. Nothing has been saved.",
  );
  await page.getByRole("button", { name: "Clear selection" }).click();
  await expect(wedding).toBeFocused();
  await expect(page.locator('input[name="occasion"]:checked')).toHaveCount(0);
  await page.getByText("Community", { exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Community preview" }),
  ).toBeVisible();
  await page.reload();
  await expect(page.locator('input[name="occasion"]:checked')).toHaveCount(0);
  expect(writes).toEqual([]);
  await accessible(page);
  await noOverflow(page);
  await page.goto("/");
  await page.screenshot({
    path: `test-results/foundation-${test.info().project.name}.png`,
    fullPage: true,
  });
});

test("navigation reaches real routes and future areas are noninteractive", async ({
  page,
}) => {
  await page.goto("/");
  const menu = page.getByRole("button", { name: "Open navigation" });
  if (await menu.isVisible()) {
    await menu.click();
    const dialog = page.getByRole("dialog", {
      name: "Navigation",
      exact: true,
    });
    await expect(dialog).toBeVisible();
    await expect(
      dialog.getByRole("button", { name: "Close dialog" }),
    ).toBeFocused();
    await page.keyboard.press("Shift+Tab");
    await expect(
      dialog.getByRole("link", { name: "System status" }),
    ).toBeFocused();
    await page.keyboard.press("Tab");
    await expect(
      dialog.getByRole("button", { name: "Close dialog" }),
    ).toBeFocused();
    await accessible(page);
    await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible();
    await expect(menu).toBeFocused();
    await menu.click();
  }
  const navigation = page.getByRole("navigation", {
    name: "Workspace navigation",
  });
  await expect(
    navigation.getByRole("link", { name: "Overview", exact: true }),
  ).toHaveAttribute("aria-current", "page");
  await expect(
    navigation.getByRole("link", { name: /Budgets|Timelines/ }),
  ).toHaveCount(0);
  await expect(
    navigation.getByRole("button", { name: /Budgets|Timelines/ }),
  ).toHaveCount(0);
  await navigation.getByRole("link", { name: "Design system" }).click();
  await expect(page).toHaveURL(/\/design-system$/);
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "A shared design language.",
  );
  if (await menu.isVisible()) await menu.click();
  await expect(
    navigation.getByRole("link", { name: "Design system" }),
  ).toHaveAttribute("aria-current", "page");
});

test("dialogs contain focus, describe preview limits, and restore focus", async ({
  page,
}) => {
  await page.goto("/");
  const trigger = page.getByRole("button", { name: "About this workspace" });
  await trigger.click();
  const dialog = page.getByRole("dialog", { name: "A thoughtful beginning" });
  const close = dialog.getByRole("button", { name: "Close dialog" });
  await expect(close).toBeFocused();
  await expect(dialog).toContainText("Nothing here books a service");
  await page.keyboard.press("Shift+Tab");
  await expect(dialog.getByRole("button", { name: "Got it" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(close).toBeFocused();
  await accessible(page);
  await page.screenshot({
    path: `test-results/dialog-${test.info().project.name}.png`,
    fullPage: false,
  });
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(trigger).toBeFocused();
  await trigger.click();
  await close.click();
  await expect(trigger).toBeFocused();
  await expect(page.locator("body")).not.toHaveCSS("overflow", "hidden");
});

test("form errors are linked and announced; sample updates never save an event", async ({
  page,
}) => {
  const writes: string[] = [];
  page.on("request", (request) => {
    if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method()))
      writes.push(request.url());
  });
  await page.goto("/design-system");
  const label = page.getByRole("textbox", { name: "Preview label" });
  await page.getByRole("button", { name: "Update sample card" }).click();
  await expect(label).toBeFocused();
  await expect(label).toHaveAttribute("aria-invalid", "true");
  await expect(label).toHaveAccessibleDescription(
    /Enter a label for the sample card/,
  );
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "Check the preview label",
  );
  await accessible(page);
  await label.fill("An evening together");
  await page.getByRole("combobox", { name: "Tone" }).selectOption("Natural");
  await page.getByRole("button", { name: "Update sample card" }).click();
  await expect(
    page.getByRole("heading", { name: "An evening together" }),
  ).toBeVisible();
  await expect(page.getByText("Natural style", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("status").filter({ hasText: "Sample updated" }),
  ).toContainText("Nothing has been saved.");
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
  await page.getByRole("button", { name: "Reset sample" }).click();
  await expect(label).toHaveValue("");
  await expect(
    page.getByRole("heading", { name: "A gathering to remember" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Coming soon" }),
  ).toBeDisabled();
  expect(writes).toEqual([]);
  await accessible(page);
  await noOverflow(page);
  await page.goto("/design-system");
  await page.screenshot({
    path: `test-results/design-system-${test.info().project.name}.png`,
    fullPage: true,
  });
});

test("example dialog and reduced-motion loading state stay honest", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/design-system");
  await expect(
    page.getByRole("main").getByText("A visual sample; no request is running."),
  ).toBeVisible();
  await expect(page.locator(".loading-state .spinner").first()).toHaveCSS(
    "animation-name",
    "none",
  );
  const trigger = page.getByRole("button", { name: "Open example dialog" });
  await trigger.click();
  const dialog = page.getByRole("dialog", { name: "A moment of clarity" });
  await expect(dialog).toHaveAccessibleDescription(
    "This is a reusable dialog example.",
  );
  await dialog.getByRole("button", { name: "Back to the preview" }).click();
  await expect(dialog).not.toBeVisible();
  await expect(trigger).toBeFocused();
});

test("pending and invalid health responses never appear healthy", async ({
  page,
}) => {
  let release!: () => void;
  const pending = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/v1/health/*", async (route) => {
    await pending;
    await route.fulfill({ json: { status: "simulated" } });
  });
  try {
    await page.goto("/system-status");
    const checking = page.getByRole("button", {
      name: "Checking...",
      exact: true,
    });
    await expect(checking).toBeDisabled();
    await expect(checking).toHaveAttribute("aria-busy", "true");
    await expect(page.getByText("Ready", { exact: true })).toHaveCount(0);
  } finally {
    release();
  }
  await expect(page.getByRole("status")).toHaveText(
    "A connection needs attention.",
  );
  await expect(page.getByRole("button", { name: "Check again" })).toBeEnabled();
  await expect(page.getByText("Unverified", { exact: true })).toBeVisible();
});

test("all preview pages reflow at 320px and enlarged text", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 800 });
  for (const path of ["/", "/design-system", "/system-status"]) {
    await page.goto(path);
    await noOverflow(page);
    await page.addStyleTag({ content: "html { font-size: 200% !important; }" });
    await noOverflow(page);
  }
});

test("unknown pages provide a real way back", async ({ page }) => {
  const response = await page.goto("/this-page-does-not-exist");
  expect(response?.status()).toBe(404);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Let's find your way back.",
  );
  await page.getByRole("link", { name: "Return to overview" }).click();
  await expect(page).toHaveURL(/\/$/);
});
