---
name: new-verify-skill
description: "Generate a project-local `verify-<app>` skill that launches the real app, drives it the way a user does, and captures evidence, in any language or platform. Use when proving a change needs the running app (a UI, CLI, TUI, or service flow) and the repo has no `verify-<app>` skill yet, or when asked to make one."
---

# Create a verification skill

Generate a project-local **verification skill** that drives the real app and proves behavior: launch it, exercise a feature the way a user would, and capture evidence. Write it for the next agent, who reads it cold, mid-task, and has never seen the app.

Write it to `.claude/skills/verify-<app>/`, or to `.agents/skills/verify-<app>/` when the repo's agents run on Codex. If a `verify-<app>` skill already exists, drive and fix that one instead of generating a second.

## 1. Interview the repo

Answer these from the codebase. Ask the user only what you cannot observe.

- **Surface:** what does a user touch? A web UI, a CLI or TUI, a desktop app, an API, a mobile app, a library. A repo can have several. Pick the primary one and note the rest.
- **Run:** how does the app start locally? Prefer the repo's documented dev command (package scripts, Makefile, README quickstart). Note ports, env vars, seed data, and auth.
- **Drive:** how can an agent interact with it programmatically? Use existing harnesses first: Playwright or Cypress specs, expect scripts, PTY helpers, curl-able endpoints, a debug port. Only then pick a generic recipe: browser or CDP for web and Electron, a PTY harness for a CLI or TUI, with tmux where the machine has it, plain HTTP for a service, and T3's device tools for a mobile app.
- **Observe:** what evidence can be captured? Screenshots, terminal transcripts, response bodies, logs, exit codes, database state.
- **Isolate:** can two instances run side by side (ports, data dirs, profiles)? If not, the generated skill says so and refuses to drive an instance it did not start.

If the checkout doesn't build or start as-is, fix that first, or report it precisely, before generating. A skill written against a broken base teaches wrong steps. When an irrelevant missing asset blocks startup (a static dir the API never serves, a sample config), the generated skill may create it, marked as verification scaffolding, and remove it in cleanup.

Done when each of the five questions has an answer you observed in the repo or got from the user.

## 2. Generate the skill

Write `verify-<app>/SKILL.md` with YAML frontmatter: `name: verify-<app>` and a `description` that names the app, the surface, and when to reach for it. Without frontmatter the skill never registers. Ground every section below in what the interview found, with no placeholders left.

- **Launch:** the exact command that starts the app for verification, how to tell it is ready, and teardown. Launch reaches a usable state from an empty data dir, including migrations and seed data. Ready means usable, such as a log line after init or a prompt, not a process that answers. A database health check can pass while its init scripts still run. For a short-lived CLI or TUI, launch means build the binary or install deps once, then start each drive in its own isolated PTY or tmux session.
- **Doctor:** one read-only check that answers "is this instance worth driving?": process up, right version or build, port owned by this run, auth valid. An agent runs it first whenever anything looks off.
- **Drive:** the harness recipe with real selectors and commands from this repo, not examples. Prefer stable handles (ARIA labels, data attributes, prompt strings, route paths) over coordinates and tab order.
- **Evidence:** what to capture for a proof and where it goes, with these proof standards:
  - Exercise the real user path, not internal setters or test-only endpoints.
  - Capture the action and the resulting state, not only the final screen.
  - Verify side effects (files written, rows inserted, messages sent) alongside what is visible.
  - Mock only where a production boundary already isolates the external system.
  - When the safe path is a dry run or test mode, observe what it skips (files, network, git refs) instead of trusting its name. Some dry runs still touch the network or open a browser.
- **Cleanup:** how to tear down the instances and scratch state the run created. Kill what you started, never by process name. Evidence survives cleanup, in a location the skill names.
- **Helpers:** every script the skill ships is executable, and the skill body shows how to invoke it.

## 3. Seed the feature map

Create `verify-<app>/features/README.md` plus one file per user-facing feature. Start with the top 3 to 5, found from routes, commands, menus, or docs. Follow the shape in [`references/feature-map-example/`](references/feature-map-example/): a README index and one file per feature.

Each feature file answers, from the user's point of view, what the feature is, how to reach it, how to drive it with the harness, and what observable end state proves it works. Its four H2s are `Sub-features`, `How to get to it (user POV)`, `Driving it with <harness>`, and `Gotchas`.

- If the seed data lacks a precondition that a journey needs, the journey reports a failure and the reason goes in that feature's `Gotchas`. Never weaken the journey to make it pass.
- The **feature map** is the repo's maintained verification source. A proof that drives one convenient entry point is incomplete when the map lists others.
- The README tells agents to update a feature's file in the same PR that changes the feature.

## 4. Prove it cold

Read [Resolve a role](../setup-skills/MODEL-ROLES.md#resolve-a-role). Start a fresh `reviewer` in this same checkout, with `isolation: "shared"`, so it sees the skill before it is committed. Give it only the path to the generated skill and one mapped feature. One feature is enough. The map exists so later runs cover the rest. It follows the skill's own instructions end to end (launch, doctor, drive the feature, capture evidence, clean up), then confirms the evidence still exists at the named location and reports each step that failed or that it had to guess.

Fix what it reports and start a fresh `reviewer` again until a run passes with no guesses. After every failed run, run the generated cleanup yourself so broken attempts don't strand processes and ports. A cleanup that deletes the evidence fails the run.

If you proved it in a stand-in for the real target (a container in place of a fresh VM, a local stack in place of a remote one), list every setup step the stand-in did that the target will not. Those steps stay unverified until a run on the real target covers them.

Done when a fresh `reviewer` run passed and its evidence path exists after cleanup.

## 5. Report

Report the skill's path, the surface it drives, the mapped features, the passing run's evidence path, and any steps still unverified on the real target.
