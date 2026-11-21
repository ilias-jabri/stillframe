"""X11 desktop capture and the native selector."""

import math

import cairo
from gi.repository import Gdk, Gtk, Pango, PangoCairo, Wnck

from artwork import box, rounded


MODES = {
    "region": ("Rectangle", "Drag to select a rectangle"),
    "freehand": ("Freehand", "Draw an outline around what you want to capture"),
    "window": ("Window", "Click a window to capture it"),
    "screen": ("Fullscreen", "Capture all displays"),
}


def snapshot():
    root = Gdk.get_default_root_window()
    if root is None:
        raise RuntimeError("Desktop capture requires an X11 session.")
    width, height = root.get_width(), root.get_height()
    pixels = Gdk.pixbuf_get_from_window(root, 0, 0, width, height)
    if pixels is None:
        raise RuntimeError("The desktop could not be captured.")
    return pixels, width, height


def window_bounds(scale_x, scale_y):
    screen = Wnck.Screen.get_default()
    if screen is None:
        return []
    screen.force_update()
    workspace = screen.get_active_workspace()
    bounds = []
    for window in reversed(screen.get_windows_stacked()):
        if window.is_minimized() or window.get_window_type() == Wnck.WindowType.DESKTOP:
            continue
        if workspace and not window.is_visible_on_workspace(workspace):
            continue
        x, y, width, height = window.get_geometry()
        bounds.append((x / scale_x, y / scale_y, width / scale_x, height / scale_y))
    return bounds


def pixel_bounds(pixels, width, height, selection):
    scale_x, scale_y = pixels.get_width() / width, pixels.get_height() / height
    x, y, w, h = selection
    left = max(0, math.floor(x * scale_x))
    top = max(0, math.floor(y * scale_y))
    right = min(pixels.get_width(), math.ceil((x + w) * scale_x))
    bottom = min(pixels.get_height(), math.ceil((y + h) * scale_y))
    return left, top, max(0, right - left), max(0, bottom - top)


def extract(pixels, width, height, selection, outline=None):
    left, top, w, h = pixel_bounds(pixels, width, height, selection)
    if w < 2 or h < 2:
        return None
    if outline is None:
        return pixels.new_subpixbuf(left, top, w, h).copy()

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    cr = cairo.Context(surface)
    scale_x, scale_y = pixels.get_width() / width, pixels.get_height() / height
    for index, (x, y) in enumerate(outline):
        point = x * scale_x - left, y * scale_y - top
        if index == 0:
            cr.move_to(*point)
        else:
            cr.line_to(*point)
    cr.close_path()
    cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    cr.clip()
    Gdk.cairo_set_source_pixbuf(cr, pixels, -left, -top)
    cr.paint()
    return Gdk.pixbuf_get_from_surface(surface, 0, 0, w, h)


class Selector(Gtk.Window):
    def __init__(self, pixels, width, height, mode, complete, recording=False):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.pixels, self.width, self.height = pixels, width, height
        self.mode = mode
        self.complete = complete
        self.recording = recording
        self.points = []
        self.selection = None
        self.seat = None
        self.set_default_size(width, height)
        self.set_size_request(width, height)
        self.move(0, 0)
        self.stick()
        self.set_keep_above(True)
        self.set_accept_focus(True)
        self.set_app_paintable(True)

        display = self.get_display()
        _, pointer_x, pointer_y = display.get_default_seat().get_pointer().get_position()
        self.monitor = display.get_monitor_at_point(pointer_x, pointer_y).get_geometry()
        self.windows = (
            window_bounds(pixels.get_width() / width, pixels.get_height() / height)
            if mode == "window" else []
        )
        self.canvas = Gtk.DrawingArea()
        self.canvas.set_can_focus(True)
        self.canvas.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK
        )
        self.canvas.connect("draw", self.draw_overlay)
        self.canvas.connect("button-press-event", self.press)
        self.canvas.connect("motion-notify-event", self.motion)
        self.canvas.connect("button-release-event", self.release)
        self.connect("key-press-event", self.key)
        self.add(self.canvas)
        self.show_all()
        self.canvas.grab_focus()
        self.get_window().raise_()
        self.get_window().focus(Gdk.CURRENT_TIME)
        seat = display.get_default_seat()
        cursor = Gdk.Cursor.new_from_name(display, "crosshair" if mode != "window" else "pointer")
        self.canvas.get_window().set_cursor(cursor)
        status = seat.grab(self.get_window(), Gdk.SeatCapabilities.ALL_POINTING |
                           Gdk.SeatCapabilities.KEYBOARD, True, cursor)
        if status == Gdk.GrabStatus.SUCCESS:
            self.seat = seat
        if mode == "window":
            self.hover_window(pointer_x, pointer_y)

    def finish(self, selection=None, outline=None):
        if self.seat:
            self.seat.ungrab()
        self.destroy()
        self.complete(selection, outline)

    def key(self, _widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.finish()
            return True
        return False

    def point(self, event):
        return min(max(0, event.x), self.width), min(max(0, event.y), self.height)

    def hover_window(self, x, y):
        self.selection = next(
            (rect for rect in self.windows
             if rect[0] <= x < rect[0] + rect[2] and rect[1] <= y < rect[1] + rect[3]),
            None,
        )

    def press(self, _area, event):
        if event.button == 3:
            self.finish()
        elif event.button != 1:
            return False
        elif self.mode == "window":
            self.hover_window(*self.point(event))
            if self.selection:
                self.finish(self.selection)
        else:
            self.points = [self.point(event)]
            self.selection = None
        return True

    def motion(self, _area, event):
        point = self.point(event)
        if self.mode == "window":
            self.hover_window(*point)
        elif self.points:
            if self.mode == "freehand":
                if math.dist(self.points[-1], point) >= 2:
                    self.points.append(point)
            else:
                self.selection = box(self.points[0], point)
        self.canvas.queue_draw()
        return True

    def release(self, _area, event):
        if event.button != 1 or not self.points:
            return False
        end = self.point(event)
        if self.mode == "freehand":
            self.points.append(end)
            xs, ys = zip(*self.points)
            selection = min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
        else:
            selection = box(self.points[0], end)
        if selection[2] >= 3 and selection[3] >= 3:
            self.finish(selection, self.points if self.mode == "freehand" else None)
        else:
            self.points.clear()
            self.selection = None
            self.canvas.queue_draw()
        return True

    def selection_path(self, cr):
        if self.mode == "freehand" and len(self.points) >= 3:
            cr.move_to(*self.points[0])
            for point in self.points[1:]:
                cr.line_to(*point)
            cr.close_path()
        elif self.selection:
            cr.rectangle(*self.selection)

    def draw_overlay(self, _area, cr):
        cr.save()
        cr.scale(self.width / self.pixels.get_width(), self.height / self.pixels.get_height())
        Gdk.cairo_set_source_pixbuf(cr, self.pixels, 0, 0)
        cr.paint()
        cr.restore()

        cr.rectangle(0, 0, self.width, self.height)
        self.selection_path(cr)
        cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
        cr.set_source_rgba(0, 0, 0, .57)
        cr.fill()
        self.selection_path(cr)
        cr.set_source_rgb(.95, .95, .95)
        cr.set_line_width(1.4)
        cr.stroke()

        instruction = "Drag to select what to record" if self.recording else MODES[self.mode][1]
        self.pill(cr, instruction + "   ·   Esc to cancel", self.monitor.x + self.monitor.width / 2,
                  self.monitor.y + 14, centered=True)
        if self.selection and self.mode != "window":
            _, _, w, h = pixel_bounds(self.pixels, self.width, self.height, self.selection)
            x, y, _, _ = self.selection
            self.pill(cr, f"{w} × {h}", x, max(0, y - 26))
        return False

    @staticmethod
    def pill(cr, text, x, y, centered=False):
        layout = PangoCairo.create_layout(cr)
        layout.set_font_description(Pango.FontDescription("Sans Medium 10"))
        layout.set_text(text, -1)
        width, height = layout.get_pixel_size()
        if centered:
            x -= (width + 18) / 2
        rounded(cr, x, y, width + 18, height + 8, 5)
        cr.set_source_rgb(.11, .11, .11)
        cr.fill_preserve()
        cr.set_source_rgb(.40, .40, .40)
        cr.set_line_width(1)
        cr.stroke()
        cr.set_source_rgb(.94, .94, .94)
        cr.move_to(x + 9, y + 4)
        PangoCairo.show_layout(cr, layout)
