# Signal subscriptions: cross-process delivery and thread-safe wakeup

## Context

`undine/subscriptions.py` delivers signal subscription events entirely in-process:

- `SignalSubscription.__init__` connects a Django signal receiver and keeps
  `self.subscribers: dict[UUID, SignalSubscriber]` — a plain in-memory dict.
- `SignalSubscription.receiver` iterates that dict and calls
  `subscriber.events.put_nowait(data)` on an `asyncio.Queue`.

This has two defects. They are independent, and the second is the more urgent one.

### Defect 1 — events do not cross process boundaries

The subscriber registry lives in the memory of one process. In any deployment with
more than one worker (the normal case: an ASGI worker holding websockets plus one or
more workers serving mutations), a write handled by worker B fires `post_save` in
worker B, whose `subscribers` dict is empty. Subscribers attached to worker A are
never notified. The subscription silently delivers nothing — no error, no log.

This is design-level and visible by reading the code; no experiment needed.

### Defect 2 — the wakeup is not thread-safe (verified)

`asyncio.Queue` is not thread-safe. `put_nowait` wakes a waiting getter by calling
`set_result` on a future; done from a non-loop thread, that does not wake the event
loop's selector. Undine reaches this path because mutations run their ORM work under
`sync_to_async` (`undine/resolvers/mutation.py:171`, `:243`, `:411`, `:486`), which
executes in a thread executor — so `post_save` fires off the loop thread.

`SignalSubscriber.subscribe` awaits `asyncio.wait_for(self.events.get(), timeout=self.subscription.timeout)`
and `timeout` defaults to `None`. With no timeout there is no timer to wake the loop,
so the getter can block indefinitely.

**Verified by experiment on this machine.** `/tmp/probe_queue2.py`:

```python
import asyncio, threading, time


async def main():
    q: asyncio.Queue = asyncio.Queue()

    def fire_from_other_thread():
        time.sleep(0.2)
        q.put_nowait(time.monotonic())

    threading.Thread(target=fire_from_other_thread, daemon=True).start()
    sent = await q.get()
    print(f"latency: {(time.monotonic() - sent) * 1000:.1f} ms")


asyncio.run(main())
```

```
$ timeout 5 poetry run python /tmp/probe_queue2.py; echo "exit=$? (124 = hung)"
exit=124 (124 = hung)
```

The same script with `asyncio.wait_for(q.get(), timeout=2.0)` instead prints
`delivered: 'event'` — the timer wakes the loop and masks the bug. That is why a
`timeout` set in tests hides this, and why the default `timeout=None` is the
dangerous configuration.

## The work

Do step 1 first and ship it independently — it is small, it is a live bug, and it
does not depend on any of the design decisions in step 2.

### 1. Make the wakeup thread-safe

In `SignalSubscriber`, capture the running loop when `subscribe()` starts and have
`SignalSubscription.receiver` hand off via `loop.call_soon_threadsafe(queue.put_nowait, data)`
rather than calling `put_nowait` directly. The receiver runs on whatever thread Django
dispatched the signal on, so it must not touch the queue directly.

Guard the case where the loop is already closed (subscriber torn down mid-dispatch);
dropping the event is correct there.

Regression test: fire the signal from a non-loop thread with `timeout=None` on the
subscription and assert the subscriber receives it. Written against the current code
this test must hang/fail — confirm that before fixing, otherwise the test is not
covering the bug.

Also consider bounding the queue. It is currently unbounded, so a subscriber slower
than the write rate grows memory without limit. A bounded queue plus an explicit
drop-or-disconnect policy is the standard answer, but **this is a proposal, not a
decision** — it changes observable behaviour and is worth raising with the user.

### 2. Introduce a pub/sub broker behind the signal subscriptions

The goal is that `receiver` publishes to a broker instead of writing into local
subscriber queues, and each process's subscribers read from that broker.

Suggested shape (proposal — the naming and module layout are guesses, check against
how `LIFECYCLE_HOOKS` / `OPTIMIZER_CLASS` style settings are wired in `undine/settings.py`):

- A small abstract broker: `publish(topic, payload)` / `subscribe(topic) -> AsyncGenerator`.
- `InMemoryBroker` as the default, preserving today's single-process behaviour so
  nothing breaks for existing users and the test suite stays green.
- A channel-layer-backed broker. Undine already depends on a channel layer for SSE
  single-connection mode (`undine/integrations/channels.py` uses `get_channel_layer`,
  `group_send`, `group_add`), so this reuses infrastructure users of subscriptions
  already have, and `channels_redis` gives the cross-process transport for free.
- Select via a setting, following the existing `*_CLASS` setting convention.

Two design points that need real decisions, not defaults:

**Payload serialisation.** Today `transform` receives live Django model instances and
`ModelDeleteSubscription` keeps a `deepcopy` of the instance. Across a process
boundary only primitives survive. The natural move is to publish the pk (plus, for
deletes, a serialised snapshot) and re-fetch through the `QueryType` on the consumer
side — which also keeps the optimizer in play, as documented in `docs/subscriptions.md`.
Deletes are the hard case precisely because the row is gone; the current in-process
`deepcopy` trick has no cross-process equivalent, and the docs already warn that
relations are unavailable there.

**Delivery semantics.** Say explicitly whether the broker is at-most-once fan-out
(every subscriber sees every event) — which is what a GraphQL subscription wants —
and note that Redis pub/sub drops messages for disconnected consumers. Do not promise
durability the transport cannot provide.

Prior art worth reading before designing: Hot Chocolate exposes exactly this seam as
`ITopicEventSender` / `ITopicEventReceiver` with in-memory, Redis, NATS and Postgres
`LISTEN/NOTIFY` providers.

### 3. Documentation

`docs/subscriptions.md` describes signal subscriptions without stating that delivery
is process-local. Until step 2 lands, that limitation should be written down — a user
cannot discover it from behaviour, because the failure is silent.

## Done when

- A test fires a model signal from a non-loop thread against a subscription with
  `timeout=None` and the subscriber receives the event. The same test hangs or fails
  against the pre-fix code.
- With a channel-layer broker configured, an event published from one process is
  received by a subscriber in another. A test process pair, or two runserver
  instances plus a manual mutation, both count — a single-process test cannot
  demonstrate this, so say in the PR how it was checked.
- Default configuration still uses the in-memory broker and the existing subscription
  tests pass unchanged.
- `docs/subscriptions.md` states which broker is in use by default and what its
  delivery guarantees are.
