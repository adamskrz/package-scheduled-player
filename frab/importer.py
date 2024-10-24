import pytz
import requests
import calendar
from datetime import timedelta

import dateutil.parser
import defusedxml.ElementTree as ET
import json


def get_schedule(url, group, timezone='UTC'):
    def load_events(xml):
        def to_unixtimestamp(dt):
            dt = dt.astimezone(pytz.utc)
            ts = int(calendar.timegm(dt.timetuple()))
            return ts
        def text_or_empty(node, child_name):
            child = node.find(child_name)
            if child is None:
                return u""
            if child.text is None:
                return u""
            return unicode(child.text)
        def parse_duration(value):
            parts = map(int, value.split(':'))
            if len(parts) == 3:
                d, h, m = parts
                return timedelta(days=d, hours=h, minutes=m)
            elif len(parts) == 2:
                h, m = parts
                return timedelta(hours=h, minutes=m)
            raise ValueError("invalid duration")
        def all_events():
            schedule = ET.fromstring(xml)
            for day in schedule.findall('day'):
                for room in day.findall('room'):
                    for event in room.findall('event'):
                        yield event

        parsed_events = []
        for event in all_events():
            start = dateutil.parser.parse(event.find('date').text)
            duration = parse_duration(event.find('duration').text)
            end = start + duration

            persons = event.find('persons')
            if persons is not None:
                persons = persons.findall('person')

            parsed_events.append(dict(
                start = start.astimezone(pytz.utc),
                start_str = start.strftime('%H:%M'),
                end_str = end.strftime('%H:%M'),
                start_unix  = to_unixtimestamp(start),
                end_unix = to_unixtimestamp(end),
                duration = int(duration.total_seconds() / 60),
                title = text_or_empty(event, 'title'),
                track = text_or_empty(event, 'track'),
                place = text_or_empty(event, 'room'),
                abstract = text_or_empty(event, 'abstract'),
                speakers = [
                    unicode(person.text.strip())
                    for person in persons
                ] if persons else [],
                lang = text_or_empty(event, 'language'),
                id = event.attrib["id"],
                group = group,
            ))
        return parsed_events

    def load_events_json(json_str):
        def to_unixtimestamp(dt):
            dt = dt.astimezone(pytz.utc)
            ts = int(calendar.timegm(dt.timetuple()))
            return ts
        def text_or_empty(object, key):
            value = object.get(key)
            if value is None:
                return ""
            return unicode(value)

        def all_events():
            return json.loads(json_str)

        parsed_events = []
        for event in all_events():
            # schedule times are gmt/utc
            local_zone = pytz.timezone(timezone)
            start = dateutil.parser.parse(event['start']).astimezone(local_zone)
            end = dateutil.parser.parse(event['end']).astimezone(local_zone)
            duration = end - start


            parsed_events.append(dict(
                start_str = start.strftime('%H:%M'),
                end_str = end.strftime('%H:%M'),
                start_unix  = to_unixtimestamp(start),
                end_unix = to_unixtimestamp(end),
                duration = int(duration.total_seconds() / 60),
                title = text_or_empty(event, 'title'),
                track = text_or_empty(event, 'type'),
                place = text_or_empty(event, 'location'),
                abstract = text_or_empty(event, 'description'),
                speakers = [],
                id = event['uuid'],
                group = group,
            ))
        return parsed_events

    r = requests.get(url)
    r.raise_for_status()
    schedule = r.content
    if url.endswith('.json'):
        return load_events_json(schedule)
    return load_events(schedule)


if __name__ == "__main__":
    url = "https://warwickhack.co.uk/schedule.json"
    schedule = get_schedule(url, "example", timezone='Europe/London')
    print(schedule)