# When to mock

Mock at **system boundaries** only: external APIs such as payment or email, time and randomness, and sometimes the database or file system, where a test database or a temp directory is the better choice when it is practical.

Everything you control stays real: your own modules and their internal collaborators.

## Make the boundary easy to mock

**Pass the dependency in.**

```typescript
// Easy to mock
function processPayment(order, paymentClient) {
  return paymentClient.charge(order.total);
}

// Hard to mock
function processPayment(order) {
  const client = new StripeClient(process.env.STRIPE_KEY);
  return client.charge(order.total);
}
```

**Give each external operation its own function.** Each mock then returns one shape, the test setup needs no conditional logic, and the test shows which endpoints it exercises.

```typescript
// GOOD: each function is mocked on its own
const api = {
  getUser: (id) => fetch(`/users/${id}`),
  getOrders: (userId) => fetch(`/users/${userId}/orders`),
  createOrder: (data) => fetch('/orders', { method: 'POST', body: data }),
};

// BAD: the mock needs conditional logic
const api = {
  fetch: (endpoint, options) => fetch(endpoint, options),
};
```
