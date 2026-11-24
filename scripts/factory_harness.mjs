// Loads skills/coordinate/factory.ts the way T3 Code does, with stand-ins for the globals it
// hands a workflow file, and prints what the file registers and what its pure helpers return.
// test_factory.py runs it. The real engine is T3 Code's: this only catches a file that cannot
// load, a renamed workflow, and helpers that parse issue bodies wrongly.
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
let text = readFileSync(source, "utf8");
for (const helper of ["blockersInBody", "issueNumber"]) {
  text = text.replace(`const ${helper} = `, `globalThis.${helper} = `);
}
const copy = join(mkdtempSync(join(tmpdir(), "factory-")), "factory.mjs");
writeFileSync(copy, text);
await import(pathToFileURL(copy).href);

const cases = JSON.parse(casesJson);
console.log(
  JSON.stringify({
    registered,
    blockers: cases.blockers.map((body) => globalThis.blockersInBody(body)),
    numbers: cases.numbers.map((displayKey) => globalThis.issueNumber({ displayKey })),
  }),
);
