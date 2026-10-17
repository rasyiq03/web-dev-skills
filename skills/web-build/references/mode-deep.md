# Deep work mode (musyawarah)

Read this when the user wants one prompt in and a ready site out, with no back-and-forth
("deep work", "mode musyawarah", "langsung jadi", "one shot"). It spends more compute so the
developer spends none. Quality comes from a council of AI roles that deliberate the
Indonesian way, *musyawarah untuk mufakat*, at four points. Deep mode never stops to ask
the user and never invents a fact.

## Setup

- In step 1 write `mode: deep` in `brief.yaml` (and leave `interactive` false). Work
  through the web-build steps as usual; the sittings replace your own judgment at the
  decision points below.
- The council: you are the **Pimpinan sidang** (chair); the five members are the
  Perancang, Penulis, Arsitek front-end, Penguji mutu, and Wakil klien. Their cards are in
  `${CLAUDE_PLUGIN_ROOT}/skills/web-build/references/council/`.

## The four sittings

| Sitting | When | The council decides | Double vote |
| --- | --- | --- | --- |
| `direction` | step 3, after you wrote `directions.yaml` | which of the five directions | Perancang |
| `copy` | step 5 | the copy for every section | Penulis |
| `first-page` | step 6, after the first page is built | the fixes before the other pages | Penguji mutu |
| `site` | before step 7's last check | the fixes for the whole site | Penguji mutu |

## One sitting

1. `run council <slug> <sitting>` writes the packet: the task, the rules, the graph ids that
   count as evidence, and the material (the five directions, or the pages and last check).
2. **Round 1, usulan mandiri.** Start one subagent per member, in parallel. Give each the
   packet and its own role card, and ask for one answer in the packet's format. Members
   must not see each other's proposals.
3. **Round 2, saling menanggapi (gotong royong).** Give every member all five proposals.
   Each improves one other member's proposal first (`target_role`), then may object.
   An objection that must be solved first is `blocking: true` and cites graph ids.
4. **Round 3, mufakat.** Write the synthesis no member still blocks. If a blocking
   objection remains, give the objecting members one revision round; mark each objection
   `resolved: true` once it is met. If one still blocks, call a vote: one vote per member,
   the sitting's owner counts double, a tie goes to the owner's choice.
5. Write `deliberation/<sitting>.yaml` (schema `schemas/deliberation.schema.json`): roles,
   rounds with every answer word for word, and the resolution (method, outcome, summary,
   votes, dissent, vetoes). Then run `run council <slug> <sitting> --record`. It checks the
   rules (everyone heard, evidence for every block, no open block under mufakat, the vote
   count) and applies the result; for `direction` it writes `decisions.yaml`. Fix the
   minutes or hold another round if it refuses.
6. Apply what was agreed. A council change to one decision goes through
   `run decide <slug> <decision> --choice <value> --by council --reason "<the council's reason>"`.

**Budget:** five calls in round 1, five in round 2, and only the blocking members in a
revision: usually about 11 subagent calls per sitting, never more than 15.

**No subagent tool?** Play the members yourself, one after another, answering round 1 for
each before reading any other answer, and set `simulated: true` in the minutes. The rules
are the same; the handoff says the council was simulated.

## How the council talks

Members speak plain Indonesian, as `references/indonesia.md` describes: *santun tapi jujur*,
objections phrased as proposals with a reason (*usul, bukan vonis*), and *tepa selira*
without hiding problems. Evidence, not seniority, decides.

## Facts are not negotiable

The Wakil klien may veto any invented fact, and the veto cannot be outvoted. Every vetoed
or missing fact stays a `[[ISI: …]]` placeholder, listed in `resolution.vetoes`.

## Ready to use

Deep mode is done when all four sittings are recorded, `check` reports zero errors and zero
warnings, and `handoff` prints "Siap pakai". Report to the user in a few plain sentences:
what the council decided and why, whether any sitting was simulated or went to a vote,
the placeholders still to fill, and that `EXPLAIN.html` and `deliberation/` show every
decision and the minutes.
