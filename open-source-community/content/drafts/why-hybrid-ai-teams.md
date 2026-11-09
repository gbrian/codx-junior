---
title: Why unsupervised AI agents fail (and what to do instead)
slug: why-hybrid-ai-teams
date: 2026-11-13
author: Gustavo Brian
status: draft
target: 900 words, 4 min read
tags: [ai-agents, software-delivery, process]
---

# Why unsupervised AI agents fail (and what to do instead)

*Draft — edit before publishing. Claims must match `research/PLATFORM_REVIEW.md`.*

---

The first time I gave an AI agent a whole task and walked away, it worked beautifully for
twenty minutes. Then it refactored a module I hadn't asked about, renamed a public function,
and reported success because the tests it wrote also passed.

Nothing was broken in the demo sense. The diff was clean. It was just... not my project anymore.

That experience is the whole reason codx-junior exists. Not "AI writes code now" — that ship
sailed. The problem is the distance between *an agent that can act* and *a team that can trust
what it did*.

## Two failure modes, one missing layer

Today's AI development tools mostly fall into two camps.

**The editor.** Cursor, Copilot, Windsurf. Excellent at the inner loop: you type, it predicts,
you accept. The human is the scheduler, the reviewer, the memory and the budget. This works
because you are always in the loop — and stops working the moment the work outgrows one person's
attention.

**The autonomous agent.** Devin, OpenHands, and the long tail of "give it a ticket, get a PR"
products. They optimize for the demo: one prompt, a branch, a pull request. The demo is real.
The production experience is a review queue of large, plausible, subtly wrong diffs, with no
clear owner and a bill nobody predicted.

Both camps share a missing layer: **the delivery system around the work.** Who decided this
task matters? What context did the agent have? Who approved the change? What did it cost, and
against whose budget? In most teams those answers live in Jira, Slack, GitHub and a provider
dashboard, connected by a human who is increasingly the bottleneck.

The hand-off tax is the product opportunity.

## Supervised autonomy

The position I've landed on is boring and, I think, correct: agents should do the volume, humans
should keep direction, and every action should be attributable.

Concretely, that means four properties.

**1. The task is the unit, not the file.** A card on a board that *is* a conversation: the
request, the agent's plan, the tools it called, the diff it produced, the review, the cost. One
object. When the object is split across four tools, supervision becomes archaeology.

**2. Context is explicit.** An agent working in a repository should retrieve from an index of
that repository, use a profile that says which model and which tools are appropriate, and record
what it looked at. "It had the whole repo in the context window" is not a strategy; it is a
receipt you can't read.

**3. Review is the product, not the afterthought.** A 600-line diff is not reviewable, no matter
who wrote it. The interface has to make the change legible in under a minute: what changed, why,
what the tests say, what the agent was trying to do. If review is slow, the whole model collapses
back into "merge and hope".

**4. Cost is a first-class object.** Every model call has a price. If the person accountable for
delivery cannot see that price per task, per user, per project, then "AI made us faster" is an
accounting fiction. Budgets — wallets, limits, approval for overruns — are not a billing feature.
They are the control surface that makes autonomy safe to grant.

Put those four together and you get something that is neither an editor nor an autonomous agent.
It is a workspace where a small team can operate a larger one.

## What this looks like in practice

In codx-junior, moving a card from *Backlog* to *In progress* starts an agent with the project
indexed, a profile selected and a budget attached. The agent searches, patches, runs commands,
opens a diff. The diff and the cost land on the same card. A human approves, rejects or asks for
changes — and the next run inherits that decision as context.

None of that is exotic. The novelty is that planning, execution, review and metering are the same
system, so the answers to "what happened, who approved it, what did it cost" are one click apart.

## What is still hard

I want to be specific, because "AI will change everything" is not useful.

* **Review quality.** Agents produce plausible code. Making a diff reviewable in seconds is an
  interface problem we have not solved, only improved.
* **Trust calibration.** Some tasks deserve full autonomy (dependency bumps, test scaffolding);
  others deserve none (auth, migrations, billing). Encoding that per profile is manual today.
* **Cost variance.** The same task can cost 10× depending on the model and the loop. Budgets
  contain the damage; they do not make the agent efficient.
* **The last mile of setup.** Self-hosting is a feature and a tax. A ten-minute install is the
  goal; today it is closer to twenty on a good day.
* **The org, not the tool.** Getting a team to agree on what agents may do is a management
  problem wearing a technical costume.

## The test I use now

Before giving an agent a task, I ask three questions:

1. Can I review the result in under a minute?
2. Do I know what it will cost before it starts?
3. If it goes wrong, will I know where and why?

When the answer to all three is yes, autonomy is cheap and safe. When any answer is no, the
bottleneck is not the model — it is the workspace around it.

That is the layer I am building. Not a smarter agent: a place where agents and humans can work on
the same project without either side losing the plot.

---

*codx-junior is an open-source workspace for hybrid AI + human software teams. Self-host it under
AGPL-3.0, or hire the managed team to run it with you. [Install in ~10 minutes →](/getting-started)*
