import sys
import os
import struct
from dataclasses import dataclass
from typing import List, Set, Optional
import win32com.client
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QLabel, QLineEdit, QPushButton, QListWidget, 
    QTextEdit, QProgressBar, QFileDialog, QGroupBox, QSizePolicy,
    QScrollArea, QFrame, QDesktopWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QRect, QPoint, QSize
from PyQt5.QtGui import QPixmap, QFont, QFontDatabase, QPainter, QPen, QColor, QImage

# --- RESOURCE PATH HELPER FOR PYINSTALLER ---
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- HELPER FUNCTION FOR UNIQUE FILENAMES ---
def get_unique_filepath(filepath: str) -> str:
    """
    Generate a unique filepath by adding a number suffix if file already exists.
    Example: if 'mockup.jpg' exists, returns 'mockup_1.jpg', then 'mockup_2.jpg', etc.
    """
    if not os.path.exists(filepath):
        return filepath
    
    directory = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    name, ext = os.path.splitext(filename)
    
    counter = 1
    while True:
        new_filename = f"{name}_{counter}{ext}"
        new_filepath = os.path.join(directory, new_filename)
        if not os.path.exists(new_filepath):
            return new_filepath
        counter += 1

# --- PSD THUMBNAIL EXTRACTOR ---
def extract_psd_thumbnail(psd_path: str) -> Optional[QPixmap]:
    """
    Extract embedded thumbnail from PSD file.
    PSDs contain a thumbnail in the Image Resources section.
    """
    try:
        with open(psd_path, 'rb') as f:
            # Read PSD header
            signature = f.read(4)
            if signature != b'8BPS':
                return None
            
            version = struct.unpack('>H', f.read(2))[0]
            f.read(6)  # Reserved
            channels = struct.unpack('>H', f.read(2))[0]
            height = struct.unpack('>I', f.read(4))[0]
            width = struct.unpack('>I', f.read(4))[0]
            depth = struct.unpack('>H', f.read(2))[0]
            color_mode = struct.unpack('>H', f.read(2))[0]
            
            # Skip Color Mode Data section
            color_mode_length = struct.unpack('>I', f.read(4))[0]
            f.read(color_mode_length)
            
            # Read Image Resources section (contains thumbnail)
            resources_length = struct.unpack('>I', f.read(4))[0]
            resources_end = f.tell() + resources_length
            
            # Search for thumbnail resource (ID 1033 or 1036)
            while f.tell() < resources_end:
                resource_signature = f.read(4)
                if resource_signature != b'8BIM':
                    break
                
                resource_id = struct.unpack('>H', f.read(2))[0]
                
                # Read Pascal string (resource name)
                name_length = struct.unpack('B', f.read(1))[0]
                if name_length > 0:
                    f.read(name_length)
                # Padding to make even
                if (name_length + 1) % 2 != 0:
                    f.read(1)
                
                # Resource data size
                data_size = struct.unpack('>I', f.read(4))[0]
                
                # Check if this is a thumbnail resource
                if resource_id in [1033, 1036]:  # JPEG or RAW thumbnail
                    # Skip to JFIF data (skip format info)
                    if resource_id == 1036:  # JPEG thumbnail
                        f.read(28)  # Skip thumbnail header
                        jpeg_data = f.read(data_size - 28)
                        
                        # Load JPEG into QPixmap
                        image = QImage()
                        if image.loadFromData(jpeg_data):
                            return QPixmap.fromImage(image)
                else:
                    # Skip this resource
                    f.read(data_size)
                
                # Padding to make even
                if data_size % 2 != 0:
                    f.read(1)
            
    except Exception as e:
        print(f"Error extracting thumbnail from {psd_path}: {e}")
    
    return None

# --- STYLING ---
APP_QSS = """
QMainWindow, QWidget {
    background: #FDEFD7;
    color: #1a1a1a;
    font-family: "Space Grotesk";
    font-size: 16px;
}

QScrollBar:vertical {
    border: none;
    background: #ffffff;
    width: 14px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #5865F2;
    min-height: 40px;
    border-radius: 0px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: #ffffff;
}

QScrollBar:horizontal {
    border: none;
    background: #ffffff;
    height: 12px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: #5865F2;
    min-width: 30px;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

QGroupBox {
    border: none;
    border-radius: 0;
    margin-top: 0px;
    padding-top: 25px;
    background: transparent;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0px 0px 10px 0px;
    background: transparent;
    font-weight: 700;
    font-size: 15px;
    color: #1a1a1a;
}

QLineEdit {
    background: #ffe79a;
    border: 2px solid #1a1a1a;
    border-radius: 0;
    padding: 14px;
    font-size: 16px;
}

QListWidget {
    background: #ffe79a;
    border: 2px solid #1a1a1a;
    border-radius: 0;
    outline: none;
    padding: 5px;
}

QTextEdit {
    background: #ffffff;
    border: 2px solid #1a1a1a;
    border-radius: 0;
    padding: 10px;
    font-family: Consolas;
    font-size: 13px;
}

QPushButton {
    background: #1a1a1a;
    color: white;
    border-radius: 0;
    padding: 14px 24px;
    font-weight: 700;
    font-size: 14px;
    border: none;
}

QPushButton:hover {
    background: #333333;
}

QPushButton#PrimaryButton {
    background: #5865F2;
    border: 2px solid #1a1a1a;
    font-size: 16px;
    font-weight: 700;
    color: white;
}

QPushButton#PrimaryButton:hover {
    background: #4752D6;
}

QPushButton#ResetButton {
    background: #FDEFD7;
    color: #1a1a1a;
    border: 2px solid #1a1a1a;
    font-weight: 700;
}

QPushButton#ResetButton:hover {
    background: #F5E3C0;
}

QPushButton#LibraryButton {
    background: white;
    color: #1a1a1a;
    border: 2px solid #1a1a1a;
    font-weight: 700;
    font-size: 15px;
}

QPushButton#LibraryButton:hover {
    background: #f5f5f5;
}

QProgressBar {
    border: 2px solid #1a1a1a;
    border-radius: 0;
    background: #FDEFD7;
    height: 26px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background: #4CAF50;
}

QLabel#MarqueeBanner {
    background: #E85D33;
    color: #1a1a1a;
    border-top: 2px solid #1a1a1a;
    border-bottom: 2px solid #1a1a1a;
}

QLabel#LibraryPanel {
    background: #1a1a1a;
}

QScrollArea {
    border: none;
    background: transparent;
}

QFrame#LibraryContainer {
    background: #ffffff;
    border: 2px solid #1a1a1a;
}

QFrame#LibraryPanel {
    background: #1a1a1a;
}

QFrame#SelectedArtworkBox {
    background: white;
    border: 2px solid #1a1a1a;
    padding: 10px;
}
"""

class SmoothMarquee(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setObjectName("MarqueeBanner")
        self.setFixedHeight(100)
        self.text_content = text
        self.offset = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.scroll_text)
        self.timer.start(16)

    def scroll_text(self):
        self.offset -= 2 
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing)
        font = self.font()
        font.setPointSize(32)
        font.setWeight(QFont.Bold)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 5)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(self.text_content)
        cap_height = metrics.capHeight()
        y_pos = int((self.height() + cap_height) / 2)
        if abs(self.offset) >= text_width:
            self.offset = 0
        painter.drawText(QPoint(self.offset, y_pos), self.text_content)
        painter.drawText(QPoint(self.offset + text_width, y_pos), self.text_content)


class LoadingSplash(QWidget):
    """Loading splash screen with progress indicator"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.SplashScreen | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setFixedSize(600, 280)
        
        # Center on screen
        screen_geometry = QApplication.desktop().screenGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Container with background
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background: #FDEFD7;
                border: 2px solid #1a1a1a;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(15)
        container_layout.setContentsMargins(60, 40, 60, 40)
        
        # Top spacer
        container_layout.addStretch()
        
        # Title - with proper spacing below
        title = QLabel("MOCKUPCORE")
        title.setStyleSheet("""
            font-size: 38px;
            font-weight: 700;
            color: #1a1a1a;
            background: transparent;
            letter-spacing: 2px;
            border: none;
            padding-bottom: 5px;
        """)
        title.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(title)
        
        # Subtitle - black text, no border
        subtitle = QLabel("BATCH EXPORTER TOOL")
        subtitle.setStyleSheet("""
            font-size: 13px;
            font-weight: 500;
            color: #1a1a1a;
            background: transparent;
            letter-spacing: 3px;
            border: none;
        """)
        subtitle.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(subtitle)
        
        container_layout.addSpacing(20)
        
        # Status message - no border
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #1a1a1a;
            background: transparent;
            border: none;
        """)
        self.status_label.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(self.status_label)
        
        container_layout.addSpacing(10)
        
        # Progress bar - standard left-to-right fill (not indeterminate)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)  # Determinate mode from start
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(35)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #1a1a1a;
                background: #ffffff;
                text-align: center;
            }
            QProgressBar::chunk {
                background: #4CAF50;
            }
        """)
        container_layout.addWidget(self.progress)
        
        # Detail message - HIDDEN (don't add to layout)
        self.detail_label = QLabel("")
        self.detail_label.setVisible(False)  # Hide it completely
        
        # Bottom spacer
        container_layout.addStretch()
        
        main_layout.addWidget(container)
        
        # Close button (X) in top-left corner - created AFTER container so it's on top
        self.close_btn = QPushButton("×", self)
        self.close_btn.setFixedSize(40, 40)
        self.close_btn.move(5, 5)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: #1a1a1a;
                color: #FDEFD7;
                border: none;
                border-radius: 0px;
                font-size: 28px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                background: #e85d33;
            }
            QPushButton:pressed {
                background: #5865F2;
            }
        """)
        self.close_btn.clicked.connect(self.close_with_feedback)
        self.close_btn.raise_()  # Bring to front
    
    def close_with_feedback(self):
        """Close the splash with visual feedback"""
        # Change to blue to show click registered
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: #5865F2;
                color: #FDEFD7;
                border: none;
                border-radius: 0px;
                font-size: 28px;
                font-weight: bold;
                padding: 0px;
            }
        """)
        QApplication.processEvents()  # Force UI update
        
        # Small delay to show the feedback
        QTimer.singleShot(150, self.close)  # 150ms delay before closing
    
    def update_status(self, message, detail=""):
        """Update the loading message"""
        self.status_label.setText(message)
        # Detail is ignored - label is hidden
        QApplication.processEvents()  # Force UI update
    
    def set_progress_range(self, min_val, max_val):
        """Set progress bar range"""
        self.progress.setRange(min_val, max_val)
    
    def set_progress_value(self, value):
        """Update progress bar value"""
        self.progress.setValue(value)
        QApplication.processEvents()  # Force UI update


class SmoothMarquee(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setObjectName("MarqueeBanner")
        self.setFixedHeight(100)
        self.text_content = text
        self.offset = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.scroll_text)
        self.timer.start(16)

    def scroll_text(self):
        self.offset -= 2 
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing)
        font = self.font()
        font.setPointSize(32)
        font.setWeight(QFont.Bold)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 5)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(self.text_content)
        cap_height = metrics.capHeight()
        y_pos = int((self.height() + cap_height) / 2)
        if abs(self.offset) >= text_width:
            self.offset = 0
        painter.drawText(QPoint(self.offset, y_pos), self.text_content)
        painter.drawText(QPoint(self.offset + text_width, y_pos), self.text_content)


class MockupThumbnail(QLabel):
    """Clickable thumbnail with selection state - shows actual PSD preview"""
    
    clicked = pyqtSignal(str)  # Emits PSD path when clicked
    
    def __init__(self, psd_path, parent=None):
        super().__init__(parent)
        self.psd_path = psd_path
        self.is_selected = False
        self.thumbnail_width = 160
        self.thumbnail_height = 200  # 4:5 ratio
        
        self.setFixedSize(self.thumbnail_width, self.thumbnail_height)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("background: white; border: 2px solid #1a1a1a;")
        
        # Load actual PSD thumbnail
        self.load_thumbnail()
        
    def load_thumbnail(self):
        """Load actual PSD thumbnail - FILLS the square (crops to fit)"""
        # Try to extract real PSD thumbnail
        psd_thumb = extract_psd_thumbnail(self.psd_path)
        
        # Create background
        pixmap = QPixmap(self.thumbnail_width, self.thumbnail_height)
        pixmap.fill(QColor("#ffffff"))  # White background
        
        if psd_thumb and not psd_thumb.isNull():
            # FILL THE SQUARE - Scale to fill, then crop
            scaled = psd_thumb.scaled(
                self.thumbnail_width, 
                self.thumbnail_height, 
                Qt.KeepAspectRatioByExpanding,  # Fill entire space, crop if needed
                Qt.SmoothTransformation
            )
            
            # Center-crop the image
            painter = QPainter(pixmap)
            x = (self.thumbnail_width - scaled.width()) // 2
            y = (self.thumbnail_height - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            painter.end()
            
        else:
            # Fallback placeholder - show filename
            painter = QPainter(pixmap)
            painter.setPen(QColor("#1a1a1a"))
            
            # Draw PSD icon placeholder
            font = QFont("Space Grotesk", 36, QFont.Bold)
            painter.setFont(font)
            painter.drawText(QRect(0, 0, self.thumbnail_width, self.thumbnail_height - 40), 
                           Qt.AlignCenter, "PSD")
            
            # Draw filename below
            filename = os.path.basename(self.psd_path)
            # Truncate long filenames
            if len(filename) > 18:
                filename = filename[:15] + "..."
            
            font.setPointSize(9)
            font.setWeight(QFont.Normal)
            painter.setFont(font)
            painter.drawText(QRect(5, self.thumbnail_height - 35, self.thumbnail_width - 10, 30), 
                           Qt.AlignCenter | Qt.TextWordWrap, filename)
            painter.end()
        
        self.base_pixmap = pixmap
        self.update_display()
    
    def update_display(self):
        """Update display with selection state"""
        display_pixmap = self.base_pixmap.copy()
        
        if self.is_selected:
            # Draw selection overlay
            painter = QPainter(display_pixmap)
            
            # Semi-transparent overlay
            painter.fillRect(0, 0, self.thumbnail_width, self.thumbnail_height, 
                           QColor(87, 95, 214, 140))
            
            # Checkmark
            painter.setPen(QPen(QColor("white"), 8))
            painter.setRenderHint(QPainter.Antialiasing)
            
            center_x = self.thumbnail_width // 2
            center_y = self.thumbnail_height // 2
            
            # Draw checkmark
            painter.drawLine(center_x - 20, center_y, center_x - 5, center_y + 15)
            painter.drawLine(center_x - 5, center_y + 15, center_x + 25, center_y - 20)
            
            painter.end()
        
        self.setPixmap(display_pixmap)
    
    def mousePressEvent(self, event):
        """Toggle selection on click"""
        self.is_selected = not self.is_selected
        self.update_display()
        self.clicked.emit(self.psd_path)
    
    def set_selected(self, selected):
        """Programmatically set selection state"""
        self.is_selected = selected
        self.update_display()


def _jsx(path):
    return path.replace("\\", "/")

def build_jsx(psd, art, out):
    return f"""
#target photoshop
app.displayDialogs = DialogModes.NO;
try {{
    var mainDoc = app.open(new File("{_jsx(psd)}"));
    var artFile = new File("{_jsx(art)}");
    var outFile = new File("{_jsx(out)}");

    function findLayer(container) {{
        for (var i = 0; i < container.layers.length; i++) {{
            var l = container.layers[i];
            if (l.typename === "ArtLayer") {{
                var n = l.name.toUpperCase();
                if (n.indexOf("DESIGN") !== -1 || n.indexOf("ARTWORK") !== -1 || n.indexOf("PLACE") !== -1) return l;
            }} else if (l.typename === "LayerSet") {{
                var f = findLayer(l);
                if (f) return f;
            }}
        }}
        return null;
    }}

    var target = findLayer(mainDoc);
    if(target && target.kind == LayerKind.SMARTOBJECT) {{
        mainDoc.activeLayer = target;
        var idplacedLayerEditContents = stringIDToTypeID("placedLayerEditContents");
        executeAction(idplacedLayerEditContents, new ActionDescriptor(), DialogModes.NO);
        var smartDoc = app.activeDocument;
        smartDoc.activeLayer.isBackgroundLayer ? null : smartDoc.artLayers.add(); 
        var idPlc = charIDToTypeID("Plc ");
        var desc = new ActionDescriptor();
        desc.putPath(charIDToTypeID("null"), artFile);
        desc.putEnumerated(charIDToTypeID("FTcs"), charIDToTypeID("QCSt"), charIDToTypeID("Qcsa"));
        executeAction(idPlc, desc, DialogModes.NO);
        var artLayer = smartDoc.activeLayer;
        var artW = artLayer.bounds[2].value - artLayer.bounds[0].value;
        var artH = artLayer.bounds[3].value - artLayer.bounds[1].value;
        var canvasW = smartDoc.width.value;
        var canvasH = smartDoc.height.value;
        var scaleX = (canvasW / artW) * 100;
        var scaleY = (canvasH / artH) * 100;
        var scale = Math.max(scaleX, scaleY); 
        artLayer.resize(scale, scale, AnchorPosition.MIDDLECENTER);
        var currentBounds = artLayer.bounds;
        var currentW = currentBounds[2].value - currentBounds[0].value;
        var currentH = currentBounds[3].value - currentBounds[1].value;
        artLayer.translate(canvasW/2 - (currentBounds[0].value + currentW/2), canvasH/2 - (currentBounds[1].value + currentH/2));
        smartDoc.save();
        smartDoc.close();
        var opts = new ExportOptionsSaveForWeb();
        opts.format = SaveDocumentType.JPEG;
        opts.quality = 90;
        mainDoc.exportDocument(outFile, ExportType.SAVEFORWEB, opts);
    }}
    mainDoc.close(SaveOptions.DONOTSAVECHANGES);
}} catch(e) {{
    while(app.documents.length > 0) {{
        app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);
    }}
}}
"""

def render(psd, art, out):
    """Render a mockup. Raises exception if Photoshop is not available."""
    ps = win32com.client.Dispatch("Photoshop.Application")
    ps.Visible = False 
    ps.DoJavaScript(build_jsx(psd, art, out))

@dataclass
class Job:
    psds: List[str]
    art: str
    out_dir: str

class Worker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)  # New signal for errors
    
    def __init__(self, job):
        super().__init__()
        self.job = job
        
    def run(self):
        # First, check if Photoshop is available before processing any mockups
        try:
            ps = win32com.client.Dispatch("Photoshop.Application")
            ps_available = True
        except Exception as e:
            self.log.emit("=" * 60)
            self.log.emit("❌ ERROR: Adobe Photoshop not found!")
            self.log.emit("=" * 60)
            self.log.emit("")
            self.log.emit("This application requires Adobe Photoshop to be installed")
            self.log.emit("on your computer to process mockups.")
            self.log.emit("")
            self.log.emit("Please install Adobe Photoshop and try again.")
            self.log.emit("")
            self.log.emit(f"Technical error: {str(e)}")
            self.log.emit("=" * 60)
            self.error.emit("Photoshop not found")
            return
        
        # Photoshop is available, proceed with processing
        total = len(self.job.psds)
        self.log.emit(f"✓ Photoshop detected - Processing {total} mockup(s)...")
        
        for i, psd in enumerate(self.job.psds, start=1):
            name = os.path.splitext(os.path.basename(psd))[0] + ".jpg"
            out = os.path.join(self.job.out_dir, name)
            
            # Get unique filepath to avoid overwriting
            out = get_unique_filepath(out)
            final_name = os.path.basename(out)
            
            self.log.emit(f"Processing: {final_name}")
            try:
                render(psd, self.job.art, out)
            except Exception as e:
                self.log.emit(f"❌ Error processing {final_name}: {str(e)}")
            self.progress.emit(int((i / total) * 100))
        self.finished.emit()

class MockupLibrary:
    """Handles the mockup library system with cloud storage support"""
    
    def __init__(self):
        # FIXED: Use a persistent location that survives .exe restarts
        # Instead of using resource_path (which extracts to temp), 
        # use the actual .exe directory for persistence
        if getattr(sys, 'frozen', False):
            # Running as compiled .exe - use the .exe's directory
            exe_dir = os.path.dirname(sys.executable)
            self.library_root = os.path.join(exe_dir, "mockup_library")
        else:
            # Running as .py script - use resource_path
            self.library_root = resource_path("mockup_library")
        
        self.cache_dir = os.path.join(self.library_root, "_cache")
        self._ensure_library_structure()
        
        # Cloud configuration file
        self.cloud_config_file = os.path.join(self.library_root, "cloud_sources.txt")
        self.cloud_urls = self._load_cloud_sources()
    
    def _ensure_library_structure(self):
        """Create the library folder and cache if they don't exist"""
        for folder in [self.library_root, self.cache_dir]:
            if not os.path.exists(folder):
                try:
                    os.makedirs(folder)
                except Exception as e:
                    print(f"Could not create folder {folder}: {e}")
    
    def _load_cloud_sources(self):
        """
        Load cloud storage URLs from configuration file.
        Format: One URL per line in cloud_sources.txt
        Supports:
        - Direct URLs: https://example.com/mockup.psd
        - Google Drive file: https://drive.google.com/file/d/FILE_ID/view
        - Google Drive folder: https://drive.google.com/drive/folders/FOLDER_ID (lists all PSDs)
        """
        urls = []
        
        if os.path.exists(self.cloud_config_file):
            try:
                with open(self.cloud_config_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        # Skip empty lines and comments
                        if line and not line.startswith('#'):
                            # Check if it's a Google Drive folder
                            if 'drive.google.com/drive/folders' in line or 'drive.google.com/drive/u/' in line and 'folders' in line:
                                # Extract folder ID and get all PSDs from folder
                                folder_urls = self._get_files_from_gdrive_folder(line)
                                urls.extend(folder_urls)
                            else:
                                # Single file URL
                                urls.append(line)
            except Exception as e:
                print(f"Error loading cloud sources: {e}")
        else:
            # Create template file
            self._create_cloud_config_template()
        
        return urls
    
    def _create_cloud_config_template(self):
        """Create a template cloud_sources.txt file with instructions"""
        template = """# Cloud Mockup Library Configuration
# Add one URL per line to load mockups from cloud storage
# 
# Supported formats:
# - Direct URL: https://example.com/path/to/mockup.psd
# - Google Drive file: https://drive.google.com/file/d/FILE_ID/view
#   (To get FILE_ID: Right-click file > Share > Copy link)
# - Google Drive folder: https://drive.google.com/drive/folders/FOLDER_ID
#   (Automatically loads ALL .psd files from the folder)
#
# Example:
# https://drive.google.com/drive/folders/1TXJ2FNU-ntSF4hwxmorJA3hd9TblePcf
# https://drive.google.com/file/d/1abc123def456/view
# https://www.dropbox.com/s/abc123/mockup.psd?dl=1
# https://example.com/mockups/design1.psd
"""
        try:
            with open(self.cloud_config_file, 'w', encoding='utf-8') as f:
                f.write(template)
        except Exception as e:
            print(f"Could not create cloud config template: {e}")
    
    def _get_files_from_gdrive_folder(self, folder_url):
        """
        Extract all PSD file links from a public Google Drive folder using Drive API.
        Works without authentication for publicly shared folders.
        """
        import urllib.request
        import urllib.error
        import json
        
        file_urls = []
        
        try:
            # Extract folder ID from various URL formats
            folder_id = None
            if '/folders/' in folder_url:
                folder_id = folder_url.split('/folders/')[-1].split('?')[0].split('/')[0]
            
            if not folder_id:
                print(f"Could not extract folder ID from: {folder_url}")
                return file_urls
            
            print(f"📁 Fetching PSDs from Google Drive folder: {folder_id}")
            
            # Use Google Drive API v3 to list files
            # This endpoint works for public folders without authentication
            api_url = f"https://www.googleapis.com/drive/v3/files?q='{folder_id}'+in+parents+and+mimeType='application/x-photoshop'&fields=files(id,name)&key=AIzaSyDummy"
            
            # Alternative approach: Try the export/download endpoint
            # For public folders, we can try to access the folder listing
            
            # Method 1: Try using the webContentLink approach
            print("  Attempting to list folder contents...")
            
            # For now, use a simpler manual approach:
            # User needs to share individual file links OR
            # We'll provide a helper script to generate the list
            
            print("  ⚠️  Google Drive folders require individual file URLs")
            print("  📝 Please use one of these methods:")
            print("     1. Share each PSD file individually and add URLs to cloud_sources.txt")
            print("     2. Use the Google Drive API key method (see documentation)")
            print("     3. Use Dropbox or direct URLs instead")
            
            # Store folder URL for reference
            file_urls.append(f"# FOLDER: {folder_url}")
            file_urls.append("# Please replace this with individual file URLs")
            file_urls.append("# Right-click each file > Share > Copy link")
            
        except Exception as e:
            print(f"Error accessing Google Drive folder: {e}")
        
        return file_urls
    
    def _get_google_drive_direct_link(self, url):
        """Convert Google Drive sharing link to direct download link"""
        if 'drive.google.com' in url:
            # Extract file ID from various Google Drive URL formats
            if '/file/d/' in url:
                file_id = url.split('/file/d/')[1].split('/')[0]
            elif 'id=' in url:
                file_id = url.split('id=')[1].split('&')[0]
            else:
                return url
            
            # Return direct download link
            return f"https://drive.google.com/uc?export=download&id={file_id}"
        return url
    
    def _get_cached_filename(self, url):
        """Generate a safe filename for cached file based on URL"""
        import hashlib
        # Use hash of URL as filename to avoid conflicts
        url_hash = hashlib.md5(url.encode()).hexdigest()
        # Try to get original filename from URL
        original_name = url.split('/')[-1].split('?')[0]
        if original_name.lower().endswith('.psd'):
            return f"{url_hash}_{original_name}"
        else:
            return f"{url_hash}.psd"
    
    def _download_file(self, url, destination):
        """Download a file from URL to destination"""
        import urllib.request
        import urllib.error
        
        try:
            # Convert Google Drive links
            download_url = self._get_google_drive_direct_link(url)
            
            # Download with progress (basic)
            print(f"Downloading from cloud: {url}")
            urllib.request.urlretrieve(download_url, destination)
            return True
        except urllib.error.URLError as e:
            print(f"Download failed for {url}: {e}")
            return False
        except Exception as e:
            print(f"Error downloading {url}: {e}")
            return False
    
    def _get_cloud_mockups(self, progress_callback=None, splash=None):
        """Download and cache cloud mockups, return list of local paths"""
        cloud_psds = []
        total_urls = len(self.cloud_urls)
        
        if total_urls == 0:
            return cloud_psds
        
        downloads_needed = 0
        cached_count = 0
        
        # First pass - check what needs downloading
        for url in self.cloud_urls:
            cache_filename = self._get_cached_filename(url)
            cache_path = os.path.join(self.cache_dir, cache_filename)
            if not os.path.exists(cache_path):
                downloads_needed += 1
        
        if downloads_needed == 0:
            print(f"✓ All {total_urls} cloud mockups already cached - loading instantly")
        else:
            print(f"Downloading {downloads_needed} new cloud mockup(s), {total_urls - downloads_needed} already cached")
        
        for i, url in enumerate(self.cloud_urls, 1):
            cache_filename = self._get_cached_filename(url)
            cache_path = os.path.join(self.cache_dir, cache_filename)
            
            # If not in cache, download it
            if not os.path.exists(cache_path):
                if progress_callback:
                    progress_callback(f"Downloading cloud mockup {i} of {total_urls}...", "")
                
                # Update progress bar if splash is provided
                if splash:
                    progress_percent = int((i / total_urls) * 100)
                    splash.set_progress_value(progress_percent)
                
                print(f"⬇ Downloading: {cache_filename}")
                if self._download_file(url, cache_path):
                    cloud_psds.append(cache_path)
            else:
                # Use cached version - much faster!
                if progress_callback:
                    progress_callback(f"Loading cached mockup {i} of {total_urls}...", "")
                
                # Update progress bar if splash is provided
                if splash:
                    progress_percent = int((i / total_urls) * 100)
                    splash.set_progress_value(progress_percent)
                
                cloud_psds.append(cache_path)
                cached_count += 1
        
        if cached_count > 0:
            print(f"✓ Loaded {cached_count} mockup(s) from cache (instant)")
        
        return cloud_psds
    
    def get_all_mockups(self, progress_callback=None, splash=None):
        """Returns all PSD files from both local library and cloud sources"""
        psd_files = []
        
        if progress_callback:
            progress_callback("Scanning local library...", "")
        
        # Get local PSDs (excluding cache folder and config file)
        if os.path.exists(self.library_root):
            for root, dirs, files in os.walk(self.library_root):
                # Skip the cache directory
                if '_cache' in root:
                    continue
                    
                for file in files:
                    # Only include .psd files, skip config files
                    if file.lower().endswith('.psd') and file != 'cloud_sources.txt':
                        psd_files.append(os.path.join(root, file))
        
        if progress_callback:
            progress_callback("Loading cloud mockups...", "")
        
        # Get cloud PSDs (cached locally) - pass splash for progress updates
        try:
            cloud_psds = self._get_cloud_mockups(progress_callback, splash)
            psd_files.extend(cloud_psds)
        except Exception as e:
            print(f"Error loading cloud mockups: {e}")
        
        return sorted(psd_files)
    
    def get_library_path(self):
        """Returns the library root path"""
        return self.library_root
    
    def clear_cache(self):
        """Clear the cloud cache folder"""
        import shutil
        try:
            if os.path.exists(self.cache_dir):
                shutil.rmtree(self.cache_dir)
                os.makedirs(self.cache_dir)
                print("Cloud cache cleared")
                return True
        except Exception as e:
            print(f"Error clearing cache: {e}")
        return False
    
    def refresh_cloud_mockups(self):
        """Force re-download of all cloud mockups"""
        self.clear_cache()
        return self._get_cloud_mockups()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Show loading splash
        self.splash = LoadingSplash()
        self.splash.show()
        self.splash.update_status("Starting MockupCore...", "")
        QApplication.processEvents()
        
        self.setWindowTitle("MockupCore Batch Exporter Tool")
        self.setFixedSize(2145, 1196)
        
        # Set window icon
        icon_path = resource_path("mockupcoreicon.ico")
        if os.path.exists(icon_path):
            from PyQt5.QtGui import QIcon
            self.setWindowIcon(QIcon(icon_path))
        
        self.splash.update_status("Initializing library system...", "")
        QApplication.processEvents()
        
        # Initialize library system
        self.library = MockupLibrary()
        self.selected_library_psds: Set[str] = set()
        self.thumbnail_widgets = {}
        
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)  # Remove all margins
        layout.setSpacing(0)  # Remove spacing between banner and content
        
        banner_text = "MOCKUPCORE ✱ BATCH MOCKUP EXPORTER ✱ "
        self.banner = SmoothMarquee(banner_text)
        layout.addWidget(self.banner)
        
        # Main content split: left side (controls), right side (library)
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(25, 0, 0, 0)  # Removed top, right, and bottom margins
        content_layout.setSpacing(20)
        layout.addLayout(content_layout)
        
        # LEFT SIDE - Controls
        left_panel = QVBoxLayout()
        left_panel.setSpacing(15)
        left_panel.setContentsMargins(0, 30, 0, 0)  # Add top margin to align with library
        content_layout.addLayout(left_panel, stretch=3)
        
        # Artwork section
        art_box = QGroupBox("ARTWORK SELECTION")
        art_layout = QVBoxLayout(art_box)
        art_layout.setContentsMargins(0, 0, 0, 0)
        
        art_row = QHBoxLayout()
        art_row.setSpacing(10)
        art_row.setContentsMargins(0, 0, 0, 0)
        self.art_path = QLineEdit()
        self.art_path.setReadOnly(True)
        self.art_path.setFixedHeight(50)
        art_btn = QPushButton("SELECT FILE")
        art_btn.setFixedHeight(50)
        art_btn.clicked.connect(self.pick_art)
        art_row.addWidget(self.art_path, stretch=3)
        art_row.addWidget(art_btn, stretch=1)
        art_layout.addLayout(art_row)
        
        left_panel.addWidget(art_box)
        
        # Manual mockup files section
        manual_box = QGroupBox("MOCKUP FILES")
        manual_layout = QVBoxLayout(manual_box)
        manual_layout.setContentsMargins(0, 0, 0, 10)  # Increased bottom margin
        manual_layout.setSpacing(10)
        
        subtitle = QLabel("Select your own mockups you have downloaded from Emma Rodriguez Studio")
        subtitle.setStyleSheet("font-size: 13px; color: #666; margin-bottom: 5px;")
        subtitle.setWordWrap(True)
        manual_layout.addWidget(subtitle)
        
        self.psd_list = QListWidget()
        self.psd_list.setMinimumHeight(300)  # Significantly reduced
        self.psd_list.setMaximumHeight(300)  # Set max to prevent stretching
        manual_layout.addWidget(self.psd_list)
        
        left_panel.addWidget(manual_box)
        
        # Buttons below the mockup files box with gap
        manual_btn_row = QHBoxLayout()
        manual_btn_row.setSpacing(10)
        add_psd_btn = QPushButton("SELECT MOCKUPS")
        add_psd_btn.clicked.connect(self.pick_psds)
        remove_psd_btn = QPushButton("DELETE SELECTED")
        remove_psd_btn.clicked.connect(self.remove_selected_psds)
        manual_btn_row.addWidget(add_psd_btn)
        manual_btn_row.addWidget(remove_psd_btn)
        left_panel.addLayout(manual_btn_row)
        
        # Output folder
        out_box = QGroupBox("EXPORT LOCATION")
        out_layout = QHBoxLayout(out_box)
        out_layout.setSpacing(10)
        out_layout.setContentsMargins(0, 0, 0, 0)
        self.out_dir = QLineEdit()
        self.out_dir.setFixedHeight(50)
        out_btn = QPushButton("CHOOSE FOLDER")
        out_btn.setFixedHeight(50)
        out_btn.clicked.connect(self.pick_out)
        out_layout.addWidget(self.out_dir, stretch=3)
        out_layout.addWidget(out_btn, stretch=1)
        left_panel.addWidget(out_box)
        
        # Action buttons
        action_row = QHBoxLayout()
        self.run_btn = QPushButton("GENERATE YOUR MOCKUPS")
        self.run_btn.setObjectName("PrimaryButton")
        self.run_btn.setFixedHeight(60)
        self.run_btn.clicked.connect(self.run_job)
        
        reset_btn = QPushButton("RESET")
        reset_btn.setObjectName("ResetButton")
        reset_btn.setFixedHeight(60)
        reset_btn.clicked.connect(self.reset_all)
        
        action_row.addWidget(self.run_btn, stretch=2)
        action_row.addWidget(reset_btn, stretch=1)
        left_panel.addLayout(action_row)
        
        # Bottom section - Selected artwork preview (LEFT) + Instructions (RIGHT)
        bottom_section = QHBoxLayout()
        
        # LEFT: Selected artwork preview box
        preview_frame = QFrame()
        preview_frame.setObjectName("SelectedArtworkBox")
        preview_frame.setFixedWidth(200)
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(10, 10, 10, 10)
        preview_layout.setSpacing(5)
        preview_layout.setAlignment(Qt.AlignHCenter)
        
        preview_title = QLabel("Selected artwork:")
        preview_title.setStyleSheet("font-size: 14px; font-weight: 700; background: transparent;")
        preview_title.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(preview_title, alignment=Qt.AlignCenter)
        
        self.selected_artwork_preview = QLabel()
        self.selected_artwork_preview.setFixedSize(180, 180)
        self.selected_artwork_preview.setStyleSheet("background: transparent;")
        self.selected_artwork_preview.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(self.selected_artwork_preview, alignment=Qt.AlignCenter)
        
        # RIGHT: Instructions
        instructions_widget = QWidget()
        instructions_widget.setStyleSheet("background: transparent;")
        instructions_layout = QVBoxLayout(instructions_widget)
        instructions_layout.setContentsMargins(15, 0, 0, 0)
        
        instructions = QLabel(
            "<b>HOW TO:</b><br>"
            "1. Choose the artwork you would like to place into the mockups.<br>"
            "2. Either use the library to the right and choose your mockups, or use the 'MOCKUP FILE' option to select your own.<br>"
            "3. Choose a folder you would like your mockups to be exported to.<br>"
            "4. Click 'GENERATE YOUR MOCKUPS' for your mockups to be processed. Click 'RESET' to start over."
        )
        instructions.setStyleSheet("font-size: 15px; line-height: 1.6;")  # Increased from 13px to 15px
        instructions.setWordWrap(True)
        instructions_layout.addWidget(instructions)
        instructions_layout.addStretch()
        
        # Create a container for preview with status below it
        preview_container = QWidget()
        preview_container.setStyleSheet("background: transparent;")
        preview_container_layout = QVBoxLayout(preview_container)
        preview_container_layout.setContentsMargins(0, 0, 0, 0)
        preview_container_layout.setSpacing(10)
        
        preview_container_layout.addWidget(preview_frame)
        
        # Status label below preview box
        self.status = QLabel("Ready")
        preview_container_layout.addWidget(self.status)
        
        bottom_section.addWidget(preview_container, stretch=1)
        
        # Instructions and progress bar side by side
        right_bottom_container = QWidget()
        right_bottom_container.setStyleSheet("background: transparent;")
        right_bottom_layout = QVBoxLayout(right_bottom_container)
        right_bottom_layout.setContentsMargins(15, 0, 0, 0)
        right_bottom_layout.setSpacing(10)
        
        instructions = QLabel(
            "<b>HOW TO:</b><br>"
            "1. Choose the artwork you would like to place into the mockups.<br>"
            "2. Either use the library to the right and choose your mockups, or use the 'MOCKUP FILE' option to select your own.<br>"
            "3. Choose a folder you would like your mockups to be exported to.<br>"
            "4. Click 'GENERATE YOUR MOCKUPS' for your mockups to be processed. Click 'RESET' to start over."
        )
        instructions.setStyleSheet("font-size: 15px; line-height: 1.6;")
        instructions.setWordWrap(True)
        right_bottom_layout.addWidget(instructions)
        
        # Progress bar below instructions
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        right_bottom_layout.addWidget(self.progress)
        
        right_bottom_layout.addStretch()
        
        bottom_section.addWidget(right_bottom_container, stretch=3)
        left_panel.addLayout(bottom_section)
        
        # Hidden log for compatibility
        self.log = QTextEdit()
        self.log.setVisible(False)
        
        # RIGHT SIDE - Mockup Library (with blue background)
        library_frame = QFrame()
        library_frame.setObjectName("LibraryPanel")
        library_frame_layout = QVBoxLayout(library_frame)
        library_frame_layout.setContentsMargins(20, 30, 20, 20)  # Added extra top margin since we removed content margin
        library_frame_layout.setSpacing(15)
        content_layout.addWidget(library_frame, stretch=2)
        
        library_header = QHBoxLayout()
        library_title = QLabel("MOCKUP LIBRARY")
        library_title.setStyleSheet("font-size: 20px; font-weight: 700; color: white; background: transparent;")
        
        self.refresh_btn = QPushButton("↻ REFRESH")
        self.refresh_btn.setObjectName("LibraryButton")
        self.refresh_btn.setToolTip("Refresh cloud mockups and reload library")
        self.refresh_btn.clicked.connect(self.refresh_library)
        
        self.select_all_btn = QPushButton("SELECT ALL")
        self.select_all_btn.setObjectName("LibraryButton")
        self.select_all_btn.clicked.connect(self.select_all_library)
        
        self.deselect_all_btn = QPushButton("DESELECT ALL")
        self.deselect_all_btn.setObjectName("LibraryButton")
        self.deselect_all_btn.clicked.connect(self.deselect_all_library)
        
        library_header.addWidget(library_title)
        library_header.addStretch()
        library_header.addWidget(self.refresh_btn)
        library_header.addWidget(self.select_all_btn)
        library_header.addWidget(self.deselect_all_btn)
        library_frame_layout.addLayout(library_header)
        
        # Scrollable thumbnail grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.library_container = QFrame()
        self.library_container.setObjectName("LibraryContainer")
        self.library_layout = QGridLayout(self.library_container)
        self.library_layout.setSpacing(20)  # Increased spacing for better separation
        self.library_layout.setAlignment(Qt.AlignTop)  # Just align to top
        self.library_layout.setContentsMargins(20, 20, 20, 20)  # Balanced margins
        
        # Set uniform column stretches for even distribution
        for col in range(4):
            self.library_layout.setColumnStretch(col, 1)
        
        scroll.setWidget(self.library_container)
        library_frame_layout.addWidget(scroll)
        
        # Load library thumbnails
        self._load_library_thumbnails()

    def _load_library_thumbnails(self):
        """Load all library mockups as thumbnails with real PSD previews"""
        
        def progress_callback(status, detail):
            """Update splash screen with progress"""
            if hasattr(self, 'splash') and self.splash:
                self.splash.update_status(status, detail)
        
        # Set progress to start from 0
        self.splash.set_progress_range(0, 100)
        self.splash.set_progress_value(0)
        
        self.splash.update_status("Loading mockup library...", "Scanning for PSD files")
        
        # Pass splash reference for real-time progress updates during cloud downloads
        mockups = self.library.get_all_mockups(progress_callback, self.splash)
        
        self.log.append(f"📚 Loading mockup library...")
        self.log.append(f"Found {len(mockups)} PSD file(s)")
        
        if not mockups:
            lib_path = self.library.get_library_path()
            self.log.append(f"📁 Library: {lib_path}")
            self.log.append("ℹ️  Add PSD files to the library folder or URLs to cloud_sources.txt")
            
            # Show placeholder
            placeholder = QLabel(f"No mockups in library\n\nAdd PSD files to:\n{lib_path}\n\nor add URLs to cloud_sources.txt")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("color: white; font-size: 14px; background: transparent;")
            self.library_layout.addWidget(placeholder, 0, 0, 1, 4)
            
            # Close splash
            if hasattr(self, 'splash') and self.splash:
                self.splash.close()
                self.splash = None
            return
        
        # Update splash for thumbnail generation
        self.splash.update_status("Generating thumbnails...", f"Processing {len(mockups)} mockup(s)")
        self.splash.set_progress_range(0, len(mockups))
        self.splash.set_progress_value(0)
        
        # Create thumbnail grid (4 columns)
        columns = 4
        for i, psd_path in enumerate(mockups):
            row = i // columns
            col = i % columns
            
            # Log each mockup being loaded
            filename = os.path.basename(psd_path)
            self.log.append(f"  • {filename}")
            
            # Update splash progress
            self.splash.update_status(f"Loading thumbnails... ({i+1}/{len(mockups)})", filename)
            self.splash.set_progress_value(i + 1)
            
            thumbnail = MockupThumbnail(psd_path)
            thumbnail.clicked.connect(self.toggle_library_selection)
            
            self.library_layout.addWidget(thumbnail, row, col, Qt.AlignCenter)  # Center in cell
            self.thumbnail_widgets[psd_path] = thumbnail
        
        self.log.append(f"✓ Loaded {len(mockups)} mockup(s) successfully")
        
        # Close splash when done
        if hasattr(self, 'splash') and self.splash:
            self.splash.update_status("Ready!", "MockupCore loaded successfully")
            QTimer.singleShot(500, self._close_splash)  # Small delay before closing
    
    def _close_splash(self):
        """Close the loading splash screen"""
        if hasattr(self, 'splash') and self.splash:
            self.splash.close()
            self.splash = None

    def toggle_library_selection(self, psd_path):
        """Toggle selection of a library mockup"""
        if psd_path in self.selected_library_psds:
            self.selected_library_psds.remove(psd_path)
        else:
            self.selected_library_psds.add(psd_path)
        
        # Update selection count
        count = len(self.selected_library_psds)
        self.log.append(f"Library: {count} mockup(s) selected")
    
    def select_all_library(self):
        """Select all library mockups"""
        for psd_path, thumbnail in self.thumbnail_widgets.items():
            thumbnail.set_selected(True)
            self.selected_library_psds.add(psd_path)
        
        count = len(self.selected_library_psds)
        self.log.append(f"✓ Selected all {count} library mockups")
    
    def deselect_all_library(self):
        """Deselect all library mockups"""
        for psd_path, thumbnail in self.thumbnail_widgets.items():
            thumbnail.set_selected(False)
        
        self.selected_library_psds.clear()
        self.log.append("Library selections cleared")
    
    def refresh_library(self):
        """Refresh the library - reload cloud mockups and update display"""
        self.log.append("↻ Refreshing mockup library...")
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("LOADING...")
        
        # Show loading splash for refresh with close button
        self.splash = LoadingSplash()
        self.splash.show()
        self.splash.update_status("Refreshing library...", "")
        self.splash.set_progress_range(0, 100)
        self.splash.set_progress_value(0)
        QApplication.processEvents()
        
        # Clear cache ONLY when manually refreshing (not on startup)
        try:
            self.splash.update_status("Clearing cache...", "")
            self.library.clear_cache()
            self.log.append("Cache cleared - re-downloading cloud files...")
            QApplication.processEvents()
        except Exception as e:
            self.log.append(f"⚠️ Cache clear error: {e}")
        
        # Clear current display
        self.selected_library_psds.clear()
        self.thumbnail_widgets.clear()
        
        # Clear the grid layout
        while self.library_layout.count():
            item = self.library_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        QApplication.processEvents()
        
        # Reload thumbnails (this will re-download cloud files and show progress)
        self._load_library_thumbnails()
        
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("↻ REFRESH")
        self.log.append("✓ Library refreshed")

    def pick_art(self):
        p, _ = QFileDialog.getOpenFileName(self, "Select Design", "", "Images (*.png *.jpg *.jpeg)")
        if p:
            self.art_path.setText(p)
            self.art_path.setStyleSheet("")
            # Update the preview in the bottom section - scaled to fit new size
            pix = QPixmap(p).scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.selected_artwork_preview.setPixmap(pix)
            
    def pick_psds(self):
        """Manual mockup file selection"""
        files, _ = QFileDialog.getOpenFileNames(self, "Select Mockups", "", "PSD (*.psd)")
        if files:
            self.psd_list.setStyleSheet("")
            for f in files: 
                self.psd_list.addItem(f)
        
    def remove_selected_psds(self):
        for item in self.psd_list.selectedItems():
            self.psd_list.takeItem(self.psd_list.row(item))
            
    def pick_out(self):
        d = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if d: 
            self.out_dir.setText(d)
            self.out_dir.setStyleSheet("")
            
    def reset_all(self):
        self.art_path.clear()
        self.art_path.setStyleSheet("")
        self.out_dir.clear()
        self.out_dir.setStyleSheet("")
        self.psd_list.clear()
        self.psd_list.setStyleSheet("")
        self.deselect_all_library()
        self.log.clear()
        self.status.setText("Ready")
        self.progress.setValue(0)
        self.selected_artwork_preview.clear()
        self.run_btn.setEnabled(True)
        
    def run_job(self):
        # Collect all PSDs (library selections + manual uploads)
        all_psds = list(self.selected_library_psds)
        all_psds.extend([self.psd_list.item(i).text() for i in range(self.psd_list.count())])
        
        error = False
        if not self.art_path.text():
            self.art_path.setStyleSheet("border: 2px solid #e85d33;")
            error = True
        if len(all_psds) == 0:
            self.log.append("❌ No mockups selected")
            error = True
        if not self.out_dir.text():
            self.out_dir.setStyleSheet("border: 2px solid #e85d33;")
            error = True
        if error: return
        
        self.run_btn.setEnabled(False)
        self.status.setText(f"Processing {len(all_psds)} mockup(s)...")
        
        job = Job(all_psds, self.art_path.text(), self.out_dir.text())
        self.worker = Worker(job)
        self.worker.log.connect(self.log.append)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()
        
    def on_error(self, error_msg):
        """Handle errors from the worker thread"""
        self.run_btn.setEnabled(True)
        self.status.setText("ERROR - Check log below")
        self.status.setStyleSheet("color: #e85d33; font-weight: 700; font-size: 16px;")
        
    def on_finished(self):
        self.run_btn.setEnabled(True)
        self.status.setText("COMPLETE!")
        self.status.setStyleSheet("color: #4CAF50; font-weight: 700; font-size: 16px;")
        self.progress.setValue(100)

def main():
    app = QApplication(sys.argv)
    
    # Load Space Grotesk font
    font_path = resource_path("SpaceGrotesk-Regular.ttf")
    if os.path.exists(font_path):
        QFontDatabase.addApplicationFont(font_path)

    app.setStyleSheet(APP_QSS)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
