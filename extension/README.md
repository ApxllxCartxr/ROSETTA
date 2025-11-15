# ROSETTA Chrome Extension

Browser extension for automatically filling web forms from scanned documents using OCR and AI.

## Features

✅ **Automatic Form Detection** - Detects fillable fields on any webpage  
✅ **Document Upload** - Upload PDF, JPG, PNG, TIFF documents  
✅ **OCR Extraction** - Multi-language text extraction  
✅ **AI Field Mapping** - Intelligent field matching with synonym understanding  
✅ **Auto-Fill** - Automatically populate form fields with extracted data  
✅ **Visual Feedback** - Highlights filled fields with confidence indicators  

## Installation

### Prerequisites
- Chrome/Edge browser (Manifest V3 compatible)
- ROSETTA API server running (see `backend/api/README.md`)

### Load Extension

1. **Build Extension** (if needed):
   ```bash
   # Extension is ready to use, no build required
   ```

2. **Load in Chrome**:
   - Open Chrome and navigate to `chrome://extensions/`
   - Enable "Developer mode" (top right)
   - Click "Load unpacked"
   - Select the `extension/` folder

3. **Configure Settings**:
   - Click the extension icon
   - Click "⚙️ Settings"
   - Enter API URL (default: `http://localhost:8000`)
   - Click "Test Connection"
   - Save settings

## Usage

### Basic Workflow

1. **Navigate to a form** (e.g., job application, registration form)
2. **Click extension icon** in toolbar
3. **Upload document** (drag & drop or click to browse)
4. **Click "Process Document"**
5. **Review extracted data**
6. **Click "Fill Form"** to auto-populate fields

### Settings

Access settings by clicking "⚙️ Settings" in the popup:

- **API URL**: URL of your ROSETTA API server
- **Default Language**: OCR language (English, Arabic, Tamil, Hindi)
- **Performance Mode**: Fast, Balanced, or Accurate
- **Image Preprocessing**: Enable/disable image enhancement
- **Auto-Fill**: Automatically fill form after extraction

## How It Works

```
1. User opens webpage with form
   ↓
2. Extension detects form fields
   → Extracts field names, types, labels
   ↓
3. User uploads document (ID, certificate, etc.)
   ↓
4. Extension sends to ROSETTA API
   → File + detected field schema
   ↓
5. API processes document
   → OCR extraction
   → LLM field mapping
   → Returns matched data
   ↓
6. Extension receives results
   → Shows preview with confidence scores
   ↓
7. User clicks "Fill Form"
   → Extension auto-fills detected fields
   → Highlights filled fields
```

## Field Detection

The extension automatically detects various input types:

- **Text inputs**: `<input type="text">`, `<input type="email">`, etc.
- **Select dropdowns**: `<select>`
- **Textareas**: `<textarea>`
- **Checkboxes/Radio buttons**: Boolean values

Field names are extracted from:
1. `name` attribute
2. `id` attribute
3. Associated `<label>` elements
4. `aria-label` attributes
5. `placeholder` text

## Synonym Matching

The extension understands field name variations:

- **firstName** = first_name = fname = given_name
- **lastName** = last_name = surname = family_name
- **email** = e-mail = email_address
- **phone** = telephone = mobile = phone_number
- **dateOfBirth** = DOB = birth_date = date_of_birth

## Project Structure

```
extension/
├── manifest.json          # Extension manifest (V3)
├── background.js          # Service worker
├── content.js             # Form detection & filling
├── content.css            # Content script styles
├── popup.html             # Extension popup UI
├── popup.js               # Popup logic
├── popup.css              # Popup styles
├── options.html           # Settings page
├── options.js             # Settings logic
└── icons/                 # Extension icons
    ├── icon16.png
    ├── icon48.png
    └── icon128.png
```

## Permissions

The extension requires:

- **activeTab**: Access current tab for form detection
- **storage**: Save user settings
- **scripting**: Inject content scripts
- **host_permissions**: 
  - `http://localhost:8000/*` (API communication)
  - `<all_urls>` (Form detection on any website)

## Troubleshooting

### Extension not detecting fields
- Ensure you're on a page with an HTML form
- Click "🔄 Refresh Fields" in popup
- Some dynamic forms may need page reload

### Connection failed
- Verify ROSETTA API is running: `http://localhost:8000/api/v1/health`
- Check API URL in settings
- Ensure CORS is enabled in API config

### Fields not filling correctly
- Some websites use JavaScript-heavy forms that block programmatic filling
- Try manual copy-paste from results preview
- Check browser console for errors (F12)

### Upload fails
- Check file size (<10MB)
- Verify file format (PDF, JPG, PNG, TIFF)
- Ensure API is running and accessible

## Development

### Testing Locally

1. **Start API server**:
   ```bash
   cd backend/api
   python main.py
   ```

2. **Load extension** in Chrome (developer mode)

3. **Open test page** with form

4. **Test workflow**

### Debugging

- **Popup**: Right-click extension icon → "Inspect popup"
- **Content script**: F12 on webpage → Console tab
- **Background worker**: `chrome://extensions/` → "Inspect views: service worker"

### Making Changes

1. Edit files in `extension/` folder
2. Click "Reload" button in `chrome://extensions/`
3. Test changes

## Known Limitations

- Cannot fill forms in iframes from different origins
- Some websites use custom form libraries that prevent auto-fill
- OCR accuracy depends on document quality
- LLM field mapping may fail for very unusual field names

## Privacy & Security

- **No data collection**: All processing happens locally or on your API server
- **No external services**: No data sent to third parties
- **Local storage only**: Settings stored in browser's sync storage
- **HTTPS recommended**: Use HTTPS for API in production

## Browser Compatibility

- ✅ Chrome 88+ (Manifest V3)
- ✅ Edge 88+
- ⚠️ Firefox (requires Manifest V2 port)
- ❌ Safari (not supported)

## License

MIT License - See LICENSE file

---

**Built with ❤️ for ROSETTA Project**
