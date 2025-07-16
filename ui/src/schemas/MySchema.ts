import { z } from "zod/v4";

export const MySchema = z.object({ hello: z.string() });
export type MySchema = z.infer<typeof MySchema>;
