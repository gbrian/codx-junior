# Budget and analytics

codx-junior makes AI cost visible and controllable, so you can plan a project with transparent human hours on one side and scalable AI tokens on the other.

## cxjcoins

Every AI call records its input and output tokens and converts them into **cxjcoins**, codx-junior's internal unit of cost. Prices are set per 1K tokens at provider level and can be overridden per model. Providers can link to their pricing page so prices are easy to keep up to date.

## Wallets

Each user has a wallet with:

* a **balance** in cxjcoins,
* a list of **transactions** (credits and AI charges with their token usage),
* **spending limits** per day, week or month.

Before a request is sent, codx-junior checks the user's balance and limits and blocks the call if it would go over.

## Token limit rules

Admins can add daily token limits per user, globally, per provider or per model. When a user hits a limit they can **request an extension** with a reason; an admin approves it (with extra tokens or an extra percentage for that day) or rejects it.

## Analytics dashboard

The **Analytics** view shows:

* total tokens and cxjcoins for a period,
* a **daily** chart,
* usage **by model**, by user and by project,
* a **price editor** for models.

Users see their own usage; admins see everyone's. Admins can also open the raw AI logs and the chat logs from **Settings → Miscellaneous**.
