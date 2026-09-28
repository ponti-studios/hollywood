import { describe, expect, it } from "vitest";
import { parseDirectorResponse, routeQuery } from "./director.js";

describe("parseDirectorResponse", () => {
  it("routes to a matching sub-agent", () => {
    expect(parseDirectorResponse("touring")).toEqual({ kind: "agent", agentId: "touring" });
  });

  it("is case-insensitive and tolerates surrounding words", () => {
    expect(parseDirectorResponse("The answer is Financial, definitely.")).toEqual({
      kind: "agent",
      agentId: "financial",
    });
  });

  it("falls back to none when the model says none", () => {
    expect(parseDirectorResponse("none of these fit")).toEqual({ kind: "none" });
  });

  it("is unresolved when neither an agent nor 'none' appears", () => {
    const decision = parseDirectorResponse("I have no idea what you mean");
    expect(decision.kind).toBe("unresolved");
  });
});

describe("routeQuery", () => {
  it("calls the chat function with a director system prompt and parses the result", async () => {
    const calls: unknown[] = [];
    const chat = async (messages: { role: string; content: string }[]) => {
      calls.push(messages);
      return "calendar";
    };

    const decision = await routeQuery("Schedule a meeting for Friday", chat);

    expect(decision).toEqual({ kind: "agent", agentId: "calendar" });
    expect(calls).toHaveLength(1);
    const [messages] = calls as [{ role: string; content: string }[]];
    expect(messages[0]!.role).toBe("system");
    expect(messages[1]).toEqual({ role: "user", content: "Schedule a meeting for Friday" });
  });
});
