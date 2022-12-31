import requests
import time
import datetime
import enum

class ESPNCompetitor():
    def __init__(self, data):
        self.data = data

    @property
    def name(self):
        return self.data["displayName"]

    @property
    def score(self):
        return self.data["score"]

    @property
    def is_home(self):
        return self.data["homeAway"] == "home"

    @property
    def logo_dark(self):
        return self.data["logoDark"]

class ESPNEventStatus():
    class ESPNEventStatusCategory(enum.IntEnum):
        not_started = 1,
        in_progress = 2,
        complete = 3
    
    def __init__(self, data):
        self.data = data
    
    @property
    def category(self):
        """See ESPNEventStatusCategory enum. Values are "not_started", "in_progress", and "complete\""""
        if not hasattr(self, "_category"):
            if not self.data["type"]["completed"]:
                state = self.data["type"]["state"]
                
                if state == "pre":
                    self._category = ESPNEventStatus.ESPNEventStatusCategory.not_started
                else:
                    self._category = ESPNEventStatus.ESPNEventStatusCategory.in_progress
            else:
                self._category = ESPNEventStatus.ESPNEventStatusCategory.complete

        return self._category
    
    @property
    def started(self):
        if self.category == ESPNEventStatus.ESPNEventStatusCategory.not_started:
            return False
        else:
            return True
    
    @property
    def completed(self):
        if self.category == ESPNEventStatus.ESPNEventStatusCategory.complete:
            return True
        else:
            return False
    
    @property
    def display_clock(self):
        return self.data["displayClock"]

    @property
    def description(self):
        return self.data["type"]["description"]
    
    @property
    def period(self):
        return self.data["period"]

class ESPNEvent():
    def __init__(self, data, league):
        self.data = data
        self.league = league
        
        self.parse_competitors()
        self.parse_status()
    
    def parse_competitors(self):
        self.competitors = list()
        
        for competitor_data in self.data["competitors"]:
            self.competitors.append(ESPNCompetitor(competitor_data))
    
    def parse_status(self):
        self.status = ESPNEventStatus(self.data["fullStatus"])
    
    @property
    def datetime(self):
        if not hasattr( self, "_datetime" ):
            parsed_datetime = time.strptime(self.data["date"], "%Y-%m-%dT%H:%M:%SZ")
            utc_datetime = datetime.datetime(year=parsed_datetime.tm_year, month=parsed_datetime.tm_mon, day=parsed_datetime.tm_mday, hour=parsed_datetime.tm_hour, minute=parsed_datetime.tm_min, second=parsed_datetime.tm_sec, tzinfo=datetime.timezone.utc)
            self._datetime = utc_datetime.astimezone() # No parameter converts to local
        
        return self._datetime
    
    @property
    def name(self):
        return self.data["name"]
    
    @property
    def id(self):
        return self.data["id"]

class ESPNLeague():
    def __init__(self, data, sport):
        self.data = data
        self.sport = sport
        
        self.parse_events()
        
    def parse_events(self):
        self.events = list()

        for event_data in self.data["events"]:
            self.events.append(ESPNEvent(event_data, self))
    
    @property
    def name(self):
        return self.data["name"]

class ESPNNFL(ESPNLeague):
    def __init__(self, data, sport):
        super().__init__(data, sport)

class ESPNSport():
    def __init__(self, data):
        self.data = data
        
        self.parse_leagues()

    def parse_leagues(self):
        self.leagues = list()

        for league_data in self.data["leagues"]:
            self.leagues.append(ESPNLeague(league_data, self))

    @property
    def name(self):
        return self.data["name"]

class ESPNFootball(ESPNSport):
    def __init__(self, data):
        super().__init__(data)
    
    def parse_leagues(self):
        self.leagues = list()

        for league_data in self.data["leagues"]:
            if league_data["shortName"] == "NFL":
                self.leagues.append(ESPNNFL(league_data, self))
            else:
                self.leagues.append(ESPNLeague(league_data, self))
                
class ESPNData():
    """Represents the results from a single query. An instance of this class should NOT be updated
    with new data, a new instance should be created for a new query result.

    Most of this class and its children rely on lazy operations to do minimal overhead. This probably 
    doesn't actually benefit the performance of the app in an appreciable way."""

    def __init__(self, data):
        self.data = data

        self.parse_sports()

    def parse_sports(self):
        self.sports = list()

        for sport_data in self.data["sports"]:
            if sport_data["name"] == "Football":
                self.sports.append(ESPNFootball(sport_data))
            else:
                self.sports.append(ESPNSport(sport_data))
    
    def get_flattened_events(self):
        results = list()
        
        for sport in self.sports:
            for league in sport.leagues:
                for event in league.events:
                    results.append(event)

        return results

def query_new_data():
    """NOTE: This is probably not a 'legal' access of this ESPN endpoint, but since it's hit
    by your browser every time you load their homepage, they're not likely to tell the difference."""

    data = requests.get("https://site.api.espn.com/apis/v2/scoreboard/header")

    return ESPNData(data.json())

def query_filtered_data(config):
    results = list()

    sport_league_list = config.get_filter_sports_and_leagues_list()
    
    for sport_league in sport_league_list:
        query_url = "https://site.api.espn.com/apis/v2/scoreboard/header?sport={}&league={}".format(sport_league[0], sport_league[1])
        
        data = requests.get(query_url)
        data_object = ESPNData(data.json())
        events = data_object.get_flattened_events()
        
        results.extend(events)
    
    return results