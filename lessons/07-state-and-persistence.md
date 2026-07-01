# 7. State scoping and persistence

## Concept

Every `output_key` you've used so far (lessons 5/5b) wrote a **plain,
unprefixed** key — that only lives for one `session_id`. State scoping is
about controlling *where* a key lives instead: for one session, for one user
across *all* their sessions, or for the whole app across *all* users. None of
that matters unless the session itself survives — which needs a persistent
`SessionService`, not `InMemorySessionService`.

## Analogy

Unprefixed state is a sticky note on today's meeting agenda — gone once the
meeting ends. `user:`-prefixed state is a sticky note on your own desk — it's
there tomorrow, no matter which meeting you're in. `app:`-prefixed state is a
sticky note on the office whiteboard everyone shares. `temp:` is a sticky
note you throw away before you even leave the room — never persisted at all.

## How it works

1. `State` (`google.adk.sessions.state.State`) defines three prefixes:
   `APP_PREFIX = "app:"`, `USER_PREFIX = "user:"`, `TEMP_PREFIX = "temp:"`.
   A plain key with no prefix is implicitly session-scoped.
2. Confirmed the actual mechanism by reading
   `SqliteSessionService._merge_state`: on session load, `app_state` (one row
   per `app_name`) and `user_state` (one row per `app_name`+`user_id`) get
   merged into the session's state dict *ahead of* `session_state` (one row
   per `session_id`). A `user:`-prefixed key set in session A is therefore
   visible when you start a brand-new session B, as long as it's the same
   `user_id`. A plain key is not — it dies with the session.
3. **We'd been using a persistent `SessionService` this whole time without
   realizing it.** `adk run`'s default local storage
   (`--use_local_storage`, on by default) IS `SqliteSessionService` at
   `.adk/session.db` — every one of those gitignored `.adk/` folders across
   this repo has been real persistence the whole time, we just never wrote a
   key that outlives one session before now.
4. `adk run` also always uses the same fixed `user_id = 'test_user'` across
   *separate* invocations (`google.adk.cli.cli`) — which is exactly what
   makes today's demo work with plain `adk run` calls, no custom
   `Runner`/`SessionService` wiring needed, unlike every other lesson so far.
5. `{user:name?}` in an instruction — the `?` suffix matters. Without it, a
   missing key raises `KeyError` instead of substituting empty string (read
   straight from `inject_session_state`, same function from lesson 5).

## Look at

`persistent_agent/agent.py` — `remember_name` is a plain function tool that
does `tool_context.state["user:name"] = name` (the same `Context.state`
object from lesson 5c's `ToolContext`, just writing a prefixed key this
time). The instruction reads it back with `{user:name?}`.

## Run this

Two **separate process invocations** — this is the whole point, not two
turns in one session:

```bash
make persist-ask Q="hi, my name is <your name>"
# ... process exits completely ...
make persist-ask Q="what's my name?"
```

It should remember. Then don't just trust the model's answer — check the raw
database:

```bash
uv run python -c "
import sqlite3
conn = sqlite3.connect('persistent_agent/.adk/session.db')
cur = conn.cursor()
cur.execute('SELECT app_name, user_id, state FROM user_states')
print('user_states:', cur.fetchall())
cur.execute('SELECT id, state FROM sessions')
print('sessions:', cur.fetchall())
"
```
You should see **one** `user_states` row with your name, and **two**
`sessions` rows (one per `adk run` call) each with `state = '{}'` — proof the
name lives only in the user-scoped bucket, not in either session's own state.
That's the whole mechanism, not an inference from behavior.

## You'll know it clicked when

You can explain why deleting `persistent_agent/.adk/session.db` and running
`make persist-ask Q="what's my name?"` again would make the agent forget —
and, separately, why the *same* delete wouldn't have mattered at all for any
earlier lesson's agent (`writer_pipeline`, `refine_loop`, etc.).
