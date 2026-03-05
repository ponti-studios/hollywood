import re
from datetime import datetime, time

import pytz
from dateutil.relativedelta import relativedelta

# from nexus.lib.clients.spacy import nlp  # TODO: Remove spacy dependency


def parse_relative_date(date_str, base_date):
    date_str = date_str.lower()

    # Dictionary for day of week mapping
    days = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    # Handle 'day after tomorrow'
    if "day after tomorrow" in date_str:
        return base_date + relativedelta(days=2)

    # Handle 'weekend'
    if "weekend" in date_str:
        # Assume weekend starts Saturday
        days_ahead = 5 - base_date.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return base_date + relativedelta(days=days_ahead)

    # Handle standalone weekdays (e.g., 'Saturday') as next occurrence
    if any(day in date_str for day in days):
        for day, offset in days.items():
            if day in date_str:
                days_ahead = (offset - base_date.weekday() + 7) % 7
                if days_ahead == 0:
                    days_ahead = 7
                return base_date + relativedelta(days=days_ahead)

    # Handle "next" expressions
    if "next" in date_str:
        if "month" in date_str:
            next_month = base_date + relativedelta(months=1)
            # last day of next month
            if "last" in date_str or "end" in date_str:
                candidate = next_month.replace(day=1)
                last_day = (candidate + relativedelta(months=1, days=-1)).day
                return next_month.replace(day=last_day)
            day_match = re.search(r"(\d+)(?:st|nd|rd|th)?", date_str)
            if day_match:
                day = int(day_match.group(1))
                candidate = next_month.replace(day=1)
                last_day = (candidate + relativedelta(months=1, days=-1)).day
                return next_month.replace(day=min(day, last_day))
            return next_month
        elif any(day in date_str for day in days):
            for day, offset in days.items():
                if day in date_str:
                    return base_date + relativedelta(days=(offset - base_date.weekday() + 7) % 7)
        elif "week" in date_str:
            return base_date + relativedelta(weeks=1)

    # Handle "this" expressions
    if "this" in date_str:
        if "month" in date_str and ("last" in date_str or "end" in date_str):
            candidate = base_date.replace(day=1)
            last_day = (candidate + relativedelta(months=1, days=-1)).day
            return base_date.replace(day=last_day)
        if any(day in date_str for day in days):
            for day, offset in days.items():
                if day in date_str:
                    days_ahead = offset - base_date.weekday()
                    if days_ahead <= 0:
                        days_ahead += 7
                    return base_date + relativedelta(days=days_ahead)

    # Handle "tomorrow" and "today"
    if "tomorrow" in date_str:
        return base_date + relativedelta(days=1)
    if "today" in date_str:
        return base_date

    # Handle month names
    months = [
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    ]
    for i, month in enumerate(months):
        if month in date_str:
            day_match = re.search(r"(\d+)(?:st|nd|rd|th)?", date_str)
            if day_match:
                day = int(day_match.group(1))
                # Build a candidate for the target month
                year = base_date.year if (i + 1) >= base_date.month else base_date.year
                candidate = base_date.replace(year=year, month=i + 1, day=1)
                last_day = (candidate + relativedelta(months=1, days=-1)).day
                day = min(day, last_day)
                date = candidate.replace(day=day)
                return date if date > base_date else date.replace(year=date.year + 1)

    # If no match found, return None
    return None


def parse_time(time_str):
    time_str = time_str.lower()
    # Handle noon/midnight explicitly
    if "noon" in time_str:
        return time(12, 0)
    if "midnight" in time_str:
        return time(0, 0)

    match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", time_str)
    if match:
        hour, minute, period = match.groups()
        hour = int(hour)
        minute = int(minute) if minute else 0
        if period == "pm" and hour != 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0
        return time(hour, minute)
    return None


def extract_date_time(text, user_timezone):
    doc = nlp(text)

    date_entity = None
    time_entity = None

    user_tz = pytz.timezone(user_timezone) if user_timezone else pytz.UTC
    now_naive = datetime.now()
    now = user_tz.localize(now_naive)

    # Collect DATE and TIME entities and choose the most specific DATE (prefer ones with digits or month names)
    date_entities = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
    time_entities = [ent.text for ent in doc.ents if ent.label_ == "TIME"]

    # Choose DATE entity: prefer one containing digits or month names
    months = [
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    ]

    def choose_date_entity(ents):
        if not ents:
            return None
        for e in ents:
            if re.search(r"\d", e):
                return e
            for m in months:
                if m in e.lower():
                    return e
        # prefer longer entity
        return max(ents, key=len)

    date_entity = choose_date_entity(date_entities)
    time_entity = time_entities[0] if time_entities else None

    # If time entity contains weekday information (e.g., 'Saturday morning'), use it to infer the date
    if not date_entity and time_entity:
        if parse_relative_date(time_entity, now.date()):
            date_entity = time_entity

    # If neither date nor time is present, return None for explicit negatives e.g. 'no date or time', otherwise default to current time
    if not date_entity and not time_entity:
        lower = text.lower()
        if re.search(r"no\s+date|no\s+time|no\s+date\s+or\s+time|no\s+date\s+time", lower):
            return None
        # fallback: return current localized datetime
        return now

    parsed_date = parse_relative_date(date_entity, now.date()) if date_entity else None
    if parsed_date is None:
        parsed_date = now.date()
    parsed_time = parse_time(time_entity) if time_entity else None

    # If a time wasn't captured by spaCy's TIME entity, try to parse directly from the text
    if parsed_time is None:
        # Only attempt to parse times if there's an explicit time-like pattern (e.g., '2:30', 'pm', 'noon')
        if (
            re.search(r"\d{1,2}:\d{2}|\d{1,2}\s*(am|pm)", text.lower())
            or "noon" in text.lower()
            or "midnight" in text.lower()
        ):
            parsed_time = parse_time(text)

    # If still None, default to now.time() when a date is present, otherwise leave as None
    if parsed_time is None:
        parsed_time = now.time() if date_entity else None

    # Handle cases where spacy captures a word like 'morning' or 'afternoon' but parse_time returns None
    if time_entity and parsed_time is None:
        te = time_entity.lower()
        if "morning" in te:
            parsed_time = now.time()
        elif "afternoon" in te:
            parsed_time = time(15, 0)
        elif "evening" in te:
            parsed_time = time(18, 0)

    # If text indicates end of month (explicit), set time to 23:59
    if "end" in text.lower() and "month" in text.lower():
        parsed_time = time(23, 59)

    if parsed_date and parsed_time:
        dt = datetime.combine(parsed_date, parsed_time)
        dt = user_tz.localize(dt)

        # If the resulting datetime is in the past and doesn't contain "last", move it to the future
        if dt < now and "last" not in text.lower():
            if "next" not in text.lower():
                # Only roll forward by a day if the input text is essentially time-only (e.g., '9am' or 'at 9am')
                time_only_pattern = r"^\s*(?:at\s*)?\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s*$"
                if re.match(time_only_pattern, text.lower()) or text.strip().lower() in [
                    "noon",
                    "midnight",
                    "morning",
                    "afternoon",
                    "evening",
                ]:
                    dt += relativedelta(days=1)
                else:
                    # keep the same day
                    pass
            else:
                dt += relativedelta(weeks=1)

        # Normalize tzinfo to match tests that use replace(tzinfo=...)
        return dt

    return None
