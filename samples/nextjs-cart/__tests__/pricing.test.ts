import { applyPercentDiscount, cartTotalCents, lineTotalCents } from "../lib/pricing";

describe("pricing", () => {
  test("line total", () => {
    expect(lineTotalCents({ sku: "tee", unitPriceCents: 2500, qty: 2 })).toBe(5000);
  });

  test("10% off a $50 cart is $45", () => {
    expect(applyPercentDiscount(5000, 10)).toBe(4500);
  });

  test("cart total with coupon", () => {
    const total = cartTotalCents(
      [
        { sku: "tee", unitPriceCents: 2500, qty: 2 },
        { sku: "hat", unitPriceCents: 1500, qty: 1 },
      ],
      10,
    );
    // 2500*2 + 1500 = 6500 → 10% off → 5850
    expect(total).toBe(5850);
  });
});
