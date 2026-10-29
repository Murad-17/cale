"""Local, aggregate ORION statistics. No transcript or credentials leave SQLite."""
from collections import Counter
from datetime import date, datetime, time as day_time, timedelta
import json
import re
import time

WORD = re.compile(r"[^\W_]+(?:[’'-][^\W_]+)*", re.UNICODE)
SOURCE_NAMES = {'companion': 'Kiçik bot', 'voice': 'Səsli komanda', 'dashboard': 'Əsas ORION'}


def statistics(store, period='month'):
    if period not in ('week', 'month', 'all'):
        raise ValueError('Statistika dövrü düzgün deyil.')
    now = time.time()
    today = date.fromtimestamp(now)
    with store.connection() as db:
        oldest = db.execute("SELECT MIN(stamp) FROM (SELECT MIN(created) AS stamp FROM messages WHERE sender='user' AND created<=? UNION ALL SELECT MIN(created) FROM usage WHERE created<=?)", (now, now)).fetchone()[0]
        if period == 'all':
            first = date.fromtimestamp(oldest) if oldest is not None else today
        else:
            first = today - timedelta(days=6 if period == 'week' else 29)
        start = datetime.combine(first, day_time.min).timestamp()
        days, sources = Counter(), Counter()
        words = messages = 0
        for text, encoded, created in db.execute("SELECT text,extras,created FROM messages WHERE sender='user' AND created>=? AND created<=?", (start, now)):
            count = len(WORD.findall(text))
            words += count
            messages += 1
            days[date.fromtimestamp(created)] += count
            try:
                source = json.loads(encoded).get('source', 'ui')
            except (ValueError, AttributeError):
                source = 'ui'
            group = 'voice' if source in ('voice', 'background_voice', 'companion_voice') else 'companion' if source == 'companion' else 'dashboard'
            sources[group] += 1
        usage = db.execute('SELECT COUNT(*),COALESCE(SUM(output_tokens),0),COALESCE(SUM(MAX(seconds,0)),0) FROM usage WHERE created>=? AND created<=?', (start, now)).fetchone()
    span = (today-first).days + 1
    month_span = (today.year-first.year)*12 + today.month-first.month + 1
    bucket = 'day' if span <= 62 else 'week' if span <= 420 else 'month' if month_span <= 60 else 'year'

    def key(day):
        if bucket == 'week':
            return day - timedelta(days=day.weekday())
        if bucket == 'month':
            return day.replace(day=1)
        if bucket == 'year':
            return day.replace(month=1, day=1)
        return day

    grouped = Counter()
    for day, count in days.items():
        grouped[key(day)] += count
    cursor, last, series = key(first), key(today), []
    while cursor <= last:
        series.append({'date': cursor.isoformat(), 'words': grouped[cursor]})
        if bucket == 'year':
            cursor = cursor.replace(year=cursor.year+1)
        elif bucket == 'month':
            cursor = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
        else:
            cursor += timedelta(days=7 if bucket == 'week' else 1)
    calls, output_tokens, seconds = usage
    return {'period': period, 'from': first.isoformat(), 'to': today.isoformat(), 'bucket': bucket,
            'words': words, 'messages': messages, 'active_days': len(days), 'api_calls': calls,
            'average_seconds': round(seconds/calls, 2) if calls else None,
            'tokens_per_second': round(output_tokens/seconds, 1) if seconds > 0 else None,
            'series': series,
            'sources': [{'id': key, 'label': SOURCE_NAMES[key], 'count': count,
                         'percent': round(count/messages*100, 1)} for key, count in sources.most_common()],
            'generated': now}
