import os
import sys
import importlib

script_path = os.path.realpath(__file__)
lib_dir = os.path.join(os.path.dirname(os.path.dirname(script_path)), "lib" )
data_lib_path = os.path.join(lib_dir, "data.py")
spec = importlib.util.spec_from_file_location("data", data_lib_path)
data_lib = importlib.util.module_from_spec(spec)
sys.modules["data_lib"] = data_lib
spec.loader.exec_module(data_lib)

def create_competitor_string(competitor):
    return competitor.name + ( " (Home)" if competitor.is_home else "" )

def create_score_summary(event):
    if event.status.category == data_lib.ESPNEventStatus.ESPNEventStatusCategory.not_started:
        return "Not Started"
    elif event.status.category == data_lib.ESPNEventStatus.ESPNEventStatusCategory.in_progress:
        return "{} to {} ({})".format( event.competitors[0].score, event.competitors[1].score, event.status.display_clock )
    else:
        return "{} to {} ({})".format( event.competitors[0].score, event.competitors[1].score, event.status.description )

data = data_lib.query_new_data()

print("Current Summary:")

for sport in data.sports:
    print("\t{}".format(sport.name))
    
    for league in sport.leagues:
        print("\t\t{}".format(league.name))

        for event in league.events:
            print("\t\t\t{}: {} vs {} - {}".format(event.datetime.strftime("%I:%M %p %Z"), create_competitor_string(event.competitors[0]), create_competitor_string(event.competitors[1]), create_score_summary(event)))