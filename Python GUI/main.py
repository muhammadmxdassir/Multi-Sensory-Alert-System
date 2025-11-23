import threading
import queue
import serial
from serial import SerialException
from plyer import notification
import tkinter as tk
from tkinter import messagebox, scrolledtext

# -----------------------
# SETTINGS
# -----------------------
DEFAULT_PORT = "COM3"     # Arduino port
DEFAULT_BAUD = 9600       # Arduino's Serial.begin(9600)


class AlarmApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Arduino Alarm Monitor")

        # Queue for messages from the serial thread
        self.msg_queue = queue.Queue()

        # Serial & thread control
        self.ser = None
        self.listen_thread = None
        self.stop_event = threading.Event()

        # -----------------------
        # GUI ELEMENTS
        # -----------------------

        # Top frame for settings
        top_frame = tk.Frame(root)
        top_frame.pack(padx=10, pady=10, fill="x")

        # Port
        tk.Label(top_frame, text="Serial Port:").grid(row=0, column=0, sticky="w")
        self.port_entry = tk.Entry(top_frame, width=10)
        self.port_entry.insert(0, DEFAULT_PORT)
        self.port_entry.grid(row=0, column=1, padx=(5, 15))

        # Baud
        tk.Label(top_frame, text="Baud Rate:").grid(row=0, column=2, sticky="w")
        self.baud_entry = tk.Entry(top_frame, width=10)
        self.baud_entry.insert(0, str(DEFAULT_BAUD))
        self.baud_entry.grid(row=0, column=3, padx=(5, 15))

        # Buttons
        self.start_button = tk.Button(top_frame, text="Start Listening", command=self.start_listening)
        self.start_button.grid(row=0, column=4, padx=5)

        self.stop_button = tk.Button(top_frame, text="Stop", command=self.stop_listening, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=5, padx=5)

        # Status label
        self.status_label = tk.Label(root, text="Status: Not connected", fg="red")
        self.status_label.pack(padx=10, anchor="w")

        # ---- STATUS PANEL: bulbs + LCD display ----
        status_panel = tk.Frame(root)
        status_panel.pack(padx=10, pady=(5, 10), fill="x")

        # Canvas for bulbs
        self.bulb_canvas = tk.Canvas(status_panel, width=170, height=90, bg="black", highlightthickness=0)
        self.bulb_canvas.grid(row=0, column=0, padx=(0, 15))

        # Green bulb (OK)
        self.green_bulb = self.bulb_canvas.create_oval(
            10, 10, 70, 70,
            fill="grey20", outline="white", width=2
        )
        self.bulb_canvas.create_text(40, 80, text="OK", fill="white", font=("Arial", 9, "bold"))

        # Red bulb (ALARM)
        self.red_bulb = self.bulb_canvas.create_oval(
            100, 10, 160, 70,
            fill="grey20", outline="white", width=2
        )
        self.bulb_canvas.create_text(130, 80, text="ALARM", fill="white", font=("Arial", 9, "bold"))

        # LCD-style label
        lcd_frame = tk.Frame(status_panel, bg="black")
        lcd_frame.grid(row=0, column=1, sticky="w")

        self.lcd_label = tk.Label(
            lcd_frame,
            text="Not Connected",
            bg="#003300",         # dark green background
            fg="#00FF00",         # bright green text
            font=("Consolas", 18, "bold"),
            width=18,
            height=2,
            bd=4,
            relief="sunken"
        )
        self.lcd_label.pack()

        # Log box
        self.log_box = scrolledtext.ScrolledText(root, width=70, height=15, state=tk.DISABLED)
        self.log_box.pack(padx=10, pady=(5, 10))

        # Initial visual state
        self.set_disconnected_state()

        # Start checking the message queue periodically
        self.root.after(100, self.process_queue)

        # Handle closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # -----------------------
    # BULB & LCD HELPERS
    # -----------------------
    def set_bulbs(self, green_on=False, red_on=False):
        """Update the two bulbs' colors."""
        self.bulb_canvas.itemconfig(
            self.green_bulb,
            fill="lime" if green_on else "grey20"
        )
        self.bulb_canvas.itemconfig(
            self.red_bulb,
            fill="red" if red_on else "grey20"
        )

    def set_disconnected_state(self):
        """No connection yet."""
        self.set_bulbs(green_on=False, red_on=False)
        self.lcd_label.config(text="Not Connected")

    def set_system_active(self):
        """System listening, no alarm."""
        self.set_bulbs(green_on=True, red_on=False)
        self.lcd_label.config(text="System Active")

    def set_alarm_state(self):
        """Alarm has been triggered."""
        self.set_bulbs(green_on=False, red_on=True)
        self.lcd_label.config(text="ALARM")

    # -----------------------
    # SERIAL LISTENING
    # -----------------------
    def start_listening(self):
        port = self.port_entry.get().strip()
        baud_text = self.baud_entry.get().strip()

        if not port:
            messagebox.showerror("Error", "Please enter a serial port (e.g., COM3).")
            return

        try:
            baud = int(baud_text)
        except ValueError:
            messagebox.showerror("Error", "Baud rate must be a number (e.g., 9600).")
            return

        try:
            self.ser = serial.Serial(port, baud, timeout=1)
        except SerialException as e:
            messagebox.showerror("Connection Error", f"Could not open port {port}.\n\nDetails:\n{e}")
            self.update_status(f"Status: Failed to connect to {port}", "red")
            self.set_disconnected_state()
            return

        # Set up threading
        self.stop_event.clear()
        self.listen_thread = threading.Thread(target=self.read_serial_loop, daemon=True)
        self.listen_thread.start()

        self.update_status(f"Status: Listening on {port} at {baud} baud", "green")
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.write_log(f"Opened port {port} at {baud} baud.\n")

        # Visually: system is active, ready for alarm
        self.set_system_active()

    def stop_listening(self):
        self.stop_event.set()

        # Close serial safely
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except SerialException:
                pass
            self.ser = None

        self.update_status("Status: Not connected", "red")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.write_log("Stopped listening and closed serial port.\n")

        # Back to disconnected visuals
        self.set_disconnected_state()

    def read_serial_loop(self):
        while not self.stop_event.is_set():
            try:
                if self.ser and self.ser.is_open:
                    line_bytes = self.ser.readline()
                    if not line_bytes:
                        continue
                    try:
                        line = line_bytes.decode(errors="ignore").strip()
                    except UnicodeDecodeError:
                        continue

                    if line:
                        # Send message to GUI thread via queue
                        self.msg_queue.put(line)
                else:
                    break
            except SerialException:
                self.msg_queue.put("__ERROR__ Lost connection to serial port.")
                break

    # -----------------------
    # GUI HELPERS
    # -----------------------
    def process_queue(self):
        """Check the queue for new messages from the serial thread."""
        try:
            while True:
                line = self.msg_queue.get_nowait()
                if line.startswith("__ERROR__"):
                    self.write_log(line + "\n")
                    messagebox.showerror("Serial Error", line.replace("__ERROR__", "").strip())
                    self.stop_listening()
                else:
                    self.write_log(f"Received: {line}\n")
                    if line == "ALARM_TRIGGERED":
                        self.handle_alarm_triggered()
                    elif line == "ALARM_CLEARED":
                        # When the button is released → back to green
                        self.set_system_active()
        except queue.Empty:
            pass

        # Schedule the next check
        self.root.after(100, self.process_queue)

    def write_log(self, text):
        self.log_box.config(state=tk.NORMAL)
        self.log_box.insert(tk.END, text)
        self.log_box.see(tk.END)
        self.log_box.config(state=tk.DISABLED)

    def update_status(self, text, color="black"):
        self.status_label.config(text=text, fg=color)

    def handle_alarm_triggered(self):
        # Update the visual panel first
        self.set_alarm_state()

        # GUI pop-up
        messagebox.showwarning("ALARM ALERT", "Your alarm system has been triggered!")
        # Desktop notification
        notification.notify(
            title="ALARM ALERT",
            message="Your Arduino alarm has been triggered!",
            timeout=5
        )

    def on_close(self):
        self.stop_listening()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AlarmApp(root)
    root.mainloop()
