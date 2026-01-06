from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button
from kivy.metrics import dp

# --- NEW IMPORTS FOR THE GRAPH ---
from kivy_garden.graph import Graph, MeshLinePlot
import psutil

# =========================
#   TRAFFIC GRAPH (UPDATED)
# =========================
class TrafficGraph(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        
        # 1. Create the Graph Object
        self.graph = Graph(
            xlabel='Time (Seconds)',     # X-Axis Title
            ylabel='Speed (KB/s)',       # Y-Axis Title
            x_ticks_minor=1,
            x_ticks_major=5,             # Show a number every 5 ticks
            y_ticks_major=10,            # Show a number every 10 KB/s
            y_grid_label=True,           # <--- THIS SHOWS THE NUMBERS ON Y-AXIS
            x_grid_label=True,           # <--- THIS SHOWS THE NUMBERS ON X-AXIS
            padding=5,
            x_grid=True,
            y_grid=True,
            xmin=0, xmax=50,             # 50 data points history
            ymin=0, ymax=100             # Initial max Y scale
        )

        # 2. Create the Plot (The green line)
        self.plot = MeshLinePlot(color=[0, 1, 0, 1])  # Green Line
        self.graph.add_plot(self.plot)
        self.add_widget(self.graph)

        # Internal storage
        self.points_list = []  # Stores (x, y) coordinates

    def update_graph(self, value):
        # 1. Add new value to list
        # We use a simple counter for X (0, 1, 2...)
        current_x = len(self.points_list)
        self.points_list.append((current_x, value))

        # 2. Keep only last 50 points (Scrolling effect)
        if len(self.points_list) > 50:
            self.points_list.pop(0)
            # Shift all X values back by 1 so the graph scrolls left
            self.points_list = [(x - 1, y) for x, y in self.points_list]

        # 3. Auto-Scale Y Axis (If speed goes above 100 KB/s, zoom out)
        if value > self.graph.ymax:
            self.graph.ymax = value * 1.2
            self.graph.y_ticks_major = int(self.graph.ymax / 5)

        # 4. Push data to graph
        self.plot.points = self.points_list


# =========================
#   APP ROW (UNCHANGED)
# =========================
class AppRow(Label):
    def __init__(self, app_name, **kwargs):
        super().__init__(**kwargs)

        self.app_name = app_name
        self.size_hint_y = None
        self.height = dp(28)
        self.halign = "left"
        self.valign = "middle"
        self.padding = (dp(10), 0)

        self.bind(size=self._update_text)
        self.dropdown = self._create_dropdown()

    def _update_text(self, *_):
        self.text_size = self.size

    def _create_dropdown(self):
        dropdown = DropDown(auto_width=False, width=dp(160))

        def add_item(text, callback):
            btn = Button(
                text=text,
                size_hint_y=None,
                height=dp(30),
                font_size="13sp"
            )
            btn.bind(on_release=lambda *_: (callback(), dropdown.dismiss()))
            dropdown.add_widget(btn)

        add_item("Information", self.show_info)
        add_item("Show Graph", self.show_graph)
        add_item("Close App", self.close_app)

        return dropdown

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and touch.button == "right":
            self.dropdown.open(self)
            return True
        return super().on_touch_down(touch)

    def show_info(self):
        from kivy.app import App
        App.get_running_app().show_app_info(self.app_name)

    def show_graph(self):
        from kivy.app import App
        App.get_running_app().show_app_graph(self.app_name)

    def close_app(self):
        for proc in psutil.process_iter(["name"]):
            try:
                if proc.info["name"] == self.app_name:
                    proc.terminate()
            except Exception:
                pass


# =========================
#   APP DASHBOARD (UNCHANGED)
# =========================
class AppDashboard(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.rows = {}

    def update_apps(self, rates):
        for app, (down, up) in rates.items():
            if app not in self.rows:
                row = AppRow(app)
                self.rows[app] = row
                self.add_widget(row)

            self.rows[app].text = (
                f"{app}  |  ⬇ {down:.2f} kbps  |  ⬆ {up:.2f} kbps"
            )