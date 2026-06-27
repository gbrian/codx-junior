# Analytics Router Documentation

The Analytics Router (`/analytics`) provides endpoints for tracking, visualizing, and managing token consumption data across the platform. The router separates functionality into two distinct scopes: **User-Scoped** (data filtered only to the authenticated user) and **Administrator-Scoped** (data aggregated across all users).

***
## 🛡️ Authentication & Scope Overview

*   **[User-scoped]**: Endpoints under `/me`, `/dates`, etc., require the standard `get_authenticated_user` dependency, ensuring data is filtered by the requesting user's account.
*   **[Admin-only]**: All endpoints under `/admin/` are restricted and require the user to possess the `admin` role (enforced via the `require_admin` dependency).

***
## 📈 User-Scoped Analytics Endpoints (Own Data)

These endpoints provide metrics specific to the authenticated user.

### GET `/api/analytics/me`
Retrieves the user's token usage metrics for two periods: today and the current calendar month.

**Returns:** A dictionary containing structured data keys for `today` and `current_month`, including start/end dates, input tokens, output tokens, total tokens, and call counts.

### GET `/api/analytics/dates`
Lists all unique ISO dates (`YYYY-MM-DD`) for which the authenticated user has recorded token usage events.

### GET `/api/analytics/total`
Returns the aggregated total token consumption for the user. This endpoint supports filtering by:
*   Start Date (Inclusive)
*   End Date (Inclusive)
*   Project Name
*   Model Name

**Response:** `{input_tokens, output_tokens, total_tokens, calls}`

### GET `/api/analytics/daily`
Provides a detailed, period-aggregated token usage breakdown for the user. The granularity can be controlled by the `grouping` query parameter.

**Parameters:**
*   `start_date`: Inclusive start date (YYYY-MM-DD).
*   `end_date`: Inclusive end date (YYYY-MM-DD).
*   `project_name`: Filter by project name.
*   `grouping`: The time period level (`day`, `hour`, or `minute`). Default is `'day'`.

**Response:** A list of objects, each containing the reporting period, and usage totals.

### GET `/api/analytics/by-model`
Returns total token usage aggregated by model name for the user. Supports filtering by date range and project name.

**Response:** `{model_name: {input_tokens, output_tokens, total_tokens, calls}}`

***
## 👑 Administrator Analytics Endpoints (Global Data)

These endpoints provide organizational visibility into resource usage across all users. **Requires Admin Role.**

### GET `/api/analytics/admin/dates`
Lists every ISO date recorded in the system across all users with token usage data.

### GET `/api/analytics/admin/total`
Retrieves global total token consumption, supporting comprehensive filtering:
*   Start Date (Inclusive)
*   End Date (Inclusive)
*   Username
*   Project Name
*   Project ID
*   Model Name

**Response:** `{input_tokens, output_tokens, total_tokens, calls}`

### GET `/api/analytics/admin/daily`
Provides a system-wide, period-aggregated token usage breakdown. Supports filtering and grouping identical to the user endpoints (`daily`). **Requires Admin Role.**

### GET `/api/analytics/admin/by-user`
Generates statistics aggregated by username across all accounts. Supports filtering by date range, project name, and project ID.

**Response:** `{username: {input_tokens, output_tokens, total_tokens, calls}}`

### GET `/api/analytics/admin/by-project`
Aggregates token usage metrics grouped by the associated project name across all users. Supports date range filtering and primary username filtering.

**Response:** `{project_name: {input_tokens, output_tokens, total_tokens, calls}}`

### GET `/api/analytics/admin/by-model`
Generates system-wide statistics aggregated by model name. Supports filtering by date range, username, and project name.

**Response:** `{model_name: {input_tokens, output_tokens, total_tokens, calls}}`

***
## 💰 Admin Pricing Management Endpoints (Settings)

These endpoints manage the global pricing schema for AI providers and models, affecting how historical data is calculated. **Requires Admin Role.**

### GET `/api/analytics/admin/pricing`
Fetches a comprehensive list of all configured AI providers and associated models. For each model, it displays the current pricing structure (model-level overrides) and falls back to the overall provider default rates.

**Response:** Detailed JSON array listing `name`, global `input_k_tokens_cxjcoins`, and sub-models with their respective prices.

### PUT `/api/analytics/admin/pricing/provider/{provider_name}`
Allows updating the base, provider-level token pricing for a specified AI service provider.

**Body:** Requires a `PricingUpdateRequest` containing optional new values for `input_k_tokens_cxjcoins` and `output_k_tokens_cxjcoins`.

### PUT `/api/analytics/admin/pricing/model/{provider_name}/{model_name}`
Updates the token pricing for an individual specialized AI model within a provider. This mechanism creates or modifies a price entry keyed by the provider-side model name.

**Body:** Requires a `PricingUpdateRequest` containing optional new values for input and output token costs.

### POST `/api/analytics/admin/pricing/recalculate`
Initiates a reprocessing task that rewrites historical analytics events—updating their attributed cost based on new pricing rules. This function is essential when global or model-specific prices change.

**Body:** Must include the service `provider`, specific `model`, the `start_date`, `end_date`, and the precise token rates used for rewriting (`input_k_tokens_cxjcoins` and `output_k_tokens_cxjcoins`).

## Dependencies
**Imports from:** codx/junior/api/__init__.py, codx/junior/model/model.py, codx/junior/security/user_management.py, codx/junior/globals.py, codx/junior/analytics/__init__.py, codx/junior/global_settings.py, codx/junior/model/ai_model.py
**Imported by:** codx/junior/app.py