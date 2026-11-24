// Loads skills/factory/factory.ts the way T3 Code does, with stand-ins for the globals it
// hands a workflow file, and prints what the file registers and what its pure helpers return.
// test_factory.py runs it. The real engine is T3 Code's: this only catches a file that cannot
// load, a renamed workflow, and pure helpers that return the wrong thing.
import { readFileSync, writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const [source, casesJson] = process.argv.slice(2);

// Any property, any call, any chain: enough for schemas and Effect combinators built at load.
const anything = () => new Proxy(function () {}, { get: (_, key) => (key === "then" ? undefined : anything()), apply: () => anything() });

const registered = [];
globalThis.T3 = new Proxy(
  { workflow: (name) => (registered.push(name), anything()), Effect: undefined },
  { get: (target, key) => (key in target ? target[key] : anything()) },
);
globalThis.Effect = new Proxy({ fn: (body) => body, gen: (body) => body }, { get: (target, key) => (key in target ? target[key] : anything()) });
for (const name of ["Schema", "Option", "Duration", "Schedule"]) globalThis[name] = anything();

// Expose the helpers under test without changing the file: rename their `const` to a global.
const HELPERS = ["blockersInBody", "issueNumber", "parentInBody", "repeatKey", "feedbackOf", "guardrailBrief", "failingChecks", "titleKey", "searchWords", "pairOf", "mayMergeUnasked", "namedButUnlisted", "holdsSlot", "answerOf", "askBrief", "approvalOf", "reviewWait", "readyNote", "readyBrief", "releaseBrief", "lastApproval", "mergeSettings", "runsThatSaw", "stoppedNote"];
let text = readFileSync(source, "utf8");
for (const helper of HELPERS) {
  if (!text.includes(`const ${helper} = `)) throw new Error(`factory.ts has no helper named ${helper}`);
  text = text.replace(`const ${helper} = `, `globalThis.${helper} = `);
}
const copy = join(mkdtempSync(join(tmpdir(), "factory-")), "factory.mjs");
writeFileSync(copy, text);
await import(pathToFileURL(copy).href);

// Each case is [helper, ...arguments]. The output holds each helper's return value, in order.
const cases = JSON.parse(casesJson);
console.log(JSON.stringify({ registered, results: cases.map(([helper, ...args]) => globalThis[helper](...args)) }));
