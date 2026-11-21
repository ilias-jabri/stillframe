"""Optional local WebM screen recording via GStreamer."""

import os
from pathlib import Path
import tempfile

import gi

try:
    gi.require_version("Gst", "1.0")
    from gi.repository import Gst
except (ImportError, ValueError):
    Gst = None


ELEMENTS = ("ximagesrc", "capsfilter", "videoconvert", "capsfilter", "queue", "webmmux", "filesink")
FPS = 30


def find_encoder():
    return next((name for name in ("vp9enc", "vp8enc") if Gst.ElementFactory.find(name)), None)


def available():
    if Gst is None:
        return False
    Gst.init(None)
    return bool(find_encoder()) and all(Gst.ElementFactory.find(name) for name in ELEMENTS)


class Recording:
    def __init__(self, destination, bounds, complete):
        self.destination = destination
        self.complete = complete
        self.finished = False
        self.pipeline = Gst.Pipeline.new("screen-recording")
        source, limit, convert, pixel_format, pending, mux, sink = [
            Gst.ElementFactory.make(name) for name in ELEMENTS
        ]
        encoder_name = find_encoder()
        if encoder_name is None:
            raise RuntimeError("No local WebM encoder is available.")
        encoder = Gst.ElementFactory.make(encoder_name)
        source.set_property("display-name", os.environ["DISPLAY"])
        source.set_property("use-damage", False)
        if bounds:
            x, y, width, height = bounds
            for key, value in (("startx", x), ("starty", y), ("endx", x + width - 1),
                               ("endy", y + height - 1)):
                source.set_property(key, value)
        limit.set_property("caps", Gst.Caps.from_string(f"video/x-raw,framerate={FPS}/1"))
        # VP9 can retain full color resolution, which keeps small colored text sharp.
        color_format = "Y444" if encoder_name == "vp9enc" else "I420"
        pixel_format.set_property("caps", Gst.Caps.from_string(f"video/x-raw,format={color_format}"))
        convert.set_property("n-threads", 2)
        # Let capture and conversion run while the encoder handles earlier frames.
        pending.set_property("max-size-buffers", 6)
        pending.set_property("max-size-bytes", 64 * 1024 * 1024)
        quality = {
            "deadline": 1,  # Real-time encoding.
            "cpu-used": 8,
            "threads": min(os.cpu_count() or 1, 8),
            "end-usage": 2,  # Constant quality instead of a fixed bitrate.
            "target-bitrate": 0,
            "bits-per-pixel": .25,
            "cq-level": 16,
            "max-quantizer": 26,
            "lag-in-frames": 0,
            "keyframe-max-dist": 2 * FPS,
        }
        if encoder_name == "vp9enc":
            quality.update({"row-mt": True, "tile-columns": 3})
        for prop, value in quality.items():
            encoder.set_property(prop, value)
        fd, path = tempfile.mkstemp(prefix=".stillframe-", suffix=".webm", dir=destination.parent)
        os.close(fd)
        self.temporary = Path(path)
        sink.set_property("location", path)
        try:
            chain = (source, limit, convert, pixel_format, pending, encoder, mux, sink)
            for element in chain:
                self.pipeline.add(element)
            for before, after in zip(chain, chain[1:]):
                if not before.link(after):
                    raise RuntimeError("The local video encoder could not be linked.")
            self.bus = self.pipeline.get_bus()
            self.bus.add_signal_watch()
            self.handler = self.bus.connect("message", self.message)
        except Exception:
            self.temporary.unlink(missing_ok=True)
            raise

    def start(self):
        if self.pipeline.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
            self.finish("The screen recorder could not start.")

    def stop(self):
        if not self.finished and not self.pipeline.send_event(Gst.Event.new_eos()):
            self.finish("The recording ended before it could be saved.")

    def message(self, _bus, message):
        if message.type == Gst.MessageType.ERROR:
            error, _debug = message.parse_error()
            self.finish(error.message)
        elif message.type == Gst.MessageType.EOS:
            self.finish(None)

    def finish(self, error):
        if self.finished:
            return
        self.finished = True
        self.pipeline.set_state(Gst.State.NULL)
        self.bus.disconnect(self.handler)
        self.bus.remove_signal_watch()
        try:
            if error is None:
                self.temporary.replace(self.destination)
        except OSError as exc:
            error = str(exc)
        finally:
            self.temporary.unlink(missing_ok=True)
        self.complete(error)
