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
            ch_offset.setRange(-5.0, 5.0)       # Range in divisions
            ch_offset.setSingleStep(0.1)        # Step in divisions
            ch_offset.setSuffix(" div")         # Update unit display
            
            ch_layout.addRow(f"Channel {i+1}:", ch_enable)
            ch_layout.addRow("  Volts/Div:", ch_volts_div)
            ch_layout.addRow("  Position:", ch_offset)
            
            widgets = {'enable': ch_enable, 'volts_div': ch_volts_div, 'position': ch_offset}
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
        self.h_time_div.addItems(["1s", "400ms", "200ms", "100ms", "40ms", "1ms", "400us", "100us", "1us", "400ns", "200ns", "100ns", "40ns", "20ns", "10ns"])
        self.h_offset = QDoubleSpinBox()
        self.h_offset.setRange(-10.0, 10.0)
        self.h_offset.setSuffix(" s")
        h_layout.addRow("Time/Div:", self.h_time_div)
        h_layout.addRow("Position:", self.h_offset)
        h_groupbox.setLayout(h_layout)
        main_layout.addWidget(h_groupbox)
        self.h_time_div.currentIndexChanged.connect(self._update_horizontal_controls)
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

        self._update_horizontal_controls()
        self._on_value_changed()

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
                'volts_div': self._parse_scale_value(self.ch_widgets[i]['volts_div'].currentText()),
                'position': self.ch_widgets[i]['position'].value()
            }
            settings['channels'].append(ch_data)
        
        # Gather horizontal settings
        settings['horizontal'] = {
            'time_div': self._parse_scale_value(self.h_time_div.currentText()),
            'position': self.h_offset.value()
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

    def _parse_scale_value(self, value_str: str) -> float:
        """Parses a string like "500mV" or "10us" into a float in base units."""
        value_str = value_str.strip().lower()
        try:
            if 'mv' in value_str: return float(value_str.replace('mv', '')) * 1e-3
            elif 'v' in value_str: return float(value_str.replace('v', '')) * 1e-0
            elif 'ms' in value_str: return float(value_str.replace('ms', '')) * 1e-3
            elif 'us' in value_str: return float(value_str.replace('us', '')) * 1e-6
            elif 'ns' in value_str: return float(value_str.replace('ns', '')) * 1e-9
            elif 's' in value_str: return float(value_str.replace('s', ''))
            return float(value_str)
        except (ValueError, TypeError):
            return 0.0 # Return a safe default

    @Slot()
    def _update_horizontal_controls(self):
        """Updates the horizontal offset range and step based on its Time/Div."""
        scale_str = self.h_time_div.currentText()
        scale_val = self._parse_scale_value(scale_str)

        if scale_val > 0:
            # Set range to be 5x the scale (e.g., 5 divisions left/right)
            offset_range = scale_val * 5
            self.h_offset.setRange(-offset_range, offset_range)

            # Set step to be 1/10th of the scale
            step = scale_val / 10.0
            self.h_offset.setSingleStep(step)

        # Trigger a general update to emit the settings
        self._on_value_changed()