import { expect, test } from "@playwright/test";
import { formatMoney, minorInput, parseMinor } from "../src/lib/money";

test("currency conversion preserves exact minor units without floating point arithmetic", () => {
  expect(parseMinor("1000.01", "INR")).toBe(100001);
  expect(parseMinor("0", "INR")).toBe(0);
  expect(parseMinor("", "INR")).toBeNull();
  expect(parseMinor("90071992547409.91", "USD")).toBe(9007199254740991);
  expect(minorInput(9007199254740991, "USD")).toBe("90071992547409.91");
  expect(formatMoney(100001, "INR")).toBe("INR 1,000.01");
  expect(formatMoney(100, "JPY")).toBe("JPY 100");
  for (const invalid of ["1.001", "-1", "1e3", "1,000", "90071992547409.92"])
    expect(() => parseMinor(invalid, "INR")).toThrow();
  expect(() => parseMinor("1.1", "JPY")).toThrow();
});
