#!/usr/bin/env python3
"""
Serial Port GUI Application
Allows connecting to a serial port, displaying lines in a text widget,
selecting lines, and sending them individually.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import serial
import serial.tools.list_ports
import threading
from queue import Queue


class SerialGUIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial Port GUI Application")
        self.root.geometry("800x600")
        
        # Serial port connection
        self.ser = None
        self.running = False
        self.queue = Queue()
        
        # Create UI
        self.create_widgets()
        self.populate_ports()
        
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
        self.baud_var = tk.StringVar(value="9600")
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
        
        # Scrolled text widget with line numbers
        self.text_widget = scrolledtext.ScrolledText(text_frame, height=15, width=80, 
                                                     wrap=tk.WORD, selectmode=tk.EXTENDED)
        self.text_widget.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags for selection
        self.text_widget.tag_config("selected_line", background="lightblue")
        
        # Control Frame
        control_frame = ttk.Frame(self.root, padding=10)
        control_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        
        # Clear text button
        clear_btn = ttk.Button(control_frame, text="Clear Text", command=self.clear_text)
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Send selected line button
        send_sel_btn = ttk.Button(control_frame, text="Send Selected Line", command=self.send_selected_line)
        send_sel_btn.pack(side=tk.LEFT, padx=5)
        
        # Send all lines button
        send_all_btn = ttk.Button(control_frame, text="Send All Lines", command=self.send_all_lines)
        send_all_btn.pack(side=tk.LEFT, padx=5)
    
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
            messagebox.showerror("Error", "Please select a port")
            return
        
        try:
            self.ser = serial.Serial(port, baud, timeout=1)
            self.running = True
            self.connect_btn.config(text="Disconnect")
            self.status_label.config(text=f"Status: Connected to {port} at {baud} baud", foreground="green")
            self.port_combo.config(state="disabled")
            messagebox.showinfo("Success", f"Connected to {port}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not connect to port: {str(e)}")
    
    def disconnect(self):
        """Disconnect from serial port"""
        try:
            if self.ser and self.ser.is_open:
                self.running = False
                self.ser.close()
                self.connect_btn.config(text="Connect")
                self.status_label.config(text="Status: Disconnected", foreground="red")
                self.port_combo.config(state="readonly")
                messagebox.showinfo("Success", "Disconnected from port")
        except Exception as e:
            messagebox.showerror("Error", f"Error disconnecting: {str(e)}")
    
    def send_selected_line(self):
        """Send selected line(s) to serial port"""
        if not self.ser or not self.ser.is_open:
            messagebox.showerror("Error", "Not connected to serial port")
            return
        
        try:
            # Get selected text
            selected_text = self.text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected_text:
                lines = selected_text.split('\n')
                for line in lines:
                    if line.strip():  # Skip empty lines
                        self.ser.write((line + '\n').encode('utf-8'))
                messagebox.showinfo("Success", f"Sent {len([l for l in lines if l.strip()])} line(s)")
            else:
                messagebox.showwarning("Warning", "No text selected")
        except tk.TclError:
            messagebox.showwarning("Warning", "No text selected")
        except Exception as e:
            messagebox.showerror("Error", f"Could not send data: {str(e)}")
    
    def send_all_lines(self):
        """Send all lines to serial port"""
        if not self.ser or not self.ser.is_open:
            messagebox.showerror("Error", "Not connected to serial port")
            return
        
        try:
            text = self.text_widget.get(1.0, tk.END)
            if text.strip():
                lines = text.split('\n')
                count = 0
                for line in lines:
                    if line.strip():  # Skip empty lines
                        self.ser.write((line + '\n').encode('utf-8'))
                        count += 1
                messagebox.showinfo("Success", f"Sent {count} line(s)")
            else:
                messagebox.showwarning("Warning", "Text area is empty")
        except Exception as e:
            messagebox.showerror("Error", f"Could not send data: {str(e)}")
    
    def clear_text(self):
        """Clear the text widget"""
        self.text_widget.delete(1.0, tk.END)
    
    def monitor_queue(self):
        """Monitor queue for any messages"""
        # This can be extended to receive data from serial port
        self.root.after(100, self.monitor_queue)
    
    def on_closing(self):
        """Handle window closing"""
        if self.ser and self.ser.is_open:
            self.disconnect()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = SerialGUIApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
