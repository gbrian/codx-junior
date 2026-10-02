This markdown file contains all 68 DaisyUI components organized by category with minimal HTML examples showing basic usage only.

# DaisyUI Components Reference

## Actions

### Button
```html
<button class="btn">Default</button>
<button class="btn btn-primary">Primary</button>
<button class="btn btn-sm">Small</button>
<button class="btn btn-lg">Large</button>
<button class="btn btn-outline">Outline</button>
<button class="btn btn-wide">Wide</button>
<button class="btn btn-block">Full Width</button>
<button class="btn btn-circle">Circle</button>
```

### Dropdown
```html
<div class="dropdown">
  <button class="btn btn-primary">Dropdown</button>
  <ul class="dropdown-content menu">
    <li><a href="#">Item 1</a></li>
    <li><a href="#">Item 2</a></li>
  </ul>
</div>
```

### FAB / Speed Dial
```html
<div class="fab">
  <button class="btn btn-circle btn-primary">+</button>
</div>
```

### Modal
```html
<dialog class="modal" id="my_modal">
  <div class="modal-box">
    <h3>Title</h3>
    <p>Content</p>
    <form method="dialog">
      <button>Close</button>
    </form>
  </div>
</dialog>
<button class="btn" onclick="my_modal.showModal()">Open</button>
```

### Swap
```html
<input type="checkbox" class="swap"/>
<div class="swap-on">On</div>
<div class="swap-off">Off</div>
```

### Theme Controller
```html
<input type="checkbox" class="theme-controller" value="dark"/>
```

---

## Data Display

### Accordion
```html
<div class="collapse">
  <input type="radio" name="accordion"/>
  <div class="collapse-title">Title</div>
  <div class="collapse-content">Content</div>
</div>
```

### Avatar
```html
<div class="avatar">
  <div class="w-24 rounded">
    <img src="image.jpg"/>
  </div>
</div>
```

### Aura
```html
<div class="aura">
  <button class="btn btn-primary">Button with Aura</button>
</div>
```

### Badge
```html
<span class="badge">Badge</span>
<span class="badge badge-primary">Primary</span>
<span class="badge badge-outline">Outline</span>
<span class="badge badge-lg">Large</span>
```

### Card
```html
<div class="card bg-base-100 w-96 shadow-sm">
  <figure><img src="image.jpg"/></figure>
  <div class="card-body">
    <h2 class="card-title">Title</h2>
    <p>Content</p>
    <div class="card-actions">
      <button class="btn btn-primary">Action</button>
    </div>
  </div>
</div>
```

### Carousel
```html
<div class="carousel w-full">
  <div class="carousel-item">Item 1</div>
  <div class="carousel-item">Item 2</div>
</div>
```

### Chat Bubble
```html
<div class="chat chat-start">
  <div class="chat-bubble">Message</div>
</div>
```

### Collapse
```html
<div class="collapse">
  <input type="checkbox"/>
  <div class="collapse-title">Title</div>
  <div class="collapse-content">Content</div>
</div>
```

### Countdown
```html
<span class="countdown" data-value="3"></span>
```

### Diff
```html
<div class="diff">
  <div class="diff-item-1">Before</div>
  <div class="diff-item-2">After</div>
</div>
```

### Hover 3D Card
```html
<div class="hover-3d">
  <div class="card">3D Content</div>
</div>
```

### Hover Gallery
```html
<div class="hover-gallery">
  <img src="img1.jpg"/>
  <img src="img2.jpg"/>
</div>
```

### Kbd
```html
<kbd class="kbd">Ctrl</kbd>
<kbd class="kbd">+</kbd>
<kbd class="kbd">C</kbd>
```

### List
```html
<ul class="list">
  <li>Item 1</li>
  <li>Item 2</li>
</ul>
```

### Stat
```html
<div class="stat">
  <div class="stat-title">Title</div>
  <div class="stat-value">100</div>
  <div class="stat-desc">Description</div>
</div>
```

### Status
```html
<span class="status status-online"></span>
<span class="status status-offline"></span>
```

### Table
```html
<table class="table">
  <thead>
    <tr><th>Header</th></tr>
  </thead>
  <tbody>
    <tr><td>Data</td></tr>
  </tbody>
</table>
```

### Text Rotate
```html
<div class="text-rotate">
  <div>Line 1</div>
  <div>Line 2</div>
</div>
```

### Timeline
```html
<ul class="timeline">
  <li>
    <div class="timeline-start">Date</div>
    <div class="timeline-middle">Event</div>
  </li>
</ul>
```

---

## Navigation

### Breadcrumbs
```html
<div class="breadcrumbs">
  <ul>
    <li><a href="#">Home</a></li>
    <li><a href="#">Page</a></li>
    <li>Current</li>
  </ul>
</div>
```

### Dock
```html
<div class="dock">
  <a href="#" class="dock-item">Item 1</a>
  <a href="#" class="dock-item">Item 2</a>
</div>
```

### Link
```html
<a href="#" class="link">Link</a>
<a href="#" class="link link-primary">Primary Link</a>
```

### Megamenu
```html
<div class="megamenu">
  <details>
    <summary>Menu</summary>
    <ul class="menu">
      <li><a href="#">Item</a></li>
    </ul>
  </details>
</div>
```

### Menu
```html
<ul class="menu">
  <li><a href="#">Item 1</a></li>
  <li><a href="#">Item 2</a></li>
</ul>
```

### Navbar
```html
<div class="navbar bg-base-100">
  <div class="flex-1">Logo</div>
  <ul class="menu menu-horizontal">
    <li><a href="#">Link</a></li>
  </ul>
</div>
```

### Pagination
```html
<div class="join">
  <button class="join-item btn">«</button>
  <button class="join-item btn btn-active">1</button>
  <button class="join-item btn">2</button>
  <button class="join-item btn">»</button>
</div>
```

### Steps
```html
<ul class="steps">
  <li class="step step-primary">Step 1</li>
  <li class="step step-primary">Step 2</li>
  <li class="step">Step 3</li>
</ul>
```

### Tabs
```html
<div class="tabs">
  <input type="radio" name="tabs" class="tab" label="Tab 1"/>
  <div class="tab-content">Content 1</div>
  
  <input type="radio" name="tabs" class="tab" label="Tab 2"/>
  <div class="tab-content">Content 2</div>
</div>
```

---

## Feedback

### Alert
```html
<div role="alert" class="alert">
  <span>Information message</span>
</div>
<div role="alert" class="alert alert-info">Info</div>
<div role="alert" class="alert alert-success">Success</div>
<div role="alert" class="alert alert-warning">Warning</div>
<div role="alert" class="alert alert-error">Error</div>
```

### Loading
```html
<span class="loading"></span>
<span class="loading loading-spinner"></span>
<span class="loading loading-dots"></span>
<span class="loading loading-ring"></span>
```

### Progress
```html
<progress class="progress" value="45" max="100"></progress>
<progress class="progress progress-primary" value="45" max="100"></progress>
```

### Radial Progress
```html
<div class="radial-progress" style="--value:70">70%</div>
```

### Skeleton
```html
<div class="skeleton h-32 w-32"></div>
```

### Toast
```html
<div class="toast">
  <div class="alert">Message</div>
</div>
```

### Tooltip
```html
<button class="btn" data-tip="Tooltip text">Hover</button>
```

---

## Data Input

### Calendar
```html
<input type="date" class="input input-bordered"/>
```

### Checkbox
```html
<input type="checkbox" class="checkbox"/>
<input type="checkbox" class="checkbox checkbox-primary" checked/>
```

### Fieldset
```html
<fieldset class="fieldset">
  <legend class="fieldset-legend">Legend</legend>
  <input class="input" placeholder="Input"/>
</fieldset>
```

### File Input
```html
<input type="file" class="file-input"/>
```

### Filter
```html
<div class="filter">
  <label class="filter-item">
    <input type="radio" name="filter"/>
    <span>Option 1</span>
  </label>
</div>
```

### Label
```html
<label class="label">
  <span class="label-text">Label</span>
</label>
```

### Radio
```html
<input type="radio" class="radio"/>
<input type="radio" class="radio radio-primary" checked/>
```

### Range
```html
<input type="range" class="range"/>
```

### Rating
```html
<div class="rating">
  <input type="radio" name="rating" class="rating-hidden"/>
  <input type="radio" name="rating" class="mask mask-star"/>
  <input type="radio" name="rating" class="mask mask-star" checked/>
</div>
```

### Select
```html
<select class="select">
  <option>Choose</option>
  <option>Option 1</option>
  <option>Option 2</option>
</select>
```

### Input Field
```html
<input type="text" class="input" placeholder="Placeholder"/>
<input type="text" class="input input-bordered"/>
<input type="text" class="input input-primary"/>
```

### Textarea
```html
<textarea class="textarea" placeholder="Text"></textarea>
```

### Toggle
```html
<input type="checkbox" class="toggle"/>
<input type="checkbox" class="toggle toggle-primary" checked/>
```

### Validator
```html
<input type="email" class="input input-error" placeholder="Invalid"/>
<input type="text" class="input input-success" placeholder="Valid"/>
```

### OTP
```html
<div class="otp-input">
  <input type="text" class="otp" maxlength="1"/>
  <input type="text" class="otp" maxlength="1"/>
  <input type="text" class="otp" maxlength="1"/>
</div>
```

---

## Layout

### Divider
```html
<div class="divider">OR</div>
```

### Drawer
```html
<div class="drawer">
  <input id="drawer" type="checkbox" class="drawer-toggle"/>
  <div class="drawer-content">Main content</div>
  <div class="drawer-side">
    <label for="drawer">Menu</label>
  </div>
</div>
```

### Footer
```html
<footer class="footer">
  <div>
    <span class="footer-title">Company</span>
    <a href="#">Link</a>
  </div>
</footer>
```

### Hero
```html
<div class="hero min-h-screen">
  <div class="hero-content text-center">
    <h1 class="text-5xl font-bold">Hero Title</h1>
  </div>
</div>
```

### Indicator
```html
<div class="indicator">
  <span class="indicator-item badge badge-primary">99+</span>
  <button class="btn">Button</button>
</div>
```

### Join
```html
<div class="join">
  <input class="join-item input"/>
  <button class="join-item btn">Search</button>
</div>
```

### Mask
```html
<div class="mask mask-circle w-24">
  <img src="image.jpg"/>
</div>
```

### Stack
```html
<div class="stack">
  <div>Layer 1</div>
  <div>Layer 2</div>
</div>
```

---

## Mockup

### Browser
```html
<div class="mockup-browser">
  <div class="mockup-browser-toolbar">
    <div class="input">https://example.com</div>
  </div>
  <div>Content</div>
</div>
```

### Code
```html
<div class="mockup-code">
  <pre><code>Code content</code></pre>
</div>
```

### Phone
```html
<div class="mockup-phone">
  <div class="camera"></div>
  <div class="display">
    <div>Phone content</div>
  </div>
</div>
```

### Window
```html
<div class="mockup-window border">
  <div class="px-4 py-16">Content</div>
</div>
```
