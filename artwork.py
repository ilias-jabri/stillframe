"""Local Cairo icons and image editing primitives."""

from dataclasses import dataclass, replace
import math
import re

import cairo
from gi.repository import Gdk, Pango, PangoCairo


ICONS = {
    "brand-mark": (
        "M9 4 L4 4 L4 9 M15 4 L20 4 L20 9 M4 15 L4 20 L9 20 M20 15 L20 20 L15 20 "
        "M7 15 L10.5 11.5 L13 14 L15 12 L18 15 M15 8.5 L16 8.5"
    ),
    "new": "M12 4 L12 20 M4 12 L20 12",
    "region": (
        "M9 3 L3 3 L3 9 M15 3 L21 3 L21 9 M3 15 L3 21 L9 21 M21 15 L21 21 L15 21 "
        "M10 12 L14 12 M12 10 L12 14"
    ),
    "freehand": (
        "M17 17 C13 20 5 19 4 14 C2 9 6 5 11 5 C16 4 21 7 21 11 "
        "C21 15 18 17 15 16 C12 15 13 12 15 12 C17 12 18 15 18 18 L20 21"
    ),
    "window": "M3 5 L21 5 L21 19 L3 19 Z M3 10 L21 10 M6 7.5 L7 7.5",
    "screen": "M3 4 L21 4 L21 16 L3 16 Z M12 16 L12 21 M7 21 L17 21",
    "timer": (
        "M9 3 L15 3 M12 3 L12 6 M12 9 L12 13 L16 13 M18 7 L20 5 "
        "M20 13.5 C20 18 16.5 21 12 21 C7.5 21 4 18 4 13.5 "
        "C4 9 7.5 6 12 6 C16.5 6 20 9 20 13.5 Z"
    ),
    "down": "M6 9 L12 15 L18 9",
    "open": "M3 19 L3 6 L9 6 L11 8 L20 8 L20 11 M3 19 L6 11 L22 11 L19 19 Z",
    "copy": "M9 8 L20 8 L20 21 L9 21 Z M5 16 L4 16 L4 3 L15 3 L15 4",
    "save": "M12 3 L12 14 M8 10 L12 14 L16 10 M4 15 L4 20 L20 20 L20 15",
    "pen": "M4 20 L6 14 L16 4 L20 8 L10 18 Z M13 7 L17 11",
    "highlight": "M5 20 L10 20 M6 15 L10 19 L15 15 L20 7 L16 3 L8 11 Z M8 11 L15 15",
    "eraser": "M4 14 L14 4 L21 11 L12 20 L8 20 L4 16 Z M8 10 L16 18 M12 20 L21 20",
    "arrow": "M4 20 L20 4 M11 4 L20 4 L20 13",
    "rectangle": "M3 5 L21 5 L21 19 L3 19 Z",
    "ellipse": "M21 12 C21 16 17 19 12 19 C7 19 3 16 3 12 C3 8 7 5 12 5 C17 5 21 8 21 12 Z",
    "text": "M4 7 L4 4 L20 4 L20 7 M12 4 L12 20 M8 20 L16 20",
    "redact": "M3 6 L21 6 L21 18 L3 18 Z M7 11 L17 11 L17 13 L7 13 Z",
    "crop": "M7 3 L7 17 L21 17 M3 7 L17 7 L17 21",
    "undo": "M9 4 L3 10 L9 16 M3 10 L15 10 C19 10 21 13 21 18",
    "redo": "M15 4 L21 10 L15 16 M21 10 L9 10 C5 10 3 13 3 18",
    "minus": "M5 12 L19 12",
    "settings": "M4 6 L20 6 M4 12 L20 12 M4 18 L20 18 M8 3 L8 9 M15 9 L15 15 M10 15 L10 21",
    "record": (
        "M21 12 C21 17 17 21 12 21 C7 21 3 17 3 12 C3 7 7 3 12 3 C17 3 21 7 21 12 Z "
        "M11 11 L13 11 L13 13 L11 13 Z"
    ),
    "stop": "M6 6 L18 6 L18 18 L6 18 Z M10 10 L14 10 L14 14 L10 14 Z",
}


def icon(cr, name, x, y, size):
    cr.save()
    cr.translate(x, y)
    cr.scale(size / 24, size / 24)
    cr.set_line_width(2)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    path = iter(re.findall(r"[MLCZ]|-?\d+(?:\.\d+)?", ICONS[name]))
    for command in path:
        if command == "M":
            cr.move_to(float(next(path)), float(next(path)))
        elif command == "L":
            cr.line_to(float(next(path)), float(next(path)))
        elif command == "C":
            cr.curve_to(*(float(next(path)) for _ in range(6)))
        else:
            cr.close_path()
    cr.stroke()
    cr.restore()


def rounded(cr, x, y, width, height, radius):
    cr.new_sub_path()
    cr.arc(x + width - radius, y + radius, radius, -math.pi / 2, 0)
    cr.arc(x + width - radius, y + height - radius, radius, 0, math.pi / 2)
    cr.arc(x + radius, y + height - radius, radius, math.pi / 2, math.pi)
    cr.arc(x + radius, y + radius, radius, math.pi, math.pi * 1.5)
    cr.close_path()


def emblem(cr, size):
    cr.save()
    cr.scale(size / 64, size / 64)
    rounded(cr, 1, 1, 62, 62, 16)
    fill = cairo.LinearGradient(0, 0, 64, 64)
    fill.add_color_stop_rgb(0, .30, .30, .30)
    fill.add_color_stop_rgb(1, .18, .18, .18)
    cr.set_source(fill)
    cr.fill_preserve()
    cr.set_source_rgb(.44, .44, .44)
    cr.set_line_width(1.5)
    cr.stroke()
    cr.set_source_rgb(.94, .94, .94)
    icon(cr, "brand-mark", 8, 8, 48)
    cr.restore()


def empty_art(cr, width, height):
    cr.save()
    cr.translate(width / 2, height / 2)
    rounded(cr, -31, -39, 80, 62, 12)
    cr.set_source_rgb(.09, .09, .09)
    cr.fill_preserve()
    cr.set_source_rgb(.27, .27, .27)
    cr.set_line_width(1)
    cr.stroke()

    rounded(cr, -47, -24, 80, 62, 12)
    cr.set_source_rgb(.17, .17, .17)
    cr.fill_preserve()
    cr.set_source_rgb(.40, .40, .40)
    cr.stroke()
    cr.set_source_rgb(.92, .92, .92)
    icon(cr, "brand-mark", -29, -15, 44)
    cr.restore()


@dataclass(frozen=True)
class Mark:
    tool: str
    points: tuple
    color: tuple
    width: int
    text: str = ""


@dataclass(frozen=True)
class Document:
    image: object
    marks: tuple = ()

    @property
    def size(self):
        return self.image.get_width(), self.image.get_height()

    def draw(self, cr, preview=None):
        Gdk.cairo_set_source_pixbuf(cr, self.image, 0, 0)
        cr.get_source().set_filter(cairo.FILTER_NEAREST)
        cr.paint()
        for mark in self.marks:
            draw_mark(cr, mark)
        if preview:
            draw_mark(cr, preview)

    def rendered(self):
        if not self.marks:
            return self.image
        width, height = self.size
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        self.draw(cairo.Context(surface))
        return Gdk.pixbuf_get_from_surface(surface, 0, 0, width, height)

    def cropped(self, bounds):
        x, y, width, height = bounds
        image = self.image.new_subpixbuf(x, y, width, height).copy()
        marks = tuple(replace(mark, points=tuple((px - x, py - y) for px, py in mark.points))
                      for mark in self.marks)
        return Document(image, marks)

    def erase_along(self, start, end, scale):
        if not self.marks:
            return self

        # Test visible ink against a brush swept between two pointer events.
        brush = 6
        x, y, width, height = box(start, end)
        surface = cairo.ImageSurface(cairo.FORMAT_A8, math.ceil(width * scale) + 2 * brush,
                                    math.ceil(height * scale) + 2 * brush)
        cr = cairo.Context(surface)
        cr.translate(brush - x * scale, brush - y * scale)
        cr.scale(scale, scale)
        cr.rectangle(0, 0, *self.size)
        cr.clip()
        radius = brush / scale
        if start == end:
            cr.arc(*start, radius, 0, 2 * math.pi)
        else:
            angle = math.atan2(end[1] - start[1], end[0] - start[0])
            cr.arc(*start, radius, angle + math.pi / 2, angle + 3 * math.pi / 2)
            cr.arc(*end, radius, angle - math.pi / 2, angle + math.pi / 2)
            cr.close_path()
        cr.clip()

        buffer = surface.get_data()
        blank = bytes(len(buffer))
        erased = set()
        for index in range(len(self.marks) - 1, -1, -1):
            mark = self.marks[index]
            draw_mark(cr, mark)
            surface.flush()
            if buffer == blank:
                continue
            erased.add(index)
            if start == end:
                break  # A click erases the topmost mark where annotations overlap.
            buffer[:] = blank
            surface.mark_dirty()
        if not erased:
            return self
        return replace(self, marks=tuple(mark for index, mark in enumerate(self.marks)
                                         if index not in erased))


def box(start, end):
    x, y = min(start[0], end[0]), min(start[1], end[1])
    width, height = abs(start[0] - end[0]), abs(start[1] - end[1])
    return x, y, width, height


def draw_mark(cr, mark):
    start, end = mark.points[0], mark.points[-1]
    tool = mark.tool
    cr.save()
    cr.set_source_rgba(*mark.color, .34 if tool == "highlight" else 1)
    cr.set_line_width(mark.width * (4 if tool == "highlight" else 1))
    cr.set_line_cap(cairo.LINE_CAP_SQUARE if tool == "highlight" else cairo.LINE_CAP_ROUND)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    if tool in ("pen", "highlight"):
        if len(mark.points) == 1:
            radius = cr.get_line_width() / 2
            if tool == "highlight":
                cr.rectangle(start[0] - radius, start[1] - radius, radius * 2, radius * 2)
            else:
                cr.arc(*start, radius, 0, 2 * math.pi)
            cr.fill()
        else:
            cr.move_to(*start)
            for point in mark.points[1:]:
                cr.line_to(*point)
    elif tool == "arrow":
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        length = min(max(12, mark.width * 3.5), math.dist(start, end) * .6)
        cr.move_to(*start)
        cr.line_to(*end)
        for direction in (angle - .55, angle + .55):
            cr.move_to(*end)
            cr.rel_line_to(-length * math.cos(direction), -length * math.sin(direction))
    elif tool in ("rectangle", "redact"):
        x, y, width, height = box(start, end)
        if tool == "redact":
            cr.set_source_rgb(0, 0, 0)
            left, top = math.floor(x), math.floor(y)
            cr.rectangle(left, top, math.ceil(x + width) - left, math.ceil(y + height) - top)
            cr.fill()
        else:
            cr.rectangle(x, y, width, height)
    elif tool == "ellipse":
        x, y, width, height = box(start, end)
        if width and height:
            cr.save()
            cr.translate(x + width / 2, y + height / 2)
            cr.scale(width / 2, height / 2)
            cr.arc(0, 0, 1, 0, 2 * math.pi)
            cr.restore()
    elif tool == "text":
        layout = PangoCairo.create_layout(cr)
        font = Pango.FontDescription("Sans Bold")
        font.set_absolute_size(max(16, mark.width * 5) * Pango.SCALE)
        layout.set_font_description(font)
        layout.set_text(mark.text, -1)
        cr.move_to(*start)
        PangoCairo.show_layout(cr, layout)
    cr.stroke()
    cr.restore()
