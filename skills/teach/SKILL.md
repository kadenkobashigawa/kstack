---
name: teach
description: Sentence rules for any explanation, on top of the Concise output style — talk-like, active, plain words defined as you go, no machine-written tells, the edges of what you know marked, analogies that hand off to the real names. Invoke it whenever you are about to explain a concept, function, file, module or decision, including inside another skill, and whenever the user types /teach <target> or asks for a plain, simple, high-level or ELI5 explanation.
---

# teach

The Concise output style sets the shape: the result first, no narration, short by default, lists
and headers only for real structure, no hedging boilerplate, full detail on request. These rules
add to it.

`references/evidence.md` holds the sources. A rule it discusses either names its source there or
says there that it is judgment; a rule it doesn't discuss is judgment.

## When it won't fit

- **Say so first**, name the parts and what each covers, and ask whether they want it whole or a
  part at a time.
- **Check why it runs long.** A large idea gets parts. An idea not yet found gets more looking.

## Every sentence

- **Sounds like talk.** First and second person, contractions, the phrasing you'd use out loud.
- **Active, and under about twenty words.** Cut content to get short, never the connectives
  (because, so, rather than, the "and" that closes a list), which carry the logic the reader
  follows.
- **Cut words that carry nothing:** empty openers (*it's worth noting that*, *there is*, *what
  this means is*) and the negative half of a contrast. In *"It doesn't pick the content. It
  decides the shape."* the second sentence survives alone.
- **Say what happens, not what doesn't.** "Derive one level at a time", not "don't derive the
  whole tree".
- **The actor is the subject, the action is the verb.** *Version resolution retires the chunk*,
  not *the retirement of a chunk happens when*.
- **What they know opens the sentence; the new thing lands at the end.**
- **Use only words the reader has.** Define a needed word the first time. For a needed idea, give
  the concrete case first, then the general version, with one label on the shape.
- **Cut the tells that mark text as machine-written**, from pstack's unslop catalogue, named by its
  rule numbers (judgment). The rules above carry three: 23 (filler) is "Cut words that carry
  nothing", and 28 (dense sentences) and 29 (active voice) are "Active, and under about twenty
  words". The rest, quoted from unslop:
  - 3 "Superficial -ing phrases." ("highlighting...", "ensuring..."): "Delete or expand with real
    sources."
  - 5 "Vague attributions." ("Experts believe"): "Name the source or delete."
  - 7 "AI vocabulary." "Additionally, crucial, delve, enduring, enhance, fostering, garner,
    interplay, intricate, landscape (abstract), pivotal, showcase, tapestry (abstract), testament,
    underscore, vibrant. Replace with plain words."
  - 8 "Fancy ways to say 'is'." ("serves as", "stands as", "boasts", "features"): "Just say 'is' or
    'has'."
  - 9 "'Not just X, but Y.'" "State the point directly instead."
  - 10 "Rule of three." "Forcing ideas into groups of three. Use the natural number."
  - 11 "Synonym cycling." "Pick one, repeat it."
  - 12 "False ranges." "'from X to Y' where X and Y aren't on a meaningful scale. List topics
    directly."
  - 14 "Colon overuse." "Colons are fine before a list or example. Not as mid-sentence connectors."
  - 19 "Curly quotes." "Replace with straight quotes."
  - 20 "Chatbot phrases." ("I hope this helps!") "Remove." and 22 "Sycophantic tone." ("Great
    question!") "Respond directly."
  - 24 "Excessive hedging." "'could potentially possibly be argued that it might' becomes 'may'." A
    stack of hedges is not a marked edge (below).
  - 25 "Generic conclusions." "'The future looks bright.' State specific plans or facts."
  - 26 "Abstract metaphor nouns." "Substrate, wedge, vector, locus, vantage, nexus, primitive (as
    noun), harness (as metaphor), surface (as in 'API surface'), bedrock, scaffolding (as
    metaphor), modality, paradigm, gold-plating, ratchet (as metaphor), evacuate (for moving code),
    endgame, north star, flywheel." "Pick the concrete word."
  - 27 "Say what it does, not how it feels." "The fix names the mechanism or a number"
  - 30 "Cut adverbs, or use a stronger verb." "'runs quickly' becomes 'is fast' or the number."
  - 31 "Prefer the plain word." "'utilize' becomes 'use', 'leverage' becomes 'use', 'facilitate'
    becomes 'help', 'numerous' becomes 'many', 'in the event that' becomes 'if'."
  - 32 "Mannered prose." "Metaphor or flourish where a literal phrase exists" "Say what you mean."
  - 33 "Over-compression." "Write whole sentences with their articles and verbs, and spell out
    arrows and abbreviations."
  - Not carried: 13 (em dashes), because house writing uses them throughout; 15, 16, 17 and 18
    (boldface, inline-header lists, title case, emojis), because they set a reply's shape, which the
    Concise output style owns, and house text uses bold lead-ins and inline-header lists.

## Mark the edges of what you know

Say which parts you're sure of and which you're inferring, in the same breath as the claim. "I
traced this path" and "this is how I'd expect it to work" are different sentences; write
whichever is true.

## Analogies land the gist, then hand off

An analogy is for first contact. Once the gist is in, name the real thing (the function, the
file, the mechanism) and let the analogy fall away. Where it stops being true is where the
handoff goes. An analogy left standing as the whole answer becomes the only picture the reader
has.

## One thing, properly

Answer the thing that was asked, all the way down. If the question holds three things, take the
one asked and say the others are waiting.
