# the two logs

Each row the hooks wrote, in seconds from its log's first row.

## baseline (a550130)

```
    0.0  start via=prompt
    5.3  end finished
   23.9  start via=again
   26.1  end finished
   51.2  start via=again
   55.4  end finished
   73.1  start via=again
   76.3  end finished
  131.3  end session closed
```

## treatment (5c4a1a5)

```
    0.0  start via=prompt
    3.5  work turn=True tasks=bk7tcpz32:shell
    4.8  work turn=False tasks=bk7tcpz32:shell
   23.6  start via=again
   25.9  end finished
   51.5  start via=again
   54.1  work turn=True tasks=a76d2fcf650ef63c4:subagent
   56.5  work turn=False tasks=a76d2fcf650ef63c4:subagent
   71.8  start via=again
   73.6  end finished
  132.0  end session closed
```
