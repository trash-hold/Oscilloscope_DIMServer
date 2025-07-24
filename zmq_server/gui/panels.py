import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QComboBox, QDoubleSpinBox, QGroupBox, QTextEdit, QPushButton, QLabel, QSpinBox
)
from PySide6.QtCore import Signal, Slot
from gui.widgets import ChannelControls, HorizontalControls, TriggerControls

class ControlPanel(QWidget):
    settings_changed = Signal(dict)

    def __init__(self, device_config: dict, parent=None):
        super().__init__(parent)
        print("ControlPanel received device_config:", device_config) 

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        main_layout.setSpacing(15)

        self.channel_widgets = []
        
        ch_groupbox = QGroupBox("Channel Settings")
        ch_vbox_layout = QVBoxLayout()
        for i in range(device_config.get('channel_count', 0)):
            ch_widget = ChannelControls(i + 1, device_config['vertical_scales'])
            self.channel_widgets.append(ch_widget)
            ch_vbox_layout.addWidget(ch_widget)
            ch_widget.settings_changed.connect(self._on_value_changed) 

        ch_groupbox.setLayout(ch_vbox_layout)
        
        self.h_widget = HorizontalControls(device_config['horizontal_scales'])
        h_groupbox = QGroupBox("Horizontal Settings")
        h_vbox_layout = QVBoxLayout()
        h_vbox_layout.addWidget(self.h_widget)
        h_groupbox.setLayout(h_vbox_layout)
        
        self.t_widget = TriggerControls(device_config['trigger_sources'], device_config['trigger_slopes'])
        t_groupbox = QGroupBox("Trigger Settings")
        t_vbox_layout = QVBoxLayout()
        t_vbox_layout.addWidget(self.t_widget)
        t_groupbox.setLayout(t_vbox_layout)

        main_layout.addWidget(ch_groupbox)
        main_layout.addWidget(h_groupbox)
        main_layout.addWidget(t_groupbox)
        main_layout.addStretch()

        self.h_widget.settings_changed.connect(self._update_horizontal_controls)
        self.t_widget.settings_changed.connect(self._on_value_changed)

        self._update_horizontal_controls()

    @Slot()
    def _update_horizontal_controls(self):
        self.h_widget.update_offset_controls()
        self._on_value_changed()

    @Slot()
    def _on_value_changed(self):
        final_settings = {'channels': []}
        for ch_widget in self.channel_widgets:
            final_settings['channels'].append(ch_widget.get_settings())
        final_settings['horizontal'] = self.h_widget.get_settings()
        final_settings['trigger'] = self.t_widget.get_settings()
        self.settings_changed.emit(final_settings)

    @Slot(bool)
    def set_enabled_controls(self, is_enabled: bool):
        for child in self.findChildren(QWidget):
            if isinstance(child, (QComboBox, QCheckBox, QDoubleSpinBox)):
                child.setEnabled(not is_enabled)




class ActionPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # --- All the widgets from the right side of the GUI now live here ---
        self.status_label = QLabel("Ready.")
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.start_button = QPushButton("Start Continuous Measurement")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.timeout_label = QLabel("Acquisition Timeout (s):")
        self.timeout_spinbox = QSpinBox()
        self.timeout_spinbox.setRange(1, 3600)
        self.timeout_spinbox.setValue(10)
        self.continue_on_timeout_checkbox = QCheckBox("Continue measurement on timeout")

        # --- The layout logic also moves here ---
        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(self.log_view, 5)
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(self.timeout_label)
        timeout_layout.addWidget(self.timeout_spinbox)
        layout.addLayout(timeout_layout)
        layout.addWidget(self.continue_on_timeout_checkbox)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def log_message(self, message: str, color: str = "black"):
        timestamp = time.strftime('%H:%M:%S')
        colored_message = f'<font color="{color}">[{timestamp}] {message}</font>'
        self.log_view.append(colored_message)

    @Slot(str)
    def update_status(self, message: str):
        self.status_label.setText(f"Status: {message}")
        self.log_message(message, "blue")

    @Slot(bool)
    def set_running_state(self, is_running: bool):
        """A slot to control the enabled state of widgets in this panel."""
        self.start_button.setEnabled(not is_running)
        self.stop_button.setEnabled(is_running)
        self.timeout_spinbox.setEnabled(not is_running)
        self.continue_on_timeout_checkbox.setEnabled(not is_running)