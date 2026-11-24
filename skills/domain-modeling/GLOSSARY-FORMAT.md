# Glossary format

## `GLOSSARY.md`

```md
# {Context Name}

{One or two sentences on what this context is and why it exists.}

## Language

**Order**:
{One or two sentences on what the term is}
_Avoid_: Purchase, transaction

**Invoice**:
A request for payment sent to a customer after delivery.
_Avoid_: Bill, payment request

**Customer**:
A person or organization that places orders.
_Avoid_: Client, buyer, account
```

- **Be opinionated.** When several words exist for one concept, pick the best and list the others under `_Avoid_`.
- **Keep definitions tight.** One or two sentences that say what the term is, not what it does.
- **Include only terms specific to this context.** A general programming concept, such as a timeout or an error type, stays out even when the project uses it heavily.
- **Group terms under subheadings** when clusters emerge. One cohesive area can stay a flat list.

## `GLOSSARY-MAP.md`

For a repo with several contexts. It lists the contexts, where each lives, and how they relate:

```md
# Glossary Map

## Contexts

- [Ordering](./src/ordering/GLOSSARY.md): receives and tracks customer orders
- [Billing](./src/billing/GLOSSARY.md): generates invoices and processes payments
- [Fulfillment](./src/fulfillment/GLOSSARY.md): manages warehouse picking and shipping

## Relationships

- **Ordering → Fulfillment**: Ordering emits `OrderPlaced` events; Fulfillment consumes them to start picking
- **Fulfillment → Billing**: Fulfillment emits `ShipmentDispatched` events; Billing consumes them to generate invoices
- **Ordering ↔ Billing**: Shared types for `CustomerId` and `Money`
```
