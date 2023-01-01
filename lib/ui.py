import time
import datetime
import threading
from contextlib import suppress
from PySide6 import QtCore, QtWidgets, QtGui

from . import data as data_lib
from . import image_cache
from . import config as config_lib

STANDARD_FONT_SIZE = 50
SCORE_FONT_SIZE = 100
FONT_FAMILY = "Arial"

class TeamLayout(QtWidgets.QVBoxLayout):
    def __init__(self):
        super().__init__()
        
        self.local_image_path = None
        
        self.create_widgets()
        
    def create_widgets(self):
        self.name_label = QtWidgets.QLabel(alignment=QtCore.Qt.AlignCenter)
        self.name_label.setMaximumHeight(STANDARD_FONT_SIZE)
        self.addWidget(self.name_label)

        self.logo = QtWidgets.QLabel()
        self.logo.setMinimumSize(QtCore.QSize(150, 150))
        self.logo.installEventFilter(self)
        self.logo.setAlignment(QtCore.Qt.AlignCenter)
        self.addWidget(self.logo)
        
        self.score_label = QtWidgets.QLabel(alignment=QtCore.Qt.AlignCenter)
        self.score_label.setMaximumHeight(SCORE_FONT_SIZE)
        self.addWidget(self.score_label)
        
    def update_image(self):
        if self.local_image_path:
            self.logo.setPixmap(QtGui.QPixmap(self.local_image_path).scaled(self.logo.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        else:
            self.logo.setPixmap(QtGui.QPixmap())
        
    def eventFilter(self, source, event):
        """We only use this function so we can ensure the image scales
        without losing the aspect ratio"""
        if source is self.logo and event.type() == QtCore.QEvent.Resize:
            self.update_image()

        return super().eventFilter(source, event)
    
    def show_team(self, team, event_started, event_ended):
        if not team:
            self.name_label.setText("")
            self.score_label.setText("")
            self.local_image_path = None
            self.update_image()
        else:
            image_cache.get_image_and_assign(team, self)
            
            if team.is_home:
                home_text = " (Home)"
            else:
                home_text = ""

            self.name_label.setText("{}{}".format(team.name, home_text))

            if event_started:
                self.score_label.setText(team.score)
            else:
                self.score_label.setText("")
            
            if event_ended and not team.winner:
                self.logo.setDisabled(True)
            else:
                self.logo.setDisabled(False)
            
            if event_ended and team.winner:
                font_weight = "bold"
            else:
                font_weight = "normal"

            self.score_label.setStyleSheet("""
                font-weight: {};
                font-family: {};
                font-size: {}px;
                """.format(
                    font_weight,
                    FONT_FAMILY,
                    SCORE_FONT_SIZE
                ))

class SportsStatusUI(QtWidgets.QWidget):
    def __init__(self, debug=False):
        super().__init__()
        
        # Parameters
        self.debug = debug

        # Build
        self.apply_style()
        self.create_widgets()
        self.create_threads()

        # Initialization
        self.events = list()
        self.current_event_index = 0
        
        # Start with an empty list
        self.set_events(list())

        # Dependents
        self.config = config_lib.SportsStatusConfig()
        
        # Actually start running
        self.start_threads()
        self.showFullScreen()
    
    def apply_style(self):
        self.setStyleSheet("""
        * {{
            background-color: #0f0f0f;
        }}

        QLabel {{
            color: #ffffff;
            font-family: {};
            font-size: {}px;
        }}
        """.format(
            FONT_FAMILY,
            STANDARD_FONT_SIZE
        ))

    def create_widgets(self):
        primary_layout = QtWidgets.QVBoxLayout(self)

        self.scheduled_time_label = QtWidgets.QLabel(alignment=QtCore.Qt.AlignCenter)
        self.scheduled_time_label.setMaximumHeight(STANDARD_FONT_SIZE)
        primary_layout.addWidget(self.scheduled_time_label)

        logos_layout = self.create_logo_widgets()
        primary_layout.addLayout(logos_layout)
        
        self.game_time_label = QtWidgets.QLabel(alignment=QtCore.Qt.AlignCenter)
        self.game_time_label.setMaximumHeight(STANDARD_FONT_SIZE)
        primary_layout.addWidget(self.game_time_label)
        
        self.period_label = QtWidgets.QLabel(alignment=QtCore.Qt.AlignCenter)
        self.period_label.setMaximumHeight(STANDARD_FONT_SIZE)
        primary_layout.addWidget(self.period_label)

    def create_logo_widgets(self):
        teams_layout = QtWidgets.QHBoxLayout()

        self.team_1_layout = TeamLayout()
        teams_layout.addLayout(self.team_1_layout)

        self.team_2_layout = TeamLayout()
        teams_layout.addLayout(self.team_2_layout)
        
        return teams_layout

    def data_retreival_thread_work(self):
        while True:
            events = data_lib.query_filtered_data(self.config)
            filtered_events = self.config.filter_event_list(events)

            self.set_events(filtered_events)
            
            time.sleep(self.config.refresh_data_period_seconds)

    def cycle_events_thread_work(self):
        while True:
            self.show_next_event()

            time.sleep(self.config.event_cycle_period_seconds)

    def create_threads(self):
        self.data_thread = threading.Thread(target=self.data_retreival_thread_work, daemon=True)
        self.cycle_thread = threading.Thread(target=self.cycle_events_thread_work, daemon=True)
    
    def start_threads(self):
        self.data_thread.start()
        self.cycle_thread.start()
    
    def set_events(self, events):
        if len(self.events) > 0:
            previous_event_id = self.events[self.current_event_index].id
        else:
            previous_event_id = None

        self.events = events

        if self.debug:
            print("Assigned {} events to UI".format(len(self.events)))
        
        # Set to 0 in case we don't find the same event
        self.current_event_index = 0

        if previous_event_id:
            for index in range(len(self.events)):
                if self.events[index].id == previous_event_id:
                    self.current_event_index = index

        self.update_current_event()
    
    def show_previous_event(self):
        self.move_event(-1)

    def show_next_event(self):
        self.move_event(1)
        
    def move_event(self, move_count):
        if len(self.events) == 0:
            # Don't do anything for an empty event list
            return

        self.current_event_index = self.current_event_index + move_count
        
        if self.current_event_index < 0:
            self.current_event_index = len(self.events) + self.current_event_index
        elif self.current_event_index >= len(self.events):
            self.current_event_index = self.current_event_index % len(self.events)
            
        self.update_current_event()
        
    def update_current_event(self):
        if len(self.events) < 1:
            self.show_event(None)
        else:
            self.show_event(self.events[self.current_event_index])
    
    def show_event(self, event):
        if not event:
            self.scheduled_time_label.setText("No Games Today")
            
            self.team_1_layout.show_team(None, False, False)
            self.team_2_layout.show_team(None, False, False)

            self.game_time_label.setText("")
            self.period_label.setText("")
        else:
            if self.debug:
                print("Showing event: {}".format(event.name))

            time_of_day_string = event.datetime.strftime("%I:%M %p").lstrip("0")
            current_datetime = datetime.datetime.now()
            if event.datetime.date() > current_datetime.date():
                day_string = "Tomorrow "
            elif event.datetime.date() < current_datetime.date():
                day_string = "Yesterday "
            else:
                day_string = ""
                
            time_string = "{}{}".format(day_string, time_of_day_string)

            self.scheduled_time_label.setText(time_string)

            team_1 = event.competitors[0]
            team_2 = event.competitors[1]
            
            if not event.status.started:
                self.game_time_label.setText("")
                self.period_label.setText("")
            else:
                if not event.status.completed:
                    self.game_time_label.setText(event.status.display_clock)
                    # TODO: Make unique per sport
                    self.period_label.setText("Period: {}".format(event.status.period))
                else:
                    self.game_time_label.setText(event.status.description)
                    self.period_label.setText("")

            self.team_1_layout.show_team(team_1, event.status.started, event.status.completed)
            self.team_2_layout.show_team(team_2, event.status.started, event.status.completed)
