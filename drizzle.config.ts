import { defineConfig } from "drizzle-kit";
import { homedir } from "node:os";
import { resolve } from "node:path";

function expandHome(path: string): string {
  if (path.startsWith("~")) return path.replace("~", homedir());
  return resolve(path);
}

export default defineConfig({
  schema: "./src/domain/schema.ts",
  out: "./drizzle",
  dialect: "sqlite",
  dbCredentials: {
    url: expandHome(process.env.HOLLYWOOD_DB_PATH ?? "~/.hominem/hollywood.db"),
  },
});
