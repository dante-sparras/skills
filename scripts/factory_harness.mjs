import { readFileSync, writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const [source, casesJson] = process.argv.slice(2);

const anything = () => new Proxy(function () {}, { get: (_, key) => (key === "then" ? undefined : anything()), apply: () => anything() });

const registered = [];
globalThis.T3 = new Proxy(
  { workflow: (name) => (registered.push(name), anything()), Effect: undefined },
  { get: (target, key) => (key in target ? target[key] : anything()) },
);
globalThis.Effect = new Proxy({ fn: (body) => body, gen: (body) => body }, { get: (target, key) => (key in target ? target[key] : anything()) });
for (const name of ["Schema", "Option", "Duration", "Schedule"]) globalThis[name] = anything();

const HELPERS = ["blockersInBody", "issueNumber", "parentInBody", "repeatKey", "feedbackOf", "guardrailBrief", "failingChecks", "titleKey", "searchWords", "pairOf", "mayMergeUnasked", "namedButUnlisted", "holdsSlot", "answerOf", "askBrief", "approvalOf", "readyNote", "readyBrief", "releaseBrief", "lastApproval", "runsThatSaw", "decide", "sameHead", "checksOf", "settingsOf", "newestLabelEvent", "claimIsStale", "againBrief", "commentId", "byHandNote"];
let text = readFileSync(source, "utf8");
for (const helper of HELPERS) {
  if (!text.includes(`const ${helper} = `)) throw new Error(`factory.ts has no helper named ${helper}`);
  text = text.replace(`const ${helper} = `, `globalThis.${helper} = `);
}
const copy = join(mkdtempSync(join(tmpdir(), "factory-")), "factory.mjs");
writeFileSync(copy, text);
await import(pathToFileURL(copy).href);

const cases = JSON.parse(casesJson);
console.log(JSON.stringify({ registered, results: cases.map(([helper, ...args]) => globalThis[helper](...args)) }));
