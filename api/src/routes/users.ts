import { createRoute, z } from "@hono/zod-openapi";
import { OpenAPIHono } from "@hono/zod-openapi";
import * as crypto from "node:crypto";

// ── Schemas ─────────────────────────────────────────────────────────────────

const UserSchema = z.object({
  id: z.string().uuid(),
  name: z.string().openapi({ example: "Hollywood API" }),
  title: z.string().openapi({ example: "System" }),
  userRole: z.string().openapi({ example: "admin" }),
});

const ProjectSchema = z.object({
  id: z.string().uuid(),
  title: z.string(),
  season: z.number().int(),
  genres: z.array(z.string()),
  format: z.string().nullable(),
  imdbLink: z.string().nullable(),
  posterLink: z.string().nullable(),
});

const UserAndProjectSchema = z.object({
  user: UserSchema,
  project: ProjectSchema,
});

const CreateUserSchema = z.object({
  clerkUserId: z.string().optional(),
  emailAddress: z.string().optional(),
  name: z.string().min(1),
  title: z.string().optional(),
  role: z.string().optional(),
});

const UpdateUserSchema = z.object({
  fullName: z.string().optional(),
  title: z.string().optional(),
  userRole: z.string().optional(),
});

const CreateProjectSchema = z.object({
  title: z.string().min(1),
  format: z.string().optional(),
  genres: z.array(z.string()).optional(),
  season: z.number().int().optional(),
  imdbLink: z.string().optional(),
});

const CreateUserAndProjectSchema = z.object({
  user: CreateUserSchema,
  project: CreateProjectSchema,
});

// ── Routes ──────────────────────────────────────────────────────────────────

const meRoute = createRoute({
  method: "get",
  path: "/users/me",
  responses: {
    200: { content: { "application/json": { schema: UserSchema } }, description: "Current user" },
  },
});

const createRoute_ = createRoute({
  method: "post",
  path: "/users",
  tags: ["mutating"],
  request: { body: { content: { "application/json": { schema: CreateUserSchema } } } },
  responses: {
    201: { content: { "application/json": { schema: UserSchema } }, description: "Created user" },
  },
});

const updateRoute = createRoute({
  method: "patch",
  path: "/users/{id}",
  tags: ["mutating"],
  request: {
    params: z.object({ id: z.string().uuid() }),
    body: { content: { "application/json": { schema: UpdateUserSchema } } },
  },
  responses: {
    200: { content: { "application/json": { schema: UserSchema } }, description: "Updated user" },
  },
});

const createUserAndProjectRoute = createRoute({
  method: "post",
  path: "/users/with-project",
  tags: ["mutating"],
  request: { body: { content: { "application/json": { schema: CreateUserAndProjectSchema } } } },
  responses: {
    201: { content: { "application/json": { schema: UserAndProjectSchema } }, description: "Created user and project" },
  },
});

// ── Router ──────────────────────────────────────────────────────────────────

const router = new OpenAPIHono();

router.openapi(meRoute, (c) => {
  return c.json({
    id: "00000000-0000-0000-0000-000000000000",
    name: "Hollywood API",
    title: "System",
    userRole: "admin",
  }, 200);
});

router.openapi(createRoute_, (c) => {
  const input = c.req.valid("json");
  return c.json({
    id: crypto.randomUUID(),
    name: input.name,
    title: input.title ?? "",
    userRole: input.role ?? "user",
  }, 201);
});

router.openapi(updateRoute, (c) => {
  const { id } = c.req.valid("param");
  const input = c.req.valid("json");
  return c.json({
    id,
    name: input.fullName ?? "User",
    title: input.title ?? "",
    userRole: input.userRole ?? "user",
  }, 200);
});

router.openapi(createUserAndProjectRoute, (c) => {
  const input = c.req.valid("json");
  return c.json({
    user: {
      id: crypto.randomUUID(),
      name: input.user.name,
      title: "",
      userRole: "user",
    },
    project: {
      id: crypto.randomUUID(),
      title: input.project.title,
      season: input.project.season ?? 1,
      genres: input.project.genres ?? [],
      format: input.project.format ?? null,
      imdbLink: input.project.imdbLink ?? null,
      posterLink: null,
    },
  }, 201);
});

export default router;
