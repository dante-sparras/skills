---
name: codebase-design
description: "Shared vocabulary for designing deep modules: module, interface, depth, seam, adapter. Use when designing or reshaping a module's interface, deciding where a seam goes, weighing a refactor that deepens a module, making code more testable or easier for agents to navigate, or when another skill needs the deep-module vocabulary."
---

# Codebase design

Design **deep modules**: a lot of behaviour behind a small interface, placed at a clean seam, testable through that interface. Callers get leverage, maintainers get locality, and tests get one surface.

## Vocabulary

Use these terms exactly. Consistent language is the point.

| Term | Meaning | Avoid |
| --- | --- | --- |
| **Module** | Anything with an interface and an implementation, at any scale: a function, class, package, or slice across tiers | Unit, component, service |
| **Interface** | Everything a caller must know to use the module correctly: the types, and also invariants, ordering, error modes, required configuration, and performance | API, signature, a language's `interface` keyword. All are too narrow |
| **Implementation** | The code inside a module | |
| **Depth** | Leverage at the interface: how much behaviour a caller or test exercises per unit of interface it must learn. **Deep** is much behaviour behind a small interface. **Shallow** is an interface nearly as complex as the implementation | Depth as a ratio of lines, which rewards padding |
| **Seam** | A place where behaviour can be altered without editing in that place (Michael Feathers). It is where a module's interface lives, and placing it is its own design decision | Boundary, which DDD's bounded context overloads |
| **Adapter** | A concrete thing that satisfies an interface at a seam. It names a role, not a size: a Postgres repo and an in-memory fake are both adapters | |
| **Leverage** | What callers get from depth: one implementation pays back across every call site and test | |
| **Locality** | What maintainers get from depth: change, bugs, and knowledge concentrate in one place | |

## Principles

- **Depth belongs to the interface.** A deep module can be built from small, swappable parts inside. Those sit behind **internal seams**, private to the implementation and its own tests, and stay out of the interface.
- **The deletion test.** Imagine deleting the module. If complexity vanishes, it was a pass-through. If complexity reappears across its callers, it earns its keep.
- **The interface is the test surface.** Callers and tests cross the same seam. Wanting to test past the interface means the module has the wrong shape.
- **Two adapters make a seam real.** With one adapter, the seam is hypothetical and only adds indirection. Add a seam when something varies across it, typically production and test.
- **Accept dependencies, return results.** A module that is handed its dependencies and returns values is tested through its interface. One that creates them or mutates its inputs is not.

When shaping an interface, ask: can it have fewer methods, simpler parameters, more complexity hidden inside?

## Going deeper

- **Deepening a cluster of shallow modules**: [DEEPENING.md](DEEPENING.md) covers how each kind of dependency is tested across the seam.
- **Exploring alternative interfaces**: [DESIGN-IT-TWICE.md](DESIGN-IT-TWICE.md) runs parallel agents on different designs, then compares them.
