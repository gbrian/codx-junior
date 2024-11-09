# [[{"id": "0", "parent_id": "", "status": "", "tags": [], "file_list": [], "profiles": [], "name": "Helimn cheatsheet", "created_at": "2024-11-06T18:35:01.308457", "updated_at": "2024-11-06T18:35:01.308457", "mode": "chat", "board": "", "column": "new column", "column_index": 10000, "chat_index": 0, "live_url": "", "branch": ""}]]
## [[{"role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2024-11-06T18:35:01.308520", "updated_at": "", "images": [], "files": []}]]
Given this document create a cheatsheet table with all commenads, description and usage example:



# Helium cheatsheet


This page very quickly teaches you the most important parts of Helium's API.


## Importing


All of Helium's public functions lie directly in the module `helium`.
You can for instance import them as follows:


```python
from helium import *
```


## Starting a browser


Helium currently supports Chrome and Firefox. You can start them with the
following functions:


```python
start_chrome()
start_firefox()
```


You can optionally pass a URL to open (eg. `start_chrome('google.com')`)


## Headless browser


When you type the above commands, you will actually see a browser window open.
This is useful for developing your scripts. However, once you run them, you may
not want this window to appear. You can achieve this by adding `headless=True`:


```python
start_chrome(headless=True)
start_chrome('google.com', headless=True)
```


(Similarly for `start_firefox(...)` of course.)


## Interacting with a web site


The following example shows the most typical statements in a Helium script:


```python
from helium import *
start_chrome('google.com')
write('helium selenium github')
press(ENTER)
click('mherrmann/helium')
go_to('github.com/login')
write('username', into='Username')
write('password', into='Password')
click('Sign in')
kill_browser()
```


Most of your own code will (hopefully) be as simple as the above.


## Element types


The above example used pure strings such as `Sign in` to identify elements on
the web page. But Helium also lets you target elements more specifically.
For instance:


 * [`Link('Sign in')`](https://github.com/mherrmann/helium/blob/0667ddb9be531367a0d707ad8f5fcfb75c528521/helium/__init__.py#L643)
 * [`Button('Sign in')`](https://github.com/mherrmann/helium/blob/0667ddb9be531367a0d707ad8f5fcfb75c528521/helium/__init__.py#L706)
 * [`TextField('First name')`](https://github.com/mherrmann/helium/blob/0667ddb9be531367a0d707ad8f5fcfb75c528521/helium/__init__.py#L768)
 * [`CheckBox('I accept')`](https://github.com/mherrmann/helium/blob/0667ddb9be531367a0d707ad8f5fcfb75c528521/helium/__init__.py#L867)
 * [`RadioButton('Windows')`](https://github.com/mherrmann/helium/blob/0667ddb9be531367a0d707ad8f5fcfb75c528521/helium/__init__.py#L907)
 * [`Image(alt='Helium logo')`](https://github.com/mherrmann/helium/blob/0667ddb9be531367a0d707ad8f5fcfb75c528521/helium/__init__.py#L739)


You can pass them into other functions such as `click(Link('Sign in'))`.
But you can also use them to _read_ data from the web site. For instance:


```python
print(TextField('First name').value)
```


A common use case is to use `.exists()` to check for the existence of an
element. For example:


```python
if Text('Accept cookies?').exists():
    click('I accept')
```


I also often find `Text(...).value` useful for reading out data:


```python
name = Text(to_right_of='Name:', below=Image(alt='Profile picture')).value
```


For a full list of element types and their properties, please see
[the source code](https://github.com/mherrmann/helium/blob/0667ddb9be531367a0d707ad8f5fcfb75c528521/helium/__init__.py#L470-L1008).


## Finding elements relative to others


You already saw in the previous section how `above=...` and `to_right_of=...`
let you find elements relative to other elements. You can similarly use
`below=...` and `to_left_of`. Here are some more examples.


```python
Text(above='Balance', below='Transactions').value
Link(to_right_of='Invoice:')
Image(to_right_of=Link('Sign in', below=Text('Navigation')))
```


## Waiting for elements to appear (or other conditions)


Use
[`wait_until(...)`](https://github.com/mherrmann/helium/blob/0667ddb9be531367a0d707ad8f5fcfb75c528521/helium/__init__.py#L410)
to wait for a condition to become true. For example:


```python
wait_until(Button('Download').exists)
```


But you can also use this to wait for an arbitrary condition:


```python
wait_until(lambda: TextField('Balance').value == '$2M')
```


## jQuery-style selectors


Sometimes, you do need to fall back to using HTML IDs, CSS Selectors or XPaths
to identify an element on the web page. Helium's
[`S(...)`](https://github.com/mherrmann/helium/blob/0667ddb9be531367a0d707ad8f5fcfb75c528521/helium/__init__.py#L568)
predicate lets you do this. The parameter you pass to it is interpreted as
follows:


* If it starts with an ``@``, then it identifies elements by HTML ``name``.
  Eg. ``S("@btnName")`` identifies an element with ``name="btnName"``.
* If it starts with ``//``, then Helium interprets it as an XPath.
* Otherwise, Helium interprets it as a CSS selector. This in particular
  lets you write ``S("#myId")`` to identify an element with ``id="myId"``,
  or ``S(".myClass")`` to identify elements with ``class="myClass"``.


As before, you can combine `S(...)` with other functions such as
`click(S(...))`, or use it to extract data. For an example of this, see
[below](#finding-all-elements).


## Combining Helium and Selenium's APIs


All Helium does is translate your high-level commands into low-level Selenium
function calls. Because of this, you can freely mix Selenium and Helium. For
example:


```python
# A Helium function:
driver = start_chrome()
# A Selenium API:
driver.execute_script("alert('Hi!');")
```


You can also get / set the Selenium WebDriver which Helium uses via
[`get_driver()`](https://github.com/mherrmann/helium/blob/0667ddb9be531367a0d707ad8f5fcfb75c528521/helium/__init__.py#L104)
and
[`set_driver(...)`](https://github.com/mherrmann/helium/blob/0667ddb9be531367a0d707ad8f5fcfb75c528521/helium/__init__.py#L97).


With the WebDriver instance, you can execute any Selenium commands you want.


To use Helium's API's to obtain Selenium `WebElement`s, use the `.web_element`
property of Helium's various GUI elements. For instance:


```python
# Get the CSS class of the "Helium" link:
Link('Helium').web_element.get_attribute('class')
```


Here, `.get_attribute(...)` is a Selenium API.




## Finding all elements


The `.web_element` property and the `S(...)` predicate are particularly useful
for extracting multiple pieces of data from a web page. To do this, you can use
Helium's [`find_all(...)`](https://github.com/mherrmann/helium/blob/0667ddb9be531367a0d707ad8f5fcfb75c528521/helium/__init__.py#L281) function.
As its name implies, it lets you find all occurrences of an element on a page.
For example:


```python
email_cells = find_all(S("table > tr > td", below="Email"))
emails = [cell.web_element.text for cell in email_cells]
```


## Implicit waits


When you issue a command such as `click('Download')`, Helium by default waits
up to 10 seconds for the respective element to appear. This feature is called
"implicit waiting". You can change the 10 second default to a different value
via the
[`Config` class](https://github.com/mherrmann/helium/blob/0667ddb9be531367a0d707ad8f5fcfb75c528521/helium/__init__.py#L437):


```python
Config.implicit_wait_secs = 30
```


However, before you do this, it may be better to add explicit waits to your
code, such as `wait_until(Button('Download').exists)`.


## Alerts


The
[`Alert` class](https://github.com/mherrmann/helium/blob/0667ddb9be531367a0d707ad8f5fcfb75c528521/helium/__init__.py#L970)
lets you interface with JavaScript popup boxes. Use `Alert().accept()`,
`Alert().dismiss()` to click "Ok" or "Cancel", `Alert().text` to read the
message shown, or `write(..., into=Alert())` to enter a value.


## File uploads, drag and drop, combo boxes, popups


Use
[`attach_file(...)`](https://github.com/mherrmann/helium/blob/0667ddb9be531367a0d707ad8f5fcfb75c528521/helium/__init__.py#L388),
[`drag_file(...)`](https://github.com/mherrmann/helium/blob/0667ddb9be531367a0d707ad8f5fcfb75c528521/helium/__init__.py#L375),
[`drag(...)`](https://github.com/mherrmann/helium/blob/0667ddb9be531367a0d707ad8f5fcfb75c528521/helium/__init__.py#L252),
[`select(...)`](https://github.com/mherrmann/helium/blob/0667ddb9be531367a0d707ad8f5fcfb75c528521/helium/__init__.py#L362),
[`switch_to(...)`](https://github.com/mherrmann/helium/blob/0667ddb9be531367a0d707ad8f5fcfb75c528521/helium/__init__.py#L1057).


## Clicking at x, y coordinates


Sometimes, you may want to click at a specific `(x, y)` coordinate, or at an
offset of an element. See the
[`Point` class](https://github.com/mherrmann/helium/blob/0667ddb9be531367a0d707ad8f5fcfb75c528521/helium/__init__.py#L1010)
for how.


## Taking a screenshot


Use Selenium's API:


```python
get_driver().save_screenshot(r'C:\screenshot.png')
```


Note the leading `r`. This is required because the string contains a backslash
`\`.


## [[{"role": "assistant", "task_item": "", "hide": false, "improvement": false, "created_at": "2024-11-06T18:35:01.308559", "updated_at": "", "images": [], "files": ["/puppeter.py", "/__init__.py", "/helium.md"]}]]
Here's a cheatsheet table for the Helium API:

| Command                          | Description                                           | Usage Example                                       |
|----------------------------------|------------------------------------------------------|-----------------------------------------------------|
| `from helium import *`          | Import all public functions from Helium module.     | ```python from helium import * ```                  |
| `start_chrome()`                | Start a Chrome browser.                             | ```python start_chrome() ```                        |
| `start_firefox()`               | Start a Firefox browser.                            | ```python start_firefox() ```                       |
| `start_chrome('url')`           | Start Chrome and open a specific URL.              | ```python start_chrome('google.com') ```           |
| `start_firefox('url')`          | Start Firefox and open a specific URL.             | ```python start_firefox('google.com') ```          |
| `headless=True`                 | Run the browser in headless mode.                   | ```python start_chrome(headless=True) ```          |
| `write(text)`                   | Type text into the currently focused input.         | ```python write('helium selenium github') ```      |
| `press(key)`                    | Press a specific key.                               | ```python press(ENTER) ```                          |
| `click(element)`                | Click on a specified web element.                   | ```python click('Sign in') ```                      |
| `go_to(url)`                    | Navigate to a specific URL.                         | ```python go_to('github.com/login') ```            |
| `kill_browser()`                 | Close the currently open browser.                   | ```python kill_browser() ```                        |
| `Text('text').exists()`         | Check if a specific text exists on the page.       | ```python if Text('Accept cookies?').exists(): click('I accept') ``` |
| `wait_until(condition)`          | Wait for a condition to become true.                | ```python wait_until(Button('Download').exists) ```|
| `S(selector)`                    | Use jQuery-style selectors to find elements.        | ```python click(S('#myId')) ```                    |
| `find_all(selector)`            | Find all occurrences of an element on a page.      | ```python email_cells = find_all(S("table > tr > td", below="Email")) ``` |
| `Config.implicit_wait_secs`     | Set implicit wait duration (in seconds).            | ```python Config.implicit_wait_secs = 30 ```       |
| `Alert().accept()`               | Accept a JavaScript alert.                          | ```python Alert().accept() ```                      |
| `Alert().dismiss()`              | Dismiss a JavaScript alert.                         | ```python Alert().dismiss() ```                     |
| `attach_file(path)`             | Attach a file to an input element.                  | ```python attach_file('/path/to/file.txt') ```     |
| `drag_file(source, target)`     | Drag a file from source to target.                  | ```python drag_file('/path/to/file.txt', target) ```|
| `get_driver()`                   | Get the current Selenium WebDriver instance.        | ```python driver = get_driver() ```                 |
| `save_screenshot(path)`          | Take a screenshot of the current page.              | ```python get_driver().save_screenshot(r'C:\screenshot.png') ``` |

This table summarizes the essential commands, their descriptions, and usage examples for quick reference.