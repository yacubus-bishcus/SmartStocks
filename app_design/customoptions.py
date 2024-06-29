# Kivy Imported Modules
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.checkbox import CheckBox
from kivy.graphics import Color, Line, Rectangle
from kivy.uix.progressbar import ProgressBar
from kivy.uix.spinner import Spinner as LoadingSpinner
from watchdog.events import FileSystemEventHandler 

class BackgroundColorBoxLayout(BoxLayout):
    def __init__(self, **kwargs):
        super(BackgroundColorBoxLayout, self).__init__(**kwargs)
        with self.canvas.before:
            Color(0.68, 0.85, 0.90, 1)  # Light blue color
            self.rect = Rectangle(size=self.size, pos=self.pos)
            self.bind(size=self._update_rect, pos=self._update_rect)

    def _update_rect(self, instance, value):
        self.rect.size = instance.size
        self.rect.pos = instance.pos

class CustomCheckBox(BoxLayout):
    def __init__(self, **kwargs):
        super(CustomCheckBox, self).__init__(**kwargs)

        # Create the internal CheckBox widget
        self.checkbox = CheckBox()
        self.add_widget(self.checkbox)

        # Create the outline for the CheckBox
        with self.checkbox.canvas.before:
            Color(0, 0, 0, 1)  # Black color for the outline
            self.outline = Line(rectangle=(self.checkbox.x, self.checkbox.y, self.checkbox.width, self.checkbox.height), width=1)

        # Bind update_outline method to position and size changes of checkbox
        self.checkbox.bind(pos=self.update_outline, size=self.update_outline)

        # Example initial state
        self.active = False

    def update_outline(self, *args):
        self.outline.rectangle = (self.checkbox.x, self.checkbox.y, self.checkbox.width, self.checkbox.height)

    # Define the 'active' property
    def _get_active(self):
        return self.checkbox.active

    def _set_active(self, value):
        self.checkbox.active = value
        self.update_outline()  # Update outline when active state changes

    active = property(_get_active, _set_active)


# Define custom ProgressBar with increased thickness
class ThickerProgressBar(ProgressBar):
    def __init__(self, **kwargs):
        super(ThickerProgressBar, self).__init__(**kwargs)
        self.color = (0, 0.7, 1, 1)  # Progress bar color
        self.height = 20  # Adjust thickness of the progress bar
        self.opacity = 0
        # Create Rectangle and Color graphics instructions
        self.rect = Rectangle(pos=self.pos, size=(0, self.height))
        self.canvas.add(Color(*self.color))
        self.canvas.add(self.rect)

        # Bind size and position properties
        self.bind(pos=self.update_rect_pos)
        self.bind(size=self.update_rect_size)

        # Bind value change to update progress
        self.bind(value=self.update_rect)

    def update_rect(self, instance, value):
        # Update the size of the rectangle based on progress
        if self.max > 0:
            self.rect.size = (self.width * self.value_normalized, self.height)

    def update_rect_size(self, instance, value):
        # Update the size of the rectangle when the progress bar size changes
        if self.max > 0:
            self.rect.size = (self.width * self.value_normalized, self.height)

    def update_rect_pos(self, instance, value):
        # Update the position of the rectangle when the progress bar position changes
        self.rect.pos = self.pos

    def update_progress(self, current_iteration, total_iterations, current_screen='compare_stocks_output'):
        if current_iteration >= total_iterations:
            self.hide_loader()  # Hide the progress bar when task is complete
            self.manager.current = current_screen
            return

    def show_loader(self):
        self.opacity = 1

    def hide_loader(self):
        self.opacity = 0

class LoadingSpinner(ProgressBar):
    def __init__(self, **kwargs):
        super(LoadingSpinner, self).__init__(**kwargs)
        self.value = 0
        self.max = 100
        self.size_hint = (None, None)
        self.size = (350, 350)
        self.opacity = 0  # Initially hidden

class HotReloadHandler(FileSystemEventHandler):
    def __init__(self, reload_callback):
        self.reload_callback = reload_callback

    def on_modified(self, event):
        if event.src_path.endswith('.kv'):
            self.reload_callback()