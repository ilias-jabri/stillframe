"""Zoomable GTK canvas for editable screenshots."""

from dataclasses import replace
import math

import cairo
from gi.repository import Gdk, Gtk

from artwork import Mark, box


CANVAS_PADDING = 28
DEFAULT_TOOL = "pen"
COLORS = {
    "Coral": (.99, .37, .39),
    "Amber": (1, .77, .22),
    "Mint": (.39, .91, .69),
    "Sky": (.38, .68, 1),
    "Lilac": (.77, .57, 1),
    "White": (1, 1, 1),
    "Black": (0, 0, 0),
}

TOOLS = {
    "pen": ("Pen", "P"),
    "highlight": ("Highlighter", "H"),
    "eraser": ("Eraser", "D"),
    "arrow": ("Arrow", "A"),
    "rectangle": ("Rectangle", "R"),
    "ellipse": ("Ellipse", "E"),
    "text": ("Text", "T"),
    "redact": ("Redact", "B"),
    "crop": ("Crop", "X"),
}


class Canvas(Gtk.DrawingArea):
    def __init__(self, commit, zoom_by, text_at):
        super().__init__()
        self.commit = commit
        self.zoom_by = zoom_by
        self.text_at = text_at
        self.document = None
        self.preview = None
        self.erase_point = None
        self.erase_preview = None
        self.tool = DEFAULT_TOOL
        self.color = COLORS["Coral"]
        self.width = 5
        self.scale = 1
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.SCROLL_MASK |
                        Gdk.EventMask.SMOOTH_SCROLL_MASK)
        self.connect("draw", self.draw_image)
        self.connect("button-press-event", self.press)
        self.connect("motion-notify-event", self.motion)
        self.connect("button-release-event", self.release)
        self.connect("scroll-event", self.scroll)
        self.connect("realize", lambda *_: self.set_tool(self.tool))

    def set_tool(self, tool):
        self.tool = tool
        self.cancel_gesture()
        if self.get_realized():
            cursor = {"eraser": "cell", "text": "text"}.get(tool, "crosshair")
            self.get_window().set_cursor(Gdk.Cursor.new_from_name(self.get_display(), cursor))

    def set_document(self, document):
        self.document = document
        self.cancel_gesture()
        self.set_scale(self.scale)

    def cancel_gesture(self):
        self.preview = None
        self.erase_point = None
        self.erase_preview = None
        self.queue_draw()

    def set_scale(self, scale):
        self.scale = scale
        if self.document:
            width, height = self.document.size
            self.set_size_request(math.ceil(width * scale) + CANVAS_PADDING,
                                  math.ceil(height * scale) + CANVAS_PADDING)
        self.queue_draw()

    def origin(self):
        width, height = self.document.size
        return (round((self.get_allocated_width() - width * self.scale) / 2),
                round((self.get_allocated_height() - height * self.scale) / 2))

    def image_point(self, event, clamp=False):
        x, y = self.origin()
        width, height = self.document.size
        point = (event.x - x) / self.scale, (event.y - y) / self.scale
        if clamp:
            return min(max(point[0], 0), width), min(max(point[1], 0), height)
        if 0 <= point[0] < width and 0 <= point[1] < height:
            return point
        return None

    def draw_image(self, _canvas, cr):
        if not self.document:
            return False
        width, height = self.document.size
        x, y = self.origin()
        cr.set_source_rgba(0, 0, 0, .28)
        cr.rectangle(x - 3, y - 2, width * self.scale + 6, height * self.scale + 7)
        cr.fill()
        cr.translate(x, y)
        cr.scale(self.scale, self.scale)
        cr.rectangle(0, 0, width, height)
        cr.clip()
        if self.document.image.get_has_alpha():
            cr.set_source_rgb(.20, .20, .20)
            cr.paint()
            tile = max(8, 12 / self.scale)
            left, top, right, bottom = cr.clip_extents()
            cr.set_source_rgb(.26, .26, .26)
            for row in range(math.floor(top / tile), math.ceil(bottom / tile)):
                for col in range(math.floor(left / tile), math.ceil(right / tile)):
                    if (row + col) % 2:
                        cr.rectangle(col * tile, row * tile, tile, tile)
            cr.fill()
        crop = self.preview is not None and self.preview.tool == "crop"
        (self.erase_preview or self.document).draw(cr, None if crop else self.preview)
        if crop:
            bounds = box(self.preview.points[0], self.preview.points[-1])
            cr.rectangle(0, 0, width, height)
            cr.rectangle(*bounds)
            cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
            cr.set_source_rgba(0, 0, 0, .55)
            cr.fill()
            cr.rectangle(*bounds)
            cr.set_source_rgb(.93, .93, .93)
            cr.set_line_width(1 / self.scale)
            cr.set_dash([5 / self.scale, 4 / self.scale])
            cr.stroke()
        return False

    def press(self, _canvas, event):
        if event.button != 1 or not self.document:
            return False
        point = self.image_point(event)
        if point is None:
            return False
        if self.tool == "eraser":
            self.erase_point = point
            self.erase_preview = self.document.erase_along(point, point, self.scale)
            self.queue_draw()
            return True
        if self.tool == "text":
            text = self.text_at()
            if text:
                self.add_mark(Mark(self.tool, (point,), self.color, self.width, text))
            return True
        self.preview = Mark(self.tool, (point,), self.color, self.width)
        self.queue_draw()
        return True

    def motion(self, _canvas, event):
        if self.erase_point is not None:
            self.move_eraser(self.image_point(event, clamp=True))
            return True
        if not self.preview:
            return False
        point = self.image_point(event, clamp=True)
        self.update_preview(point)
        self.queue_draw()
        return True

    def update_preview(self, point):
        if self.tool in ("pen", "highlight"):
            if math.dist(self.preview.points[-1], point) >= .6:
                self.preview = replace(self.preview, points=(*self.preview.points, point))
        else:
            self.preview = replace(self.preview, points=(self.preview.points[0], point))

    def release(self, _canvas, event):
        if event.button != 1:
            return False
        if self.erase_point is not None:
            self.move_eraser(self.image_point(event, clamp=True))
            edited = self.erase_preview
            self.cancel_gesture()
            if edited is not self.document:
                self.commit(edited, False)
            return True
        if not self.preview:
            return False
        self.update_preview(self.image_point(event, clamp=True))
        mark = self.preview
        self.preview = None
        x, y, width, height = box(mark.points[0], mark.points[-1])
        if self.tool == "crop" and width >= 2 and height >= 2:
            left, top = math.floor(x), math.floor(y)
            bounds = left, top, math.ceil(x + width) - left, math.ceil(y + height) - top
            self.commit(self.document.cropped(bounds), True)
        elif self.tool in ("pen", "highlight") or (self.tool == "arrow" and (width or height)):
            self.add_mark(mark)
        elif self.tool != "crop" and width > 1 and height > 1:
            self.add_mark(mark)
        self.queue_draw()
        return True

    def move_eraser(self, point):
        if point != self.erase_point:
            self.erase_preview = self.erase_preview.erase_along(self.erase_point, point, self.scale)
            self.erase_point = point
            self.queue_draw()

    def add_mark(self, mark):
        self.commit(replace(self.document, marks=(*self.document.marks, mark)), False)

    def scroll(self, _canvas, event):
        if not self.document or not event.state & Gdk.ModifierType.CONTROL_MASK:
            return False
        if event.direction == Gdk.ScrollDirection.SMOOTH:
            _, _, dy = event.get_scroll_deltas()
        else:
            dy = -1 if event.direction == Gdk.ScrollDirection.UP else 1
        if dy:
            self.zoom_by(1 if dy < 0 else -1)
        return True
