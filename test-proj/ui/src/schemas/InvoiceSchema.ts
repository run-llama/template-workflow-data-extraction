import { z } from "zod/v4";

export const InvoiceSchema = z.object({
  invoice_date: z
    .union([z.string(), z.null()])
    .describe("The date of the invoice")
    .default(null),
  total_with_tax: z
    .union([z.number(), z.null()])
    .describe(
      "The total amount including tax. Sometimes this is referred to as Invoice total after WHT, beware.",
    )
    .default(null),
  total_without_tax: z
    .union([z.number(), z.null()])
    .describe("The total amount excluding tax")
    .default(null),
  currency: z
    .union([z.string(), z.null()])
    .describe(
      "The currency code (e.g., USD, EUR, GBP). Use the ISO 4217 currency code.",
    )
    .default(null),
  invoice_id: z
    .union([z.string(), z.null()])
    .describe("The invoice ID or number provided by the vendor")
    .default(null),
  vendor_name: z
    .union([z.string(), z.null()])
    .describe("The name of the vendor or supplier")
    .default(null),
  line_items: z
    .array(
      z.object({
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
      }),
    )
    .describe("The line items of the invoice")
    .optional(),
});
export type InvoiceSchema = z.infer<typeof InvoiceSchema>;
