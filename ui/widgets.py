from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle
from kivy.core.window import Window
from kivy_garden.graph import Graph, MeshLinePlot
import psutil
import math
import subprocess
import os
import platform
import datetime
import csv
import time

# --- COLOR CONSTANTS ---
COLOR_DOWN = [0, 1, 0, 1]       # Green
COLOR_UP   = [0.2, 0.8, 1, 1]   # Bright Sky Blue
COLOR_TEXT = [1, 1, 1, 1]       # White

# =========================
#   CUSTOM HOVER BUTTON
# =========================
class HoverButton(Button):
    """A button that shows a faint highlight on hover."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''  # Remove default Kivy background image
        self.background_color = (0, 0, 0, 0)  # Start transparent
        # A faint, transparent grey for the hover effect
        self.hover_color = (0.5, 0.5, 0.5, 0.2) 
        Window.bind(mouse_pos=self.on_mouse_pos)

    def on_mouse_pos(self, window, pos):
        if not self.get_root_window():
            return # Button not yet on screen
        
        # Check if the mouse is over this button widget
        if self.collide_point(*self.to_widget(*pos)):
            self.background_color = self.hover_color
        else:
            self.background_color = (0, 0, 0, 0)

# =========================
#   1. TRAFFIC GRAPH
# =========================
class TrafficGraph(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.graph = Graph(
            xlabel='Time (Seconds)', ylabel='Speed (KB/s)',
            x_ticks_minor=0, x_ticks_major=10, y_ticks_major=100,
            y_grid_label=True, x_grid_label=True, padding=5,
            x_grid=True, y_grid=True, xmin=0, xmax=60, ymin=0, ymax=100,
            label_options={'color': [1, 1, 1, 1], 'bold': True}
        )
        # Added line_width=2 for thicker, more visible lines
        self.plot_down = MeshLinePlot(color=COLOR_DOWN, line_width=2)
        self.plot_up = MeshLinePlot(color=COLOR_UP, line_width=2)
        self.graph.add_plot(self.plot_down)
        self.graph.add_plot(self.plot_up)
        self.add_widget(self.graph)
        self.points_down = []
        self.points_up = []

    def update_graph(self, down_val, up_val):
        current_x = len(self.points_down)
        self.points_down.append((current_x, down_val))
        self.points_up.append((current_x, up_val))

        if len(self.points_down) > 60:
            self.points_down.pop(0)
            self.points_up.pop(0)
            self.points_down = [(x - 1, y) for x, y in self.points_down]
            self.points_up = [(x - 1, y) for x, y in self.points_up]

        max_v = max(
            max([y for x, y in self.points_down] or [0]), 
            max([y for x, y in self.points_up] or [0])
        )
        
        target_ymax = max(100, math.ceil(max_v / 100) * 100)
        self.graph.ymax = int(target_ymax)
        self.graph.y_ticks_major = int(target_ymax / 4)
        
        self.plot_down.points = self.points_down
        self.plot_up.points = self.points_up


# =========================
#   2. APP GRAPH POPUP
# =========================
class AppGraphPopup(ModalView):
    def __init__(self, app_name, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.9, 0.7)
        self.auto_dismiss = True
        
        layout = BoxLayout(orientation='vertical', padding=10)
        header = BoxLayout(size_hint_y=None, height=dp(30))
        header.add_widget(Label(text=f"Traffic: {app_name}", bold=True, font_size='18sp'))
        close_btn = Button(text="Close", size_hint_x=None, width=100)
        close_btn.bind(on_release=self.dismiss)
        header.add_widget(close_btn)
        
        layout.add_widget(header)
        self.graph_widget = TrafficGraph()
        layout.add_widget(self.graph_widget)
        self.add_widget(layout)

    def update(self, down, up):
        self.graph_widget.update_graph(down, up)


# =========================
#   3. TABLE HEADER
# =========================
class TableHeader(BoxLayout):
    def update_icons(self, sort_key, sort_desc):
        """Updates header text to show correct arrow on the active column."""
        # 1. Reset all labels base text
        self.btn_name.text = "APPLICATION"
        self.btn_down.text = "DOWNLOAD"
        self.btn_up.text = "UPLOAD"

        # 2. Determine arrow symbol
        arrow = " ▼" if sort_desc else " ▲"

        # 3. Append arrow to the active column's button text
        if sort_key == 'name':
            self.btn_name.text += arrow
        elif sort_key == 'download':
            self.btn_down.text += arrow
        elif sort_key == 'upload':
            self.btn_up.text += arrow

    def __init__(self, sort_callback, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(40)
        self.padding = (dp(10), 0)
        
        # Helper to create our new HoverButtons
        def create_header_btn(text, key, color, size_x):
            btn = HoverButton( 
                text=text, 
                size_hint_x=size_x, 
                color=color,
                bold=True
            )
            btn.bind(on_release=lambda x: sort_callback(key))
            return btn

        # Keep references to the buttons so we can change their text later
        self.btn_name = create_header_btn("APPLICATION", 'name', [1,1,0,1], 0.5)
        self.btn_down = create_header_btn("DOWNLOAD", 'download', COLOR_DOWN, 0.25)
        self.btn_up = create_header_btn("UPLOAD", 'upload', COLOR_UP, 0.25)

        self.add_widget(self.btn_name)
        self.add_widget(self.btn_down)
        self.add_widget(self.btn_up)


# =========================
#   4. APP ROW
# =========================
class AppRow(BoxLayout):
    def __init__(self, app_name, **kwargs):
        super().__init__(**kwargs)
        self.app_name = app_name
        self.size_hint_y = None
        self.height = dp(40)
        self.padding = (dp(10), 0)
        self.popup = None

        # --- ADD TABLE SEPARATOR LINE ---
        with self.canvas.before:
            Color(0.3, 0.3, 0.3, 1) # Subtle dark grey for the line
            # Create a 1-pixel high rectangle at the bottom of the row
            self.rect = Rectangle(size=(self.width, 1), pos=(self.x, self.y))
        # Bind to size/pos changes so the line stretches with the row
        self.bind(pos=self.update_rect, size=self.update_rect)

        self.lbl_name = Label(
            text=app_name, 
            size_hint_x=0.5, 
            halign='left', 
            valign='middle',
            shorten=True,
            color=COLOR_TEXT
        )
        self.lbl_name.bind(size=self.lbl_name.setter('text_size'))
        self.add_widget(self.lbl_name)

        self.lbl_down = Label(text="0.00", size_hint_x=0.25, color=COLOR_DOWN)
        self.add_widget(self.lbl_down)

        self.lbl_up = Label(text="0.00", size_hint_x=0.25, color=COLOR_UP)
        self.add_widget(self.lbl_up)

        self.dropdown = self._create_dropdown()

    def update_rect(self, *args):
        """Keeps the separator line positioned correctly."""
        self.rect.pos = self.pos
        self.rect.size = (self.width, 1)

    def update_data(self, down, up):
        self.lbl_down.text = f"{down:.2f} KB/s"
        self.lbl_up.text = f"{up:.2f} KB/s"
        if self.popup and self.popup.parent:
            self.popup.update(down, up)

    def _create_dropdown(self):
        dropdown = DropDown(auto_width=False, width=dp(160))
        def add_item(text, cb):
            btn = Button(text=text, size_hint_y=None, height=dp(30), font_size="13sp")
            btn.bind(on_release=lambda *_: (cb(), dropdown.dismiss()))
            dropdown.add_widget(btn)
        
        add_item("Show Graph", self.open_graph)
        add_item("Close App", self.close_app)
        return dropdown

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and touch.button == "right":
            self.dropdown.open(self)
            return True
        return super().on_touch_down(touch)

    def open_graph(self):
        if not self.popup: self.popup = AppGraphPopup(self.app_name)
        self.popup.open()

    def close_app(self):
        for proc in psutil.process_iter(["name"]):
            try:
                if proc.info["name"] == self.app_name:
                    proc.terminate()
            except Exception: pass


# =========================
#   5. APP DASHBOARD
# =========================
class AppDashboard(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        
        # SORTING STATE
        self.sort_key = 'download'
        self.sort_desc = True

        # Create header and keep a reference to it
        self.header = TableHeader(self.change_sort)
        self.add_widget(self.header)
        
        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.rows_container = BoxLayout(orientation='vertical', size_hint_y=None)
        self.rows_container.bind(minimum_height=self.rows_container.setter('height'))
        self.scroll_view.add_widget(self.rows_container)
        self.add_widget(self.scroll_view)
        self.rows = {}

        # Set initial arrows on headers
        self.header.update_icons(self.sort_key, self.sort_desc)

    def change_sort(self, key):
        """Called when user clicks a header button"""
        if self.sort_key == key:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_key = key
            self.sort_desc = True
        
        # Update header icons immediately
        self.header.update_icons(self.sort_key, self.sort_desc)

    def update_apps(self, rates):
        current_apps = set(rates.keys())
        existing_apps = set(self.rows.keys())
        
        for app in existing_apps - current_apps:
            self.rows_container.remove_widget(self.rows[app])
            del self.rows[app]

        # --- SORTING LOGIC ---
        data_list = list(rates.items())
        if self.sort_key == 'name':
            data_list.sort(key=lambda x: x[0].lower(), reverse=not self.sort_desc)
        elif self.sort_key == 'download':
            data_list.sort(key=lambda x: x[1][0], reverse=self.sort_desc)
        elif self.sort_key == 'upload':
            data_list.sort(key=lambda x: x[1][1], reverse=self.sort_desc)

        # --- RENDER IN ORDER ---
        self.rows_container.clear_widgets()
        for app_name, (down, up) in data_list:
            if app_name not in self.rows:
                self.rows[app_name] = AppRow(app_name)
            
            self.rows[app_name].update_data(down, up)
            self.rows_container.add_widget(self.rows[app_name])

# ... (LogViewer classes remain unchanged)