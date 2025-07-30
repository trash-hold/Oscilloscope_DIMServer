from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QTextEdit, QLabel
)
from PySide6.QtCore import Slot
from PySide6.QtGui import QColor

import pyqtgraph as pg
import numpy as np

class LogPanel(QWidget):
    """
    A panel dedicated to displaying the backend status and a stream of logs.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        # --- Widgets ---
        self.status_label = QLabel("Connecting to backend...")
        self.status_label.setStyleSheet("font-weight: bold; padding: 5px;")
        
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

        # --- Layout ---
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        log_groupbox = QGroupBox("Live Logs")
        log_layout = QVBoxLayout()
        log_layout.addWidget(self.log_view)
        log_groupbox.setLayout(log_layout)

        main_layout.addWidget(self.status_label)
        main_layout.addWidget(log_groupbox)

    @Slot(str)
    def log_message(self, message: str):
        """Appends a raw message to the log view, determining color by content."""
        color = "black"
        if "ERROR" in message or "CRITICAL" in message:
            color = "red"
        elif "WARNING" in message:
            color = "orange"
        elif "INFO" in message:
            color = "blue"
        
        colored_message = f'<font color="{color}">{message}</font>'
        self.log_view.append(colored_message)

    @Slot(str)
    def update_status(self, message: str):
        """Updates the main status label at the top of the panel."""
        self.status_label.setText(f"Backend Status: {message}")


class PlotPanel(QWidget):
    """
    A panel that holds and manages four separate plots for oscilloscope channels.
    """
            
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Use a dark background for plots
        pg.setConfigOption('background', 'k')
        pg.setConfigOption('foreground', 'w')

        # --- Layout ---
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        self.plots = {} # Dictionary to hold our plot data lines

        # --- Create 4 Plots ---
        for i in range(1, 5):
            # Create a plot widget
            plot_widget = pg.PlotWidget()
            plot_widget.setTitle(f"Channel {i}", color="w", size="10pt")
            plot_widget.setLabel('left', 'Voltage', units='V')
            plot_widget.setLabel('bottom', 'Time', units='s')
            plot_widget.showGrid(x=True, y=True, alpha=0.3)
            
            # Create a data line item with a yellow pen
            # We will update the data of this line item, which is very fast.
            data_line = plot_widget.plot(pen='y')

            # Store the data line for future updates
            self.plots[i] = data_line

            # Add the plot widget to our layout
            main_layout.addWidget(plot_widget)

    @Slot(dict)
    def update_waveforms(self, payload: dict):
        """
        Receives the combined payload and updates plots.
        The payload is a dict: {'time_increment': float, 'waveforms': dict}
        """
        for data_line in self.plots.values():
            data_line.clear()
            
        time_increment = float(payload.get('time_increment', 0.0))
        waveform_data = payload.get('waveforms', {})
        
        # We need a valid time increment to plot
        if time_increment <= 0:
            return

        for channel_num, data_line in self.plots.items():
            channel_key = str(channel_num)

            if channel_key in waveform_data:
                # --- THIS IS THE CRITICAL FIX ---
                # 1. Convert the incoming list of y-points to a NumPy array.
                #    Explicitly set the data type to float64 for robustness.
                y_points = np.array(waveform_data[channel_key], dtype=np.float64)

                # 2. Create the x-axis points as a NumPy array directly.
                #    This is more efficient than a list comprehension.
                x_points = np.arange(len(y_points)) * time_increment
                # --------------------------------

                # 3. Pass the NumPy arrays to setData.
                data_line.setData(x_points, y_points)
            else:
                data_line.clear()

    