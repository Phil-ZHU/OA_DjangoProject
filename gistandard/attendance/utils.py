import calendar
from datetime import date, timedelta
from attendance.models import Holiday, Shift

def build_calendar(year, month):
    """返回当月所有日期是否上班 & 默认班次"""
    shift = Shift.objects.first()  # 默认班
    cal = calendar.monthcalendar(year, month)
    days = []
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(None)
            else:
                today = date(year, month, day)
                is_hol = Holiday.objects.filter(date=today).exists()
                row.append({'day': day, 'is_work': not is_hol, 'shift': shift})
        days.append(row)
    return days