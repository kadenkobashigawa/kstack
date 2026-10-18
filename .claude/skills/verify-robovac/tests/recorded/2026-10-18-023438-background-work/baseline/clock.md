# baseline clock

a550130 = a5501301332ee8ace8ad71c6d0b5b0ac60ea3bae; 2.1.299 (Claude Code); scenario background-work; seconds from the drive's start; the film's second 0 is its film started line, within a second.

```
    0.0  driver  film started: window 47318 at 476,143 560x420
    0.0  driver  session 1951e4a0-ff7b-4c78-a515-9abd398806d9 started in the desktop host mode
    0.0  driver  prompt: /robovac Use the Bash tool with run_in_background set to true to run exactly: sleep 20 . D
    1.1  log     start via=prompt
    1.1  hook    UserPromptSubmit
    3.1  hook    PreToolUse Bash
    5.0  hook    PostToolUse Bash
    5.0  hook    PostToolBatch
    6.3  log     end finished
    6.3  hook    Stop
    6.3  driver  result: success 'launched'
   20.5  driver  still shell-running
   25.0  log     start via=again
   25.0  hook    UserPromptSubmit
   27.1  log     end finished
   27.2  hook    Stop
   27.2  driver  result: success 'The background `sleep 20` finished with exit code 0. Nothing'
   50.2  driver  still shell-done
   50.2  driver  pause 2 s
   52.2  driver  prompt: Call the Agent tool once with subagent_type "general-purpose", run_in_background true, and
   52.2  log     start via=again
   52.3  hook    UserPromptSubmit
   54.4  hook    PreToolUse Agent
   54.4  hook    SubagentStart agent=afc5637be6ed9e303
   54.4  hook    PostToolUse Agent
   54.5  hook    PostToolBatch
   56.4  log     end finished
   56.4  hook    Stop
   56.5  driver  result: success 'launched'
   58.0  hook    PreToolUse Bash agent=afc5637be6ed9e303
   70.6  driver  still agent-running
   73.1  hook    PostToolUse Bash agent=afc5637be6ed9e303
   73.2  hook    PostToolBatch agent=afc5637be6ed9e303
   74.1  hook    SubagentStop agent=afc5637be6ed9e303
   74.2  log     start via=again
   74.2  hook    UserPromptSubmit
   77.3  log     end finished
   77.3  hook    Stop
   77.3  driver  result: success 'The background agent finished. It ran `sleep 15` and reporte'
  132.3  driver  still agent-done
  132.4  log     end session closed
  132.4  hook    SessionEnd
  132.6  driver  session closed by the host
  135.6  driver  film stopped
  135.9  driver  app pid 83880 quit, window gone
  135.9  driver  session folder holds: nothing
```
