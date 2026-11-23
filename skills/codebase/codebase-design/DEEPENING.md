# Deepening

How to deepen a cluster of shallow modules, given its dependencies. Uses the vocabulary in [SKILL.md](SKILL.md).

## Classify the dependencies

The category decides how the deepened module is tested across its seam.

| Category | What it is | How to deepen and test |
| --- | --- | --- |
| **In-process** | Pure computation and in-memory state, with no I/O | Merge the modules and test through the new interface. No adapter |
| **Local-substitutable** | A dependency with a local stand-in, such as PGLite for Postgres or an in-memory filesystem | Test with the stand-in running in the suite. The seam stays internal, with no port in the module's interface |
| **Remote but owned** | Your own services across a network: microservices, internal APIs | Define a **port** at the seam. The deep module owns the logic, and the transport is an injected adapter: HTTP, gRPC, or a queue in production, in-memory in tests |
| **True external** | A third-party service you do not control, such as Stripe or Twilio | Inject it as a port. Tests provide a mock adapter |

Add a port only when two adapters are justified, and keep internal seams out of the interface even when tests use them.

## Replace the tests

- Write new tests at the deepened module's interface, asserting on outcomes a caller observes.
- Delete the old unit tests on the shallow modules. They are waste once the interface is tested.
- A test that must change when only the implementation changes is testing past the interface.
