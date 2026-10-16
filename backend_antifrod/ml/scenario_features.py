"""Причинные признаки различий S/D: сутки истории, переадресации, жертва, IMSI."""
from collections import Counter, defaultdict, deque
import heapq

from core.telecom import CITY_CODES

SCENARIO_FEATURES = [
    "caller_imsi_count_24h", "caller_active_calls", "caller_other_imsi_active",
    "caller_calls_24h", "caller_normal_share_24h", "caller_night_share_24h",
    "caller_business_share_24h", "caller_unique_share_24h", "caller_active_hours_24h",
    "caller_peak_hour_share_24h", "caller_adjacent_step_share_24h", "target_step_is_one",
    "caller_forward_destination_count_24h", "forward_destination_source_count_24h",
    "forward_destination_normal_share_24h", "victim_short_city_sources_2h",
    "victim_previous_long_calls_2h", "caller_duration_6_20_share_24h",
]


class Profile:
    def __init__(self):
        self.events = deque()
        self.targets, self.imsis, self.hours, self.forwards = (Counter() for _ in range(4))
        self.normal = self.night = self.business = self.short_notice = self.adjacent = 0
        self.active = []
        self.active_imsis = Counter()

    def update_counts(self, event, sign):
        t, b, imsi, c, duration, hour, adjacent = event
        for counter, key in ((self.targets, b), (self.imsis, imsi), (self.hours, hour), (self.forwards, c)):
            if key != "":
                counter[key] += sign
                if counter[key] == 0:
                    del counter[key]
        self.normal += sign * (duration >= 30)
        self.night += sign * (hour < 6)
        self.business += sign * (8 <= hour <= 19)
        self.short_notice += sign * (6 <= duration <= 20)
        self.adjacent += sign * adjacent

    def expire(self, t):
        while self.events and self.events[0][0] < t - 86400:
            self.update_counts(self.events.popleft(), -1)
        while self.active and self.active[0][0] <= t:
            _, imsi = heapq.heappop(self.active)
            self.active_imsis[imsi] -= 1
            if not self.active_imsis[imsi]:
                del self.active_imsis[imsi]

    def add(self, t, b, imsi, c, duration, hour):
        self.expire(t)
        adjacent = bool(self.events and abs(int(b) - int(self.events[-1][1])) == 1)
        event = (t, b, imsi, c, duration, hour, adjacent)
        self.events.append(event)
        self.update_counts(event, 1)
        if duration > 0:
            heapq.heappush(self.active, (t + duration, imsi))
            self.active_imsis[imsi] += 1


class ScenarioHistory:
    def __init__(self):
        self.callers = defaultdict(Profile)
        self.forwarded = defaultdict(Profile)
        self.victims = defaultdict(deque)
        self.city_sources = defaultdict(Counter)
        self.long_calls = Counter()

    def expire_victim(self, b, t):
        events = self.victims[b]
        while events and events[0][0] < t - 7200:
            _, a, short_city, long_call = events.popleft()
            if short_city:
                self.city_sources[b][a] -= 1
                if not self.city_sources[b][a]:
                    del self.city_sources[b][a]
            self.long_calls[b] -= long_call

    def values(self, t, a, b, imsi, c):
        p = self.callers[a]
        p.expire(t)
        self.expire_victim(b, t)
        n = max(1, len(p.events))
        forward_sources = forward_normal = 0
        if c:
            q = self.forwarded[c]
            q.expire(t)
            forward_sources = len(q.targets)
            forward_normal = q.normal / max(1, len(q.events))
        return [
            len(p.imsis), len(p.active), sum(count for key, count in p.active_imsis.items() if key and key != imsi),
            len(p.events), p.normal/n, p.night/n, p.business/n, len(p.targets)/n, len(p.hours),
            max(p.hours.values(), default=0)/n, p.adjacent/n,
            int(bool(p.events and abs(int(b) - int(p.events[-1][1])) == 1)),
            len(p.forwards), forward_sources, forward_normal, len(self.city_sources[b]),
            self.long_calls[b], p.short_notice/n,
        ]

    def add(self, t, a, b, imsi, c, duration, hour, type_):
        self.callers[a].add(t, b, imsi, c if type_ == "03" else "", duration, hour)
        if type_ == "03" and c:
            self.forwarded[c].add(t, a, "", "", duration, hour)
        short_city = duration <= 10 and a[:3] in CITY_CODES
        long_call = 420 <= duration <= 1500
        if short_city or long_call:
            self.expire_victim(b, t)
            self.victims[b].append((t, a, short_city, long_call))
            if short_city:
                self.city_sources[b][a] += 1
            self.long_calls[b] += long_call
