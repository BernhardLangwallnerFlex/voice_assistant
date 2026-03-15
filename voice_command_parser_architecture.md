# Voice Command Parsing Architecture (Slack / Todoist / Calendar)

This document summarizes a robust architecture for parsing voice
commands into structured actions for services such as **Slack**,
**Todoist**, and **Calendar**.

The goal is to create a **deterministic, safe, and predictable system**
where the LLM cannot accidentally trigger the wrong service.

------------------------------------------------------------------------

# 1. Overall Architecture

The recommended pipeline separates **service detection** from **intent
extraction**.

Pipeline:

1.  Voice input → Speech-to-text
2.  Text normalization
3.  **Code-level trigger detection**
4.  Pass routing flags to the LLM
5.  LLM extracts structured intents
6.  **Pydantic schema validation**
7.  **Final safety filter**
8.  Execute integrations (Slack / Todoist / Calendar)

This layered approach prevents hallucinated actions and keeps the system
predictable.

------------------------------------------------------------------------

# 2. Core Design Principle

The system intentionally avoids letting the model infer actions.

Instead, it follows three principles:

### 1. Hard routing rules

Services can only be triggered by specific keywords.

### 2. Code-enforced safety

Routing is detected in Python before the LLM runs.

### 3. Post-validation filtering

Even if the model produces an invalid intent, it is discarded.

------------------------------------------------------------------------

# 3. Service Trigger Rules

## Slack

Slack actions are allowed **only if the word `slack` appears explicitly
in the command**.

Examples:

Valid:

> "Slack Sarah that I'm running late"

Invalid:

> "Tell Sarah I'm running late"

> "Message Sarah that I'm running late"

These should **NOT trigger Slack**.

------------------------------------------------------------------------

## Todoist

Todoist actions are allowed only when the command includes one of these
terms:

-   reminder
-   remind me
-   task
-   to-do
-   todo

Examples:

Valid:

> "Remind me tomorrow to send the proposal"

> "Create a task to review the budget"

Invalid:

> "I need to review the budget tomorrow"

------------------------------------------------------------------------

## Calendar

Calendar intents are allowed when the command clearly refers to
scheduling time.

Typical phrases include:

-   schedule
-   book
-   set up a meeting
-   create an event
-   move a meeting
-   block time
-   add to calendar

Example:

> "Schedule a meeting with Alex tomorrow at 3pm"

------------------------------------------------------------------------

# 4. Python Preprocessing Layer

Before the LLM runs, the transcript is normalized and analyzed.

Example tasks:

-   convert to lowercase
-   normalize spacing
-   detect service triggers

Example service detection:

``` python
flags = {
    "slack_allowed": contains_slack_trigger(text),
    "todoist_allowed": contains_todoist_trigger(text),
    "calendar_allowed": contains_calendar_trigger(text)
}
```

These flags are then injected into the prompt.

This ensures the model **cannot activate forbidden services**.

------------------------------------------------------------------------

# 5. LLM Prompt Strategy

The LLM is instructed to behave as a **strict parser**.

Important instructions:

-   Do **not infer services**
-   Only extract intents allowed by routing flags
-   Return empty intents if nothing qualifies
-   Do not invent details

Example routing flags passed to the prompt:

    Slack allowed: true
    Todoist allowed: false
    Calendar allowed: true

The prompt explicitly states:

> If Slack allowed is false, Slack intents are forbidden.

------------------------------------------------------------------------

# 6. Structured Output Schema

The LLM returns JSON with this structure:

``` json
{
  "intents": [
    {
      "service": "calendar | todoist | slack",
      "calendar": {...} | null,
      "todoist": {...} | null,
      "slack": {...} | null
    }
  ],
  "raw_text": "original command"
}
```

Only one service object should be populated per intent.

------------------------------------------------------------------------

# 7. Pydantic Validation

After parsing, the response is validated using **Pydantic models**.

Example:

-   service must be one of: calendar, todoist, slack
-   only the matching object can be populated
-   priorities must be within allowed ranges

Example validation rule:

    If service == "todoist"
    calendar must be null
    slack must be null
    todoist must exist

If validation fails, the result is rejected.

------------------------------------------------------------------------

# 8. Final Safety Filter

A final layer ensures the LLM did not bypass routing rules.

Example logic:

``` python
if intent.service == "slack" and not flags["slack_allowed"]:
    discard intent
```

This guarantees the system never executes forbidden actions.

------------------------------------------------------------------------

# 9. Example Inputs

## Example 1

Input:

> Tell Sarah I'm running late

Output:

    {
      "intents": []
    }

Reason: Slack keyword not present.

------------------------------------------------------------------------

## Example 2

Input:

> Slack Sarah that I'm running late

Output:

Slack message intent.

------------------------------------------------------------------------

## Example 3

Input:

> Remind me tomorrow to send the proposal

Output:

Todoist task.

------------------------------------------------------------------------

## Example 4

Input:

> Schedule a meeting with Alex tomorrow at 3

Output:

Calendar event.

------------------------------------------------------------------------

## Example 5 (multiple actions)

Input:

> Slack Sarah that I'm running late and remind me to send the deck
> tonight

Output:

Two intents:

1.  Slack message
2.  Todoist task

------------------------------------------------------------------------

# 10. Why This Architecture Works

Benefits:

### Predictability

Services only trigger when explicitly requested.

### Safety

Multiple validation layers prevent incorrect actions.

### Extensibility

New services (Email, Notion, etc.) can be added by introducing:

-   new trigger rules
-   new schema objects
-   new service flags

### LLM Control

The model acts as a **parser**, not an autonomous agent.

------------------------------------------------------------------------

# 11. Recommended Future Improvements

### Add Email service

Trigger word:

    email
    send an email

Similar routing logic can be added.

------------------------------------------------------------------------

### Add Debug Mode

During development, include debugging information:

    "debug": {
      "slack_allowed": true,
      "todoist_allowed": false
    }

This helps diagnose parser mistakes.

------------------------------------------------------------------------

### Add Unit Tests

Recommended test cases:

-   no Slack inference
-   explicit Slack
-   explicit Todoist
-   ambiguous obligations
-   multiple intents
-   mixed services

------------------------------------------------------------------------

# 12. Summary

The production-safe architecture is:

    Speech → Text
            ↓
    Trigger Detection (Python)
            ↓
    Strict Prompt with Routing Flags
            ↓
    LLM Intent Extraction
            ↓
    Pydantic Validation
            ↓
    Service Safety Filter
            ↓
    Execute Integration

This combination produces a **deterministic, safe, and extensible
voice-command system**.
