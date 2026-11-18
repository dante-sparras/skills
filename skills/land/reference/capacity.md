# Capacity

The governor is machine-wide. It defaults to one worker slot per four cores, at least one and at most four. Set the count in `${XDG_STATE_HOME:-~/.local/state}/skills/governor/governor.json` as `{"slots": N}`. The queue's checks take their own landing slot, so workers never starve the queue. A command already inside a slot runs nested `land.py slot` commands without taking another. Dev servers take no slot.

`slot --slots N` takes N worker slots in one admission, for a command that runs several heavy processes, such as a whole test suite. A count above the governor's worker slots is refused before the command runs.

A measurement taken while other work loads the machine is wrong, not noisy. `slot --exclusive` takes the landing slot and every worker slot in a fixed order, waits for running heavy commands to finish, and holds every slot until the measurement ends. It must be the outermost slot. The hold ends after 600 seconds: land.py stops the command and its child processes and exits 124. `--for SECONDS` sets another limit, up to 7200. A limit over 600 needs `--reason TEXT`, which waiters see.

A command that waits 15 seconds for a slot prints the holders of the busy slots on stderr, or `unknown` when no record names one. Slots are file locks, so a crashed holder frees its slot at once.
