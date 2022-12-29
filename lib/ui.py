import time
import threading
from contextlib import suppress
from PySide6 import QtCore, QtWidgets, QtGui

from . import data as data_lib
from . import image_cache

class TeamLayout(QtWidgets.QVBoxLayout):
    def __init__(self):
        super().__init__()
        
        self.local_image_path = None
        
        self.create_widgets()
        
    def create_widgets(self):
        self.name_label = QtWidgets.QLabel(alignment=QtCore.Qt.AlignCenter)
        self.name_label.setMaximumHeight(20)
        self.addWidget(self.name_label)

        self.logo = QtWidgets.QLabel()
        self.logo.setMinimumSize(QtCore.QSize(150, 150))
        self.logo.installEventFilter(self)
        self.logo.setAlignment(QtCore.Qt.AlignCenter)
        self.addWidget(self.logo)
        
        self.score_label = QtWidgets.QLabel(alignment=QtCore.Qt.AlignCenter)
        self.score_label.setStyleSheet("font-size: 40px")
        self.score_label.setMaximumHeight(40)
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
    
    def show_team(self, team, event_started):
        if not team:
            self.name_label.setText("")
            self.score_label.setText("")
            self.local_image_path = None
            self.update_image()
        else:
            image_cache.get_image_and_assign(team, self)
            self.name_label.setText(team.name)

            if event_started:
                self.score_label.setText(team.score)
            else:
                self.score_label.setText("")

class SportsStatusUI(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        
        self.events = list()

        self.apply_style()
        self.create_widgets()
        self.create_threads()

        # Start with an empty list
        self.set_events(list())
        
        self.showFullScreen()
    
    def apply_style(self):
        self.setStyleSheet("""
        * {
            background-color: #0f0f0f;
        }

        QLabel {
            color: #ffffff;
            font-family: Arial;
            font-size: 20px;
        }
        """)

    def create_widgets(self):
        primary_layout = QtWidgets.QVBoxLayout(self)

        self.scheduled_time_label = QtWidgets.QLabel(alignment=QtCore.Qt.AlignCenter)
        self.scheduled_time_label.setMaximumHeight(20)
        primary_layout.addWidget(self.scheduled_time_label)

        logos_layout = self.create_logo_widgets()
        primary_layout.addLayout(logos_layout)
        
        self.game_time_label = QtWidgets.QLabel(alignment=QtCore.Qt.AlignCenter)
        self.game_time_label.setMaximumHeight(20)
        primary_layout.addWidget(self.game_time_label)
        
        self.period_label = QtWidgets.QLabel(alignment=QtCore.Qt.AlignCenter)
        self.period_label.setMaximumHeight(20)
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
            data = data_lib.query_new_data()
            events = data.get_flattened_events()
            self.set_events(events)
            
            time.sleep(300)

    def cycle_events_thread_work(self):
        while True:
            self.show_next_event()

            time.sleep(10)

    def create_threads(self):
        self.data_thread = threading.Thread(target=self.data_retreival_thread_work, daemon=True)
        self.data_thread.start()
        
        self.cycle_thread = threading.Thread(target=self.cycle_events_thread_work, daemon=True)
        self.cycle_thread.start()
    
    def set_events(self, events):
        # TODO this should be more elegant so we don't just jump back to the start
        self.events = events
        self.current_event_index = 0

        if len(self.events) > 0:
            print("Assigned {} events to UI".format(len(self.events)))
            self.show_event(self.events[0])
        else:
            self.show_event(None)
    
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
            self.current_event_index = self.current_event_index - len(self.events) - 1
        
        self.show_event(self.events[self.current_event_index])
    
    def show_event(self, event):
        if not event:
            self.scheduled_time_label.setText("No Games Today")
            
            self.team_1_layout.show_team(None, False)
            self.team_2_layout.show_team(None, False)

            self.game_time_label.setText("")
            self.period_label.setText("")
        else:
            print("Showing event: {}".format(event.name))

            self.scheduled_time_label.setText(event.datetime.strftime("%I:%M %p"))

            team_1 = event.competitors[0]
            team_2 = event.competitors[1]
            
            if not event.status.started:
                self.team_1_layout.show_team(team_1, False)
                self.team_2_layout.show_team(team_2, False)
                
                self.game_time_label.setText("")
                self.period_label.setText("")
            else:
                self.team_1_layout.show_team(team_1, True)
                self.team_2_layout.show_team(team_2, True)

                if not event.status.completed:
                    self.game_time_label.setText(event.status.display_clock)
                    # TODO: Make unique per sport
                    self.period_label.setText("Period: {}".format(event.status.period))
                else:
                    self.game_time_label.setText(event.status.description)
                    self.period_label.setText("")