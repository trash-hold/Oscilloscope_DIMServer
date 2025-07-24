from PySide6.QtWidgets import (
    QWidget, QCheckBox, QFormLayout, QComboBox, QDoubleSpinBox 
)

from PySide6.QtCore import Signal, Slot

class ChannelControls(QWidget):
    settings_changed = Signal()
    def __init__(self, channel_num: int, v_scales: list, parent=None):
        super().__init__(parent)
        self.channel_num = channel_num
        
        # Layout
        layout = QFormLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)

        self.enable = QCheckBox("Enabled")
        self.volts_div = QComboBox()
        self.volts_div.addItems(v_scales)
        self.offset = QDoubleSpinBox()
        self.offset.setRange(-5.0, 5.0)
        self.offset.setSingleStep(0.1)
        self.offset.setSuffix(" div")

        layout.addRow(f"Channel {self.channel_num}:", self.enable)
        layout.addRow("  Volts/Div:", self.volts_div)
        layout.addRow("  Position:", self.offset)

        # Connecting signals
        self.enable.stateChanged.connect(self._emit_change_signal)
        self.volts_div.currentIndexChanged.connect(self._emit_change_signal)
        self.offset.editingFinished.connect(self._emit_change_signal)

    def _parse_value_with_unit(self, value_str: str) -> float:
        """
        Parses a string with units (mV, V) into a float value in Volts.
        """
        value_str = value_str.strip().lower()
        try:
            # Check for the more specific 'mv' unit first.
            if 'mv' in value_str:
                numeric_part = value_str.replace('mv', '')
                # If the numeric part is empty (e.g., "mv"), default to 1.0.
                value = float(numeric_part) if numeric_part else 1.0
                return value * 1e-3
            # Use elif for mutually exclusive checks.
            elif 'v' in value_str:
                numeric_part = value_str.replace('v', '')
                # If the numeric part is empty (e.g., "V"), default to 1.0.
                value = float(numeric_part) if numeric_part else 1.0
                return value
            
            # Fallback for values with no units.
            return float(value_str)
        except (ValueError, TypeError):
            # If any parsing fails, return 0.0 to prevent crashes.
            return 0.0

    def get_settings(self) -> dict:
        """Parses and calculates its own settings, returning final values."""
        volts_per_div = self._parse_value_with_unit(self.volts_div.currentText())
        offset_in_divs = self.offset.value()
        offset_in_volts = offset_in_divs * volts_per_div
        return {
            'enabled': self.enable.isChecked(),
            'volts_div': volts_per_div,
            'position': offset_in_volts
        }
    
    @Slot()
    def _emit_change_signal(self):
        """Private slot to emit the public signal."""
        self.settings_changed.emit()

class HorizontalControls(QWidget):
    settings_changed = Signal()

    def __init__(self, h_scales: list, parent=None):
        super().__init__(parent)

        # Layout
        layout = QFormLayout()
        self.setLayout(layout)

        layout.setContentsMargins(0, 0, 0, 0)

        self.time_div = QComboBox()
        self.time_div.addItems(h_scales)
        self.offset = QDoubleSpinBox()
        self.offset.setSuffix(" s")
        
        layout.addRow("Time/Div:", self.time_div)
        layout.addRow("Offset:", self.offset)

        # Connect signals
        self.time_div.currentIndexChanged.connect(self._emit_change_signal)
        self.offset.editingFinished.connect(self._emit_change_signal)

    def _parse_value_with_unit(self, value_str: str) -> float:
        value_str = value_str.strip().lower()
        try:
            if 'ms' in value_str: return float(value_str.replace('ms', '')) * 1e-3
            elif 'us' in value_str: return float(value_str.replace('us', '')) * 1e-6
            elif 'ns' in value_str: return float(value_str.replace('ns', '')) * 1e-9
            elif 's' in value_str: return float(value_str.replace('s', ''))
            return float(value_str)
        except (ValueError, TypeError): return 0.0

    def get_settings(self) -> dict:
        """Parses its own settings and returns final values."""
        return {
            'time_div': self._parse_value_with_unit(self.time_div.currentText()),
            'position': self.offset.value()
        }
    
    def update_offset_controls(self):
        """Updates the offset range based on the current time scale."""
        scale_val = self._parse_value_with_unit(self.time_div.currentText())
        if scale_val > 0:
            self.offset.setRange(-scale_val * 5, scale_val * 5)
            self.offset.setSingleStep(scale_val / 10.0)


    @Slot()
    def _emit_change_signal(self):
        self.settings_changed.emit()

class TriggerControls(QWidget):
    settings_changed = Signal()

    def __init__(self, sources: list, slopes: list, parent=None):
        super().__init__(parent)

        # Layout
        layout = QFormLayout()
        self.setLayout(layout)

        layout.setContentsMargins(0, 0, 0, 0)
        self.source = QComboBox()
        self.source.addItems(sources)
        self.level = QDoubleSpinBox()
        self.level.setRange(-10.0, 10.0)
        self.level.setSuffix(" V")
        self.slope = QComboBox()
        self.slope.addItems(slopes)
        layout.addRow("Source:", self.source)
        layout.addRow("Level:", self.level)
        layout.addRow("Slope:", self.slope)

        # Connecting signals
        self.source.currentIndexChanged.connect(self._emit_change_signal)
        self.slope.currentIndexChanged.connect(self._emit_change_signal)
        self.level.editingFinished.connect(self._emit_change_signal)

    def get_settings(self) -> dict:
        return {'source': self.source.currentText(), 'level': self.level.value(), 'slope': self.slope.currentText()}
    

    @Slot()
    def _emit_change_signal(self):
        self.settings_changed.emit()
    
    