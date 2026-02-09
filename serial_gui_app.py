#!/usr/bin/env python3
"""
Serial Port GUI Application
Allows connecting to a serial port, displaying lines in a text widget,
selecting lines, and sending them individually.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import serial
import serial.tools.list_ports
import threading
from queue import Queue
import shelve
import os


class SerialGUIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial Port GUI Application")
        self.root.geometry("800x600")
        
        # Serial port connection
        self.ser = None
        self.running = False
        self.queue = Queue()
        self.reader_thread = None
        self.berry_mode = False  # Track if Berry mode is active
        
        # Initialize shelve for persistent storage
        self.config_db = shelve.open(os.path.join(os.path.dirname(__file__), 'serial_config'))
        
        # Create UI
        self.create_widgets()
        self.populate_ports()
        
        # Try to auto-connect with saved settings
        self.root.after(500, self.auto_connect)
        
        # Start monitoring queue
        self.monitor_queue()
    
    def create_widgets(self):
        """Create all UI widgets"""
        # Connection Frame
        conn_frame = ttk.LabelFrame(self.root, text="Serial Connection", padding=10)
        conn_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        # Port selection
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(conn_frame, textvariable=self.port_var, width=20, state="readonly")
        self.port_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # Refresh ports button
        self.refresh_btn = ttk.Button(conn_frame, text="Refresh Ports", command=self.populate_ports)
        self.refresh_btn.grid(row=0, column=2, padx=5)
        
        # Baud rate selection
        ttk.Label(conn_frame, text="Baud Rate:").grid(row=0, column=3, sticky=tk.W, padx=5)
        self.baud_var = tk.StringVar(value="115200")
        baud_combo = ttk.Combobox(conn_frame, textvariable=self.baud_var, 
                                   values=["9600", "19200", "38400", "57600", "115200"], 
                                   width=10, state="readonly")
        baud_combo.grid(row=0, column=4, sticky=tk.W, padx=5)
        
        # Connect/Disconnect button
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=5, padx=5)
        
        # Status label
        self.status_label = ttk.Label(conn_frame, text="Status: Disconnected", foreground="red")
        self.status_label.grid(row=1, column=0, columnspan=6, sticky=tk.W, padx=5, pady=5)
        
        # Text display frame
        text_frame = ttk.LabelFrame(self.root, text="Text Lines", padding=10)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create notebook (tabs) for Normal and Berry modes
        self.notebook = ttk.Notebook(text_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Normal mode tab
        normal_frame = ttk.Frame(self.notebook)
        self.notebook.add(normal_frame, text="Normal mode")
        
        self.text_widget = scrolledtext.ScrolledText(normal_frame, height=15, width=80, 
                                                     wrap=tk.WORD)
        self.text_widget.pack(fill=tk.BOTH, expand=True)
        self.text_widget.bind("<Control-Return>", self.send_line_at_cursor)
        self.text_widget.bind("<KeyRelease>", self._on_cursor_move)
        self.text_widget.bind("<ButtonRelease-1>", self._on_cursor_move)
        self.text_widget.bind("<Motion>", self._on_cursor_move)
        
        # Berry mode tab
        berry_frame = ttk.Frame(self.notebook)
        self.notebook.add(berry_frame, text="Berry mode")
        
        self.text_widget_berry = scrolledtext.ScrolledText(berry_frame, height=15, width=80, 
                                                           wrap=tk.WORD)
        self.text_widget_berry.pack(fill=tk.BOTH, expand=True)
        self.text_widget_berry.bind("<Control-Return>", self.send_line_at_cursor)
        self.text_widget_berry.bind("<KeyRelease>", self._on_cursor_move)
        self.text_widget_berry.bind("<ButtonRelease-1>", self._on_cursor_move)
        self.text_widget_berry.bind("<Motion>", self._on_cursor_move)
        
        # Bind tab change event
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)
        
        # Configure text tags for selection and cursor highlight
        self.text_widget.tag_config("selected_line", background="lightblue")
        self.text_widget_berry.tag_config("selected_line", background="lightblue")
        self.text_widget.tag_config("current_line", background="#fff2a8")
        self.text_widget_berry.tag_config("current_line", background="#fff2a8")
        
        # Control Frame
        control_frame = ttk.Frame(self.root, padding=10)
        control_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        
        # Clear text button
        clear_btn = ttk.Button(control_frame, text="Clear Text", command=self.clear_text)
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Send selected line button (shows shortcut)
        send_sel_btn = ttk.Button(control_frame, text="Send Selected Line (Ctrl+Enter)", command=self.send_selected_line)
        send_sel_btn.pack(side=tk.LEFT, padx=5)
        
        # Send all lines button (show shortcut)
        send_all_btn = ttk.Button(control_frame, text="Send All Lines (Ctrl+Shift+A)", command=self.send_all_lines)
        send_all_btn.pack(side=tk.LEFT, padx=5)

        # Open file button
        open_btn = ttk.Button(control_frame, text="Open File (Ctrl+O)", command=self.open_file)
        open_btn.pack(side=tk.LEFT, padx=5)
        # Bind global shortcut for send all
        self.root.bind_all('<Control-Shift-A>', lambda e: self.send_all_lines())
        # Bind global shortcut for open file (both lower and upper O)
        self.root.bind_all('<Control-o>', lambda e: self.open_file())
        self.root.bind_all('<Control-O>', lambda e: self.open_file())
        
        # Status message bar (at the bottom above serial output)
        self.status_message = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, font=("Arial", 9))
        self.status_message.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)
        
        # Status bar frame at the bottom
        status_frame = ttk.LabelFrame(self.root, text="Serial Output", padding=5)
        status_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Status bar text widget
        self.statusbar = scrolledtext.ScrolledText(status_frame, height=10, width=80, 
                                                   wrap=tk.WORD, font=("Arial", 9))
        self.statusbar.pack(fill=tk.BOTH, expand=True)
        self.statusbar.insert(tk.END, "Waiting for data...")
        self.statusbar.config(state=tk.DISABLED)
        
        # Make status frame resizable with a separator
        separator = ttk.Separator(self.root, orient=tk.HORIZONTAL)
        separator.pack(side=tk.BOTTOM, fill=tk.X)
        # Initialize current-line highlight
        self._on_cursor_move()
    
    def populate_ports(self):
        """Populate available serial ports"""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.current(0)
        else:
            messagebox.showwarning("Warning", "No serial ports found")
    
    def toggle_connection(self):
        """Toggle serial connection"""
        if not self.ser or not self.ser.is_open:
            self.connect()
        else:
            self.disconnect()
    
    def connect(self):
        """Connect to serial port"""
        port = self.port_var.get()
        baud = int(self.baud_var.get())
        
        if not port:
            self.set_status_message("Error: Please select a port", "red")
            return
        
        try:
            self.ser = serial.Serial(port, baud, timeout=1)
            self.running = True
            self.connect_btn.config(text="Disconnect")
            self.status_label.config(text=f"Status: Connected to {port} at {baud} baud", foreground="green")
            self.set_status_message(f"Connected to {port} at {baud} baud")
            self.port_combo.config(state="disabled")
            
            # Save settings to shelve
            self.config_db['last_port'] = port
            self.config_db['last_baud'] = baud
            self.config_db.sync()
            
            # Start reader thread
            self.reader_thread = threading.Thread(target=self.read_serial_data, daemon=True)
            self.reader_thread.start()
        except Exception as e:
            self.set_status_message(f"Error: Could not connect to port - {str(e)}", "red")
    
    def disconnect(self):
        """Disconnect from serial port"""
        try:
            if self.ser and self.ser.is_open:
                self.running = False
                self.ser.close()
                self.connect_btn.config(text="Connect")
                self.status_label.config(text="Status: Disconnected", foreground="red")
                self.set_status_message("Disconnected")
                self.port_combo.config(state="readonly")
        except Exception as e:
            self.set_status_message(f"Error disconnecting: {str(e)}", "red")
    
    def send_selected_line(self):
        """Send selected line(s) to serial port"""
        if not self.ser or not self.ser.is_open:
            self.set_status_message("Error: Not connected to serial port", "red")
            return
        
        try:
            # Determine active text widget
            active_tab = self.notebook.index(self.notebook.select())
            text_widget = self.text_widget if active_tab == 0 else self.text_widget_berry

            # Try to get selected text; if none, use the line at cursor
            try:
                selected_text = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            except tk.TclError:
                selected_text = None

            if selected_text and selected_text.strip():
                self._clear_statusbar()  # Clear serial output
                lines = selected_text.split('\n')
                count = 0
                for line in lines:
                    if line.strip():
                        # Berry prefix if needed
                        out = ("br " + line) if active_tab == 1 else line
                        self.ser.write((out + '\n').encode('utf-8'))
                        count += 1
                self.set_status_message(f"Sent {count} line(s)")
            else:
                # Send current line at cursor
                cursor_pos = text_widget.index(tk.INSERT)
                line_num = int(cursor_pos.split('.')[0])
                line_start = f"{line_num}.0"
                line_end = f"{line_num}.end"
                line_text = text_widget.get(line_start, line_end).strip()
                if line_text:
                    self._clear_statusbar()
                    out = ("br " + line_text) if active_tab == 1 else line_text
                    self.ser.write((out + '\n').encode('utf-8'))
                    # highlight this line
                    self._highlight_line_in_widget(text_widget, line_num)
                    self.set_status_message("Line sent")
                else:
                    self.set_status_message("Warning: Line is empty", "orange")
        except Exception as e:
            self.set_status_message(f"Error: Could not send data - {str(e)}", "red")
    
    def send_line_at_cursor(self, event=None):
        """Send the line at cursor position to serial port"""
        if not self.ser or not self.ser.is_open:
            self.set_status_message("Error: Not connected to serial port", "red")
            return "break"
        
        try:
            # Get the active text widget based on current tab
            active_tab = self.notebook.index(self.notebook.select())
            if active_tab == 0:  # Normal mode
                text_widget = self.text_widget
            else:  # Berry mode
                text_widget = self.text_widget_berry
            
            # Get cursor position
            cursor_pos = text_widget.index(tk.INSERT)
            line_num = int(cursor_pos.split('.')[0])
            
            # Get the line at cursor position
            line_start = f"{line_num}.0"
            line_end = f"{line_num}.end"
            line_text = text_widget.get(line_start, line_end).strip()
            
            if line_text:  # Only send if line has content
                self._clear_statusbar()  # Clear serial output
                
                # Add "br " prefix in Berry mode
                if active_tab == 1:  # Berry mode
                    line_text = "br " + line_text
                
                self.ser.write((line_text + '\n').encode('utf-8'))
                self.set_status_message("Line sent")
            else:
                self.set_status_message("Warning: Line is empty", "orange")
        except Exception as e:
            self.set_status_message(f"Error: Could not send data - {str(e)}", "red")
        
        return "break"  # Prevent default Enter behavior
    
    def send_all_lines(self, event=None):
        """Send all lines from the active tab to serial port"""
        if not self.ser or not self.ser.is_open:
            self.set_status_message("Error: Not connected to serial port", "red")
            return "break"

        try:
            active_tab = self.notebook.index(self.notebook.select())
            text_widget = self.text_widget if active_tab == 0 else self.text_widget_berry
            text = text_widget.get(1.0, tk.END)
            if text.strip():
                self._clear_statusbar()  # Clear serial output
                lines = text.split('\n')
                count = 0
                for line in lines:
                    if line.strip():  # Skip empty lines
                        out = ("br " + line) if active_tab == 1 else line
                        self.ser.write((out + '\n').encode('utf-8'))
                        count += 1
                self.set_status_message(f"Sent {count} line(s)")
            else:
                self.set_status_message("Warning: Text area is empty", "orange")
        except Exception as e:
            self.set_status_message(f"Error: Could not send data - {str(e)}", "red")
        return "break"
    
    def clear_text(self):
        """Clear the text widget"""
        # Clear the active tab's text widget
        try:
            active_tab = self.notebook.index(self.notebook.select())
            widget = self.text_widget if active_tab == 0 else self.text_widget_berry
            widget.delete(1.0, tk.END)
        except Exception:
            pass

    def open_file(self):
        """Open a text file (starting in script dir) and load into active tab"""
        try:
            start_dir = os.path.dirname(__file__)
        except Exception:
            start_dir = os.getcwd()

        filepath = filedialog.askopenfilename(initialdir=start_dir,
                                              title="Open Text File",
                                              filetypes=[("Text Files", "*.txt"), ("All Files", "*")])
        if not filepath:
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            active_tab = self.notebook.index(self.notebook.select())
            widget = self.text_widget if active_tab == 0 else self.text_widget_berry
            widget.delete(1.0, tk.END)
            widget.insert(tk.END, content)
            self.set_status_message(f"Loaded file: {os.path.basename(filepath)}")
            # update highlight
            self._on_cursor_move()
        except Exception as e:
            self.set_status_message(f"Error loading file: {str(e)}", "red")
    
    def set_status_message(self, message, color="black"):
        """Set the status message at the bottom"""
        self.status_message.config(text=message, foreground=color)
    
    def _clear_statusbar(self):
        """Clear the serial output"""
        self.statusbar.config(state=tk.NORMAL)
        self.statusbar.delete(1.0, tk.END)
        self.statusbar.config(state=tk.DISABLED)

    def _highlight_line_in_widget(self, widget, line_num):
        """Highlight a specific line number in the given text widget"""
        try:
            widget.tag_remove("current_line", "1.0", tk.END)
            start = f"{line_num}.0"
            end = f"{line_num}.end"
            widget.tag_add("current_line", start, end)
            widget.see(start)
        except Exception:
            pass

    def _clear_line_highlights(self):
        """Clear highlights on both text widgets"""
        try:
            self.text_widget.tag_remove("current_line", "1.0", tk.END)
        except Exception:
            pass
        try:
            self.text_widget_berry.tag_remove("current_line", "1.0", tk.END)
        except Exception:
            pass

    def _on_cursor_move(self, event=None):
        """Called when cursor moves or user clicks — highlight current line in the widget"""
        widget = None
        if event is not None and hasattr(event, 'widget'):
            widget = event.widget
        else:
            # choose based on active tab
            active_tab = self.notebook.index(self.notebook.select())
            widget = self.text_widget if active_tab == 0 else self.text_widget_berry

        try:
            idx = widget.index(tk.INSERT)
            line_num = int(idx.split('.')[0])
            self._highlight_line_in_widget(widget, line_num)
        except Exception:
            pass
    
    def _update_statusbar(self, text):
        """Update the status bar text widget"""
        self.statusbar.config(state=tk.NORMAL)
        self.statusbar.insert(tk.END, text)
        self.statusbar.see(tk.END)  # Auto-scroll to bottom
        self.statusbar.config(state=tk.DISABLED)
    
    def on_tab_change(self, event=None):
        """Handle tab change event"""
        active_tab = self.notebook.index(self.notebook.select())
        if active_tab == 0:
            self.berry_mode = False
        else:
            self.berry_mode = True
        # Update highlight for the newly selected tab
        self._on_cursor_move()
    
    def monitor_queue(self):
        """Monitor queue for any messages"""
        # Process any data from the serial reader
        try:
            while True:
                data = self.queue.get_nowait()
                self._update_statusbar(data + "\n")
        except:
            pass
        
        self.root.after(100, self.monitor_queue)
    
    def read_serial_data(self):
        """Read data from serial port in a separate thread"""
        while self.running and self.ser and self.ser.is_open:
            try:
                if self.ser.in_waiting > 0:
                    data = self.ser.read(self.ser.in_waiting)
                    text = data.decode('utf-8', errors='ignore').strip()
                    if text:
                        self.queue.put(text)
            except Exception as e:
                self.queue.put(f"Error reading: {str(e)}")
                break
    
    def on_closing(self):
        """Handle window closing"""
        if self.ser and self.ser.is_open:
            self.disconnect()
        if self.config_db:
            self.config_db.close()
        self.root.destroy()
    
    def auto_connect(self):
        """Auto-connect with saved settings if available"""
        try:
            if 'last_port' in self.config_db and 'last_baud' in self.config_db:
                last_port = self.config_db['last_port']
                last_baud = self.config_db['last_baud']
                
                # Check if the port still exists
                available_ports = [port.device for port in serial.tools.list_ports.comports()]
                if last_port in available_ports:
                    self.port_var.set(last_port)
                    self.baud_var.set(str(last_baud))
                    self.connect()
        except Exception as e:
            self.set_status_message(f"Auto-connect failed: {str(e)}", "orange")


def main():
    root = tk.Tk()
    app = SerialGUIApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
