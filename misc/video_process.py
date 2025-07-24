#!/usr/bin/env python3
import os
import subprocess
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk  # <-- Add this import
from datetime import datetime, timedelta
import soundfile as sf
import numpy as np
import pickle
import threading
import concurrent.futures
import tkinter.simpledialog

from sklearn.linear_model import SGDRegressor
from sklearn.preprocessing import StandardScaler

# ---- Clasa PatternAI (combinată) ----
class PatternAI:
    def __init__(self, save_path="patternai_state.pkl"):
        self.save_path = save_path
        self.history = []
        self.scaler = StandardScaler()
        self.model = SGDRegressor(max_iter=1, tol=None, penalty='l2', alpha=1e-3)
        self.initialized = False
        self._load_state()

    def add_observation(self, week_day: int, hour: float, value: float):
        self.history.append((week_day, hour, value))
        # Primul batch la 100 de observații
        if not self.initialized and len(self.history) >= 100:
            X = np.array([[d, h] for d,h,_ in self.history])
            y = np.array([v for _,_,v in self.history])
            Xs = self.scaler.fit_transform(X)
            self.model.partial_fit(Xs, y)
            self.initialized = True
        # Învățare online
        elif self.initialized:
            X_new = np.array([[week_day, hour]])
            Xs_new = self.scaler.transform(X_new)
            self.model.partial_fit(Xs_new, [value])
        self._save_state()

    def predict_current_pattern(self):
        if not self.initialized:
            return None
        now = datetime.now()
        d, h = now.weekday(), now.hour + now.minute/60
        xs = self.scaler.transform([[d, h]])
        return float(self.model.predict(xs)[0])

    def _save_state(self):
        with open(self.save_path, "wb") as f:
            pickle.dump({
                "history": self.history,
                "scaler": self.scaler,
                "model": self.model,
                "initialized": self.initialized
            }, f)

    def _load_state(self):
        if os.path.exists(self.save_path):
            try:
                with open(self.save_path, "rb") as f:
                    st = pickle.load(f)
                    self.history = st.get("history", [])
                    self.scaler = st.get("scaler", StandardScaler())
                    self.model = st.get("model", SGDRegressor(max_iter=1, tol=None, penalty='l2', alpha=1e-3))
                    self.initialized = st.get("initialized", False)
                print(f"[PatternAI] State loaded from {self.save_path}")
            except Exception:
                print(f"[PatternAI] Failed to load state; starting fresh.")
                self.history = []
                self.scaler = StandardScaler()
                self.model = SGDRegressor(max_iter=1, tol=None, penalty='l2', alpha=1e-3)
                self.initialized = False

# ---- Funcții de procesare audio și video ----

def ffprobe_start_time(video_path):
    """Returnează start_time ISO al video-ului folosind ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=start_time",
        "-of", "default=nw=1:nk=1",
        video_path
    ]
    out = subprocess.check_output(cmd).decode().strip()
    # uneori apare în secunde zecimale
    return datetime.fromtimestamp(float(out))

def extract_audio_tracks(video_path, out_dir):
    """Extrage fiecare pistă audio într-un WAV separat; returnează lista de căi."""
    # află numărul de piste cu ffprobe
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=index",
        "-of", "csv=p=0",
        video_path
    ]
    streams = subprocess.check_output(cmd).decode().strip().splitlines()
    paths = []
    for idx, s in enumerate(streams):
        out = os.path.join(out_dir, f"track_{idx}.wav")
        subprocess.check_call([
            "ffmpeg", "-y", "-i", video_path,
            "-map", f"0:a:{idx}", out
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        paths.append(out)
    return paths

def compute_db_levels(wav_path, interval_ms=100):
    """Împarte WAV în ferestre și returnează lista de dB pozitivi (0=silence, max~40-60)."""
    data, sr = sf.read(wav_path)
    hop = int(sr * interval_ms / 1000)
    dbs = []
    for i in range(0, len(data), hop):
        seg = data[i:i+hop]
        if seg.size == 0: break
        rms = np.sqrt(np.mean(seg**2))
        # Invert the sign so silence is 0, loud is positive
        db = -20 * np.log10(rms + 1e-12)
        dbs.append(db)
    return dbs

# ---- GUI minimal pentru selecție și procesare ----

class TrainerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Video → PatternAI Trainer")
        tk.Button(self, text="Selectează video", command=self.select_video).pack(padx=20,pady=10)
        self.log = tk.Text(self, width=60, height=15, state='disabled')
        self.log.pack(padx=20,pady=10)
        self.progress = ttk.Progressbar(self, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(padx=20, pady=(0,10))
        self.ai = PatternAI()

    def log_msg(self, msg):
        self.log.config(state='normal')
        self.log.insert(tk.END, msg+"\n")
        self.log.see(tk.END)
        self.log.config(state='disabled')

    def select_video(self):
        vp = filedialog.askopenfilename(
            title="Alege fișier video",
            filetypes=[("MP4", "*.mp4"),("All","*.*")])
        if not vp:
            return

        # Detect number of tracks
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tracks = extract_audio_tracks(vp, tmp)
                num_tracks = len(tracks)
        except Exception as e:
            self.log_msg(f"Eroare la detectarea pistelor audio: {e}")
            return

        if num_tracks == 0:
            self.log_msg("Nu s-au găsit piste audio.")
            return

        # Ask user for track index
        track_index = tkinter.simpledialog.askinteger(
            "Alege pista audio",
            f"Acest video are {num_tracks} piste audio (0-{num_tracks-1}).\nIntrodu indexul pistei de procesat:",
            minvalue=0, maxvalue=num_tracks-1
        )
        if track_index is None:
            self.log_msg("Procesare anulată de utilizator.")
            return

        threading.Thread(target=self.process_video, args=(vp, track_index), daemon=True).start()

    def process_video(self, video_path, track_index=0):
        self.log_msg(f"Încep procesare: {video_path}")
        try:
            start_dt = ffprobe_start_time(video_path)
            self.log_msg(f"Start video: {start_dt.isoformat()}")
        except Exception as e:
            self.log_msg(f"Eroare ffprobe: {e}")
            return

        with tempfile.TemporaryDirectory() as tmp:
            try:
                tracks = extract_audio_tracks(video_path, tmp)
            except Exception as e:
                self.log_msg(f"Eroare ffmpeg: {e}")
                return

            # Only process the selected track
            if track_index < 0 or track_index >= len(tracks):
                self.log_msg(f"Track index {track_index} invalid. Număr de piste: {len(tracks)}")
                return

            track = tracks[track_index]
            self.log_msg(f"Procesare pistă: {os.path.basename(track)}")
            dbs = compute_db_levels(track)
            total_dbs = len(dbs)
            self.after(0, lambda: self.progress.config(maximum=total_dbs, value=0))

            for idx, db in enumerate(dbs):
                ts = start_dt + timedelta(milliseconds=(idx)*100)
                wd = ts.weekday()
                hr = ts.hour + ts.minute/60 + ts.second/3600
                self.ai.add_observation(wd, hr, db)
                self.after(0, lambda v=idx+1: self.progress.config(value=v))
            self.log_msg(f"Observații adăugate: {total_dbs}")
            self.after(0, lambda: messagebox.showinfo("Gata", f"{total_dbs} observații adăugate în PatternAI."))
            self.after(0, lambda: self.progress.config(value=0))
        self.ai._save_state()

if __name__ == "__main__":
    app = TrainerApp()
    app.mainloop()
