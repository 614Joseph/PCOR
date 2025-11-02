import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import json
import os
import base64
from io import BytesIO
from PIL import Image, ImageGrab, ImageTk, ImageDraw
import pyperclip
from pystray import Icon, Menu, MenuItem
from PIL import Image as PILImage
import sys
import ollama

class PCORApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PCOR")
        self.root.geometry("900x600")
        self.root.minsize(700, 500)
        
        # Windows 11 style colors
        self.bg_color = "#f3f3f3"
        self.toolbar_color = "#ffffff"
        self.accent_color = "#0067C0"
        self.text_color = "#1f1f1f"
        
        self.root.configure(bg=self.bg_color)
        
        # Load configuration
        self.load_config()
        
        # State variables
        self.screenshots = []
        self.max_screenshots = 3
        self.multi_mode = tk.BooleanVar(value=False)
        self.is_capturing = False
        self.capture_window = None
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        
        # Setup UI
        self.setup_ui()
        
        # Apply saved settings
        if self.config.get("ui", {}).get("start_minimized", False):
            self.root.withdraw()
        
        # System tray setup
        self.tray_icon = None
        self.setup_tray()
        
        # Protocol for window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Check Ollama connection
        self.root.after(500, self.check_ollama)
    
    def load_config(self):
        """Load configuration from config.json"""
        try:
            with open('config.json', 'r') as f:
                self.config = json.load(f)
        except Exception as e:
            self.config = {
                "model": {
                    "name": "minicpm-v",
                    "alternatives": ["minicpm-v:latest"],
                    "ollama_host": "http://localhost:11434"
                },
                "ui": {
                    "window_size": "900x600",
                    "start_minimized": False
                },
                "ocr": {
                    "prompt": "Copy the text from the image character by character. Do not use *text* or **text** or ###text or any special symbols for formatting. Write plain text only. Preserve line breaks."
                }
            }
    
    def save_config(self):
        """Save configuration to config.json"""
        self.config["ui"]["window_size"] = f"{self.root.winfo_width()}x{self.root.winfo_height()}"
        
        try:
            with open('config.json', 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Failed to save config: {e}")
    
    def check_ollama(self):
        """Check if Ollama is running and model is available"""
        try:
            models = ollama.list()
            model_name = self.config["model"]["name"]
            
            model_found = any(model_name in model['name'] for model in models.get('models', []))
            
            if not model_found:
                self.status_label.config(text=f"Model '{model_name}' not found")
            else:
                self.status_label.config(text="Ready")
        except Exception as e:
            self.status_label.config(text="Ollama not running")
    
    def create_icon_button(self, parent, text, command, width=10):
        """Create a Windows 11 style button"""
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI", 10),
            bg=self.toolbar_color,
            fg=self.text_color,
            relief=tk.FLAT,
            bd=0,
            padx=15,
            pady=8,
            cursor="hand2",
            width=width
        )
        
        def on_enter(e):
            btn.config(bg="#e6e6e6")
        
        def on_leave(e):
            btn.config(bg=self.toolbar_color)
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn
    
    def setup_ui(self):
        """Setup Windows 11 style UI"""
        
        # Top toolbar
        toolbar = tk.Frame(self.root, bg=self.toolbar_color, height=60)
        toolbar.pack(fill=tk.X, side=tk.TOP)
        toolbar.pack_propagate(False)
        
        # Left buttons
        left_frame = tk.Frame(toolbar, bg=self.toolbar_color)
        left_frame.pack(side=tk.LEFT, padx=10, pady=5)
        
        new_btn = self.create_icon_button(left_frame, "📸 New", self.start_screenshot)
        new_btn.pack(side=tk.LEFT, padx=2)
        
        # Separator
        tk.Frame(toolbar, bg="#d1d1d1", width=1).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        
        # Mode frame
        mode_frame = tk.Frame(toolbar, bg=self.toolbar_color)
        mode_frame.pack(side=tk.LEFT, padx=5)
        
        tk.Label(mode_frame, text="Mode:", bg=self.toolbar_color, 
                font=("Segoe UI", 9), fg=self.text_color).pack(side=tk.LEFT, padx=5)
        
        rect_btn = self.create_icon_button(mode_frame, "▢", None, width=3)
        rect_btn.pack(side=tk.LEFT, padx=2)
        rect_btn.config(bg="#e6e6e6")
        
        tk.Checkbutton(
            mode_frame,
            text="Multi (3x)",
            variable=self.multi_mode,
            font=("Segoe UI", 9),
            bg=self.toolbar_color,
            fg=self.text_color,
            selectcolor=self.toolbar_color,
            activebackground=self.toolbar_color,
            command=self.toggle_multi_mode,
            relief=tk.FLAT
        ).pack(side=tk.LEFT, padx=5)
        
        # Right controls
        right_frame = tk.Frame(toolbar, bg=self.toolbar_color)
        right_frame.pack(side=tk.RIGHT, padx=10, pady=5)
        
        tk.Label(right_frame, text="Model:", bg=self.toolbar_color,
                font=("Segoe UI", 9), fg=self.text_color).pack(side=tk.LEFT, padx=5)
        
        self.model_var = tk.StringVar(value=self.config["model"]["name"])
        models = [self.config["model"]["name"]] + self.config["model"].get("alternatives", [])
        
        self.model_dropdown = ttk.Combobox(
            right_frame,
            textvariable=self.model_var,
            values=models,
            state="readonly",
            width=18
        )
        self.model_dropdown.pack(side=tk.LEFT, padx=5)
        self.model_dropdown.bind('<<ComboboxSelected>>', self.on_model_change)
        
        # Main content
        content_frame = tk.Frame(self.root, bg=self.bg_color)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Screenshot preview
        preview_frame = tk.Frame(content_frame, bg="#ffffff")
        preview_frame.pack(fill=tk.X, padx=20, pady=(20, 10))
        
        preview_header = tk.Frame(preview_frame, bg="#ffffff")
        preview_header.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Label(
            preview_header,
            text="Screenshots",
            font=("Segoe UI", 11, "bold"),
            bg="#ffffff",
            fg=self.text_color
        ).pack(side=tk.LEFT)
        
        self.send_btn = tk.Button(
            preview_header,
            text="Process",
            command=self.process_screenshots,
            font=("Segoe UI", 10),
            bg=self.accent_color,
            fg="#ffffff",
            relief=tk.FLAT,
            bd=0,
            padx=20,
            pady=5,
            cursor="hand2",
            state=tk.DISABLED
        )
        self.send_btn.pack(side=tk.RIGHT)
        
        # Thumbnails
        self.thumbnail_frame = tk.Frame(preview_frame, bg="#ffffff", height=100)
        self.thumbnail_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        self.thumbnail_widgets = []
        
        # OCR result
        result_frame = tk.Frame(content_frame, bg="#ffffff")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        result_header = tk.Frame(result_frame, bg="#ffffff")
        result_header.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Label(
            result_header,
            text="Extracted Text",
            font=("Segoe UI", 11, "bold"),
            bg="#ffffff",
            fg=self.text_color
        ).pack(side=tk.LEFT)
        
        tk.Button(
            result_header,
            text="📋 Copy",
            command=self.copy_text,
            font=("Segoe UI", 10),
            bg=self.toolbar_color,
            fg=self.text_color,
            relief=tk.FLAT,
            bd=0,
            padx=15,
            pady=5,
            cursor="hand2"
        ).pack(side=tk.RIGHT)
        
        # Text area
        self.text_area = scrolledtext.ScrolledText(
            result_frame,
            font=("Consolas", 10),
            wrap=tk.WORD,
            bg="#fafafa",
            relief=tk.FLAT,
            bd=0
        )
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        self.text_area.config(state=tk.DISABLED)
        
        # Status bar
        status_bar = tk.Frame(self.root, bg=self.toolbar_color, height=30)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        status_bar.pack_propagate(False)
        
        self.status_label = tk.Label(
            status_bar,
            text="Checking...",
            font=("Segoe UI", 9),
            fg="#666666",
            bg=self.toolbar_color,
            anchor=tk.W
        )
        self.status_label.pack(side=tk.LEFT, padx=15)
    
    def on_model_change(self, event=None):
        """Handle model selection change"""
        new_model = self.model_var.get()
        self.config["model"]["name"] = new_model
        self.save_config()
        self.status_label.config(text=f"Model: {new_model}")
        self.root.after(2000, lambda: self.status_label.config(text="Ready"))
    
    def toggle_multi_mode(self):
        """Handle multi-mode toggle"""
        if self.multi_mode.get():
            self.send_btn.config(state=tk.NORMAL if self.screenshots else tk.DISABLED)
        else:
            self.send_btn.config(state=tk.DISABLED)
    
    def start_screenshot(self):
        """Start screenshot capture"""
        if self.is_capturing:
            return
        
        self.is_capturing = True
        self.status_label.config(text="Select area... (ESC to cancel)")
        
        self.root.withdraw()
        self.root.after(100, self.create_capture_window)
    
    def create_capture_window(self):
        """Create capture overlay"""
        self.capture_window = tk.Toplevel(self.root)
        self.capture_window.attributes('-fullscreen', True)
        self.capture_window.attributes('-alpha', 0.3)
        self.capture_window.attributes('-topmost', True)
        self.capture_window.config(cursor="cross")
        
        self.canvas = tk.Canvas(self.capture_window, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.canvas.bind('<Button-1>', self.on_mouse_down)
        self.canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_up)
        self.capture_window.bind('<Escape>', self.cancel_capture)
    
    def on_mouse_down(self, event):
        """Handle mouse down"""
        self.start_x = event.x
        self.start_y = event.y
        
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline='red', width=2
        )
    
    def on_mouse_drag(self, event):
        """Handle mouse drag"""
        if self.rect_id:
            self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)
    
    def on_mouse_up(self, event):
        """Handle mouse up - capture"""
        end_x = event.x
        end_y = event.y
        
        self.capture_window.destroy()
        self.capture_window = None
        
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)
        
        if abs(x2 - x1) < 10 or abs(y2 - y1) < 10:
            self.is_capturing = False
            self.root.deiconify()
            self.status_label.config(text="Cancelled - area too small")
            return
        
        self.root.after(100, lambda: self.capture_screenshot(x1, y1, x2, y2))
    
    def cancel_capture(self, event=None):
        """Cancel capture"""
        if self.capture_window:
            self.capture_window.destroy()
            self.capture_window = None
        
        self.is_capturing = False
        self.root.deiconify()
        self.status_label.config(text="Cancelled")
    
    def capture_screenshot(self, x1, y1, x2, y2):
        """Capture screenshot"""
        try:
            screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            
            if len(self.screenshots) >= self.max_screenshots:
                self.screenshots.pop(0)
            
            self.screenshots.append(screenshot)
            self.update_thumbnail_display()
            self.root.deiconify()
            
            if not self.multi_mode.get():
                self.status_label.config(text="Processing...")
                self.root.after(100, self.process_screenshots)
            else:
                self.status_label.config(text=f"Captured ({len(self.screenshots)}/3)")
                self.send_btn.config(state=tk.NORMAL)
            
        except Exception as e:
            self.root.deiconify()
            self.status_label.config(text=f"Error: {str(e)}")
        finally:
            self.is_capturing = False
    
    def update_thumbnail_display(self):
        """Update thumbnails"""
        for widget in self.thumbnail_widgets:
            widget.destroy()
        self.thumbnail_widgets.clear()
        
        for idx, screenshot in enumerate(self.screenshots):
            thumb = screenshot.copy()
            thumb.thumbnail((120, 80), Image.Resampling.LANCZOS)
            
            photo = ImageTk.PhotoImage(thumb)
            
            thumb_frame = tk.Frame(self.thumbnail_frame, relief=tk.FLAT, bd=1, bg="#e6e6e6")
            thumb_frame.pack(side=tk.LEFT, padx=5)
            
            thumb_label = tk.Label(thumb_frame, image=photo, bg="#e6e6e6")
            thumb_label.image = photo
            thumb_label.pack(padx=2, pady=2)
            
            remove_btn = tk.Button(
                thumb_frame,
                text="✕",
                fg="red",
                font=("Segoe UI", 8, "bold"),
                command=lambda i=idx: self.remove_screenshot(i),
                cursor="hand2",
                relief=tk.FLAT,
                bg="#e6e6e6"
            )
            remove_btn.pack()
            
            self.thumbnail_widgets.append(thumb_frame)
    
    def remove_screenshot(self, index):
        """Remove screenshot"""
        if 0 <= index < len(self.screenshots):
            self.screenshots.pop(index)
            self.update_thumbnail_display()
            
            if len(self.screenshots) == 0:
                self.send_btn.config(state=tk.DISABLED)
            
            self.status_label.config(text=f"Removed ({len(self.screenshots)}/3)")
    
    def process_screenshots(self):
        """Process screenshots"""
        if not self.screenshots:
            return
        
        self.status_label.config(text="Processing OCR...")
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)
        
        thread = threading.Thread(target=self.run_ocr)
        thread.daemon = True
        thread.start()
    
    def run_ocr(self):
        """Run OCR"""
        results = []
        
        try:
            model_name = self.config["model"]["name"]
            prompt = self.config["ocr"]["prompt"]
            
            for idx, screenshot in enumerate(self.screenshots):
                img_byte_arr = BytesIO()
                screenshot.save(img_byte_arr, format='PNG')
                img_bytes = img_byte_arr.getvalue()
                
                response = ollama.generate(
                    model=model_name,
                    prompt=prompt,
                    images=[img_bytes]
                )
                
                text = response['response']
                
                # Strip markdown
                import re
                text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
                text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
                text = re.sub(r'\*([^*]+)\*', r'\1', text)
                text = re.sub(r'_([^_]+)_', r'\1', text)
                
                if self.multi_mode.get() and len(self.screenshots) > 1:
                    results.append(f"--- Screenshot {idx + 1} ---\n{text}\n")
                else:
                    results.append(text)
            
            combined_text = "\n".join(results)
            
            if not combined_text.strip():
                combined_text = "No text detected."
            
            self.root.after(0, lambda: self.display_ocr_result(combined_text))
            
        except Exception as e:
            error_msg = f"Error: {str(e)}\n\nCheck:\n1. Ollama is running\n2. Model installed"
            self.root.after(0, lambda: self.display_ocr_result(error_msg))
    
    def display_ocr_result(self, text):
        """Display result"""
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(1.0, text)
        self.text_area.config(state=tk.DISABLED)
        
        self.screenshots.clear()
        self.update_thumbnail_display()
        self.send_btn.config(state=tk.DISABLED)
        
        self.status_label.config(text="Complete")
    
    def copy_text(self):
        """Copy text"""
        text = self.text_area.get(1.0, tk.END).strip()
        
        if text and text != "No text detected.":
            pyperclip.copy(text)
            self.status_label.config(text="✓ Copied!")
            self.root.after(2000, lambda: self.status_label.config(text="Ready"))
        else:
            self.status_label.config(text="No text to copy")
    
    def setup_tray(self):
        """Setup tray"""
        icon_image = PILImage.new('RGB', (64, 64), color='#0067C0')
        draw = ImageDraw.Draw(icon_image)
        draw.text((10, 20), "OCR", fill='white')
        
        menu = Menu(
            MenuItem('New Screenshot', self.tray_take_screenshot),
            MenuItem('Show Window', self.show_window),
            MenuItem('Quit', self.quit_app)
        )
        
        self.tray_icon = Icon("PCOR", icon_image, "PCOR", menu)
        
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()
    
    def tray_take_screenshot(self):
        """Take screenshot from tray"""
        self.root.after(0, self.start_screenshot)
    
    def show_window(self):
        """Show window"""
        self.root.after(0, self.root.deiconify)
    
    def on_closing(self):
        """Handle close"""
        self.save_config()
        self.root.withdraw()
    
    def quit_app(self):
        """Quit app"""
        self.save_config()
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()
        sys.exit(0)

def main():
    root = tk.Tk()
    app = PCORApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
