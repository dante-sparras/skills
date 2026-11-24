# HTML report format

One HTML page, shown in the T3 thread with `html_render`. The diagrams carry the weight, and prose stays sparse.

The page follows `html_render`'s contract, which that tool's description states in full:

- **No page background.** Leave `html` and `body` transparent, with no outer card or banner.
- **Theme variables for every colour**, so the page reads in light and dark: `--foreground`, `--muted-foreground`, `--card`, `--border`, `--success`, `--warning`, `--destructive`, and `--chart-1` to `--chart-6`.
- **Fluid width.** The frame is about 728px on desktop and 360px on a phone.
- **Inline styles.** One `<style>` block, and Mermaid from its CDN as the only script.

## Scaffold

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Architecture review for {{repo name}}</title>
    <style>
      .r { font-family: var(--font-sans); color: var(--foreground); line-height: 1.5; }
      .r article { border: 1px solid var(--border); border-radius: var(--radius); background: var(--card); padding: 16px; margin-bottom: 24px; }
      .r .files { font-family: var(--font-mono); font-size: 13px; color: var(--muted-foreground); }
      .r .pair { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
      .r .badge { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 12px; border: 1px solid var(--border); }
      .r .strong { color: var(--success); }
      .r .explore { color: var(--warning); }
      .r .leak { stroke: var(--destructive); color: var(--destructive); }
      .r .seam { border-top: 2px dashed var(--muted-foreground); }
      .r .deep { border: 3px solid var(--foreground); border-radius: var(--radius); padding: 12px; }
      @media (max-width: 520px) { .r .pair { grid-template-columns: minmax(0, 1fr); } }
    </style>
  </head>
  <body>
    <div class="r">
      <header>...</header>
      <section id="candidates">...</section>
      <section id="top-recommendation">...</section>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
    <script>
      const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      mermaid.initialize({ startOnLoad: false, theme: dark ? "dark" : "neutral" });
      mermaid.run({ querySelector: ".mermaid" });
    </script>
  </body>
</html>
```

## Sections

- **Header**: the repo name, the date, and a compact legend: solid box is a module, dashed line is a seam, red arrow is leakage, thick box is a deep module. Then straight into the candidates.
- **Candidates**: one `<article>` each, described below.
- **Top recommendation**: one larger card with the candidate you would tackle first, one sentence on why, and an anchor link to its card.

## Candidate card

| Part | Content |
| --- | --- |
| **Title** | Short, naming the deepening: "Collapse the Order intake pipeline" |
| **Badges** | Strength: `Strong`, `Worth exploring`, or `Speculative`. Dependency category: `in-process`, `local-substitutable`, `ports & adapters`, or `mock` |
| **Files** | A monospaced list |
| **Before / After** | The centrepiece: two diagrams side by side, stacked on a phone |
| **Problem** | One sentence on what hurts |
| **Solution** | One sentence on what changes |
| **Wins** | Bullets of six words or fewer, each naming a gain in locality, leverage, or tests: "Tests hit one interface", "Pricing logic stops leaking", "Delete 4 shallow wrappers" |

If a diagram needs a paragraph to be understood, redraw the diagram.

## Diagram patterns

Pick the pattern that fits each candidate, and vary them across the report.

| Pattern | Use for | How |
| --- | --- | --- |
| **Mermaid graph** | Dependencies and call flow: "X calls Y calls Z, and look at the mess". A sequence diagram suits "before: 6 round-trips, after: 1" | A `flowchart` in a `<pre class="mermaid">`, with `classDef` marking leakage edges |
| **Hand-built boxes and arrows** | An "after" that must read as one thick-bordered deep module with faded internals, which Mermaid cannot weight | Modules as bordered `<div>`s. Arrows as inline SVG over a relative container |
| **Cross-section** | Layered shallowness | Stacked horizontal bands. Before: six thin layers. After: one thick band named for the consolidated responsibility |
| **Mass diagram** | An interface as wide as its implementation | Two rectangles per module, interface and implementation. Before: nearly equal heights. After: a short interface over a tall implementation |
| **Call-graph collapse** | A tree of calls that becomes one module | Before: nested boxes. After: one box, with the now-internal calls faded inside it |

```html
<pre class="mermaid">
  flowchart LR
    A[OrderHandler] --> B[OrderValidator]
    B --> C[OrderRepo]
    C -.leak.-> D[PricingClient]
</pre>
```

## Style

- Editorial, not corporate dashboard: generous whitespace, few colours.
- One accent from the chart variables, plus `--destructive` for leakage and `--warning` for warnings.
- Diagrams about 320px tall, so before and after sit side by side without scrolling.
- Module labels inside diagrams small, uppercase, and letter-spaced, so they read as schematic.

## Tone

Plain, concise English in the `codebase-design` vocabulary: module, interface, implementation, depth, deep, shallow, seam, adapter, leverage, locality.

- "Order intake module is shallow: interface nearly matches the implementation."
- "Pricing leaks across the seam."
- "Deepen: one interface, one place to test."
- "Two adapters justify the seam: HTTP in prod, in-memory in tests."

Name each win in those terms, such as "locality: bugs concentrate in one module", where a looser report would say "easier to maintain". If a sentence could be a bullet, make it one. If a bullet could be cut, cut it.
