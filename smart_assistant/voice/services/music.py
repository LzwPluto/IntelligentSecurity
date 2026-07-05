import json
import os
import socket
import subprocess
from pathlib import Path

from .base import BaseService


class MusicService(BaseService):

    def __init__(self, music_dir, audio_device):
        self.music_dir = Path(music_dir)
        self.audio_device = audio_device
        self.songs = []
        self.current_index = 0
        self.process = None
        self.is_playing = False
        self.is_paused = False
        self.was_playing_before_wakeup = False
        self._user_changed_state = False
        self.socket_path = "/tmp/mpv_music_socket"
        self.ref_fifo = "/tmp/mpv_ref_fifo"
        self._mpv_available = False

        self._check_mpv()
        self._scan()
        self._setup_fifo()

    def _check_mpv(self):
        try:
            result = subprocess.run(
                ["mpv", "--version"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                self._mpv_available = True
                print("[MusicService] mpv detected.")
            else:
                print("[MusicService] mpv not available. Music playback disabled.")
        except Exception:
            print("[MusicService] mpv not found. Music playback disabled.")

    def _setup_fifo(self):
        try:
            os.unlink(self.ref_fifo)
        except OSError:
            pass
        try:
            os.mkfifo(self.ref_fifo)
        except OSError:
            pass

    def _scan(self):
        extensions = ["*.mp3", "*.wav", "*.flac", "*.ogg", "*.m4a"]
        self.songs = []
        for ext in extensions:
            for filepath in sorted(self.music_dir.glob(ext)):
                self.songs.append({
                    "path": str(filepath),
                    "filename": filepath.name,
                    "display_name": filepath.stem,
                })

        if self.songs:
            song_list = [s["display_name"] for s in self.songs]
            print(f"[MusicService] Found {len(self.songs)} songs: {song_list}")
        else:
            print("[MusicService] No music files found in "
                  + str(self.music_dir))

    def execute(self, params):
        if not self._mpv_available:
            return

        self._user_changed_state = True

        action = params.get("action", "play")
        query = params.get("query", "") or params.get("artist", "")

        if action == "play":
            self._play(query)
        elif action == "pause":
            self._pause()
        elif action == "resume":
            self._resume()
        elif action == "next":
            self._next()
        elif action == "previous":
            self._previous()
        elif action == "stop":
            self._stop()
        else:
            self._play(query)

    def _find_match(self, query):
        if not query or not self.songs:
            return list(range(len(self.songs)))

        query_lower = query.lower()
        for i, song in enumerate(self.songs):
            if query_lower in song["display_name"].lower():
                return [i]

        query_chars = set(query_lower.replace(" ", ""))
        best_idx = 0
        best_score = 0
        for i, song in enumerate(self.songs):
            name_lower = song["display_name"].lower().replace(" ", "")
            score = sum(1 for c in query_chars if c in name_lower)
            if score > best_score:
                best_score = score
                best_idx = i

        return [best_idx] if best_score > 0 else [0]

    def _play(self, query):
        indices = self._find_match(query)
        if not indices:
            return

        self._kill_mpv()
        self.current_index = indices[0]
        song = self.songs[self.current_index]
        self._start_mpv(song["path"])
        print(f"[MusicService] Playing: {song['display_name']}")

    def _start_mpv(self, filepath):
        try:
            os.unlink(self.socket_path)
        except OSError:
            pass

        cmd = [
            "mpv",
            "--no-video",
            "--audio-device=alsa/" + self.audio_device,
            "--input-ipc-server=" + self.socket_path,
            "--idle=yes",
            "--audio-samplerate=44100",
            "--audio-format=s16",
            "--audio-channels=1",
            "--record-file=" + self.ref_fifo,
            filepath,
        ]

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.is_playing = True
        self.is_paused = False

    def _send_command(self, command):
        if self.process is None:
            return
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.connect(self.socket_path)
            sock.send(json.dumps({"command": command}).encode() + b"\n")
            sock.close()
        except Exception:
            pass

    def _pause(self):
        if self.process and self.is_playing and not self.is_paused:
            self._send_command(["set_property", "pause", True])
            self.is_paused = True
            print("[MusicService] Paused")

    def _resume(self):
        if self.process and self.is_paused:
            self._send_command(["set_property", "pause", False])
            self.is_paused = False
            print("[MusicService] Resumed")

    def _next(self):
        if not self.songs:
            return
        self.current_index = (self.current_index + 1) % len(self.songs)
        song = self.songs[self.current_index]
        self._send_command(["loadfile", song["path"]])
        self.is_playing = True
        self.is_paused = False
        print(f"[MusicService] Next: {song['display_name']}")

    def _previous(self):
        if not self.songs:
            return
        self.current_index = (self.current_index - 1) % len(self.songs)
        song = self.songs[self.current_index]
        self._send_command(["loadfile", song["path"]])
        self.is_playing = True
        self.is_paused = False
        print(f"[MusicService] Previous: {song['display_name']}")

    def _kill_mpv(self):
        if self.process:
            self._send_command(["quit"])
            try:
                self.process.wait(timeout=2)
            except Exception:
                self.process.kill()
            self.process = None
        self.is_playing = False
        self.is_paused = False

    def _stop(self):
        self._kill_mpv()
        print("[MusicService] Stopped")

    def on_wakeup(self):
        self.was_playing_before_wakeup = self.is_playing and not self.is_paused
        self._user_changed_state = False
        if self.was_playing_before_wakeup:
            self._pause()

    def on_interaction_done(self):
        if self.was_playing_before_wakeup and not self._user_changed_state:
            self._resume()
        self.was_playing_before_wakeup = False
        self._user_changed_state = False
