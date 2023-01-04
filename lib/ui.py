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
    set_name = QtCore.Signal(str)
    set_logo = QtCore.Signal(QtGui.QPixmap)
    set_logo_disabled = QtCore.Signal(bool)
    set_score = QtCore.Signal(str)
    set_score_stylesheet = QtCore.Signal(str)

    def __init__(self):
        super().__init__()
        
        self.local_image_path = None
        
        self.create_widgets()
        
    def create_widgets(self):
        self.name_label = QtWidgets.QLabel(alignment=QtCore.Qt.AlignCenter)
        self.name_label.setMaximumHeight(STANDARD_FONT_SIZE + (STANDARD_FONT_SIZE//8))
        self.addWidget(self.name_label)
        self.set_name.connect(self.name_label.setText)

        self.logo = QtWidgets.QLabel()
        self.logo.setMinimumSize(QtCore.QSize(150, 150))
        self.logo.installEventFilter(self)
        self.logo.setAlignment(QtCore.Qt.AlignCenter)
        self.addWidget(self.logo)
        self.set_logo.connect(self.logo.setPixmap)
        self.set_logo_disabled.connect(self.logo.setDisabled)
        
        self.score_label = QtWidgets.QLabel(alignment=QtCore.Qt.AlignCenter)
        self.score_label.setMaximumHeight(SCORE_FONT_SIZE + (STANDARD_FONT_SIZE//8))
        self.addWidget(self.score_label)
        self.set_score.connect(self.score_label.setText)
        self.set_score_stylesheet.connect(self.score_label.setStyleSheet)
        
    def update_image(self):
        if self.local_image_path:
            self.set_logo.emit(QtGui.QPixmap(self.local_image_path).scaled(self.logo.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        else:
            self.set_logo.emit(QtGui.QPixmap())
        
    def eventFilter(self, source, event):
        """We only use this function so we can ensure the image scales
        without losing the aspect ratio"""
        if source is self.logo and event.type() == QtCore.QEvent.Resize:
            self.update_image()

        return super().eventFilter(source, event)
    
    def show_team(self, team, event_started, event_ended):
        if not team:
            self.set_name.emit("")
            self.set_score.emit("")
            self.local_image_path = None
            self.update_image()
        else:
            image_cache.get_image_and_assign(team, self)
            
            if team.is_home:
                home_text = " (Home)"
            else:
                home_text = ""

            self.set_name.emit("{}{}".format(team.name, home_text))

            if event_started:
                self.set_score.emit(team.score)
            else:
                self.set_score.emit("")
            
            if event_ended and not team.winner:
                self.set_logo_disabled.emit(True)
            else:
                self.set_logo_disabled.emit(False)
            
            if event_ended and team.winner:
                font_weight = "bold"
            else:
                font_weight = "normal"

            self.set_score_stylesheet.emit("""
                font-weight: {};
                font-family: {};
                font-size: {}px;
                """.format(
                    font_weight,
                    FONT_FAMILY,
                    SCORE_FONT_SIZE
                ))

class SportsStatusUI(QtWidgets.QWidget):
    progress_changed = QtCore.Signal(int)
    set_scheduled_time_text = QtCore.Signal(str)
    set_game_time_text = QtCore.Signal(str)

    def __init__(self, debug=False):
        super().__init__()
        
        # Parameters
        self.debug = debug

        # Build
        self.create_widgets()
        self.create_threads()
        self.apply_style()

        # Initialization
        self.events = list()
        self.current_event_index = 0
        self.cycle_event_time = 0
        
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
        
        QProgressBar {{
            border-radius: 1px;
            padding: 0px;
            margin: 0px;
            border: none;
        }}
        
        QProgressBar::chunk {{
            background-color: #ffffff;
        }}
        """.format(
            FONT_FAMILY,
            STANDARD_FONT_SIZE
        ))

        self.setCursor(QtCore.Qt.BlankCursor)

    def create_widgets(self):
        primary_layout = QtWidgets.QVBoxLayout(self)

        self.scheduled_time_label = QtWidgets.QLabel(alignment=QtCore.Qt.AlignCenter)
        self.scheduled_time_label.setMaximumHeight(STANDARD_FONT_SIZE)
        self.set_scheduled_time_text.connect(self.scheduled_time_label.setText)
        primary_layout.addWidget(self.scheduled_time_label)

        logos_layout = self.create_logo_widgets()
        primary_layout.addLayout(logos_layout)
        
        self.game_time_label = QtWidgets.QLabel(alignment=QtCore.Qt.AlignCenter)
        self.game_time_label.setMaximumHeight(STANDARD_FONT_SIZE)
        self.set_game_time_text.connect(self.game_time_label.setText)
        primary_layout.addWidget(self.game_time_label)
        
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(10)
        self.progress_changed.connect(self.progress_bar.setValue)
        primary_layout.addWidget(self.progress_bar)

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
            cycle_time = time.time()

            if cycle_time > self.cycle_event_time:
                self.show_next_event()
                
            start_time = self.cycle_event_time - self.config.event_cycle_period_seconds
            since_start_time = cycle_time - start_time
            progress_value = (since_start_time / self.config.event_cycle_period_seconds) * 100
            
            self.progress_changed.emit(progress_value)

            time.sleep(0.01)

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
            
        if len(self.events) > 1:
            self.progress_bar.setVisible(True)
        else:
            self.progress_bar.setVisible(False)

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
        self.cycle_event_time = time.time() + self.config.event_cycle_period_seconds

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
            self.set_scheduled_time_text.emit("No Games Today")
            
            self.team_1_layout.show_team(None, False, False)
            self.team_2_layout.show_team(None, False, False)

            self.set_game_time_text.emit("")
        else:
            if self.debug:
                print("Showing event: {}".format(event.name))

            event_day = event.datetime.date()

            current_datetime = datetime.datetime.now()
            current_day = current_datetime.date()
            
            day_difference = current_day - event_day
            
            print(event_day)
            print(current_day)
            print(day_difference)

            if abs(day_difference.days) == 1:
                if day_difference.days < 0:
                    day_string = "Tomorrow"
                else:
                    day_string = "Yesterday"
            elif day_difference.days == 0:
                day_string = ""
            else:
                day_string = event.datetime.strftime("%m/%d")

            time_of_day_string = event.datetime.strftime("%I:%M %p").lstrip("0")
                
            scheduled_time_string = "{} {}".format(day_string, time_of_day_string)

            self.set_scheduled_time_text.emit(scheduled_time_string)

            team_1 = event.competitors[0]
            team_2 = event.competitors[1]
            
            if not event.status.started:
                self.set_game_time_text.emit("")
            else:
                if not event.status.completed:
                    self.set_game_time_text.emit(event.status.display_clock)
                else:
                    self.set_game_time_text.emit(event.status.description)

            self.team_1_layout.show_team(team_1, event.status.started, event.status.completed)
            self.team_2_layout.show_team(team_2, event.status.started, event.status.completed)
