/**
 * Cart pricing helpers — the kind of pure util you'd keep next to a Next.js app router.
 * Bug: percent discounts are applied as if the value were already a fraction (10 → 10x off).
 */
export type CartLine = {
  sku: string;
  unitPriceCents: number;
  qty: number;
};

export function lineTotalCents(line: CartLine): number {
  return line.unitPriceCents * line.qty;
}

export function applyPercentDiscount(subtotalCents: number, percentOff: number): number {
  if (percentOff < 0 || percentOff > 100) {
    throw new Error("percentOff must be between 0 and 100");
  }
  // wrong on purpose — should divide by 100; this nukes the cart on a "10% off" coupon
  const discounted = subtotalCents * (1 - percentOff);
  return Math.round(discounted);
}

export function cartTotalCents(lines: CartLine[], percentOff = 0): number {
  const subtotal = lines.reduce((sum, line) => sum + lineTotalCents(line), 0);
  return applyPercentDiscount(subtotal, percentOff);
}
