from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QCheckBox,
    QGroupBox, QFormLayout, QComboBox, QDoubleSpinBox 
)
from PySide6.QtCore import Signal, Slot

class ControlPanel(QWidget):
    """A widget containing all oscilloscope configuration controls."""
    settings_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        # --- Channel Settings ---
        ch_groupbox = QGroupBox("Channel Settings")
        ch_layout = QFormLayout()
        
        self.ch_widgets = []
        for i in range(4):
            ch_enable = QCheckBox("Enabled")
            ch_volts_div = QComboBox()
            ch_volts_div.addItems(["1V", "500mV", "200mV", "100mV", "50mV", "20mV", "10mV", "5mV", "2mV", "1mV"])
            ch_offset = QDoubleSpinBox()
            ch_offset.setRange(-100.0, 100.0)
            ch_offset.setSuffix(" V")
            
            ch_layout.addRow(f"Channel {i+1}:", ch_enable)
            ch_layout.addRow("  Volts/Div:", ch_volts_div)
            ch_layout.addRow("  Offset:", ch_offset)
            
            widgets = {'enable': ch_enable, 'volts_div': ch_volts_div, 'offset': ch_offset}
            self.ch_widgets.append(widgets)

            # Connect signals
            ch_enable.stateChanged.connect(self._on_value_changed)
            ch_volts_div.currentIndexChanged.connect(self._on_value_changed)
            ch_offset.valueChanged.connect(self._on_value_changed)

        ch_groupbox.setLayout(ch_layout)
        main_layout.addWidget(ch_groupbox)

        # --- Horizontal Settings ---
        h_groupbox = QGroupBox("Horizontal Settings")
        h_layout = QFormLayout()
        self.h_time_div = QComboBox()
        self.h_time_div.addItems(["1s", "500ms", "200ms", "100ms", "50ms", "1ms", "500us", "100us"])
        self.h_offset = QDoubleSpinBox()
        self.h_offset.setRange(-10.0, 10.0)
        self.h_offset.setSuffix(" s")
        h_layout.addRow("Time/Div:", self.h_time_div)
        h_layout.addRow("Offset:", self.h_offset)
        h_groupbox.setLayout(h_layout)
        main_layout.addWidget(h_groupbox)
        self.h_time_div.currentIndexChanged.connect(self._on_value_changed)
        self.h_offset.valueChanged.connect(self._on_value_changed)

        # --- Trigger Settings ---
        t_groupbox = QGroupBox("Trigger Settings")
        t_layout = QFormLayout()
        self.t_source = QComboBox()
        self.t_source.addItems(["CH1", "CH2", "CH3", "CH4"])
        self.t_level = QDoubleSpinBox()
        self.t_level.setRange(-10.0, 10.0)
        self.t_level.setSuffix(" V")
        self.t_slope = QComboBox()
        self.t_slope.addItems(["Rising", "Falling"])
        t_layout.addRow("Source:", self.t_source)
        t_layout.addRow("Level:", self.t_level)
        t_layout.addRow("Slope:", self.t_slope)
        t_groupbox.setLayout(t_layout)
        main_layout.addWidget(t_groupbox)
        self.t_source.currentIndexChanged.connect(self._on_value_changed)
        self.t_level.valueChanged.connect(self._on_value_changed)
        self.t_slope.currentIndexChanged.connect(self._on_value_changed)

        main_layout.addStretch()

    @Slot()
    def _on_value_changed(self):
        """Gathers all settings and emits them."""
        settings = {
            'channels': [],
            'horizontal': {},
            'trigger': {}
        }
        # Gather channel settings
        for i in range(4):
            ch_data = {
                'enabled': self.ch_widgets[i]['enable'].isChecked(),
                'volts_div': self.ch_widgets[i]['volts_div'].currentText(),
                'offset': self.ch_widgets[i]['offset'].value()
            }
            settings['channels'].append(ch_data)
        
        # Gather horizontal settings
        settings['horizontal'] = {
            'time_div': self.h_time_div.currentText(),
            'offset': self.h_offset.value()
        }

        # Gather trigger settings
        settings['trigger'] = {
            'source': self.t_source.currentText(),
            'level': self.t_level.value(),
            'slope': self.t_slope.currentText()
        }
        
        self.settings_changed.emit(settings)

    def set_enabled_controls(self, is_enabled: bool):
        """Enable or disable all controls in the panel."""
        for child in self.findChildren(QWidget):
            if isinstance(child, (QComboBox, QCheckBox, QDoubleSpinBox)):
                child.setEnabled(is_enabled)