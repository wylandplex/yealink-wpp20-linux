#!/usr/bin/env python3
"""Render an explicitly selected GNOME ScreenCast stream into a private X display."""
import ctypes
import os
from pathlib import Path
import signal
import sys
import uuid

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gio, GLib, Gst, GstVideo

Gst.init(None)
ready = Path(sys.argv[1])
bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
destination = 'org.freedesktop.portal.Desktop'
object_path = '/org/freedesktop/portal/desktop'
interface = 'org.freedesktop.portal.ScreenCast'
loop = GLib.MainLoop()
session = None
pipeline = None
remote_fd = None
failed = False

def request(method, signature, args, options, callback):
    token = 'wpp_' + uuid.uuid4().hex
    options['handle_token'] = GLib.Variant('s', token)
    sender = bus.get_unique_name()[1:].replace('.', '_')
    path = '/org/freedesktop/portal/desktop/request/' + sender + '/' + token
    def response(conn, sender_name, path, iface, member, parameters):
        global failed
        bus.signal_unsubscribe(subscription)
        status, results = parameters.unpack()
        if status:
            failed = True
            print('Screen selection cancelled or failed:', status, flush=True)
            loop.quit()
        else:
            try:
                callback(results)
            except Exception as error:
                failed = True
                print('Bridge error:', error, flush=True)
                loop.quit()
    subscription = bus.signal_subscribe(destination, 'org.freedesktop.portal.Request',
                                        'Response', path, None, Gio.DBusSignalFlags.NONE,
                                        response)
    bus.call_sync(destination, object_path, interface, method,
                  GLib.Variant(signature, (*args, options)), None,
                  Gio.DBusCallFlags.NONE, 10000, None)

# This X display is created just for this bridge and the Yealink client.
xlib = ctypes.CDLL('libX11.so.6')
xlib.XOpenDisplay.argtypes = [ctypes.c_char_p]
xlib.XOpenDisplay.restype = ctypes.c_void_p
xlib.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
xlib.XDefaultRootWindow.restype = ctypes.c_ulong
xlib.XCreateSimpleWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int,
    ctypes.c_int, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_ulong, ctypes.c_ulong]
xlib.XCreateSimpleWindow.restype = ctypes.c_ulong
for name in ['XMapRaised', 'XRaiseWindow', 'XDestroyWindow']:
    getattr(xlib, name).argtypes = [ctypes.c_void_p, ctypes.c_ulong]
xlib.XFlush.argtypes = [ctypes.c_void_p]
xlib.XCloseDisplay.argtypes = [ctypes.c_void_p]
xlib.XStoreName.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_char_p]
display = xlib.XOpenDisplay(os.environ['DISPLAY'].encode())
if not display:
    raise SystemExit('Cannot open private X display.')
root_window = xlib.XDefaultRootWindow(display)
window = xlib.XCreateSimpleWindow(display, root_window, 0, 0, 1920, 1080, 0, 0, 0)
xlib.XStoreName(display, window, b'Yealink Wayland Screen')
xlib.XMapRaised(display, window)
xlib.XFlush(display)

def create_done(result):
    global session
    session = result['session_handle']
    bus.signal_subscribe(destination, 'org.freedesktop.portal.Session', 'Closed',
                         session, None, Gio.DBusSignalFlags.NONE,
                         lambda *args: loop.quit())
    request('SelectSources', '(oa{sv})', (session,),
            {'types': GLib.Variant('u', 1), 'multiple': GLib.Variant('b', False),
             'cursor_mode': GLib.Variant('u', 2)}, sources_done)

def sources_done(result):
    print('Please select the screen in the GNOME sharing dialog.', flush=True)
    request('Start', '(osa{sv})', (session, ''), {}, start_done)

def start_done(result):
    global pipeline, remote_fd
    streams = result['streams']
    if len(streams) != 1:
        raise RuntimeError('Expected one selected screen.')
    node, properties = streams[0]
    reply, fds = bus.call_with_unix_fd_list_sync(destination, object_path, interface,
        'OpenPipeWireRemote', GLib.Variant('(oa{sv})', (session, {})),
        GLib.VariantType.new('(h)'), Gio.DBusCallFlags.NONE, 10000, None, None)
    remote_fd = fds.get(reply.unpack()[0])
    pipeline = Gst.parse_launch(
        f'pipewiresrc name=source fd={remote_fd} path={node} do-timestamp=true '
        '! queue max-size-buffers=2 leaky=downstream ! videoconvert ! videoscale '
        '! video/x-raw,width=1920,height=1080,pixel-aspect-ratio=1/1 '
        '! ximagesink name=screen sync=false force-aspect-ratio=true')
    sink = pipeline.get_by_name('screen')
    sink.set_property('display', os.environ['DISPLAY'])
    GstVideo.VideoOverlay.set_window_handle(sink, window)
    GstVideo.VideoOverlay.handle_events(sink, False)
    announced = [False]
    def first_frame(pad, info):
        if not announced[0]:
            announced[0] = True
            ready.write_text('frames-ready\n')
            print('Screen frames are arriving on the private display.', flush=True)
        return Gst.PadProbeReturn.OK
    sink.get_static_pad('sink').add_probe(Gst.PadProbeType.BUFFER, first_frame)
    gst_bus = pipeline.get_bus()
    gst_bus.add_signal_watch()
    def gst_message(bus, message):
        global failed
        if message.type == Gst.MessageType.ERROR:
            error, debug = message.parse_error()
            print('Video error:', error, debug, flush=True)
            failed = True
            loop.quit()
        elif message.type == Gst.MessageType.EOS:
            loop.quit()
    gst_bus.connect('message', gst_message)
    pipeline.set_state(Gst.State.PLAYING)
    # Keep the video surface above Wine's helper windows on the private display.
    def raise_video():
        xlib.XRaiseWindow(display, window)
        xlib.XFlush(display)
        return True
    GLib.timeout_add(500, raise_video)

for sig in (signal.SIGINT, signal.SIGTERM):
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, sig, lambda: (loop.quit(), False)[1])
try:
    request('CreateSession', '(a{sv})', (),
            {'session_handle_token': GLib.Variant('s', 'wpp_' + uuid.uuid4().hex)}, create_done)
    loop.run()
finally:
    if pipeline:
        pipeline.set_state(Gst.State.NULL)
    if session:
        try:
            bus.call_sync(destination, session, 'org.freedesktop.portal.Session', 'Close',
                          None, None, Gio.DBusCallFlags.NONE, 3000, None)
        except GLib.Error:
            pass
    if remote_fd is not None:
        os.close(remote_fd)
    xlib.XDestroyWindow(display, window)
    xlib.XCloseDisplay(display)
    ready.unlink(missing_ok=True)
raise SystemExit(1 if failed else 0)
