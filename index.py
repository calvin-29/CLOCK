# Import necessary modules from PyQt5, along with other standard Python libraries.
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout, 
                             QHBoxLayout, QDialog, QFormLayout, QLineEdit, QMessageBox, QListWidget, 
                             QStackedLayout, QComboBox, QSystemTrayIcon, QFileDialog, QMenu, QAction)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QIntValidator, QIcon
import sys, time, os, json, pygame

# Initialize the pygame mixer for sound playback.
pygame.mixer.init()

# Get the absolute path of the directory containing the script.
file_path = os.path.split(__file__)[0]

# Define the save folder path for configuration files. 
# This uses a cross-platform approach for application data.
save_folder = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "CCU Software", "Clock")

# Create the save folder if it doesn't already exist.
if not os.path.exists(save_folder):
    os.makedirs(save_folder, exist_ok=True)

# Define the default configuration.
configs = {
    "Alarms": [],
    "Sound": os.path.join(file_path, "data", "sound.wav")
}

# Try to load the configuration from the file.
try:
    with open(os.path.join(save_folder, "config.json"), "r") as f:
        configs = json.load(f)
# If the file is not found, create a new one with default settings.
except FileNotFoundError:
    with open(os.path.join(save_folder, "config.json"), "w") as f:
        json.dump(configs, f, indent=2)
# If the file is corrupted or empty, reset to the default configuration.
except json.decoder.JSONDecodeError:
      with open(os.path.join(save_folder, "config.json"), "w") as f:
        json.dump(configs, f, indent=2)

# A generic dialog class for getting user input.
class Dialog(QDialog):
    def __init__(dialog, parent, title, label, num_of_line_edits, combo, func):
        super().__init__(parent)
        dialog.resize(200, 100)
        dialog.setWindowTitle(title)
        form = QFormLayout(dialog)
        form.addRow(QLabel(label))
        hbox = QHBoxLayout()
        line_edits = []
        
        # Create the specified number of line edit widgets with an integer validator.
        for i in range(num_of_line_edits):
            edit = QLineEdit()
            edit.setValidator(QIntValidator())
            hbox.addWidget(edit)
            line_edits.append(edit)
        
        # Add a QComboBox for AM/PM selection if requested.
        if combo:
            combo = QComboBox()
            combo.addItems(["AM", "PM"])
            hbox.addWidget(combo)
        
        form.addRow(hbox)
        btn = QPushButton("Submit")
        
        # Connect the submit button to the provided function.
        if combo:
            btn.clicked.connect(lambda: func(dialog, line_edits, combo.currentText()))
        else:
            btn.clicked.connect(lambda: func(dialog, line_edits))
        
        form.addRow(btn)
        # Show the dialog as a modal window.
        dialog.exec_()

# Widget for displaying the current time.
class Clock(QWidget):
    def __init__(self):
        super().__init__()
        self.timer = QTimer(self)
        self.title = QLabel("Clock")
        self.time_label = QLabel("00:00:00 MM")
        
        # Connect the timer to the update_time method and start it.
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000) # Update every second (1000 milliseconds).
        self.initUI()
    
    def initUI(self):
        vbox = QVBoxLayout()
        vbox.addWidget(self.title)
        vbox.addStretch()
        self.time_label.setAlignment(Qt.AlignCenter)
        vbox.addWidget(self.time_label)
        vbox.addStretch()
        vbox.addWidget(QLabel("")) # Placeholder for consistent layout.
        self.setLayout(vbox)
    
    def update_time(self):
        # Format and display the current time in 12-hour format with AM/PM.
        self.time_label.setText(time.strftime("%I:%M:%S %p"))

# Widget for managing alarms.
class Alarm(QWidget):
    times = [] # Class-level list to store alarm times.
    def __init__(self):
        super().__init__()
        self.timer = QTimer()
        self.title = QLabel("Alarm")
        self.frame = QListWidget()
        
        # Buttons for adding, removing, and stopping alarms.
        self.add = QPushButton("+")
        self.add.setToolTip("Add Alarm")
        self.remove = QPushButton("-")
        self.remove.setToolTip("Remove Alarm")
        self.stop = QPushButton("Stop")
        self.stop.setToolTip("Stop Sound")
        
        # Load alarms from the config file into the list widget.
        for i in configs["Alarms"]:
            self.frame.addItem(f"{':'.join(i[0])} {i[1]}")
            self.times.append((i[0], i[1]))
            
        self.initUI()
    
    def initUI(self):
        btn_hbox = QHBoxLayout()
        btn_hbox.addWidget(self.add)
        btn_hbox.addWidget(self.remove)
        btn_hbox.addWidget(self.stop)

        vbox = QVBoxLayout()
        vbox.addWidget(self.title)
        vbox.addStretch()
        
        # Connect button signals to their respective methods.
        self.add.clicked.connect(lambda: Dialog(self, "Set Alarm", "Input Hour and Minute", 2, True, self.get_info))
        self.remove.clicked.connect(self.delete)
        self.stop.clicked.connect(pygame.mixer.stop)
        
        vbox.addWidget(self.frame)
        vbox.addLayout(btn_hbox)
        self.setLayout(vbox)

        # Start a timer to check for alarms every second.
        self.timer.timeout.connect(self.count)
        self.timer.start(1000)
    
    def delete(self):
        # Remove the selected alarm from the list and the saved config.
        if self.frame.currentItem():
            time_str = self.frame.currentItem().text()
            # Parse the time string back into a tuple for the 'times' list.
            n_time = (time_str[0:5].split(':'), time_str[6:])
            self.times.remove(n_time)
            
            # Re-populate the list widget to reflect the change.
            self.frame.clear()
            for i in self.times:
                self.frame.addItem(":".join(i[0])+ " " + i[1])
            
            # Save the updated alarms to the config file.
            self.window().save()
    
    def get_info(self, parent, line_edits, meridiem):
        input_data = []
        problem = False
        
        # Validate the user's input for hours and minutes.
        for count, i in enumerate(line_edits):
            if i.text() == "":
                input_data.append(f"{int('0'):02}")
            else:
                val = int(i.text())
                if count == 1 and val > 59: # Minutes check.
                    QMessageBox.warning(self, "Problem with input", "Minutes is greater than 59")
                    problem = True
                    break
                elif count == 0 and val > 12: # Hours check.
                    QMessageBox.warning(self, "Problem with input", "Hours is greater than 12")
                    problem = True
                    break
                else:
                    input_data.append(f"{val:02}")
        
        # If input is valid, add the new alarm and save the config.
        if not problem:
            parent.close()
            self.frame.addItem(":".join(input_data) + f" {meridiem}")
            self.times.append((input_data, meridiem))
            self.window().save()

    def play(self):
        pygame.mixer.stop()
        try:
            # Load and play the sound from the configured file.
            music = pygame.mixer.Sound(configs["Sound"])
            music.play()
        except FileNotFoundError:
            QMessageBox.warning(self, "The file is not found", "The file doesn't exist") 

    def count(self):
        # Check if any alarm time matches the current time.
        # The check only happens if no sound is currently playing.
        if not pygame.mixer.get_busy():
            for alarm_time, meridiem in self.times:
                # Get current time components.
                current_hour = int(time.strftime("%I"))
                current_minute = int(time.strftime("%M"))
                current_meridiem = time.strftime("%p")
                
                # Check for a match.
                if current_meridiem == meridiem and current_hour == int(alarm_time[0]) and current_minute == int(alarm_time[1]):
                    self.play()
                    self.window().tray_icon.showMessage("Alarm", "Alarm is going off!", QSystemTrayIcon.Warning, 5000)

# Widget for a countdown timer.
class Timer(QWidget):
    def __init__(self):
        super().__init__()
        self.timer = QTimer()
        self.title = QLabel("Timer")
        self.label = QLabel("00:00:00")
        
        # Buttons to set and stop the timer sound.
        self.btn = QPushButton("+")
        self.btn.setToolTip("Set timer")
        self.btn2 = QPushButton("Stop")
        self.btn2.setToolTip("Stop sound")
        self.remaining_seconds = 0
        
        self.initUI()
        
        # Connect the timer to the update_label method.
        self.timer.timeout.connect(self.update_label)

    def initUI(self):
        btn_hbox = QHBoxLayout()
        btn_hbox.addWidget(self.btn)
        btn_hbox.addWidget(self.btn2)

        vbox = QVBoxLayout()
        self.label.setAlignment(Qt.AlignCenter)
        
        # Connect buttons to their functions.
        self.btn.clicked.connect(lambda: Dialog(self, "Set Timer", "Input Hour, Minute, Second", 3, False, self.get_info))
        self.btn2.clicked.connect(pygame.mixer.stop)
        
        vbox.addWidget(self.title)
        vbox.addStretch()
        vbox.addWidget(self.label)
        vbox.addStretch()
        vbox.addLayout(btn_hbox)
        self.setLayout(vbox)

    def get_info(self, parent, line_edits):
        input_data = []
        problem = False
        
        # Validate the input for hours, minutes, and seconds.
        for count, i in enumerate(line_edits):
            if i.text() == "":
                input_data.append(int("0"))
            else:
                val = int(i.text())
                if (count == 1 or count == 2) and val > 59:
                    QMessageBox.warning(self, "Problem with input", "Minutes/Seconds cannot exceed 59")
                    problem = True
                    break
                else:
                    input_data.append(val)
                    
        # Calculate total seconds and validate the timer duration.
        self.remaining_seconds = input_data[0] * 3600 + input_data[1] * 60 + input_data[2]
        if self.remaining_seconds == 0:
            QMessageBox.warning(self, "Invalid Timer", "Timer duration must be greater than 0.")
            problem = True
            
        # If valid, start the timer.
        if not problem:
            parent.close()
            self.update_label()
            self.timer.start(1000)

    def update_label(self):
        # Decrement the timer and update the display.
        if self.remaining_seconds > 0:
            hrs = self.remaining_seconds // 3600 
            mins = (self.remaining_seconds % 3600) // 60
            secs = self.remaining_seconds % 60
            self.label.setText(f"{hrs:02}:{mins:02}:{secs:02}")
            self.remaining_seconds -= 1
        else:
            # When the timer finishes, stop it, reset the label, and play the sound.
            self.timer.stop()
            self.label.setText("00:00:00")
            if not pygame.mixer.get_busy():
                try:
                    music = pygame.mixer.Sound(configs["Sound"])
                except FileNotFoundError:
                    QMessageBox.warning(self, "The file is not found", "The file doesn't exist")
                else:
                    music.play()
                    self.window().tray_icon.showMessage("Timer", "Timer is done!", QSystemTrayIcon.Warning, 5000)

# Main application window.
class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setMaximumSize(600, 300)
        self.setMinimumSize(400, 200)
        self.setWindowTitle("Clock App")
        # Set the application icon.
        self.setWindowIcon(QIcon(os.path.join(file_path, "data", "logo.png")))
        self.windows = QWidget()

        # Initialize the three main widgets.
        self.clock = Clock()
        self.timer = Timer()
        self.alarm = Alarm()

        # Settings button.
        self.setting_btn = QPushButton(QIcon(os.path.join(file_path, "data", "set.png")), "", self.windows)
        self.setting_btn.setToolTip("Settings")
        self.setting_btn.setGeometry(10, 13, 30, 30)
        self.setting_btn.setObjectName("set")
        self.setting_btn.clicked.connect(self.settings)

        # QStackedLayout to manage the three main views (Clock, Timer, Alarm).
        self.stack = QStackedLayout()
        self.stack.addWidget(self.clock)
        self.stack.addWidget(self.timer)
        self.stack.addWidget(self.alarm)
        self.current_index = 0

        # Navigation buttons for the stacked layout.
        prev = QPushButton("<")
        prev.setToolTip("Previous")
        next = QPushButton(">")
        next.setToolTip("Next")
        prev.clicked.connect(self.prev)
        next.clicked.connect(self.next)

        # Main layout for the window.
        hbox = QHBoxLayout()
        hbox.addStretch()
        hbox.addWidget(prev)
        hbox.addStretch()
        stack_container = QWidget()
        stack_container.setLayout(self.stack)
        hbox.addWidget(stack_container)
        hbox.addStretch()
        hbox.addWidget(next)
        hbox.addStretch()

        self.windows.setLayout(hbox)
        self.setCentralWidget(self.windows)
        
        self.initStyle() # Apply custom stylesheet.
        self.initTray()  # Initialize system tray icon.
    
    def initTray(self):
        # Set up the system tray icon and its menu.
        self.tray_icon = QSystemTrayIcon(QIcon(os.path.join(file_path, "data", "logo.png")), self)
        self.tray_icon.setToolTip("Clock App")

        tray_menu = QMenu()
        restore_action = QAction("Restore", self)
        restore_action.triggered.connect(self.show)
        tray_menu.addAction(restore_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        # Connect a click on the tray icon to the trayClick method.
        self.tray_icon.activated.connect(self.trayClick)
        self.tray_icon.show()

    def trayClick(self, reason):
        # Toggle window visibility when the tray icon is clicked.
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show()
    
    def settings(self):
        # Function to open a file dialog for choosing a new sound file.
        def open_file():
            while True:
                try:
                    file = QFileDialog.getOpenFileName(self, 
                        caption="Choose a file", 
                        filter="Sound Files (*.mp3 *.wav *.ogg *.m4a)"
                    )
                except Exception:
                    continue
                else:
                    if file[0]: # Check if a file was selected.
                        configs["Sound"] = file[0]
                        # Update the label with the new sound file name.
                        name = os.path.split(configs["Sound"])[1]
                        song_name.setText(f"Current Sound is {name[:10]}..." if len(name) > 10 else f"Current Sound is {name}")
                        self.save_configs()
                    break

        # Create and display the settings dialog.
        app = QDialog(self)
        app.resize(200, 100)
        app.setWindowTitle("Settings")
        vbox = QVBoxLayout()
        title = QLabel("Change sound")
        title.setStyleSheet("font-weight: 700")
        title.setAlignment(Qt.AlignCenter)
        vbox.addWidget(title)
        
        # Display the current sound file name.
        name = os.path.split(configs["Sound"])[1]
        song_name = QLabel(f"Current Sound is {name[:10]}..." if len(name) > 10 else f"Current Sound is {name}")
        vbox.addWidget(song_name)
        
        open_btn = QPushButton("Choose...")
        open_btn.clicked.connect(open_file)
        vbox.addWidget(open_btn)
        app.setLayout(vbox)
        app.exec_()

    def prev(self):
        # Switch to the previous widget in the stacked layout.
        self.current_index = (self.current_index - 1) % self.stack.count()
        self.stack.setCurrentIndex(self.current_index)

    def next(self):
        # Switch to the next widget in the stacked layout.
        self.current_index = (self.current_index + 1) % self.stack.count()
        self.stack.setCurrentIndex(self.current_index)

    def save(self):
        # Update the alarm list in the global configs dictionary.
        configs["Alarms"] = Alarm.times
        # Save the updated configs to the file.
        self.save_configs()
    
    def save_configs(self):
        # A separate function for saving to prevent code duplication.
        try:
            with open(os.path.join(save_folder, "config.json"), "w") as f:
                json.dump(configs, f, indent=2)
        except FileNotFoundError:
            # Recreate the file if it's somehow missing.
            with open(os.path.join(save_folder, "config.json"), "w") as f:
                json.dump(configs, f, indent=2)

    def closeEvent(self, event):
        self.save()
        # Intercept the close event to hide the window to the system tray instead of exiting.
        event.ignore()
        self.hide()
        self.tray_icon.showMessage("Clock App", "App is still running in the tray.", QIcon("data/logo.png"), 3000)

    def initDarkStyle(self):
        # Apply a custom CSS stylesheet for a dark theme and consistent styling.
        self.setStyleSheet("""
            QWidget{
                font-family: Consolas;
                background-color: black;
                color: white
            }
            QPushButton {
                font-size: 18px;
                width: 40px;
                height: 20px;
                background-color: grey;
                border-radius: 10px;
                padding: 5px;
                color: black
            }
            QPushButton:hover{
                background-color: green
            }
            QLabel{
                font-size: 20px;
            }
            QDialog QLabel{
                font-size: 18px;
            }
            QLineEdit, QListWidget{
                font-size: 15px;
            }
            #set{
                background-color: black;
            }
            #set:hover{
                background-color: rgb(53, 53, 53);
            }
            QScrollBar{
                background-color: white;
                color: black
            }
            QComboBox{
                
            }
        """)

    def initLightStyle(self):
        # Apply a custom CSS stylesheet for a light theme and consistent styling.
        self.setStyleSheet("""
            QWidget{
                font-family: Consolas;
                background-color: white;
                color: black
            }
            QPushButton {
                font-size: 18px;
                width: 40px;
                height: 20px;
                background-color: grey;
                border-radius: 10px;
                padding: 5px;
                color: black
            }
            QPushButton:hover{
                background-color: green
            }
            QLabel{
                font-size: 20px;
            }
            QDialog QLabel{
                font-size: 18px;
            }
            QLineEdit, QListWidget{
                font-size: 15px;
            }
            #set{
                background-color: black;
            }
            #set:hover{
                background-color: rgb(53, 53, 53);
            }
            QScrollBar{
                background-color: white;
                color: black
            }
            QComboBox{
                font-size: 10px
            }
        """)

# Main function to run the application.
def main():
    app = QApplication(sys.argv)
    # Ensure the application stays running even when the main window is closed.
    app.setQuitOnLastWindowClosed(False)
    window = App()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()