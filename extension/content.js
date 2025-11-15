/**
 * ROSETTA Form Filler - Content Script
 * Detects form fields and fills them with extracted data
 */

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'detectFields') {
    const fields = detectFormFields();
    sendResponse({ fields });
  } else if (request.action === 'fillForm') {
    fillForm(request.data);
    sendResponse({ success: true });
  }
  
  return true;
});

/**
 * Detect all fillable form fields on the page
 */
function detectFormFields() {
  const fields = [];
  
  // Find all input, select, and textarea elements
  const inputs = document.querySelectorAll('input, select, textarea');
  
  inputs.forEach((input, index) => {
    // Skip certain input types
    const type = input.type?.toLowerCase();
    if (['submit', 'button', 'reset', 'image', 'file', 'hidden'].includes(type)) {
      return;
    }
    
    // Get field name
    const name = getFieldName(input);
    if (!name) return;
    
    // Get field type
    const fieldType = getFieldType(input);
    
    // Check if required
    const required = input.required || input.hasAttribute('required');
    
    // Get label
    const label = getFieldLabel(input);
    
    // Get placeholder
    const placeholder = input.placeholder || input.getAttribute('placeholder') || '';
    
    // Get aria-label
    const ariaLabel = input.getAttribute('aria-label') || '';
    
    // Get autocomplete
    const autocomplete = input.getAttribute('autocomplete') || '';
    
    // Get current value (if any)
    const currentValue = input.value || '';
    
    // Get additional context clues
    const nearbyText = getNearbyText(input);
    const formContext = getFormContext(input);
    
    fields.push({
      name,
      type: fieldType,
      required,
      label,
      placeholder,
      ariaLabel,
      autocomplete,
      currentValue,
      selector: getUniqueSelector(input),
      element: input,
      // Additional context for LLM
      id: input.id || '',
      className: input.className || '',
      title: input.title || '',
      nearbyText,
      formContext
    });
  });
  
  console.log('ROSETTA: Detected', fields.length, 'form fields');
  return fields;
}

/**
 * Get field name from various attributes
 */
function getFieldName(input) {
  // Priority: name > id > aria-label > placeholder > type
  return input.name ||
         input.id ||
         input.getAttribute('aria-label') ||
         input.getAttribute('placeholder') ||
         input.type ||
         `field_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Get field type
 */
function getFieldType(input) {
  if (input.tagName === 'SELECT') return 'select';
  if (input.tagName === 'TEXTAREA') return 'textarea';
  
  const type = input.type?.toLowerCase();
  return type || 'text';
}

/**
 * Get field label with extended context search
 */
function getFieldLabel(input) {
  // Try associated label
  if (input.id) {
    const label = document.querySelector(`label[for="${input.id}"]`);
    if (label) return label.textContent.trim();
  }
  
  // Try parent label
  const parentLabel = input.closest('label');
  if (parentLabel) {
    const clone = parentLabel.cloneNode(true);
    // Remove the input from clone to get just label text
    const inputClone = clone.querySelector('input, select, textarea');
    if (inputClone) inputClone.remove();
    const text = clone.textContent.trim();
    if (text) return text;
  }
  
  // Try aria-label
  if (input.getAttribute('aria-label')) {
    return input.getAttribute('aria-label');
  }
  
  // Try aria-labelledby
  const labelledBy = input.getAttribute('aria-labelledby');
  if (labelledBy) {
    const labelEl = document.getElementById(labelledBy);
    if (labelEl) return labelEl.textContent.trim();
  }
  
  // Try placeholder
  if (input.placeholder) {
    return input.placeholder;
  }
  
  // Try previous sibling text node or element
  let prev = input.previousSibling;
  while (prev) {
    if (prev.nodeType === Node.TEXT_NODE && prev.textContent.trim()) {
      return prev.textContent.trim();
    }
    if (prev.nodeType === Node.ELEMENT_NODE) {
      const text = prev.textContent.trim();
      if (text && text.length < 100) return text; // Avoid long text blocks
    }
    prev = prev.previousSibling;
  }
  
  // Try parent's previous sibling (for div > label + div > input structure)
  const parent = input.parentElement;
  if (parent) {
    let prevSib = parent.previousSibling;
    while (prevSib) {
      if (prevSib.nodeType === Node.ELEMENT_NODE) {
        const text = prevSib.textContent.trim();
        if (text && text.length < 100) return text;
      }
      prevSib = prevSib.previousSibling;
    }
  }
  
  return null;
}

/**
 * Get nearby text context around input field
 */
function getNearbyText(input) {
  const texts = [];
  
  // Get parent container text (limit to reasonable size)
  const parent = input.closest('div, fieldset, section, form');
  if (parent) {
    // Get all text nodes in parent
    const walker = document.createTreeWalker(
      parent,
      NodeFilter.SHOW_TEXT,
      null
    );
    
    let node;
    while (node = walker.nextNode()) {
      const text = node.textContent.trim();
      if (text && text.length < 50 && text.length > 2) {
        texts.push(text);
      }
    }
  }
  
  return texts.slice(0, 5).join(' | '); // Limit to 5 nearby texts
}

/**
 * Get form-level context
 */
function getFormContext(input) {
  const form = input.closest('form');
  if (form) {
    const formName = form.name || form.id || '';
    const formAction = form.action || '';
    const formClass = form.className || '';
    
    return [formName, formAction, formClass]
      .filter(x => x)
      .join(' | ')
      .slice(0, 100);
  }
  return '';
}

/**
 * Generate unique CSS selector for element
 */
function getUniqueSelector(element) {
  if (element.id) return `#${element.id}`;
  if (element.name) return `[name="${element.name}"]`;
  
  // Generate path-based selector
  const path = [];
  let current = element;
  
  while (current && current !== document.body) {
    let selector = current.tagName.toLowerCase();
    
    if (current.className) {
      const classes = current.className.split(' ').filter(c => c.trim());
      if (classes.length > 0) {
        selector += '.' + classes.join('.');
      }
    }
    
    path.unshift(selector);
    current = current.parentElement;
    
    if (path.length > 5) break; // Limit depth
  }
  
  return path.join(' > ');
}

/**
 * Fill form with extracted data
 */
function fillForm(data) {
  console.log('ROSETTA: Filling form with data:', data);
  console.log('ROSETTA: Data keys:', Object.keys(data));
  console.log('ROSETTA: Data entries:', Object.entries(data));
  
  let filledCount = 0;
  
  for (const [fieldName, fieldData] of Object.entries(data)) {
    console.log(`ROSETTA: Processing field "${fieldName}":`, fieldData);
    
    // Skip fields not found in document
    if (fieldData.not_found) {
      console.log(`ROSETTA: Skipping ${fieldName} (not found in document)`);
      continue;
    }
    
    // Get the value
    const value = fieldData.value || fieldData;
    if (!value || value === '') {
      console.log(`ROSETTA: Skipping ${fieldName} (empty value)`);
      continue;
    }
    
    console.log(`ROSETTA: Looking for input for field "${fieldName}" with value "${value}"`);
    
    // Find matching input
    const input = findInputByName(fieldName);
    
    if (input) {
      console.log(`ROSETTA: Found input for ${fieldName}:`, input);
      const success = setInputValue(input, value);
      if (success) {
        filledCount++;
        highlightField(input);
      }
    } else {
      console.log(`ROSETTA: Could not find input for field: ${fieldName}`);
    }
  }
  
  console.log(`ROSETTA: Filled ${filledCount} fields`);
  
  // Show notification
  showNotification(`✅ Filled ${filledCount} fields`);
}

/**
 * Find input by field name (with fuzzy matching)
 */
function findInputByName(fieldName) {
  const normalized = normalizeFieldName(fieldName);
  
  // Try exact matches first
  let input = document.querySelector(`[name="${fieldName}"]`) ||
              document.querySelector(`#${fieldName}`) ||
              document.querySelector(`[id="${fieldName}"]`);
  
  if (input) return input;
  
  // Try normalized matches
  input = document.querySelector(`[name="${normalized}"]`) ||
          document.querySelector(`#${normalized}`);
  
  if (input) return input;
  
  // Try fuzzy matching by label
  const inputs = document.querySelectorAll('input, select, textarea');
  
  for (const inp of inputs) {
    const name = normalizeFieldName(getFieldName(inp));
    const label = normalizeFieldName(getFieldLabel(inp) || '');
    
    if (name === normalized || label.includes(normalized) || normalized.includes(label)) {
      return inp;
    }
  }
  
  return null;
}

/**
 * Normalize field name for matching
 */
function normalizeFieldName(name) {
  return name.toLowerCase()
    .replace(/[_\-\s]+/g, '')
    .replace(/([a-z])([A-Z])/g, '$1$2')
    .toLowerCase();
}

/**
 * Set input value
 */
function setInputValue(input, value) {
  try {
    const type = input.type?.toLowerCase();
    
    if (type === 'checkbox') {
      // Handle checkbox
      const checked = ['true', 'yes', '1', 'on'].includes(value.toLowerCase());
      input.checked = checked;
    } else if (type === 'radio') {
      // Handle radio
      if (input.value === value) {
        input.checked = true;
      }
    } else if (input.tagName === 'SELECT') {
      // Handle select
      const option = Array.from(input.options).find(opt => 
        opt.value === value || opt.text === value
      );
      if (option) {
        input.value = option.value;
      }
    } else {
      // Handle text inputs
      input.value = value;
    }
    
    // Trigger change event
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
    
    return true;
  } catch (error) {
    console.error('ROSETTA: Error setting value:', error);
    return false;
  }
}

/**
 * Highlight filled field
 */
function highlightField(input) {
  input.style.transition = 'all 0.3s ease';
  input.style.backgroundColor = '#d4edda';
  input.style.borderColor = '#28a745';
  
  setTimeout(() => {
    input.style.backgroundColor = '';
    input.style.borderColor = '';
  }, 2000);
}

/**
 * Show notification overlay
 */
function showNotification(message) {
  // Remove existing notification
  const existing = document.getElementById('rosetta-notification');
  if (existing) existing.remove();
  
  // Create notification
  const notification = document.createElement('div');
  notification.id = 'rosetta-notification';
  notification.className = 'rosetta-notification';
  notification.textContent = message;
  
  document.body.appendChild(notification);
  
  // Fade in
  setTimeout(() => notification.classList.add('show'), 10);
  
  // Remove after delay
  setTimeout(() => {
    notification.classList.remove('show');
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

// Initialize
console.log('ROSETTA Form Filler content script loaded');
