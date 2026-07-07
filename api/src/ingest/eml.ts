import { simpleParser } from "mailparser";
import { stripHtmlFragment } from "./extractors.js";
import { normalizeWhitespace } from "./models.js";

const FORWARD_MARKER_RE = /^-+\s*Forwarded message\s*-+$|^Begin forwarded message:$/i;
const FORWARD_HEADER_LINE_RE = /^(From|Date|To|Cc|Subject|Resent-From|Resent-To|Sent):/i;
const SIGNATURE_BOILERPLATE_RE = /^Sent from my (iPhone|iPad|Android)/i;
const GET_OUTLOOK_RE = /^Get Outlook for /i;

export function cleanEmailBody(text: string): string {
  const lines = text.split("\n");
  const kept: string[] = [];
  let inForwardHeaderBlock = false;

  for (const rawLine of lines) {
    // Strip leading quote markers (handles nested "> >" quoting).
    const line = rawLine.replace(/^(\s*>)+\s?/, "").trimEnd();

    if (FORWARD_MARKER_RE.test(line.trim())) {
      inForwardHeaderBlock = true;
      continue;
    }
    if (inForwardHeaderBlock) {
      if (FORWARD_HEADER_LINE_RE.test(line.trim()) || line.trim() === "") continue;
      inForwardHeaderBlock = false;
    }
    if (SIGNATURE_BOILERPLATE_RE.test(line.trim()) || GET_OUTLOOK_RE.test(line.trim())) continue;

    kept.push(line);
  }

  const collapsed = kept.join("\n").replace(/\n{3,}/g, "\n\n");
  return normalizeWhitespace(collapsed) === "" ? "" : collapsed.trim();
}

export async function parseEml(buffer: Buffer): Promise<string> {
  const parsed = await simpleParser(buffer);
  const raw = parsed.text ?? (parsed.html ? stripHtmlFragment(parsed.html) : "");
  return cleanEmailBody(raw);
}
