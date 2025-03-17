from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QCheckBox, QHBoxLayout, QSpinBox,
                              QComboBox, QSlider, QPushButton)
from PySide6.QtCore import Qt
from datetime import datetime, timedelta

class ScheduleDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Schedule Posts")
        self.setFixedSize(400, 250)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addStretch()

        time_label = QLabel("Time")
        time_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        layout.addWidget(time_label)

        self.now_checkbox = QCheckBox("Now")
        self.now_checkbox.setChecked(True)
        self.now_checkbox.stateChanged.connect(self.toggle_time_inputs)
        layout.addWidget(self.now_checkbox)

        time_layout = QHBoxLayout()
        time_layout.setSpacing(2)

        self.hour_spinbox = QSpinBox()
        self.hour_spinbox.setRange(1, 12)
        self.hour_spinbox.setValue(12)
        self.hour_spinbox.setFixedSize(80, 60)
        self.hour_spinbox.setEnabled(False)
        time_layout.addWidget(self.hour_spinbox)

        time_layout.addWidget(QLabel(":"))

        self.minute_spinbox = QSpinBox()
        self.minute_spinbox.setRange(0, 59)
        self.minute_spinbox.setValue(0)
        self.minute_spinbox.setFixedSize(80, 60)
        self.minute_spinbox.setEnabled(False)
        time_layout.addWidget(self.minute_spinbox)

        time_layout.addWidget(QLabel(":"))

        self.second_spinbox = QSpinBox()
        self.second_spinbox.setRange(0, 59)
        self.second_spinbox.setValue(0)
        self.second_spinbox.setFixedSize(80, 60)
        self.second_spinbox.setEnabled(False)
        time_layout.addWidget(self.second_spinbox)

        self.ampm_combobox = QComboBox()
        self.ampm_combobox.addItems(["AM", "PM"])
        self.ampm_combobox.setFixedSize(80, 60)
        self.ampm_combobox.setEnabled(False)
        time_layout.addWidget(self.ampm_combobox)

        time_layout.addStretch()
        layout.addLayout(time_layout)

        interval_layout = QVBoxLayout()
        interval_layout.addStretch()

        interval_label = QLabel("Set Interval")
        interval_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        interval_layout.addWidget(interval_label)

        interval_input_layout = QHBoxLayout()
        interval_input_layout.addStretch()
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setRange(1, 60)
        self.interval_spinbox.setValue(1)
        self.interval_spinbox.setFixedSize(100, 60)
        self.interval_spinbox.valueChanged.connect(self.update_slider)
        interval_input_layout.addWidget(self.interval_spinbox)
        interval_input_layout.addStretch()
        interval_layout.addLayout(interval_input_layout)

        self.interval_slider = QSlider(Qt.Horizontal)
        self.interval_slider.setRange(1, 60)
        self.interval_slider.setValue(1)
        self.interval_slider.setFixedHeight(30)
        interval_layout.addWidget(self.interval_slider)

        interval_layout.addStretch()
        layout.addLayout(interval_layout)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def toggle_time_inputs(self):
        is_enabled = not self.now_checkbox.isChecked()
        self.hour_spinbox.setEnabled(is_enabled)
        self.minute_spinbox.setEnabled(is_enabled)
        self.second_spinbox.setEnabled(is_enabled)
        self.ampm_combobox.setEnabled(is_enabled)

    def update_slider(self):
        self.interval_slider.setValue(self.interval_spinbox.value())

    def update_spinbox(self):
        self.interval_spinbox.setValue(self.interval_slider.value())

    def get_schedule_time(self):
        if self.now_checkbox.isChecked():
            return datetime.now()
        
        hour = self.hour_spinbox.value()
        minute = self.minute_spinbox.value()
        second = self.second_spinbox.value()
        ampm = self.ampm_combobox.currentText()

        if ampm == "PM" and hour != 12:
            hour += 12
        elif ampm == "AM" and hour == 12:
            hour = 0

        now = datetime.now()
        schedule_time = datetime(now.year, now.month, now.day, hour, minute, second)

        if schedule_time < now:
            schedule_time += timedelta(days=1)

        return schedule_time

    def get_interval(self):
        return self.interval_spinbox.value()