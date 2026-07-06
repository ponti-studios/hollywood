import { getDb } from "../db/index.js";
import type { DbRow } from "../db/index.js";
import * as crypto from "node:crypto";

export const userResolvers = {
  Query: {
    user: () => ({
      id: "00000000-0000-0000-0000-000000000000",
      name: "Hollywood API",
      title: "System",
      userRole: "admin",
    }),
  },

  Mutation: {
    addUser: (_parent: unknown, args: { user: Record<string, unknown> }) => {
      return {
        id: crypto.randomUUID(),
        ...args.user,
      };
    },

    updateUser: (_parent: unknown, args: { user: Record<string, unknown> }) => ({
      id: args.user["userId"],
      name: args.user["fullName"] ?? "User",
      title: args.user["title"] ?? "",
      userRole: args.user["userRole"] ?? "user",
    }),

    addUserAndProject: (_parent: unknown, args: { input: Record<string, unknown> }) => ({
      user: {
        id: crypto.randomUUID(),
        name: (args.input["user"] as Record<string, unknown>)?.["name"] ?? "User",
        title: "",
        userRole: "user",
      },
      project: {
        id: crypto.randomUUID(),
        title: (args.input["project"] as Record<string, unknown>)?.["title"] ?? "Project",
        season: 1,
        genres: [],
        format: null,
        imdbLink: null,
        posterLink: null,
      },
    }),
  },
};
