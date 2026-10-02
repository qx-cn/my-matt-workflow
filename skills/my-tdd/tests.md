# Good and Bad Tests

## Good Tests

**Integration-style**: Test through a stable behavior seam, not private implementation details.

```typescript
// GOOD: Tests observable behavior
test("user can checkout with valid cart", async () => {
  const cart = createCart();
  cart.add(product);
  const result = await checkout(cart, paymentMethod);
  expect(result.status).toBe("confirmed");
});
```

Characteristics:

- Tests behavior users/callers care about
- Uses a public interface or the module boundary under test
- Survives internal refactors
- Describes WHAT, not HOW
- One coherent behavior scenario may have multiple separately identifiable assertions

## Bad Tests

**Implementation-detail tests**: Coupled to internal structure.

```typescript
// BAD: Tests implementation details
test("checkout calls paymentService.process", async () => {
  const mockPayment = jest.mock(paymentService);
  await checkout(cart, payment);
  expect(mockPayment.process).toHaveBeenCalledWith(cart.total);
});
```

Red flags:

- Mocking internal collaborators
- Testing private methods
- Asserting on call counts/order
- Test breaks when refactoring without behavior change
- Test name describes HOW not WHAT
- Asserting private representation when it is not part of the behavior contract

```typescript
// GOOD: Public behavior and an independent persistence oracle
// when durable storage / redaction is an explicit contract.
test("user survives reopen without storing the secret", async () => {
  const user = await createUser({ name: "Alice", secret: "sensitive" });
  await closeStore();
  await reopenStore();
  expect((await getUser(user.id)).name).toBe("Alice"); // recovery acceptance
  const row = await independentConnection.query("SELECT * FROM users WHERE id = ?", [user.id]);
  expect(row.secret).not.toBe("sensitive"); // storage/redaction acceptance
});
```

The assertions map to different acceptance criteria. A public read that shares
the write bug is not sufficient by itself; private layout unrelated to the
contract should remain free to change. Use the actual router/adapter entry when
wiring is part of the change, so unit tests cannot hide a missing connection.

**Tautological tests**: Expected value restates the implementation, so the test passes by construction.

```typescript
// BAD: Expected value is recomputed the way the code computes it
test("calculateTotal sums line items", () => {
  const items = [{ price: 10 }, { price: 5 }];
  const expected = items.reduce((sum, i) => sum + i.price, 0);
  expect(calculateTotal(items)).toBe(expected);
});

// GOOD: Expected value is an independent, known literal
test("calculateTotal sums line items", () => {
  expect(calculateTotal([{ price: 10 }, { price: 5 }])).toBe(15);
});
```
