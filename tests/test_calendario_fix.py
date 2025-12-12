import calendar
import datetime

def get_month_calendar(year, month):
    cal = calendar.monthcalendar(year, month)
    lines = [f"{calendar.month_name[month].upper()}:"]
    lines.append(" D  L  M  M  J  V  S")
    for week in cal:
        # Find the first non-zero day in the week to calculate the week number
        day = next((d for d in week if d != 0), None)
        week_num = datetime.date(year, month, day).isocalendar()[1] if day else 0
        line = f"{week_num:2d} " + " ".join(f"{d:2d}" if d else "  " for d in week)
        lines.append(line)
    return "<br>".join(lines)

def test_calendario():
    print("Testing 2024...")
    for m in range(1, 13):
        try:
            get_month_calendar(2024, m)
            print(f"Month {m} OK")
        except Exception as e:
            print(f"Month {m} FAILED: {e}")
            raise

    print("Testing 2025...")
    for m in range(1, 13):
        try:
            get_month_calendar(2025, m)
            print(f"Month {m} OK")
        except Exception as e:
            print(f"Month {m} FAILED: {e}")
            raise

if __name__ == "__main__":
    test_calendario()
