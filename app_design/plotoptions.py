import logging

logger = logging.getLogger(__name__)

class PlotOptions:
    def __init__(self, ax, graph_layout):
        self.ax = ax 
        self.graph_layout = graph_layout 

    def zoom_in(self, *args):
        logger.info("Zoom In Button Pressed!")
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        self.ax.set_xlim(xlim[0] * 0.8, xlim[1] * 0.8)
        self.ax.set_ylim(ylim[0] * 0.8, ylim[1] * 0.8)
        self.graph_layout.children[0].figure.canvas.draw()

    def zoom_out(self, *args):
        logger.info("Zoom Out Button Pressed!")
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        self.ax.set_xlim(xlim[0] / 0.8, xlim[1] / 0.8)
        self.ax.set_ylim(ylim[0] / 0.8, ylim[1] / 0.8)
        self.graph_layout.children[0].figure.canvas.draw()

    def pan_left(self, *args):
        logger.info("Pan Left Button Pressed!")
        xlim = self.ax.get_xlim()
        self.ax.set_xlim(xlim[0] - 1, xlim[1] - 1)
        self.graph_layout.children[0].figure.canvas.draw()

    def pan_right(self, *args):
        logger.info("Pan Right Button Pressed!")
        xlim = self.ax.get_xlim()
        self.ax.set_xlim(xlim[0] + 1, xlim[1] + 1)
        self.graph_layout.children[0].figure.canvas.draw()

    def reset_view(self, *args):
        logger.info("Reset Button Pressed!")
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(-1, 1)
        self.graph_layout.children[0].figure.canvas.draw()