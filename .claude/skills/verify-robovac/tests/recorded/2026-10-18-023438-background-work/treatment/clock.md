# treatment clock

5c4a1a52800dafad9a895038d759620c0561c2f0 = 5c4a1a52800dafad9a895038d759620c0561c2f0; 2.1.299 (Claude Code); scenario background-work; seconds from the drive's start; the film's second 0 is its film started line, within a second.

```
    0.0  driver  film started: window 47335 at 476,143 560x420
    0.0  driver  session e5be6bbe-2c0d-4f0b-86f2-70b63bac0219 started in the desktop host mode
    0.0  driver  prompt: /robovac Use the Bash tool with run_in_background set to true to run exactly: sleep 20 . D
    0.7  log     start via=prompt
    0.7  hook    UserPromptSubmit
    3.1  hook    PreToolUse Bash
    4.2  log     work turn=True tasks=bk7tcpz32:shell
    4.2  hook    PostToolUse Bash
    4.2  hook    PostToolBatch
    5.5  log     work turn=False tasks=bk7tcpz32:shell
    5.5  hook    Stop
    5.5  driver  result: success 'launched'
   19.6  driver  still shell-running
   24.3  log     start via=again
   24.3  hook    UserPromptSubmit
   26.5  log     end finished
   26.5  hook    Stop
   26.5  driver  result: success 'The background `sleep 20` finished with exit code 0.'
   50.1  driver  still shell-done
   50.1  driver  pause 2 s
   52.1  driver  prompt: Call the Agent tool once with subagent_type "general-purpose", run_in_background true, and
   52.2  log     start via=again
   52.2  hook    UserPromptSubmit
   54.7  hook    PreToolUse Agent
   54.8  log     work turn=True tasks=a76d2fcf650ef63c4:subagent
   54.8  hook    SubagentStart agent=a76d2fcf650ef63c4
   54.8  hook    PostToolUse Agent
   54.8  hook    PostToolBatch
   56.0  hook    PreToolUse Bash agent=a76d2fcf650ef63c4
   57.1  log     work turn=False tasks=a76d2fcf650ef63c4:subagent
   57.1  hook    Stop
   57.1  driver  result: success 'launched'
   71.1  hook    PostToolUse Bash agent=a76d2fcf650ef63c4
   71.2  hook    PostToolBatch agent=a76d2fcf650ef63c4
   71.4  driver  still agent-running
   72.3  hook    SubagentStop agent=a76d2fcf650ef63c4
   72.5  log     start via=again
   72.5  hook    UserPromptSubmit
   74.2  log     end finished
   74.2  hook    Stop
   74.2  driver  result: success 'The background agent finished. It ran `sleep 15` and replied'
  132.4  driver  still agent-done
  132.7  hook    SessionEnd
  132.7  log     end session closed
  132.9  driver  session closed by the host
  136.1  driver  film stopped
  136.3  driver  app pid 86313 quit, window gone
  136.3  driver  session folder holds: nothing
```
