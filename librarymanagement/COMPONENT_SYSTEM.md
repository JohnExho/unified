# Reusable Component System - Django Template Edition

A React-inspired component architecture using Django templates, achieving composability and reusability without JavaScript frameworks.

## 📁 Directory Structure

```
librarymanagement/templates/librarymanagement/
├── components/
│   └── ui/
│       └── dialog.html           # Base dialog component
├── modals/
│   ├── add-book-dialog.html      # Add book dialog content
│   ├── add-library-dialog.html   # Add library dialog content
│   └── borrow-book-dialog.html   # Borrow book dialog content
└── pages/
    └── books_list.html           # Page using dialog components
```

## 🎯 Core Concept

This system replicates React's component paradigm using Django's `{% include %}` template tag with context passing, creating reusable, composable UI components.

## 🧩 Component Architecture

### Base Dialog Component

**File:** `components/ui/dialog.html`

A reusable modal dialog component that accepts "props" via Django template context.

#### Props (Parameters):

| Prop             | Type   | Required | Default   | Description                                       |
| ---------------- | ------ | -------- | --------- | ------------------------------------------------- |
| `dialog_id`      | string | ✅ Yes   | -         | Unique identifier for the dialog                  |
| `dialog_title`   | string | ✅ Yes   | -         | Title displayed in dialog header                  |
| `dialog_content` | string | ✅ Yes   | -         | Template path to include as dialog body           |
| `dialog_footer`  | string | ❌ No    | null      | Template path for custom footer                   |
| `dialog_size`    | string | ❌ No    | "default" | Size variant: "sm", "default", "lg", "xl", "full" |
| `dialog_class`   | string | ❌ No    | ""        | Additional CSS classes                            |

#### Usage Example:

```django
{# Include the dialog component with props #}
{% include "librarymanagement/components/ui/dialog.html" with
  dialog_id="addBookDialog"
  dialog_title="Add New Book"
  dialog_content="librarymanagement/modals/add-book-dialog.html"
  dialog_size="lg"
%}
```

### Content Components

**Files:** `modals/*-dialog.html`

These are "children" components that contain the actual dialog content (forms, text, etc.).

#### Example Structure:

```django
{# add-book-dialog.html - Dialog content #}
<form id="addBookForm" method="post" action="{% url 'librarymanagement:add_book' %}">
  {% csrf_token %}

  <div class="form-grid">
    {# Form fields here #}
  </div>

  {# Footer inside content (optional) #}
  <div class="dialog-footer">
    <button type="button" class="btn btn-ghost" onclick="closeDialog('addBookDialog')">
      Cancel
    </button>
    <button type="submit" class="btn btn-primary">
      Add Book
    </button>
  </div>
</form>
```

## 🚀 Implementation Guide

### Step 1: Create Base Component

Create `components/ui/dialog.html` with the reusable dialog structure:

```django
<div id="{{ dialog_id }}" class="dialog-overlay" data-dialog-size="{{ dialog_size|default:'default' }}">
  <div class="dialog-content {{ dialog_class|default:'' }}">
    <div class="dialog-header">
      <h3 class="dialog-title">{{ dialog_title }}</h3>
      <button class="dialog-close" onclick="closeDialog('{{ dialog_id }}')">×</button>
    </div>

    <div class="dialog-body">
      {% include dialog_content %}
    </div>

    {% if dialog_footer %}
      <div class="dialog-footer">
        {% include dialog_footer %}
      </div>
    {% endif %}
  </div>
</div>
```

### Step 2: Create Content Components

Create separate files for each dialog's content in `modals/` directory.

### Step 3: Use Components in Pages

In your page template (e.g., `books_list.html`):

```django
{% block content %}
  {# Page content #}
  {% include "librarymanagement/components/sidebar.html" %}
  {% include "librarymanagement/components/books/main.html" %}

  {# Reusable Dialog Components #}
  {% include "librarymanagement/components/ui/dialog.html" with
    dialog_id="addLibraryDialog"
    dialog_title="Add New Library"
    dialog_content="librarymanagement/modals/add-library-dialog.html"
  %}

  {% include "librarymanagement/components/ui/dialog.html" with
    dialog_id="addBookDialog"
    dialog_title="Add New Book"
    dialog_content="librarymanagement/modals/add-book-dialog.html"
    dialog_size="lg"
  %}
{% endblock content %}
```

## 🎨 JavaScript API

### Global Helper Functions

The base dialog component provides global JavaScript helpers:

```javascript
// Open a dialog
openDialog(dialogId);

// Close a dialog
closeDialog(dialogId);

// Example usage
openDialog("addBookDialog");
```

### Event System

Dialogs emit custom events:

```javascript
// Listen for dialog opened
document.getElementById("myDialog").addEventListener("dialog:opened", (e) => {
  console.log("Dialog opened:", e.detail.dialogId);
});

// Listen for dialog closed
document.getElementById("myDialog").addEventListener("dialog:closed", (e) => {
  console.log("Dialog closed:", e.detail.dialogId);
});
```

### Features:

- ✅ Click outside to close
- ✅ Press Escape to close
- ✅ Auto form reset on close
- ✅ Body scroll lock when open
- ✅ Custom event dispatching

## 💡 Advantages Over Old Approach

### Before (Inline Modals):

```django
<!-- 200 lines of modal HTML repeated 3 times = 600 lines -->
<div id="addBookModal" class="modal-overlay">
  <div class="modal">
    <div class="modal-header">
      <h3>Add New Book</h3>
      <button onclick="closeAddBookModal()">×</button>
    </div>
    <div class="modal-body">
      <!-- 150 lines of form fields -->
    </div>
  </div>
</div>

<!-- Duplicate for each modal -->
<div id="addLibraryModal">...</div>
<div id="borrowBookModal">...</div>
```

### After (Reusable Components):

```django
<!-- 3 dialogs = 3 clean lines -->
{% include "ui/dialog.html" with dialog_id="addBookDialog" dialog_title="Add New Book" dialog_content="modals/add-book.html" %}
{% include "ui/dialog.html" with dialog_id="addLibraryDialog" dialog_title="Add New Library" dialog_content="modals/add-library.html" %}
{% include "ui/dialog.html" with dialog_id="borrowBookDialog" dialog_title="Borrow Book" dialog_content="modals/borrow-book.html" %}
```

#### Benefits:

1. **DRY (Don't Repeat Yourself):** Dialog structure defined once
2. **Maintainability:** Update dialog styling in one place
3. **Consistency:** All dialogs look and behave the same
4. **Readability:** Page templates are clean and semantic
5. **Flexibility:** Easy to add new dialogs
6. **Separation of Concerns:** Structure (dialog.html) vs Content (modals/\*.html)

## 🔧 Customization Examples

### Custom Size Dialog:

```django
{% include "ui/dialog.html" with
  dialog_id="fullscreenDialog"
  dialog_title="Full Screen View"
  dialog_content="modals/fullscreen.html"
  dialog_size="full"
%}
```

### Dialog with Additional Classes:

```django
{% include "ui/dialog.html" with
  dialog_id="specialDialog"
  dialog_title="Special Dialog"
  dialog_content="modals/special.html"
  dialog_class="dialog-blur dialog-animated"
%}
```

### Dialog with Separate Footer:

```django
{% include "ui/dialog.html" with
  dialog_id="customDialog"
  dialog_title="Custom Dialog"
  dialog_content="modals/custom-content.html"
  dialog_footer="modals/custom-footer.html"
%}
```

## 📋 Best Practices

### 1. Consistent Naming

```django
{# Pattern: {action}{Entity}Dialog #}
addBookDialog
editBookDialog
deleteBookDialog
confirmActionDialog
```

### 2. Content Organization

```
modals/
├── books/
│   ├── add-book-dialog.html
│   ├── edit-book-dialog.html
│   └── delete-book-dialog.html
├── libraries/
│   └── add-library-dialog.html
└── shared/
    └── confirm-dialog.html
```

### 3. Form IDs Match Dialog IDs

```django
{# Dialog ID #}
dialog_id="addBookDialog"

{# Form ID (inside content) #}
<form id="addBookForm">...</form>
```

### 4. Consistent Button Actions

```html
<!-- Cancel button always calls closeDialog -->
<button onclick="closeDialog('dialogId')">Cancel</button>

<!-- Submit uses standard form submission -->
<button type="submit">Save</button>
```

## 🎓 Advanced Patterns

### Dynamic Content Loading

```javascript
// Load dialog content dynamically
function showUserProfile(userId) {
  // Fetch user data
  fetch(`/api/users/${userId}`)
    .then((r) => r.json())
    .then((data) => {
      // Populate dialog
      document.getElementById("profile_name").textContent = data.name;
      document.getElementById("profile_email").textContent = data.email;

      // Open dialog
      openDialog("userProfileDialog");
    });
}
```

### Nested Dialogs

```django
{# Parent dialog #}
{% include "ui/dialog.html" with
  dialog_id="parentDialog"
  dialog_title="Parent"
  dialog_content="modals/parent.html"
%}

{# Child dialog (higher z-index) #}
{% include "ui/dialog.html" with
  dialog_id="childDialog"
  dialog_title="Child"
  dialog_content="modals/child.html"
  dialog_class="dialog-nested"
%}
```

### Confirmation Dialogs

```django
{# Reusable confirmation #}
{% include "ui/dialog.html" with
  dialog_id="confirmDialog"
  dialog_title="Confirm Action"
  dialog_content="modals/confirm.html"
  dialog_size="sm"
%}
```

```javascript
// Usage
function confirmDelete(itemId) {
  document.getElementById("confirm_message").textContent =
    "Are you sure you want to delete this item?";
  document.getElementById("confirm_action").onclick = () => {
    deleteItem(itemId);
    closeDialog("confirmDialog");
  };
  openDialog("confirmDialog");
}
```

## 🔍 Comparison with React

| Feature              | React            | Django Templates      |
| -------------------- | ---------------- | --------------------- |
| Component Definition | JSX/Function     | Django Template       |
| Props                | Function params  | Context variables     |
| Children             | `props.children` | `{% include %}`       |
| Reusability          | Import component | `{% include %}` tag   |
| State Management     | useState/Redux   | Server-side/JS        |
| Events               | Props/callbacks  | onclick/custom events |

## 📊 File Size Comparison

| Approach                      | Total Lines         | Maintainability |
| ----------------------------- | ------------------- | --------------- |
| **Before:** Inline modals × 3 | ~600 lines          | ❌ Low          |
| **After:** Component system   | ~250 lines          | ✅ High         |
| **Savings**                   | **350 lines (58%)** | ⭐ Excellent    |

## 🚦 Migration Checklist

- [x] Create `components/ui/dialog.html` base component
- [x] Create `modals/` directory
- [x] Extract modal content to separate files
- [x] Update page templates to use `{% include %}`
- [x] Update JavaScript to use `openDialog()` / `closeDialog()`
- [x] Test all dialogs
- [x] Remove old modal code
- [x] Update CSS for `.dialog-*` classes

## 📝 Notes

- All dialogs share the same HTML structure
- Content is completely separated from structure
- JavaScript API is consistent across all dialogs
- Django context (user, libraries, etc.) is available in content templates
- CSS uses `.dialog-*` classes from shadcn-ui design system

## 🎉 Result

**A clean, maintainable, React-like component system using only Django templates and vanilla JavaScript!**
