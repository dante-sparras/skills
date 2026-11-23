# HTML report format

One static HTML file. Tailwind and Mermaid come from CDNs, and those are its only scripts. The diagrams carry the weight, and prose stays sparse.

## Scaffold

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Architecture review for {{repo name}}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script type="module">
      import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
      mermaid.initialize({ startOnLoad: true, theme: "neutral", securityLevel: "loose" });
    </script>
    <style>
      /* small custom layer for things Tailwind doesn't cover cleanly:
         dashed seam lines, hand-drawn-feeling arrow heads, etc. */
      .seam { stroke-dasharray: 4 4; }
      .leak { stroke: #dc2626; }
      .deep { background: linear-gradient(135deg, #0f172a, #1e293b); }
    </style>
  </head>
  <body class="bg-stone-50 text-slate-900 font-sans">
    <main class="max-w-5xl mx-auto px-6 py-12 space-y-12">
      <header>...</header>
      <section id="candidates" class="space-y-10">...</section>
      <section id="top-recommendation">...</section>
    </main>
  </body>
</html>
```

## Sections

- **Header**: the repo name, the date, and a compact legend: solid box is a module, dashed line is a seam, red arrow is leakage, thick dark box is a deep module. Then straight into the candidates.
- **Candidates**: one `<article>` each, described below.
- **Top recommendation**: one larger card with the candidate you would tackle first, one sentence on why, and an anchor link to its card.

## Candidate card

| Part | Content |
| --- | --- |
| **Title** | Short, naming the deepening: "Collapse the Order intake pipeline" |
| **Badges** | Strength: `Strong` in emerald, `Worth exploring` in amber, `Speculative` in slate. Dependency category: `in-process`, `local-substitutable`, `ports & adapters`, or `mock` |
| **Files** | A monospaced list, `font-mono text-sm` |
| **Before / After** | The centrepiece: two diagrams side by side |
| **Problem** | One sentence on what hurts |
| **Solution** | One sentence on what changes |
| **Wins** | Bullets of six words or fewer, each naming a gain in locality, leverage, or tests: "Tests hit one interface", "Pricing logic stops leaking", "Delete 4 shallow wrappers" |

If a diagram needs a paragraph to be understood, redraw the diagram.

## Diagram patterns

Pick the pattern that fits each candidate, and vary them across the report.

| Pattern | Use for | How |
| --- | --- | --- |
| **Mermaid graph** | Dependencies and call flow: "X calls Y calls Z, and look at the mess". A sequence diagram suits "before: 6 round-trips, after: 1" | A `flowchart` inside a Tailwind card, with `classDef` colouring leakage edges red and the deep module dark |
| **Hand-built boxes and arrows** | An "after" that must read as one thick-bordered deep module with greyed-out internals, which Mermaid cannot weight | Modules as bordered `<div>`s. Arrows as inline SVG positioned over a relative container |
| **Cross-section** | Layered shallowness | Stacked horizontal bands (`h-12 border-l-4`). Before: six thin layers. After: one thick band named for the consolidated responsibility |
| **Mass diagram** | An interface as wide as its implementation | Two rectangles per module, interface and implementation. Before: nearly equal heights. After: a short interface over a tall implementation |
| **Call-graph collapse** | A tree of calls that becomes one module | Before: nested boxes. After: one box, with the now-internal calls faded inside it |

```html
<div class="rounded-lg border border-slate-200 bg-white p-4">
  <pre class="mermaid">
    flowchart LR
      A[OrderHandler] --> B[OrderValidator]
      B --> C[OrderRepo]
      C -.leak.-> D[PricingClient]
      classDef leak stroke:#dc2626,stroke-width:2px;
      class C,D leak
  </pre>
</div>
```

## Style

- Editorial, not corporate dashboard: generous whitespace, and `font-serif` headings work well with stone and slate.
- One accent colour, emerald or indigo, plus red for leakage and amber for warnings.
- Diagrams about 320px tall, so before and after sit side by side without scrolling.
- Module labels inside diagrams in `text-xs uppercase tracking-wider`, so they read as schematic.

## Tone

Plain, concise English in the `codebase-design` vocabulary: module, interface, implementation, depth, deep, shallow, seam, adapter, leverage, locality.

- "Order intake module is shallow: interface nearly matches the implementation."
- "Pricing leaks across the seam."
- "Deepen: one interface, one place to test."
- "Two adapters justify the seam: HTTP in prod, in-memory in tests."

Name each win in those terms, such as "locality: bugs concentrate in one module", where a looser report would say "easier to maintain". If a sentence could be a bullet, make it one. If a bullet could be cut, cut it.
