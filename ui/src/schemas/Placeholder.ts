import { z } from "zod/v4";

export const Placeholder = z.object({
  name: z.string(),
  age: z.number(),
});

export type Placeholder = z.infer<typeof Placeholder>;