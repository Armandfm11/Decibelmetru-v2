# Librarii
# GUI
import tkinter as tk
from tkinter import ttk, messagebox


# Multitasking
import threading
import queue

# Timp
import time

# Conexiune wireless
import socket

# GUI - Plot
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Componenta de inteligenta artificiala
from pattern_ai import PatternAI



        # Configurare socket UDP
# Aplicatia va accepta pachete de la orice IP de pe portul 0
UDP_IP = "0.0.0.0"
UDP_PORT = 0

# Creare socket care va folosi IPv4 și UDP
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# Timeout pentru socket
sock.settimeout(5)
# Legare IP & port de socket
sock.bind((UDP_IP, UDP_PORT))



class DecibelMetru(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Decibelmetru cu comunicatie fara fir")
        self.geometry("1000x600")
        

            # Initializare
        self.running = False

        # Valori inregistrate
        self.values = []


        self.plot_update_times = []
        self.plot_update_max = 0
        self.plot_update_sum = 0
        self.plot_update_count = 0

        # Valoarea medie, minima, maxima + contor pentru medie
        self.count = 0
        self.avg = 0.0
        self.min = float('inf')
        self.max = float('-inf')

        # Functie predictie AI
        self.ai = PatternAI()
        self.ai_queue = queue.Queue()
        self.ai_pred = None
        self.ai_thread = threading.Thread(target=self._ai_worker, daemon=True)
        self.ai_thread.start()

        # GUI
        self.create_widgets()
        self.create_plot()

        self.plot_update_times = []

        # Show confirmation when model is loaded
        self.after(100, self.show_model_loaded_popup)
        # Start periodic prediction update
        self.after(200, self._update_prediction_var)

    def _ai_worker(self):
        while True:
            value = self.ai_queue.get()
            self.ai.add_observation(value)
            # Only predict if model is trained and enough data exists
            if self.ai.initialized and len(self.ai.history) >= 50:
                try:
                    pred = self.ai.predict_current_pattern()
                    self.ai_pred = pred
                except Exception:
                    pass
            self.ai_queue.task_done()

    def _update_prediction_var(self):
        if hasattr(self, 'pred_var') and self.ai_pred is not None:
            self.pred_var.set(f"{self.ai_pred:.1f}")
        self.after(200, self._update_prediction_var)
    def show_model_loaded_popup(self):
        messagebox.showinfo("Model Loaded", "PatternAI model loaded successfully.")

    def create_widgets(self):
        # Container widget-uri
        controls_frame = tk.Frame(self)
        controls_frame.pack(side=tk.LEFT, fill=tk.Y, padx=20, pady=10)

        # Titlu
        tk.Label(controls_frame, text="Decibelmetru", font=("Freestyle Script", 36), fg="#129FE1").pack(pady=10)

        # Medie
        tk.Label(controls_frame, text="Medie sunet").pack()
        self.avg_var = tk.StringVar(value="---")
        tk.Entry(controls_frame, textvariable=self.avg_var, font=("Digital-7",28),
                 justify='center', state='readonly', width=12).pack(pady=5)

        # Min/Max
        min_max = tk.Frame(controls_frame)
        min_max.pack(pady=5)
        tk.Label(min_max, text="Min").pack(side=tk.LEFT)
        self.min_var = tk.StringVar(value="---")
        tk.Entry(min_max, textvariable=self.min_var, font=("Digital-7",16),
                 justify='center', state='readonly', width=6, fg="blue").pack(side=tk.LEFT, padx=5)
        self.max_var = tk.StringVar(value="---")
        tk.Entry(min_max, textvariable=self.max_var, font=("Digital-7",16),
                 justify='center', state='readonly', width=6, fg="red").pack(side=tk.LEFT, padx=5)
        tk.Label(min_max, text="Max").pack(side=tk.LEFT)

        # Buton reset + safety lock
        self.lock_var = tk.BooleanVar()
        lock_cb = ttk.Checkbutton(controls_frame, text="Unlock?", variable=self.lock_var, command=self.on_lock)
        lock_cb.pack(pady=5)
        self.reset_btn = ttk.Button(controls_frame, text="Reset", command=self.reset_avg, state=tk.DISABLED)
        self.reset_btn.pack()

        # Prag + alerta
        tk.Label(controls_frame, text="Prag dB").pack(pady=(20,0))
        self.threshold_var = tk.DoubleVar(value=40.0)
        th_frame = tk.Frame(controls_frame)
        th_frame.pack()
        tk.Scale(th_frame, from_=5, to=70, orient=tk.HORIZONTAL,
                 variable=self.threshold_var, length=150).pack(side=tk.LEFT)
        tk.Entry(th_frame, textvariable=self.threshold_var, width=5).pack(side=tk.RIGHT, padx=5)

        # Predictie nivel zgomot
        tk.Label(controls_frame, text="Predictie nivel zgomot").pack(pady=(20,0))
        self.pred_var = tk.StringVar(value="---")
        tk.Entry(controls_frame, textvariable=self.pred_var, font=("Digital-7",16),
                 justify='center', state='readonly', width=8).pack()

        # Bara stare + indicator LED
        status_frame = tk.LabelFrame(controls_frame, text="Status")
        status_frame.pack(pady=20)
        self.lamp = tk.Canvas(status_frame, width=30, height=20)
        self.lamp.create_oval(2,2,18,18, fill="red", tags="led")
        self.lamp.pack(side=tk.LEFT, padx=5)
        self.status_text = tk.Text(status_frame, width=40, height=3)
        self.status_text.insert(tk.END, "Program oprit\nSalut! :)")
        self.status_text.configure(state='disabled')
        self.status_text.pack(side=tk.LEFT)

        # Buton start
        self.start_btn = ttk.Button(controls_frame, text="Start", command=self.start_udp)
        self.start_btn.pack(side=tk.BOTTOM, pady=20, fill=tk.X)

        # Plot update times (small, responsive, single row)
        self.plot_times_var = tk.StringVar(value="")
        self.plot_times_label = tk.Label(
            controls_frame,
            textvariable=self.plot_times_var,
            font=("Arial", 7),
            fg="gray",
            anchor="w",
            justify="left"
           
        )
        self.plot_times_label.pack(side=tk.BOTTOM, pady=(2, 0), fill=tk.X)

    # Plot
    def create_plot(self):
        fig = Figure(figsize=(4,3))
        self.ax = fig.add_subplot(111)
        self.ax.set_title("Nivel sunet")
        self.ax.set_xlabel("Timp [s]")
        self.ax.set_ylabel("dB")
        self.line, = self.ax.plot([], [], 'b-')
        self.canvas = FigureCanvasTkAgg(fig, master=self)
        self.canvas.get_tk_widget().pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    # Safety lock
    def on_lock(self):
        if self.lock_var.get():
            self.reset_btn.config(state=tk.NORMAL)
        else:
            self.reset_btn.config(state=tk.DISABLED)

    # Logica buton reset
    def reset_avg(self):
        if self.lock_var.get():

            # Resetare valori
            self.avg = 0.0
            self.min = float('inf')
            self.max = float('-inf')
            self.count = 0
            self.values.clear()
            self.avg_var.set("---")
            self.min_var.set("---")
            self.max_var.set("---")

            # Se afiseaza un mesaj de confirmare a resetarii - dupa 5 secunde se revine la mesajul de stare curent
            self._set_status("Statistici resetate.")
            self.after(5000, lambda: self._set_status("Conectat la Arduino Uno R4 WiFi") if  self.running else self._set_status("Program oprit\nSalut! :)"))        

            # Resetare plot
            self.ax.clear()
            self.ax.set_title("Nivel sunet")
            self.ax.set_xlabel("Timp [s]")
            self.ax.set_ylabel("dB")
            self.canvas.draw_idle()

    # Pornire conexiune UDP - buton start
    def start_udp(self):

        # Led-ul este un flag - daca conexiunea este deja stabilita...
        #                            ...nu poti porni un program deja pornit
        if self.lamp.itemcget("led", "fill") == "green":
            messagebox.showinfo("Alerta", "Programul functioneaza.")
            return
        self._set_status("Se conecteaza...")
        self._set_lamp('yellow')
        # Executa in continuu citirea de la socket-ul UDP
        threading.Thread(target=self.read_loop, daemon=True).start()

    # Confirmare in status ca avem conexiune
    def confirm_conn(self):
        self._set_status("Conectat la Arduino Uno R4 WiFi")
        self._set_lamp('green')
        self.running = True

    # Citire valori
    def read_loop(self):
        start_time = time.time()
        last_plot_time = None
        while self.lamp.itemcget("led", "fill") != "red":
            try:
                # Data primeste valoarea de la socket, _ este neglijabila intrucat nu sunt relevante IP-ul expeditorului
                data, _ = sock.recvfrom(1024)
                # Daca nu se primesc date este declansata exceptia si se indica un timeout

                if self.lamp.itemcget("led", "fill") != "green":
                    self.confirm_conn();
                # ...altfel ne asiguram ca status-ul este actualizat
            except socket.timeout:
                self._set_lamp('red')
                self._set_status("Timeout UDP")
                self.running = False
                break


            # Decodare pachet de la Arduino
            line = data.decode().strip()


            # Reset remote, daca se detecteaza cuvantul "reset"
            if line.lower() == "reset":
                self.reset_avg()
                continue
            # Daca pachet-ul primit nu contine "reset", se incearca extragerea unei valori float
            try:
                value = float(line)
            # Daca nu se reuseste, pachetul a avut o eroare - ignora pachetul fara sa opresti programul
            except:
                continue

            # Adaugare valoare noua + timestamp
            elapsed = time.time() - start_time
            self.values.append((elapsed, value))

            # Indicatori avg, min, max
            self.count += 1
            self.avg = ((self.avg * (self.count-1)) + value) / self.count
            self.min = min(self.min, value)
            self.max = max(self.max, value)

            self.avg_var.set(f"{self.avg:.1f}")
            self.min_var.set(f"{self.min:.1f}")
            self.max_var.set(f"{self.max:.1f}")

            # Logica prag
            thr = self.threshold_var.get()
            bg = 'red' if value >= thr else 'white'
            self.configure(bg=bg)

            # Invatare & predictie AI (non-blocking)
            try:
                self.ai_queue.put_nowait(value)
            except queue.Full:
                pass  # If queue is full, skip this value

            # Update plot
            if self.values:
                xs, ys = zip(*self.values)
            else:
                # Exceptie - cazul in care se face reset si nu exista valori
                xs, ys = [], []
            self.ax.clear()
            self.ax.plot(xs, ys, 'b-')

            # Afisare prag selectat pe grafic
            self.ax.axhline(self.threshold_var.get(), color='red', linestyle='dotted', linewidth=2, label='Prag')
            self.ax.set_title("Nivel sunet")
            self.ax.set_xlabel("Timp [s]")
            self.ax.set_ylabel("dB")

            # Actualizeaza plot-ul cand nu esti ocupat
            self.canvas.draw_idle()

            # Output time between plot updates
            now = time.time()
            if last_plot_time is not None:
                delta_ms = (now - last_plot_time) * 1000
                self.plot_update_times.append(delta_ms)
                if len(self.plot_update_times) > 15:
                    self.plot_update_times.pop(0)
                self.plot_update_sum += delta_ms
                self.plot_update_count += 1
                if delta_ms > self.plot_update_max:
                    self.plot_update_max = delta_ms
                times_str = " ".join(f"{t:.0f}" for t in self.plot_update_times)
                avg_session = self.plot_update_sum / self.plot_update_count
                self.plot_times_var.set(
                    f"Δt(ms): [{times_str}]  |  Avg: {avg_session:.1f}  Max: {self.plot_update_max:.1f}"
                )
            last_plot_time = now

            # Delay 
            # time.sleep(0.05)

    # Lampa
    def _set_lamp(self, color):
        self.lamp.itemconfig("led", fill=color)

    # Zona status
    def _set_status(self, text):
        self.status_text.config(state='normal')
        self.status_text.delete('1.0', tk.END)
        self.status_text.insert(tk.END, text)
        self.status_text.config(state='disabled')

    # Oprire program
    def on_close(self):
        self.running = False
        self._set_status("Program oprit")
        self._set_lamp('orange')

        # Salvare dataset AI & confirmare salvare
        self.ai._save_state()
        if hasattr(self.ai, 'save_path'):
            print(f"[PatternAI] State saved to {self.ai.save_path}")
            # Show confirmation when model is saved
            messagebox.showinfo("Model Saved", "PatternAI model saved successfully.")
        self.destroy()

# Daca programul este rulat direct (nu importat), creeaza o instanta,
    # defineste un protocol de oprire
        # si executa un event loop pentru GUI
if __name__ == "__main__":
    app = DecibelMetru()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
