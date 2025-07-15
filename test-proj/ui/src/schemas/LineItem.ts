import { z } from "zod/v4";

export const LineItem = z.object({
  description: z.string(),
  quantity: z
    .union([z.number(), z.null()])
    .describe("The quantity of the line item")
    .default(null),
  unit_price: z
    .union([z.number(), z.null()])
    .describe("The unit price of the line item")
    .default(null),
  date: z
    .union([z.string(), z.null()])
    .describe("The date of the line item")
    .default(null),
  total_price: z
    .union([z.number(), z.null()])
    .describe("The total price of the line item")
    .default(null),
});
export type LineItem = z.infer<typeof LineItem>;
