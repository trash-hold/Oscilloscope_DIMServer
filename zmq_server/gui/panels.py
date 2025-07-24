from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QCheckBox, QComboBox, QDoubleSpinBox, QGroupBox 
)
from PySide6.QtCore import Signal, Slot
from gui.widgets import ChannelControls, HorizontalControls, TriggerControls

class ControlPanel(QWidget):
    settings_changed = Signal(dict)

    def __init__(self, device_config: dict, parent=None):
        super().__init__(parent)
        
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
            ch_widget.enable.stateChanged.connect(self._on_value_changed)
            ch_widget.volts_div.currentIndexChanged.connect(self._on_value_changed)
            ch_widget.offset.editingFinished.connect(self._on_value_changed)
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

        self.h_widget.time_div.currentIndexChanged.connect(self._update_horizontal_controls)
        self.h_widget.offset.editingFinished.connect(self._on_value_changed)
        self.t_widget.source.currentIndexChanged.connect(self._on_value_changed)
        self.t_widget.slope.currentIndexChanged.connect(self._on_value_changed)
        self.t_widget.level.editingFinished.connect(self._on_value_changed)

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

    def set_enabled_controls(self, is_enabled: bool):
        for child in self.findChildren(QWidget):
            if isinstance(child, (QComboBox, QCheckBox, QDoubleSpinBox)):
                child.setEnabled(is_enabled)