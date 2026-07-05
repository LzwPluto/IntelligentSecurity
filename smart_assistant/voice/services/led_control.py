import threading
import time

try:
    import gpiod
    HAS_GPIOD = True
except ImportError:
    HAS_GPIOD = False

_chip = None
_request = None

_blink_thread = None
_blink_stop = False
_initialized = False
_pin = None


def init(pin, chip_name="gpiochip3"):

    global _chip, _request, _initialized, _pin

    if _initialized:
        return True

    if not HAS_GPIOD:
        print("[LED] gpiod not installed. Run: pip install gpiod")
        return False

    _pin = pin
    chip_path = f"/dev/{chip_name}"

    try:
        _chip = gpiod.Chip(chip_path)

        if hasattr(gpiod, "LineSettings"):
            _request = _chip.request_lines(
                {pin: gpiod.LineSettings(direction=gpiod.line.Direction.OUTPUT)},
                consumer="smart_assistant_led",
            )
        else:
            _line = _chip.get_line(pin)
            _request = _line
            _line.request(
                consumer="smart_assistant_led",
                type=gpiod.LINE_REQ_DIR_OUT,
                default_vals=[0],
            )

        _initialized = True
        print(f"[LED] {chip_path} pin {pin} initialized")
        return True

    except PermissionError:
        print("[LED] Permission denied. Add user to gpio group or run with sudo.")
        return False
    except Exception as e:
        print(f"[LED] Init failed: {e}")
        return False


def _set(val):

    try:
        if hasattr(gpiod, "LineSettings"):
            v = gpiod.line.Value.ACTIVE if val else gpiod.line.Value.INACTIVE
            _request.set_value(_pin, v)
        else:
            _request.set_value(val)
    except Exception as e:
        print(f"[LED] Set value failed: {e}")


def on():

    if not _initialized:
        print("[LED] Not initialized")
        return

    stop_blink()
    _set(1)
    print("[LED] ON")


def off():

    if not _initialized:
        print("[LED] Not initialized")
        return

    stop_blink()
    _set(0)
    print("[LED] OFF")


def blink(interval=0.5):

    global _blink_thread, _blink_stop

    if not _initialized:
        print("[LED] Not initialized")
        return

    stop_blink()
    _blink_stop = False

    def _run():
        v = 1
        while not _blink_stop:
            try:
                _set(v)
                v = 1 - v
                time.sleep(interval)
            except Exception as e:
                print(f"[LED] Blink error: {e}")
                break

    _blink_thread = threading.Thread(target=_run, daemon=True)
    _blink_thread.start()
    print(f"[LED] BLINK (interval={interval}s)")


def stop_blink():

    global _blink_stop, _blink_thread

    _blink_stop = True
    if _blink_thread:
        _blink_thread.join(timeout=1)
        _blink_thread = None


def cleanup():

    stop_blink()

    global _request, _chip, _initialized

    if _request is not None:
        try:
            _request.release()
        except Exception:
            pass
        _request = None

    if _chip is not None:
        try:
            _chip.close()
        except Exception:
            pass
        _chip = None

    _initialized = False
