import pytest

from app.services.classifier import classify_intents


# --- Slack ---

@pytest.mark.parametrize("text", [
    "Slack Sarah that I'm running late",
    "slack john hello",
    "SLACK Sarah good morning",
    "Hey, slack Sarah about the meeting",
])
def test_slack_positive(text):
    assert "slack" in classify_intents(text)


@pytest.mark.parametrize("text", [
    "Tell Sarah I'm running late",
    "Message Sarah about the report",
    "slackbot is down",
    "check the slackware install",
])
def test_slack_negative(text):
    assert "slack" not in classify_intents(text)


# --- Todoist ---

@pytest.mark.parametrize("text", [
    "Remind me to buy milk",
    "remind me tomorrow to send the proposal",
    "Create a reminder to call the dentist",
    "Set a reminder for Friday",
    "Add a task to review the PR",
    "I need to create a task for this",
    "Add this to my to-do list",
    "Add a todo to clean the garage",
    "todos for this week",
    "reminders for today",
    "Create a new task for the project",
    "tasks for tomorrow",
])
def test_todoist_positive(text):
    assert "todoist" in classify_intents(text)


@pytest.mark.parametrize("text", [
    "I need to send the proposal tomorrow",
    "I should buy milk",
    "remind John to send the report",
    "Don't forget to call the dentist",
    "tasker app is great",
    "multitasking is hard",
])
def test_todoist_negative(text):
    assert "todoist" not in classify_intents(text)


# --- Calendar ---

@pytest.mark.parametrize("text", [
    "Schedule a meeting with Alex tomorrow at 3pm",
    "Create an event for Friday afternoon",
    "Book a call with the team at 2pm",
    "Move the meeting to Thursday",
    "Block time on my calendar for deep work",
    "schedule a call with Sarah",
    "create an appointment for Monday",
    "BOOK A MEETING at noon",
])
def test_calendar_positive(text):
    assert "calendar" in classify_intents(text)


@pytest.mark.parametrize("text", [
    "Schedule something for tomorrow",
    "I have a meeting tomorrow",
    "The event starts at 3pm",
    "Call Sarah about the report",
    "Create a task to review the PR",
    "book club is tonight",
    "move the furniture",
    "Block the user",
])
def test_calendar_negative(text):
    assert "calendar" not in classify_intents(text)


# --- Multi-intent ---

def test_multi_slack_and_todoist():
    result = classify_intents("Slack Sarah that I'm running late and remind me to send the deck tonight")
    assert "slack" in result
    assert "todoist" in result


def test_multi_calendar_and_todoist():
    result = classify_intents("Schedule a meeting with Alex and create a task to prepare the agenda")
    assert "calendar" in result
    assert "todoist" in result


def test_multi_all_three():
    result = classify_intents("Schedule a meeting, create a task for prep, and slack Sarah the details")
    assert "slack" in result
    assert "todoist" in result
    assert "calendar" in result


# --- Edge cases ---

def test_empty_input():
    assert classify_intents("") == []


def test_whitespace_only():
    assert classify_intents("   ") == []


def test_no_keywords():
    assert classify_intents("Hello, how are you today?") == []


def test_case_insensitivity_mixed():
    assert "todoist" in classify_intents("REMIND ME to buy groceries")
    assert "slack" in classify_intents("sLaCk Sarah hello")
    assert "calendar" in classify_intents("SCHEDULE a MEETING")


def test_word_boundary_slackbot():
    assert "slack" not in classify_intents("The slackbot sent a notification")


def test_word_boundary_tasker():
    assert "todoist" not in classify_intents("The tasker app is useful")


def test_word_boundary_multitasking():
    assert "todoist" not in classify_intents("I'm good at multitasking")


def test_remind_without_me():
    """'remind' alone (without 'me') should NOT trigger todoist."""
    assert "todoist" not in classify_intents("Remind John to send the report")


def test_reminder_triggers():
    """'reminder' should trigger todoist even without 'me'."""
    assert "todoist" in classify_intents("Set a reminder for the dentist")


def test_schedule_without_noun():
    """'schedule' alone without a calendar noun should not trigger calendar."""
    assert "calendar" not in classify_intents("Schedule the deployment for tonight")


def test_calendar_noun_without_verb():
    """Calendar noun without action verb should not trigger calendar."""
    assert "calendar" not in classify_intents("The meeting went well today")
