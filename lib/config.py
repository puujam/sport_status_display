import os
import json

lib_dir = os.path.dirname(os.path.realpath(__file__))
script_root_dir = os.path.dirname(lib_dir)
default_config_path = os.path.join(script_root_dir, "config.json")

class SportsStatusConfig():
    def __init__(self, file_path=default_config_path):
        with open(file_path, "r") as file_handle:
            self.data = json.load(file_handle)
        
    @property
    def event_cycle_period_seconds(self):
        return self.data["event_cycle_period_seconds"]

    @property
    def refresh_data_period_seconds(self):
        return self.data["refresh_data_period_seconds"]

    def filter_event_list(self, event_list):
        results = list()

        for event in event_list:
            # Check Sport
            for sport_filter in self.data["filter"]["sports"]:
                if common_json_properties_exist(sport_filter, event.league.sport.data):
                    # This sport is in the fitler, next check the league
                    for league_filter in sport_filter["leagues"]:
                        if common_json_properties_exist(league_filter, event.league.data):
                            # This league is in the filter, check for competitors
                            if "competitors" in league_filter:
                                for competitor_filter in league_filter["competitors"]:
                                    # Need to check multiple objects this time
                                    for competitor in event.competitors:
                                        if common_json_properties_exist(competitor_filter, competitor.data):
                                            results.append(event)
                            else:
                                # Allow for ommitting competitor filter entirely
                                # Include every event in the league
                                results.append(event)
        
        return results

    def get_filter_sports_and_leagues_list(self):
        results = list()

        for sport in self.data["filter"]["sports"]:
            for league in sport["leagues"]:
                results.append((sport["slug"].lower(), league["abbreviation"].lower()))
        
        return results

def common_json_properties_exist(filter_object, check_object):
    """We specify the filter_object first for optimization, we assume
    there are fewer properties on it than the queried data."""
    
    for key, value in filter_object.items():
        if key in check_object and check_object[key] == value:
            return True
    
    return False