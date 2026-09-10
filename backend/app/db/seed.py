"""Seed / upsert component_definitions with the full palette catalog.

Re-running this (e.g. via `python -m app.db.seed`) is safe: existing
definitions are updated in place (so schema changes like the new `fieldKey`
prop or the structured Button `action` reach databases that were seeded
before this change), new ones are inserted, and nothing already-seeded is
duplicated.
"""

from datetime import datetime

from app.db.mongo import get_database, init_indexes

COMPONENT_DEFINITIONS = [
    # ---------------------------------------------------------------- Basic Fields
    {
        "type": "user_input",
        "label": "User Input",
        "icon": "text_fields",
        "category": "Basic Fields",
        "is_container": False,
        "is_input": True,
        "data_type": "string",
        "default_props": {
            "label": "User Input",
            "placeholder": "Enter value…",
            "inputType": "text",
            "required": False,
            "unique": False,
            "defaultValue": "",
            "fieldKey": "",
            "showToggle": True,
            "options": ["Option 1", "Option 2"],
            "rows": 4,
            "minDate": "",
            "maxDate": "",
            "accept": "image/*",
            "multiple": False,
        },
        "property_schema": [
            {
                "key": "inputType",
                "label": "Input type",
                "inputType": "select",
                "options": [
                    "text", "email", "password", "number", "phone", "url",
                    "textarea", "checkbox", "toggle", "dropdown", "radio", "date", "file",
                ],
            },
            {"key": "label", "label": "Label", "inputType": "text"},
            {"key": "placeholder", "label": "Placeholder", "inputType": "text"},
            {"key": "fieldKey", "label": "Field Key (for saved data)", "inputType": "field_key"},
            {"key": "required", "label": "Required", "inputType": "boolean"},
            {"key": "unique", "label": "Must be unique", "inputType": "boolean"},
            {"key": "defaultValue", "label": "Default Value", "inputType": "text"},
            {"key": "showToggle", "label": "Show/Hide Toggle (password only)", "inputType": "boolean"},
            {"key": "options", "label": "Options", "inputType": "list"},
            {"key": "rows", "label": "Rows (textarea)", "inputType": "number"},
            {"key": "minDate", "label": "Min Date", "inputType": "text"},
            {"key": "maxDate", "label": "Max Date", "inputType": "text"},
            {"key": "accept", "label": "Accepted file types", "inputType": "text"},
            {"key": "multiple", "label": "Allow multiple files", "inputType": "boolean"},
        ],
    },
    {
        "type": "text_block",
        "label": "Text",
        "icon": "title",
        "category": "Layout",
        "is_container": False,
        "default_props": {
            "textType": "body",
            "content": "Text content",
            "binding": "",
            "align": "left",
            "color": "#333333",
            "fontSize": 16,
            "fontWeight": "normal",
            "textAlign": "left",
        },
        "property_schema": [
            {
                "key": "textType",
                "label": "Text type",
                "inputType": "select",
                "options": ["h1", "h2", "h3", "h4", "body", "label"],
            },
            {"key": "content", "label": "Content", "inputType": "text"},
            {"key": "binding", "label": "Formula (bind to variables)", "inputType": "formula"},
            {
                "key": "align",
                "label": "Alignment (headings)",
                "inputType": "select",
                "options": ["left", "center", "right"],
            },
            {"key": "color", "label": "Color", "inputType": "color"},
            {"key": "fontSize", "label": "Font Size", "inputType": "number"},
            {
                "key": "fontWeight",
                "label": "Font Weight",
                "inputType": "select",
                "options": ["normal", "600", "bold"],
            },
            {
                "key": "textAlign",
                "label": "Text Align",
                "inputType": "select",
                "options": ["left", "center", "right"],
            },
        ],
    },
    {
        "type": "media",
        "label": "Media",
        "icon": "image",
        "category": "Branding",
        "is_container": False,
        "default_props": {
            "mediaType": "image",
            "src": "",
            "alt": "Image",
            "fit": "contain",
            "initials": "AB",
            "shape": "circle",
            "size": 40,
            "iconName": "star",
            "color": "#333333",
            "url": "",
            "title": "",
        },
        "property_schema": [
            {
                "key": "mediaType",
                "label": "Media type",
                "inputType": "select",
                "options": ["image", "avatar", "icon", "video"],
            },
            {"key": "src", "label": "Image", "inputType": "image"},
            {"key": "alt", "label": "Alt Text", "inputType": "text"},
            {
                "key": "fit",
                "label": "Fit",
                "inputType": "select",
                "options": ["contain", "cover", "fill"],
            },
            {"key": "initials", "label": "Initials (avatar fallback)", "inputType": "text"},
            {
                "key": "shape",
                "label": "Shape",
                "inputType": "select",
                "options": ["circle", "square", "rounded"],
            },
            {"key": "size", "label": "Size (px)", "inputType": "number"},
            {"key": "iconName", "label": "Icon Name", "inputType": "text"},
            {"key": "color", "label": "Color", "inputType": "color"},
            {"key": "url", "label": "Video URL", "inputType": "text"},
            {"key": "title", "label": "Video Title", "inputType": "text"},
        ],
    },
    {
        "type": "container",
        "label": "Container",
        "icon": "view_agenda",
        "category": "Layout",
        "is_container": True,
        "default_props": {
            "containerType": "section",
            "label": "",
            "backgroundColor": "#ffffff",
            "backgroundImage": "",
            "padding": 24,
            "direction": "column",
            "gap": 12,
        },
        "property_schema": [
            {
                "key": "containerType",
                "label": "Container type",
                "inputType": "select",
                "options": ["section", "row", "card", "page"],
            },
            {"key": "label", "label": "Label", "inputType": "text"},
            {"key": "backgroundColor", "label": "Background Color", "inputType": "color"},
            {"key": "backgroundImage", "label": "Background Image", "inputType": "image"},
            {"key": "padding", "label": "Padding (px)", "inputType": "number"},
            {
                "key": "direction",
                "label": "Layout Direction",
                "inputType": "select",
                "options": ["column", "row"],
            },
            {"key": "gap", "label": "Gap (px)", "inputType": "number"},
        ],
    },
    {
        "type": "display",
        "label": "Display",
        "icon": "label",
        "category": "Display",
        "is_container": False,
        "default_props": {
            "displayType": "badge",
            "text": "Badge",
            "tone": "neutral",
            "thickness": 1,
            "style": "solid",
            "color": "#e5e7eb",
            "height": 24,
            "value": 60,
            "max": 100,
            "label": "",
            "items": ["Item 1", "Item 2"],
        },
        "property_schema": [
            {
                "key": "displayType",
                "label": "Display type",
                "inputType": "select",
                "options": ["badge", "divider", "spacer", "progress", "rating", "list"],
            },
            {"key": "text", "label": "Text", "inputType": "text"},
            {
                "key": "tone",
                "label": "Tone",
                "inputType": "select",
                "options": ["neutral", "success", "warning", "danger", "info"],
            },
            {"key": "thickness", "label": "Thickness (px)", "inputType": "number"},
            {
                "key": "style",
                "label": "Line Style",
                "inputType": "select",
                "options": ["solid", "dashed", "dotted"],
            },
            {"key": "color", "label": "Color", "inputType": "color"},
            {"key": "height", "label": "Height (px)", "inputType": "number"},
            {"key": "value", "label": "Value", "inputType": "number"},
            {"key": "max", "label": "Max", "inputType": "number"},
            {"key": "label", "label": "Label", "inputType": "text"},
            {"key": "items", "label": "Items", "inputType": "list"},
        ],
    },
    {
        "type": "widget",
        "label": "Widget",
        "icon": "widgets",
        "category": "Advanced",
        "is_container": False,
        "default_props": {
            "widgetType": "data_table",
            "title": "",
            "sourcePageId": "",
            "pageSize": 50,
            "links": ["Home", "About"],
            "tabs": ["Tab 1", "Tab 2"],
            "items": ["Item 1", "Item 2"],
            "steps": ["Step 1", "Step 2"],
        },
        "property_schema": [
            {
                "key": "widgetType",
                "label": "Widget type",
                "inputType": "select",
                "options": [
                    "data_table", "kanban", "navbar", "tabs",
                    "accordion", "stepper", "breadcrumb",
                ],
            },
            {"key": "title", "label": "Title", "inputType": "text"},
            {"key": "sourcePageId", "label": "Source Page", "inputType": "page_select"},
            {"key": "pageSize", "label": "Rows per Page", "inputType": "number"},
            {"key": "links", "label": "Links", "inputType": "list"},
            {"key": "tabs", "label": "Tabs", "inputType": "list"},
            {"key": "items", "label": "Items", "inputType": "list"},
            {"key": "steps", "label": "Steps", "inputType": "list"},
        ],
    },
    {
        "type": "text_input",
        "label": "Short Text",
        "icon": "text_fields",
        "category": "Basic Fields",
        "is_container": False,
        "is_input": True,
        "data_type": "string",
        "default_props": {
            "label": "Short Text",
            "placeholder": "Enter text...",
            "required": False,
            "defaultValue": "",
            "fieldKey": "",
            "unique": False,
        },
        "property_schema": [
            {"key": "label", "label": "Label", "inputType": "text"},
            {"key": "placeholder", "label": "Placeholder", "inputType": "text"},
            {"key": "required", "label": "Required", "inputType": "boolean"},
            {"key": "unique", "label": "Must be unique", "inputType": "boolean"},
            {"key": "defaultValue", "label": "Default Value", "inputType": "text"},
            {"key": "fieldKey", "label": "Field Key (for saved data)", "inputType": "text"},
        ],
    },
    {
        "type": "textarea",
        "label": "Long Text",
        "icon": "notes",
        "category": "Basic Fields",
        "is_container": False,
        "is_input": True,
        "data_type": "string",
        "default_props": {
            "label": "Long Text",
            "placeholder": "Enter details...",
            "required": False,
            "rows": 4,
            "defaultValue": "",
            "fieldKey": "",
        },
        "property_schema": [
            {"key": "label", "label": "Label", "inputType": "text"},
            {"key": "placeholder", "label": "Placeholder", "inputType": "text"},
            {"key": "required", "label": "Required", "inputType": "boolean"},
            {"key": "rows", "label": "Rows", "inputType": "number"},
            {"key": "defaultValue", "label": "Default Value", "inputType": "text"},
            {"key": "fieldKey", "label": "Field Key (for saved data)", "inputType": "text"},
        ],
    },
    {
        "type": "number_input",
        "label": "Number",
        "icon": "pin",
        "category": "Basic Fields",
        "is_container": False,
        "is_input": True,
        "data_type": "number",
        "default_props": {
            "label": "Number",
            "placeholder": "0",
            "required": False,
            "min": None,
            "max": None,
            "defaultValue": None,
            "fieldKey": "",
            "unique": False,
        },
        "property_schema": [
            {"key": "label", "label": "Label", "inputType": "text"},
            {"key": "placeholder", "label": "Placeholder", "inputType": "text"},
            {"key": "required", "label": "Required", "inputType": "boolean"},
            {"key": "unique", "label": "Must be unique", "inputType": "boolean"},
            {"key": "min", "label": "Minimum", "inputType": "number"},
            {"key": "max", "label": "Maximum", "inputType": "number"},
            {"key": "defaultValue", "label": "Default Value", "inputType": "number"},
            {"key": "fieldKey", "label": "Field Key (for saved data)", "inputType": "text"},
        ],
    },
    {
        "type": "dropdown",
        "label": "Dropdown",
        "icon": "arrow_drop_down_circle",
        "category": "Basic Fields",
        "is_container": False,
        "is_input": True,
        "data_type": "string",
        "default_props": {
            "label": "Dropdown",
            "placeholder": "Select...",
            "options": ["Option 1", "Option 2", "Option 3"],
            "required": False,
            "defaultValue": "",
            "fieldKey": "",
        },
        "property_schema": [
            {"key": "label", "label": "Label", "inputType": "text"},
            {"key": "placeholder", "label": "Placeholder", "inputType": "text"},
            {"key": "options", "label": "Options", "inputType": "list"},
            {"key": "required", "label": "Required", "inputType": "boolean"},
            {"key": "defaultValue", "label": "Default Value", "inputType": "text"},
            {"key": "fieldKey", "label": "Field Key (for saved data)", "inputType": "text"},
        ],
    },
    {
        "type": "checkbox",
        "label": "Checkbox",
        "icon": "check_box",
        "category": "Basic Fields",
        "is_container": False,
        "is_input": True,
        "data_type": "boolean",
        "default_props": {
            "label": "Checkbox",
            "required": False,
            "defaultValue": False,
            "fieldKey": "",
        },
        "property_schema": [
            {"key": "label", "label": "Label", "inputType": "text"},
            {"key": "required", "label": "Required", "inputType": "boolean"},
            {"key": "defaultValue", "label": "Checked by Default", "inputType": "boolean"},
            {"key": "fieldKey", "label": "Field Key (for saved data)", "inputType": "text"},
        ],
    },
    {
        "type": "radio_group",
        "label": "Radio Group",
        "icon": "radio_button_checked",
        "category": "Basic Fields",
        "is_container": False,
        "is_input": True,
        "data_type": "string",
        "default_props": {
            "label": "Radio Group",
            "options": ["Option A", "Option B", "Option C"],
            "required": False,
            "defaultValue": "",
            "layout": "vertical",
            "fieldKey": "",
        },
        "property_schema": [
            {"key": "label", "label": "Label", "inputType": "text"},
            {"key": "options", "label": "Options", "inputType": "list"},
            {"key": "required", "label": "Required", "inputType": "boolean"},
            {"key": "defaultValue", "label": "Default Value", "inputType": "text"},
            {
                "key": "layout",
                "label": "Layout",
                "inputType": "select",
                "options": ["vertical", "horizontal"],
            },
            {"key": "fieldKey", "label": "Field Key (for saved data)", "inputType": "text"},
        ],
    },
    {
        "type": "email_input",
        "label": "Email",
        "icon": "alternate_email",
        "category": "Basic Fields",
        "is_container": False,
        "is_input": True,
        "data_type": "string",
        "default_props": {
            "label": "Email",
            "placeholder": "you@example.com",
            "required": True,
            "unique": False,
            "defaultValue": "",
            "fieldKey": "email",
        },
        "property_schema": [
            {"key": "label", "label": "Label", "inputType": "text"},
            {"key": "placeholder", "label": "Placeholder", "inputType": "text"},
            {"key": "required", "label": "Required", "inputType": "boolean"},
            {"key": "unique", "label": "Must be unique", "inputType": "boolean"},
            {"key": "defaultValue", "label": "Default Value", "inputType": "text"},
            {"key": "fieldKey", "label": "Field Key (for saved data)", "inputType": "text"},
        ],
    },
    {
        "type": "password_input",
        "label": "Password",
        "icon": "lock",
        "category": "Basic Fields",
        "is_container": False,
        "is_input": True,
        "data_type": "string",
        "default_props": {
            "label": "Password",
            "placeholder": "Enter password",
            "required": True,
            "showToggle": True,
            "fieldKey": "password",
        },
        "property_schema": [
            {"key": "label", "label": "Label", "inputType": "text"},
            {"key": "placeholder", "label": "Placeholder", "inputType": "text"},
            {"key": "required", "label": "Required", "inputType": "boolean"},
            {"key": "showToggle", "label": "Show/Hide Toggle", "inputType": "boolean"},
            {"key": "fieldKey", "label": "Field Key (for saved data)", "inputType": "text"},
        ],
    },
    {
        "type": "date_picker",
        "label": "Date",
        "icon": "calendar_month",
        "category": "Basic Fields",
        "is_container": False,
        "is_input": True,
        "data_type": "string",
        "default_props": {
            "label": "Date",
            "required": False,
            "minDate": "",
            "maxDate": "",
            "defaultValue": "",
            "fieldKey": "",
        },
        "property_schema": [
            {"key": "label", "label": "Label", "inputType": "text"},
            {"key": "required", "label": "Required", "inputType": "boolean"},
            {"key": "minDate", "label": "Earliest Date", "inputType": "text"},
            {"key": "maxDate", "label": "Latest Date", "inputType": "text"},
            {"key": "fieldKey", "label": "Field Key (for saved data)", "inputType": "text"},
        ],
    },
    {
        "type": "toggle_switch",
        "label": "Toggle",
        "icon": "toggle_on",
        "category": "Basic Fields",
        "is_container": False,
        "is_input": True,
        "data_type": "boolean",
        "default_props": {
            "label": "Toggle",
            "defaultChecked": False,
            "fieldKey": "",
        },
        "property_schema": [
            {"key": "label", "label": "Label", "inputType": "text"},
            {"key": "defaultChecked", "label": "On by Default", "inputType": "boolean"},
            {"key": "fieldKey", "label": "Field Key (for saved data)", "inputType": "text"},
        ],
    },
    {
        "type": "file_upload",
        "label": "File Upload",
        "icon": "upload_file",
        "category": "Basic Fields",
        "is_container": False,
        "is_input": True,
        "data_type": "string",
        "default_props": {
            "label": "Upload File",
            "accept": "",
            "multiple": False,
            "fieldKey": "",
        },
        "property_schema": [
            {"key": "label", "label": "Label", "inputType": "text"},
            {"key": "accept", "label": "Accepted Types (e.g. .pdf,.png)", "inputType": "text"},
            {"key": "multiple", "label": "Allow Multiple Files", "inputType": "boolean"},
            {"key": "fieldKey", "label": "Field Key (for saved data)", "inputType": "text"},
        ],
    },
    # ---------------------------------------------------------------- Actions
    {
        "type": "button",
        "label": "Button",
        "icon": "smart_button",
        "category": "Actions",
        "is_container": False,
        "default_props": {
            "label": "Click Me",
            "variant": "primary",
            "appearance": "button",
            "providers": ["google"],
            "action": {"actionType": "none"},
        },
        "property_schema": [
            {"key": "label", "label": "Label", "inputType": "text"},
            {
                "key": "appearance",
                "label": "Appearance",
                "inputType": "select",
                "options": ["button", "link", "social"],
            },
            {
                "key": "variant",
                "label": "Variant",
                "inputType": "select",
                "options": ["primary", "secondary", "outline", "danger"],
            },
            {
                "key": "providers",
                "label": "Social providers",
                "inputType": "checkbox_group",
                "options": [
                    "google",
                    "facebook",
                    "twitter",
                    "microsoft",
                    "github",
                    "apple",
                    "linkedin",
                ],
            },
            {"key": "action", "label": "On Click", "inputType": "action"},
        ],
    },
    {
        "type": "link_button",
        "label": "Link / Text Button",
        "icon": "link",
        "category": "Actions",
        "is_container": False,
        "default_props": {
            "label": "Forgot password?",
            "action": {"actionType": "none"},
        },
        "property_schema": [
            {"key": "label", "label": "Label", "inputType": "text"},
            {"key": "action", "label": "On Click", "inputType": "action"},
        ],
    },
    {
        "type": "social_login_button",
        "label": "Social Login Button",
        "icon": "badge",
        "category": "Actions",
        "is_container": False,
        "default_props": {
            "provider": "google",
            "label": "",
            "action": {"actionType": "none"},
        },
        "property_schema": [
            {
                "key": "provider",
                "label": "Provider",
                "inputType": "select",
                "options": ["google", "microsoft", "github", "facebook"],
            },
            {"key": "label", "label": "Custom Label (optional)", "inputType": "text"},
            {"key": "action", "label": "On Click", "inputType": "action"},
        ],
    },
    # ---------------------------------------------------------------- Layout
    {
        "type": "page",
        "label": "Page",
        "icon": "web",
        "category": "Layout",
        "is_container": True,
        "default_props": {
            "label": "Page",
            "backgroundColor": "#f4f6f9",
            "backgroundImage": "",
            "padding": 0,
        },
        "property_schema": [
            {"key": "label", "label": "Page Name", "inputType": "text"},
            {"key": "backgroundColor", "label": "Background Color", "inputType": "color"},
            {"key": "backgroundImage", "label": "Background Image", "inputType": "image"},
            {"key": "padding", "label": "Padding (px)", "inputType": "number"},
        ],
    },
    {
        "type": "section",
        "label": "Section",
        "icon": "view_agenda",
        "category": "Layout",
        "is_container": True,
        "default_props": {
            "label": "",
            "backgroundColor": "#ffffff",
            "padding": 24,
            "direction": "column",
            "gap": 12,
        },
        "property_schema": [
            {"key": "label", "label": "Label", "inputType": "text"},
            {"key": "backgroundColor", "label": "Background Color", "inputType": "color"},
            {"key": "padding", "label": "Padding", "inputType": "number"},
            {
                "key": "direction",
                "label": "Layout Direction",
                "inputType": "select",
                "options": ["column", "row"],
            },
            {"key": "gap", "label": "Gap (px)", "inputType": "number"},
        ],
    },
    {
        "type": "heading",
        "label": "Heading",
        "icon": "format_size",
        "category": "Layout",
        "is_container": False,
        "default_props": {
            "content": "Heading",
            "binding": "",
            "level": "h2",
            "align": "left",
            "color": "#111827",
        },
        "property_schema": [
            {"key": "content", "label": "Content", "inputType": "text"},
            {"key": "binding", "label": "Formula (bind to variables)", "inputType": "formula"},
            {
                "key": "level",
                "label": "Level",
                "inputType": "select",
                "options": ["h1", "h2", "h3", "h4"],
            },
            {
                "key": "align",
                "label": "Alignment",
                "inputType": "select",
                "options": ["left", "center", "right"],
            },
            {"key": "color", "label": "Color", "inputType": "color"},
        ],
    },
    {
        "type": "text",
        "label": "Text / Label",
        "icon": "title",
        "category": "Layout",
        "is_container": False,
        "default_props": {
            "content": "Text content",
            "binding": "",
            "fontSize": 16,
            "fontWeight": "normal",
            "color": "#333333",
            "textAlign": "left",
        },
        "property_schema": [
            {"key": "content", "label": "Content", "inputType": "text"},
            {"key": "binding", "label": "Formula (bind to variables)", "inputType": "formula"},
            {"key": "fontSize", "label": "Font Size", "inputType": "number"},
            {
                "key": "fontWeight",
                "label": "Font Weight",
                "inputType": "select",
                "options": ["normal", "medium", "bold"],
            },
            {"key": "color", "label": "Color", "inputType": "color"},
            {
                "key": "textAlign",
                "label": "Alignment",
                "inputType": "select",
                "options": ["left", "center", "right"],
            },
        ],
    },
    {
        "type": "row",
        "label": "Row",
        "icon": "view_column",
        "category": "Layout",
        "is_container": True,
        "default_props": {
            "label": "Row",
            "gap": 8,
        },
        "property_schema": [
            {"key": "label", "label": "Label", "inputType": "text"},
            {"key": "gap", "label": "Gap (px)", "inputType": "number"},
        ],
    },
    {
        "type": "card",
        "label": "Card",
        "icon": "dashboard",
        "category": "Layout",
        "is_container": True,
        "default_props": {
            "title": "",
            "padding": 12,
            "elevated": True,
        },
        "property_schema": [
            {"key": "title", "label": "Title", "inputType": "text"},
            {"key": "padding", "label": "Padding (px)", "inputType": "number"},
            {"key": "elevated", "label": "Show Shadow", "inputType": "boolean"},
        ],
    },
    {
        "type": "divider",
        "label": "Divider",
        "icon": "horizontal_rule",
        "category": "Layout",
        "is_container": False,
        "default_props": {
            "thickness": 1,
            "style": "solid",
            "color": "#e5e7eb",
        },
        "property_schema": [
            {"key": "thickness", "label": "Thickness (px)", "inputType": "number"},
            {
                "key": "style",
                "label": "Line Style",
                "inputType": "select",
                "options": ["solid", "dashed", "dotted"],
            },
            {"key": "color", "label": "Color", "inputType": "color"},
        ],
    },
    {
        "type": "spacer",
        "label": "Spacer",
        "icon": "space_bar",
        "category": "Layout",
        "is_container": False,
        "default_props": {
            "height": 24,
        },
        "property_schema": [
            {"key": "height", "label": "Height (px)", "inputType": "number"},
        ],
    },
    {
        "type": "navbar",
        "label": "Navbar",
        "icon": "menu",
        "category": "Layout",
        "is_container": False,
        "default_props": {
            "brandLabel": "My App",
            "links": ["Home", "Dashboard", "Settings"],
            "backgroundColor": "#111827",
        },
        "property_schema": [
            {"key": "brandLabel", "label": "Brand Label", "inputType": "text"},
            {"key": "links", "label": "Links", "inputType": "list"},
            {"key": "backgroundColor", "label": "Background Color", "inputType": "color"},
        ],
    },
    {
        "type": "tabs",
        "label": "Tabs",
        "icon": "tab",
        "category": "Layout",
        "is_container": False,
        "default_props": {
            "tabs": ["Tab 1", "Tab 2"],
        },
        "property_schema": [
            {"key": "tabs", "label": "Tab Labels", "inputType": "list"},
        ],
    },
    {
        "type": "breadcrumb",
        "label": "Breadcrumb",
        "icon": "chevron_right",
        "category": "Layout",
        "is_container": False,
        "default_props": {
            "items": ["Home", "Section", "Current Page"],
        },
        "property_schema": [
            {"key": "items", "label": "Trail Items", "inputType": "list"},
        ],
    },
    {
        "type": "stepper",
        "label": "Stepper",
        "icon": "linear_scale",
        "category": "Layout",
        "is_container": False,
        "default_props": {
            "steps": ["Step 1", "Step 2", "Step 3"],
            "activeStep": 0,
        },
        "property_schema": [
            {"key": "steps", "label": "Steps", "inputType": "list"},
            {"key": "activeStep", "label": "Active Step (0-based)", "inputType": "number"},
        ],
    },
    {
        "type": "accordion",
        "label": "Accordion",
        "icon": "expand_more",
        "category": "Layout",
        "is_container": False,
        "default_props": {
            "items": ["Section 1", "Section 2"],
        },
        "property_schema": [
            {"key": "items", "label": "Section Titles", "inputType": "list"},
        ],
    },
    # ---------------------------------------------------------------- Branding
    {
        "type": "image",
        "label": "Image / Logo",
        "icon": "image",
        "category": "Branding",
        "is_container": False,
        "default_props": {
            "src": "",
            "alt": "Company Logo",
            "fit": "contain",
        },
        "property_schema": [
            {"key": "src", "label": "Logo / Image", "inputType": "image"},
            {"key": "alt", "label": "Alt Text", "inputType": "text"},
            {
                "key": "fit",
                "label": "Fit",
                "inputType": "select",
                "options": ["contain", "cover", "fill"],
            },
        ],
    },
    {
        "type": "avatar",
        "label": "Avatar",
        "icon": "account_circle",
        "category": "Branding",
        "is_container": False,
        "default_props": {
            "src": "",
            "initials": "AB",
            "shape": "circle",
            "size": 40,
        },
        "property_schema": [
            {"key": "src", "label": "Image", "inputType": "image"},
            {"key": "initials", "label": "Initials (fallback)", "inputType": "text"},
            {
                "key": "shape",
                "label": "Shape",
                "inputType": "select",
                "options": ["circle", "square"],
            },
            {"key": "size", "label": "Size (px)", "inputType": "number"},
        ],
    },
    {
        "type": "video_embed",
        "label": "Video Embed",
        "icon": "smart_display",
        "category": "Branding",
        "is_container": False,
        "default_props": {
            "url": "",
            "autoplay": False,
        },
        "property_schema": [
            {"key": "url", "label": "Video URL (embed link)", "inputType": "text"},
            {"key": "autoplay", "label": "Autoplay", "inputType": "boolean"},
        ],
    },
    {
        "type": "icon",
        "label": "Icon",
        "icon": "emoji_symbols",
        "category": "Branding",
        "is_container": False,
        "default_props": {
            "glyph": "★",
            "size": 24,
            "color": "#17a2b8",
        },
        "property_schema": [
            {"key": "glyph", "label": "Icon / Emoji", "inputType": "text"},
            {"key": "size", "label": "Size (px)", "inputType": "number"},
            {"key": "color", "label": "Color", "inputType": "color"},
        ],
    },
    # ---------------------------------------------------------------- Display
    {
        "type": "badge",
        "label": "Badge",
        "icon": "label",
        "category": "Display",
        "is_container": False,
        "default_props": {
            "text": "Badge",
            "tone": "neutral",
        },
        "property_schema": [
            {"key": "text", "label": "Text", "inputType": "text"},
            {
                "key": "tone",
                "label": "Tone",
                "inputType": "select",
                "options": ["neutral", "success", "warning", "danger", "info"],
            },
        ],
    },
    {
        "type": "list",
        "label": "List",
        "icon": "list",
        "category": "Display",
        "is_container": False,
        "default_props": {
            "label": "",
            "items": ["Item 1", "Item 2"],
            "itemType": "bullet",
        },
        "property_schema": [
            {"key": "label", "label": "Title (optional)", "inputType": "text"},
            {"key": "items", "label": "Items", "inputType": "list"},
            {
                "key": "itemType",
                "label": "Style",
                "inputType": "select",
                "options": ["bullet", "numbered", "plain"],
            },
        ],
    },
    {
        "type": "data_table",
        "label": "Data Table",
        "icon": "table_chart",
        "category": "Display",
        "is_container": False,
        "default_props": {
            "sourcePageId": "",
            "pageSize": 50,
        },
        "property_schema": [
            {"key": "sourcePageId", "label": "Source Page", "inputType": "page_select"},
            {"key": "pageSize", "label": "Rows per Page", "inputType": "number"},
        ],
    },
    {
        "type": "progress_bar",
        "label": "Progress Bar",
        "icon": "linear_scale",
        "category": "Display",
        "is_container": False,
        "default_props": {
            "value": 60,
            "showLabel": True,
            "color": "#17a2b8",
        },
        "property_schema": [
            {"key": "value", "label": "Value (0-100)", "inputType": "number"},
            {"key": "showLabel", "label": "Show Percentage", "inputType": "boolean"},
            {"key": "color", "label": "Color", "inputType": "color"},
        ],
    },
    {
        "type": "rating",
        "label": "Rating",
        "icon": "star",
        "category": "Display",
        "is_container": False,
        "default_props": {
            "value": 3,
            "max": 5,
            "color": "#f59e0b",
        },
        "property_schema": [
            {"key": "value", "label": "Value", "inputType": "number"},
            {"key": "max", "label": "Max Stars", "inputType": "number"},
            {"key": "color", "label": "Color", "inputType": "color"},
        ],
    },
    # ---------------------------------------------------------------- Advanced
    {
        "type": "kanban_board",
        "label": "Kanban Board",
        "icon": "view_kanban",
        "category": "Advanced",
        "is_container": True,
        "default_props": {
            "label": "Kanban Board",
            "columns": [
                {"id": "todo", "title": "To Do"},
                {"id": "in_progress", "title": "In Progress"},
                {"id": "done", "title": "Done"},
            ],
            "allowAddCards": True,
        },
        "property_schema": [
            {"key": "label", "label": "Label", "inputType": "text"},
            {"key": "columns", "label": "Columns", "inputType": "list"},
            {"key": "allowAddCards", "label": "Allow Adding Cards", "inputType": "boolean"},
        ],
    },
]


def seed_component_definitions() -> None:
    """Upserts every entry in COMPONENT_DEFINITIONS.

    Existing documents are updated in place (without touching their original
    created_at) so re-running this after a code change — e.g. adding
    `fieldKey` to text inputs, or upgrading Button's `action` to a structured
    object — actually reaches databases that were seeded before the change.
    """
    db = get_database()
    init_indexes()

    now = datetime.utcnow()
    inserted = 0
    updated = 0

    for item in COMPONENT_DEFINITIONS:
        payload = dict(item)
        payload.setdefault("is_input", False)
        payload.setdefault("data_type", "string")
        payload["updated_at"] = now

        result = db.component_definitions.update_one(
            {"type": payload["type"]},
            {
                "$set": payload,
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        if result.upserted_id is not None:
            inserted += 1
        elif result.modified_count:
            updated += 1

    print(
        f"Component definitions: {inserted} inserted, {updated} updated "
        f"(of {len(COMPONENT_DEFINITIONS)} total) in '{db.name}.component_definitions'."
    )


if __name__ == "__main__":
    seed_component_definitions()
