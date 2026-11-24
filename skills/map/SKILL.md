---
name: map
description: "Chart work too big for one agent session as a map of decision tickets on the issue tracker. Use when a person brings a loose idea whose route is still unclear, or hands over an existing map to work through its next decision."
disable-model-invocation: true
---

# Map

A loose idea has arrived, too big for one session and wrapped in fog: the way to the **destination** is not visible yet. Chart the way as a **map** on the issue tracker, then work its **decision tickets** one per session until the route is clear.

Read `docs/agents/issue-tracker.md`, and its "Map operations" section for how this repo expresses the map, child tickets, blocking, and frontier queries. If the file is missing, stop and say that `/setup-skills` has not run in this repo.

## Rules

- **Plan, don't do.** A ticket resolves a decision, and the map is done when nothing is left to decide before someone does the work. The pull to just do the work is the signal that you reached the edge of the map: hand off. A map that leads to a spec hands off to `to-spec-and-tickets`. An effort overrides this only in its **Notes**.
- **One ticket per session.** Research tickets are the exception.
- **Refer by name.** In everything the user reads, call a map or ticket by its title, with its link wrapped inside the name. A row of bare ids is illegible.
- **Expect other sessions.** The user may run unblocked tickets in parallel. Fetch the map's body again right before you write to it, and change only the lines you add or graduate.

## The map

The map is one issue labelled `map`, and its tickets are its child issues. It is an **index**: a decision lives in its ticket, and the map gists it in one line and links to it. Open tickets are found by query, so the map leaves them out.

```markdown
## Destination

<what reaching the end looks like: the spec, decision, or change this effort is finding its way to, in one or two lines>

## Notes

<domain, skills every session should consult, standing preferences for this effort>

## Decisions so far

- [<closed ticket title>](link): <one-line gist of the answer>

## Not yet specified

<in-scope fog you cannot ticket yet>

## Out of scope

<work ruled beyond the destination>
```

## Tickets

A ticket is a child issue of the map. Its body is the question, sized to one session:

```markdown
## Question

<the decision or investigation this ticket resolves>
```

- **Label.** One `map:<type>` label from the table below. A map carries the `map` label and its tickets a `map:<type>` label, with no triage label, since they are decisions and not work to grab.
- **Claim.** A session claims a ticket by assigning it to the user, before any work. An open, unassigned ticket is unclaimed. Unassign a ticket you give up on.
- **Blocking.** Use the tracker's native dependency relationship, which shows the user what is takeable without opening the map. Fall back to a body convention only where the tracker has none.
- **Frontier.** The open, unblocked, unclaimed tickets. A ticket is unblocked when every ticket blocking it is closed.
- **Answer.** Recorded when the ticket resolves, as a comment. Assets made along the way are linked from the issue.

| Type | Driven by | Use when | Resolve by |
| --- | --- | --- | --- |
| `research` | Agent | A decision waits on a fact from outside the working directory: docs, a third-party API, a knowledge base | Starting a fresh `explorer` per [Resolve a role](../setup-skills/model-roles.md#resolve-a-role), as the `research` skill says. When it returns, record the ticket like any other |
| `prototype` | Human and agent | The question is how it should look or behave | Making a cheap, rough thing to react to: an outline, a stub, UI or logic code. Keep it throwaway, on a branch outside main, linked from the ticket |
| `interview` | Human and agent | The default: the decision needs a conversation | Calling the Skill tool with "interview" |
| `task` | Either | Manual work blocks a decision: signing up for a service to judge its API, provisioning access, moving data to see its shape | Doing it alone where you can, and handing the user a precise checklist where you cannot. The answer records what was done and the facts later tickets depend on |

A ticket driven with the user resolves only through the live exchange. Their side of it is theirs to answer.

## Fog of war

The map is deliberately incomplete. **Not yet specified** holds the fog: decisions you can tell are coming but cannot state yet, because they hang on questions still open. Everything in it is in scope.

- **Ticket** a question you can state precisely now, even when it is blocked.
- **Leave in the fog** what you cannot phrase that sharply. Write it as loosely as the view allows and leave it unsliced: one patch may become several tickets, or none.

Resolving a ticket clears the fog ahead of it. Graduate what became specifiable into tickets, and remove it from the section.

## Out of scope

The destination fixes the scope. Work beyond it goes under **Out of scope** as one line: the gist, why it is out, and a link to its closed ticket if it had one. When an open ticket turns out to sit past the destination, close it and add that line.

Out-of-scope work never graduates. It returns only as a new effort, when the destination is redrawn. Keep it out of **Decisions so far**, which records the route walked.

## Chart the map

The user brought a loose idea.

1. **Name the destination.** Call the Skill tool with "interview" to pin down what this map leads to: a spec to hand off, a decision to lock, or a change made in place. The destination shapes every ticket, so settle it first.
2. **Map the frontier.** Interview again, breadth-first: fan out across the whole space, surfacing the open decisions and the steps takeable now. If this finds no fog, the work needs no map. Stop and ask the user how to proceed.
3. **Create the map** with Destination and Notes filled in, Decisions so far empty, and the fog sketched under Not yet specified.
4. **Create the tickets** you can specify now as child issues. Wire blockers and cross-references in a second pass, with real ids, since a placeholder `#<n>` links to an unrelated issue.
5. **Start the research.** Claim each `research` ticket, then start a fresh `explorer` for it, in parallel. Each saves its findings on a pushed `chore/research-<name>` branch with no PR, linked from its ticket.
6. **Record the research** as each agent returns: post its findings' link as the ticket's answer, close the ticket, and add its line to Decisions so far.
7. **Stop.** Charting is one session's work, and it resolves nothing else.

## Work through the map

The user brought a map, and maybe a ticket.

1. **Load the map**, not every ticket body.
2. **Choose** the ticket the user named, or the first one on the frontier. Claim it.
3. **Resolve** it as its `map:<type>` label says. Fetch the body of any related or closed ticket when you need it, and call the Skill tool for each skill the map's Notes name. When in doubt, call the Skill tool with "interview".
4. **Record.** Post the answer as a comment, close the issue, and add its line to Decisions so far.
5. **Update the map.** Add the tickets the answer surfaced, graduate the fog it made specifiable, rule out of scope any ticket it showed to sit past the destination, and update or delete the tickets it invalidated.
