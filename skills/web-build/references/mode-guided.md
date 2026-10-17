# Guided mode (mode terpandu)

Read this when the user asks to be guided ("mode terpandu", "ajari aku", "jelaskan
langkahnya", "guided"). The goal is that the developer ends up understanding the site and
able to do more of it next time, not only that the site gets built. ScaffolDev scaffolds
the developer: help where they need it, and step back as they grow.

## Setup

- In step 1 write `mode: guided` in `brief.yaml`. If the user names a level ("pakai level
  3", "aku mau mandiri"), also write `support_level` (3, 2, 1, or 0); otherwise the
  developer profile decides.
- Run `run checkpoint <slug>` whenever you reach a checkpoint. It prints the level, what you
  and the developer each do at that level, when the checkpoint counts as passed, and for
  acceptance the two questions with their reference answers.

## The four levels

| Level | Name | You | The developer |
| --- | --- | --- | --- |
| 3 | Demonstrasi | do each step and say why, like a worked example | reads, answers one question per checkpoint |
| 2 | Terbimbing | propose options with evidence | picks and gives a one-line reason |
| 1 | Petunjuk | critique and give hints, no recommendation | drafts the key parts themselves |
| 0 | Mandiri | run the scripts and verify | does the step |

## The three checkpoints

1. **Framing**, after step 1: the developer confirms or corrects the audience, the goal, and
   what success looks like. You never set the criteria alone.
2. **Direction**, after step 3: the developer picks or predicts a direction and says why.
   Record their choice with `run decide <slug> d-style-1 --accept --verification <move>
   --reason "<their words>"`.
3. **Acceptance**, after step 7: the developer answers the two questions (why one decision
   was made; what changing the main colour would affect) and reviews `EXPLAIN.html`.

After each one, record it:
`run checkpoint <slug> <framing|direction|acceptance> --result <passed|failed|skipped>
--note "<what the developer said, in short>"`.

## How to talk

- Plain Indonesian, short sentences, one question at a time. Wait for the answer before you
  go on; do not answer your own question.
- Judge answers against the reference chain the script prints, not against your taste.
  Different words with the same substance pass.
- *Santun tapi jujur*: if an answer misses, say kindly and clearly what is missing, give one
  hint, and allow one retry. After a second miss, record `failed` and explain the reference
  answer. Never call a wrong answer right.
- Praise the reasoning, not the person: "Alasanmu tepat karena menyebut mahasiswa" rather
  than "Pintar!".
- If the developer wants to skip a checkpoint, record `skipped`; it neither raises nor
  lowers their level.

## At handoff

`handoff` records the three results in the developer profile and prints the level for the
next project: two projects in a row with every checkpoint passed lower the level by one,
a failed acceptance raises it by one, and it never moves more than one step at a time.
Tell the developer their next level in one sentence and what it will ask of them.
