from datetime import datetime, timedelta
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def main():
    creds = None
    if os.path.exists("keys/token.json"):
        print("loading token")
        creds = Credentials.from_authorized_user_file("keys/token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "keys/credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("keys/token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)

        working_hours_start = "09:00:00"
        working_hours_end = "17:00:00"
        breaks = [("12:00:00", "13:00:00")]

        now = datetime.utcnow()
        max_time = now + timedelta(days=14)

        print("Availability for the next 14 days:")
        print("------------------------------------\n")

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now.isoformat() + "Z",
                timeMax=max_time.isoformat() + "Z",
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        for day_offset in range(14):
            day_start = now.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) + timedelta(days=day_offset)

            # Skip Saturdays and Sundays
            if day_start.weekday() >= 5:
                continue

            work_start = datetime.strptime(
                day_start.strftime("%Y-%m-%d") + " " + working_hours_start,
                "%Y-%m-%d %H:%M:%S",
            )
            work_end = datetime.strptime(
                day_start.strftime("%Y-%m-%d") + " " + working_hours_end,
                "%Y-%m-%d %H:%M:%S",
            )

            print(f"{work_start.strftime('%A, %B %d, %Y')}:")

            busy_periods = [
                (
                    datetime.strptime(
                        day_start.strftime("%Y-%m-%d") + " " + start,
                        "%Y-%m-%d %H:%M:%S",
                    ),
                    datetime.strptime(
                        day_start.strftime("%Y-%m-%d") + " " + end, "%Y-%m-%d %H:%M:%S"
                    ),
                )
                for start, end in breaks
            ]

            for event in events:
                event_start = event["start"].get("dateTime")
                event_end = event["end"].get("dateTime")

                if event_start and event_end:
                    event_start = datetime.fromisoformat(
                        event_start.replace("Z", "+00:00")
                    ).replace(tzinfo=None)
                    event_end = datetime.fromisoformat(
                        event_end.replace("Z", "+00:00")
                    ).replace(tzinfo=None)
                    if work_start.date() == event_start.date():
                        busy_periods.append((event_start, event_end))

            busy_periods.append((work_start, work_start))
            busy_periods.append((work_end, work_end))

            busy_periods.sort(key=lambda x: x[0])
            available_slots = [
                (busy_periods[i][1], busy_periods[i + 1][0])
                for i in range(len(busy_periods) - 1)
                if busy_periods[i][1] < busy_periods[i + 1][0]
                and busy_periods[i + 1][0] - busy_periods[i][1] >= timedelta(minutes=30)
            ]

            for start, end in available_slots:
                print(f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
