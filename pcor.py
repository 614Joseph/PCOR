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
        self.root.title("PCOR - Screenshot OCR")
        self.root.geometry("600x700")
        self.root.minsize(500, 600)
        
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
                    "name": "minicpm-v:2b",
                    "alternatives": ["minicpm-v:8b"],
                    "ollama_host": "http://localhost:11434"
                },
                "ui": {
                    "window_size": "600x700",
                    "start_minimized": False
                },
                "ocr": {
                    "prompt": "Extract all text from this image. Preserve the original layout and formatting. Return only the extracted text, line by line."
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
                self.status_label.config(
                    text=f"⚠ Model '{model_name}' not found. Run: ollama pull {model_name}",
                    fg="red"
                )
            else:
                self.status_label.config(text="Ready", fg="#666666")
        except Exception as e:
            self.status_label.config(
                text="⚠ Ollama not running. Please start Ollama.",
                fg="red"
            )
    
    def setup_ui(self):
        """Setup the main user interface"""
        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Screenshot tray section
        tray_frame = tk.Frame(main_frame, bg="#ffffff", relief=tk.RIDGE, bd=2)
        tray_frame.pack(fill=tk.X, pady=(0, 10))
        
        tray_header = tk.Frame(tray_frame, bg="#ffffff")
        tray_header.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(tray_header, text="Screenshots:", font=("Arial", 10, "bold"), 
                bg="#ffffff").pack(side=tk.LEFT, padx=5)
        
        self.add_btn = tk.Button(tray_header, text="+", font=("Arial", 16, "bold"),
                                fg="#ffffff", bg="#4CAF50", cursor="hand2",
                                width=3, command=self.start_screenshot)
        self.add_btn.pack(side=tk.LEFT, padx=5)
        
        # Model selector
        model_label = tk.Label(tray_header, text="Model:", font=("Arial", 9), 
                              bg="#ffffff")
        model_label.pack(side=tk.LEFT, padx=(20, 5))
        
        self.model_var = tk.StringVar(value=self.config["model"]["name"])
        models = [self.config["model"]["name"]] + self.config["model"].get("alternatives", [])
        self.model_dropdown = ttk.Combobox(tray_header, textvariable=self.model_var,
                                          values=models, state="readonly", width=15)
        self.model_dropdown.pack(side=tk.LEFT)
        self.model_dropdown.bind('<<ComboboxSelected>>', self.on_model_change)
        
        # Screenshot thumbnails container
        self.thumbnail_frame = tk.Frame(tray_frame, bg="#ffffff", height=100)
        self.thumbnail_frame.pack(fill=tk.X, padx=5, pady=5)
        self.thumbnail_widgets = []
        
        # Multi toggle and send button
        control_frame = tk.Frame(main_frame, bg="#f0f0f0")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.multi_toggle = tk.Checkbutton(control_frame, text="Multi Mode",
                                          variable=self.multi_mode,
                                          font=("Arial", 10),
                                          command=self.toggle_multi_mode,
                                          bg="#f0f0f0", 
                                          selectcolor="#2196F3",
                                          activebackground="#f0f0f0")
        self.multi_toggle.pack(side=tk.LEFT, padx=5)
        
        self.send_btn = tk.Button(control_frame, text="Send to OCR",
                                 font=("Arial", 10, "bold"),
                                 fg="#ffffff", bg="#FF9800",
                                 cursor="hand2", state=tk.DISABLED,
                                 command=self.process_screenshots)
        self.send_btn.pack(side=tk.LEFT, padx=5)
        
        # OCR result section
        result_frame = tk.Frame(main_frame, bg="#ffffff", relief=tk.RIDGE, bd=2)
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top copy button
        top_button_frame = tk.Frame(result_frame, bg="#ffffff")
        top_button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(top_button_frame, text="OCR Result:", font=("Arial", 10, "bold"),
                bg="#ffffff").pack(side=tk.LEFT, padx=5)
        
        tk.Button(top_button_frame, text="Copy Text", font=("Arial", 9),
                 fg="#ffffff", bg="#2196F3", cursor="hand2",
                 command=self.copy_text).pack(side=tk.RIGHT, padx=5)
        
        # Scrollable text area
        self.text_area = scrolledtext.ScrolledText(result_frame, 
                                                   font=("Consolas", 10),
                                                   wrap=tk.WORD,
                                                   bg="#fafafa",
                                                   relief=tk.FLAT)
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.text_area.config(state=tk.DISABLED)
        
        # Bottom copy button
        bottom_button_frame = tk.Frame(result_frame, bg="#ffffff")
        bottom_button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(bottom_button_frame, text="Copy Text", font=("Arial", 9),
                 fg="#ffffff", bg="#2196F3", cursor="hand2",
                 command=self.copy_text).pack(side=tk.RIGHT, padx=5)
        
        # Status label
        self.status_label = tk.Label(main_frame, text="Checking Ollama...", 
                                    font=("Arial", 9), fg="#666666",
                                    bg="#f0f0f0")
        self.status_label.pack(fill=tk.X, pady=(5, 0))
    
    def on_model_change(self, event=None):
        """Handle model selection change"""
        new_model = self.model_var.get()
        self.config["model"]["name"] = new_model
        self.save_config()
        self.status_label.config(text=f"Model changed to: {new_model}", fg="#2196F3")
        self.root.after(2000, lambda: self.status_label.config(text="Ready", fg="#666666"))
    
    def toggle_multi_mode(self):
        """Handle multi-mode toggle"""
        if self.multi_mode.get():
            self.send_btn.config(state=tk.NORMAL if self.screenshots else tk.DISABLED)
        else:
            self.send_btn.config(state=tk.DISABLED)
    
    def start_screenshot(self):
        """Start screenshot capture mode"""
        if self.is_capturing:
            return
        
        self.is_capturing = True
        self.status_label.config(text="Select area to capture... (Press ESC to cancel)")
        
        self.root.withdraw()
        self.root.after(100, self.create_capture_window)
    
    def create_capture_window(self):
        """Create transparent overlay for screenshot selection"""
        self.capture_window = tk.Toplevel(self.root)
        self.capture_window.attributes('-fullscreen', True)
        self.capture_window.attributes('-alpha', 0.3)
        self.capture_window.attributes('-topmost', True)
        self.capture_window.config(cursor="cross")
        
        self.canvas = tk.Canvas(self.capture_window, bg='black', 
                               highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.canvas.bind('<Button-1>', self.on_mouse_down)
        self.canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_up)
        self.capture_window.bind('<Escape>', self.cancel_capture)
    
    def on_mouse_down(self, event):
        """Handle mouse button press"""
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
            self.canvas.coords(self.rect_id, self.start_x, self.start_y,
                             event.x, event.y)
    
    def on_mouse_up(self, event):
        """Handle mouse button release - capture the selected area"""
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
            self.status_label.config(text="Capture cancelled - area too small")
            return
        
        self.root.after(100, lambda: self.capture_screenshot(x1, y1, x2, y2))
    
    def cancel_capture(self, event=None):
        """Cancel screenshot capture"""
        if self.capture_window:
            self.capture_window.destroy()
            self.capture_window = None
        
        self.is_capturing = False
        self.root.deiconify()
        self.status_label.config(text="Capture cancelled")
    
    def capture_screenshot(self, x1, y1, x2, y2):
        """Capture the screenshot of the selected area"""
        try:
            screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            
            if len(self.screenshots) >= self.max_screenshots:
                self.screenshots.pop(0)
            
            self.screenshots.append(screenshot)
            self.update_thumbnail_display()
            self.root.deiconify()
            
            if not self.multi_mode.get():
                self.status_label.config(text="Processing OCR...")
                self.root.after(100, self.process_screenshots)
            else:
                self.status_label.config(text=f"Screenshot captured ({len(self.screenshots)}/{self.max_screenshots})")
                self.send_btn.config(state=tk.NORMAL)
            
        except Exception as e:
            self.root.deiconify()
            self.status_label.config(text=f"Error capturing screenshot: {str(e)}")
        finally:
            self.is_capturing = False
    
    def update_thumbnail_display(self):
        """Update the thumbnail display in the tray"""
        for widget in self.thumbnail_widgets:
            widget.destroy()
        self.thumbnail_widgets.clear()
        
        for idx, screenshot in enumerate(self.screenshots):
            thumb = screenshot.copy()
            thumb.thumbnail((120, 80), Image.Resampling.LANCZOS)
            
            photo = ImageTk.PhotoImage(thumb)
            
            thumb_frame = tk.Frame(self.thumbnail_frame, relief=tk.RAISED, bd=1)
            thumb_frame.pack(side=tk.LEFT, padx=5)
            
            thumb_label = tk.Label(thumb_frame, image=photo)
            thumb_label.image = photo
            thumb_label.pack()
            
            remove_btn = tk.Button(thumb_frame, text="✕", fg="red", 
                                  font=("Arial", 8, "bold"),
                                  command=lambda i=idx: self.remove_screenshot(i),
                                  cursor="hand2")
            remove_btn.pack()
            
            self.thumbnail_widgets.append(thumb_frame)
    
    def remove_screenshot(self, index):
        """Remove a screenshot from the tray"""
        if 0 <= index < len(self.screenshots):
            self.screenshots.pop(index)
            self.update_thumbnail_display()
            
            if len(self.screenshots) == 0:
                self.send_btn.config(state=tk.DISABLED)
            
            self.status_label.config(text=f"Screenshot removed ({len(self.screenshots)}/{self.max_screenshots})")
    
    def process_screenshots(self):
        """Process all screenshots with OCR"""
        if not self.screenshots:
            return
        
        self.status_label.config(text="Processing OCR...")
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)
        
        thread = threading.Thread(target=self.run_ocr)
        thread.daemon = True
        thread.start()
    
    def run_ocr(self):
        """Run OCR on all screenshots using Ollama"""
        results = []
        
        try:
            model_name = self.config["model"]["name"]
            prompt = self.config["ocr"]["prompt"]
            
            for idx, screenshot in enumerate(self.screenshots):
                # Convert PIL Image to bytes
                img_byte_arr = BytesIO()
                screenshot.save(img_byte_arr, format='PNG')
                img_bytes = img_byte_arr.getvalue()
                
                # Call Ollama with vision model
                response = ollama.generate(
                    model=model_name,
                    prompt=prompt,
                    images=[img_bytes]
                )
                
                text = response['response']
                
                # Strip markdown formatting
                import re
                # Remove ### headers
                text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
                # Remove ** bold
                text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
                # Remove * italic
                text = re.sub(r'\*([^*]+)\*', r'\1', text)
                # Remove _ italic
                text = re.sub(r'_([^_]+)_', r'\1', text)
                
                if self.multi_mode.get() and len(self.screenshots) > 1:
                    results.append(f"--- Screenshot {idx + 1} ---\n{text}\n")
                else:
                    results.append(text)
            
            combined_text = "\n".join(results)
            
            if not combined_text.strip():
                combined_text = "No text detected. Try capturing a clearer region."
            
            self.root.after(0, lambda: self.display_ocr_result(combined_text))
            
        except Exception as e:
            error_msg = f"OCR Error: {str(e)}\n\nPlease ensure:\n1. Ollama is running\n2. Model '{self.config['model']['name']}' is installed"
            self.root.after(0, lambda: self.display_ocr_result(error_msg))
    
    def display_ocr_result(self, text):
        """Display OCR result in text area"""
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(1.0, text)
        self.text_area.config(state=tk.DISABLED)
        
        self.screenshots.clear()
        self.update_thumbnail_display()
        self.send_btn.config(state=tk.DISABLED)
        
        self.status_label.config(text="OCR complete - text ready to copy")
    
    def copy_text(self):
        """Copy text from text area to clipboard"""
        text = self.text_area.get(1.0, tk.END).strip()
        
        if text and text != "No text detected. Try capturing a clearer region.":
            pyperclip.copy(text)
            self.status_label.config(text="✓ Copied to clipboard!")
            self.root.after(2000, lambda: self.status_label.config(text="Ready"))
        else:
            self.status_label.config(text="No text to copy")
    
    def setup_tray(self):
        """Setup system tray icon"""
        icon_image = PILImage.new('RGB', (64, 64), color='#4CAF50')
        draw = ImageDraw.Draw(icon_image)
        draw.text((10, 20), "OCR", fill='white')
        
        menu = Menu(
            MenuItem('Take Screenshot', self.tray_take_screenshot),
            MenuItem('Toggle Multi Mode', self.tray_toggle_multi),
            MenuItem('Show Window', self.show_window),
            MenuItem('Quit', self.quit_app)
        )
        
        self.tray_icon = Icon("PCOR", icon_image, "PCOR - Screenshot OCR", menu)
        
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()
    
    def tray_take_screenshot(self):
        """Take screenshot from tray"""
        self.root.after(0, self.start_screenshot)
    
    def tray_toggle_multi(self):
        """Toggle multi mode from tray"""
        self.root.after(0, lambda: self.multi_mode.set(not self.multi_mode.get()))
    
    def show_window(self):
        """Show main window"""
        self.root.after(0, self.root.deiconify)
    
    def on_closing(self):
        """Handle window close - minimize to tray"""
        self.save_config()
        self.root.withdraw()
    
    def quit_app(self):
        """Quit the application"""
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
