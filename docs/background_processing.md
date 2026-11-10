# Background processing and the Stop button

This document describes how long computations (Preview, Run, batch mode, fragment extraction in Module 2)
run in the background,
how they talk to the UI, what the user sees, and how to add a new long action (e.g. document
reconstruction in Module 2).

The code lives in `src/ui/main_window.py` (`run_in_background`, `check_messages`, `stop_action`),
`src/ui/module_1_sidebar.py` (`set_busy`, the Stop button) and `src/processing/mask_generator.py`
(`stop_callback`).

## Why

Before, every computation ran directly in the Tkinter thread. While a mask was generated or an image
was cut, Tkinter couldn't handle any events - the window froze, couldn't be moved, and there was
no way to interrupt the computation.

Now the computations run in a separate **worker thread**, the window stays responsive, and the user
can press **Stop**.

## Two threads

| Thread | Created by | What it does |
|---|---|---|
| **UI thread** (main thread) | the program itself, `app.mainloop()` in `src/main.py` | everything connected with the window: buttons, drawing images, the status bar, pop-ups, `ProjectSession` |
| **Worker thread** | `run_in_background`, one per Preview / Run / batch / extraction | only computations: mask, cutting, rotation, placing on the background, extracting fragments, reading and saving files |

There is at most one worker thread at a time - the buttons are locked while it runs.

> **The most important rule:** the worker thread never touches the UI (widgets, `messagebox`,
> `self.sidebar`) or `ProjectSession`. Tkinter isn't thread-safe, and changing shared state from two
> threads leads to bugs that are hard to reproduce. Everything the worker needs is read in the UI
> thread **before** it starts; everything it produces goes back to the UI thread.

## How the threads communicate

```
              ┌───────────────────┐
              │     UI THREAD     │
              └───────────────────┘
   stop_event  │              ▲   messages (queue.Queue)
   "please     │              │   ("status", text), ("image", img),
    stop"      ▼              │   ("warning", text), ("done", result),
              ┌───────────────────┐   ("stopped", None), ("error", exception)
              │   WORKER THREAD   │
              └───────────────────┘
```

**`self.messages` (`queue.Queue`) - from the worker to the UI.**
The worker puts `(kind, value)` messages into it; the UI thread reads them every
`CHECK_MESSAGES_EVERY_MS` (50 ms) in `check_messages`. The queue is thread-safe, so no locks are needed.

| Message | Sent by | The UI thread then |
|---|---|---|
| `("status", text)` | batch, before each image | shows the text in the status bar |
| `("image", img)` | batch, after each saved image | draws the image |
| `("warning", text)` | `show_warning`, when `mask_generator` calls `warning_callback` from the worker | shows a warning pop-up |
| `("done", result)` | `worker`, when `work()` returned | unlocks the UI and calls `on_done(result)` |
| `("stopped", None)` | `worker`, when `work()` raised `ProcessingStopped` | unlocks the UI and shows `stopped_message` |
| `("error", exception)` | `worker`, when `work()` raised any other exception | unlocks the UI and shows an error pop-up |

`done`, `stopped` and `error` end the work - after them `check_messages` stops checking the queue.

**`self.stop_event` (`threading.Event`) - from the UI to the worker.**
A flag set by `stop_action` when the user presses Stop. A thread can't be stopped from outside in
Python, so the worker checks the flag itself in safe places and ends early. The code that checks it
gets it as `stop_callback` (which is `self.stop_event.is_set`), so it doesn't need to know anything
about the window. `run_in_background` clears the flag at the start, so a Stop pressed earlier can't
stop a new computation.

## `run_in_background`

Every long action is split into three parts:

```python
def preview_split_action(self):
    # 1. UI thread: read everything from the UI
    image = ProjectSession.original_image.copy()
    dynamic_params = self.sidebar.get_split_parameters()
    ...

    # 2. worker thread: only computations, returns the result
    def work():
        mask = mask_generator.generate_mask(current_method, height, width, **dynamic_params)
        return mask, draw_preview_lines(image, mask)

    # 3. UI thread: show the result, update ProjectSession
    def on_done(result):
        ProjectSession.mask, preview = result
        self.render_image_on_ui(preview)

    self.run_in_background(work, on_done)
```

`run_in_background(work, on_done, stopped_message="Stopped.")`:
1. clears `stop_event` and locks the UI (`set_busy(True)`),
2. starts the worker thread, which runs `worker()`:
   - calls `work()` and puts `("done", result)` into the queue,
   - or puts `("stopped", None)` if `work()` raised `ProcessingStopped`,
   - or puts `("error", e)` if it raised anything else,
3. schedules `check_messages`, which handles the messages and, when the work ends, unlocks the UI
   (`set_busy(False)`) and calls `on_done`.

`run_in_background` returns right away - the UI thread goes back to handling the window while the
worker computes. `work` takes no arguments: it uses the variables of the action it's defined in (a closure).

The worker thread is a daemon thread, so closing the window doesn't wait for the computation to end.

## The Stop button

### What the code does

1. The user presses Stop. `stop_action` sets `stop_event` and greys out the Stop button.
   If the computation is still running `STOPPING_MESSAGE_DELAY_MS` (300 ms) later, the status bar
   shows "Stopping..." (most stops are faster, so the text doesn't just flash).
2. The worker notices the flag at the next check and ends in one of two ways:
   - **`break` with a partial result** - when the part done so far is useful
     (the mask with the lines drawn so far, the images of a batch saved so far),
   - **`raise ProcessingStopped`** (via `raise_if_stopped(stop_callback)`) - when it isn't
     (half of a cut image). Nothing reaches the screen or `ProjectSession`.

Where the flag is checked:

| Place | When |
|---|---|
| `mask_generator`: `hierarchical_random_lines_mask`, `polylines_mask`, `voronoi_mask` | at the start of every loop iteration (one attempt to draw a line) |
| `fragment_image` | after cutting and after rotation |
| Run | after generating the mask and at the end |
| batch | before each image, after its mask, in `fragment_image`, and before saving it |

The strip and rectangle methods aren't checked - they take a fraction of a second.

### What the user sees

| Action | After Stop | Status bar |
|---|---|---|
| **Preview** | the mask with the lines drawn so far (Voronoi: made from the center points chosen so far); it's saved in `ProjectSession.mask`, so Run uses it | "Stopped. The preview shows the lines drawn before stopping." |
| **Run** | the screen keeps what it showed; nothing in `ProjectSession` changes; Save goes back to its previous state | "Stopped. The previous result is kept." if a Run result was on the screen, otherwise "Stopped. Nothing was processed." |
| **Batch** | the images saved so far stay on disk; the image being processed is skipped (an image is saved whole or not at all) | "Stopped. Saved X of N images to: ..." and a "Batch Stopped" pop-up ("Batch Stopped With Errors" if some images failed before) |

If Stop is pressed but the work ends before it notices, the result is shown normally with
"Finished before it could be stopped."

While anything is computed, Run, Preview, Reset, Save, the file menu and the module switch are locked,
and Stop is active (`set_busy`). After the work ends, Save goes back to the state it had before.
The module switch is locked because switching modules destroys the sidebar the computation reports to.


## Adding a new long action (e.g. reconstruction)

### In the window

```python
def reconstruct_action(self):  # example, the names are made up
    # 1. UI thread: read everything the computation needs
    fragments = list(ProjectSession.fragments)
    algorithm = self.reconstruction_sidebar.get_algorithm()
    stop_callback = self.stop_event.is_set

    # 2. worker thread: no UI, no ProjectSession
    def work():
        return reconstruction.reconstruct(fragments, algorithm, stop_callback=stop_callback)

    # 3. UI thread
    def on_done(result):
        ProjectSession.reconstructed_document = result
        self.render_image_on_ui(result)

    self.run_in_background(work, on_done, stopped_message="Stopped.")
```

### In the algorithm

Pass `stop_callback` (and `warning_callback` if needed) as optional arguments, the same way as in
`mask_generator`, and check it in every loop that can take long:

```python
def reconstruct(fragments, algorithm, stop_callback=None):
    best = initial_solution(fragments)

    for iteration in range(MAX_ITERATIONS):
        # the user pressed Stop - return the best solution found so far
        if stop_callback is not None and stop_callback():
            break
        ...improve best...

    return best
```

- **Check the flag at least every ~0.1 s.** Checking is very cheap; in very fast loops check every
  N iterations (`if i % 1000 == 0 and stop_callback()`).
- **Partial result useful** (best solution so far, a partly assembled document) - `break` and return it.
- **Partial result useless** - `raise ProcessingStopped` (or `raise_if_stopped(stop_callback)`).
  Without `stop_callback`, the function works as before (`None` means "never stop"), so tests and other
  callers don't have to change.
- **Progress or intermediate images:** the worker may only use the queue. Pass a callback like
  `progress_callback=lambda text: self.messages.put(("status", text))` (or `("image", img)`) -
  it doesn't touch the window, the UI thread shows the message.
- **Warnings:** `warning_callback=self.show_warning` works from the worker - it notices it isn't in the
  UI thread and sends the warning through the queue.

## Limitations and decisions

- **Threads, not processes.** We decided to use threads only (`threading`, `queue`), which are simpler.
  The price: a thread can only stop where the code checks the flag.
- **A single long library call can't be interrupted.** If the worker spends minutes inside one call
  of OpenCV / NumPy / SciPy, Stop waits until the call returns. To avoid it:
  - split long computations into parts (e.g. compare fragments in a loop instead of one huge call)
    and check the flag between them,
  - use library callbacks - many iterative functions (e.g. optimizers in `scipy.optimize`) accept a
    `callback` called after each iteration; check its docs for how to end early,
  - write iterative algorithms as our own loop.
- **The GIL.** Only one Python thread runs Python code at a time, so long pure-Python loops in the
  worker take some time from the UI. In our tests the window stayed responsive (~80% of the time for
  the UI); very long, heavy Python loops may make it a bit less smooth.

## Testing

- **Functions with `stop_callback`** can be tested without the window - pass a function instead of the
  flag, e.g. `lambda: True` (stop right away) or a counter that says "stop" from its N-th call
  (`stop_after` in `tests/test_mask_generator.py`). Check that the loop ends at the first "stop", the
  partial result is valid, and `lambda: False` gives the same result as no callback.
- **The UI** can be tested by creating `MainWindow()`, calling an action (e.g. `app.run_action_splitting()`),
  then calling `app.update()` in a loop until the buttons are unlocked. Replace `messagebox` functions
  with ones that record their arguments, so the test doesn't wait for a click.
