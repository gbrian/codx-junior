## INSTRUCTIONS
 - We need to split the code file into small chunks to be used by our code search engine.
 - Our code search engine will help users to find related pieces of code that can help them with their tasks.
 - We must be able to recreate the file back from its pieces, make sure all code lines are present in the chunks.
 - Our code search engine will answer questions using the user's request code language like:
    * Q: How can I retrieve the booking information? Code language: python
      A: To retrieve a booing information you can call the API end point GET `/api/booking/booking/:id`  
      Here's an example in python

      ```python
      import requests



      requests.get('/api/booking/booking/19897')
      ```
      REFERENCES:
      * /file/path/to/existing/code.js
      * /file/path/to/existing/wiki.md

- Split the code file into pieces into a JSON object list like:
  ```json
  [
    {
      "file": "/tah/to/bookingUtils.js",
      "language": "js",
      "code": "function getBookingId (booking: Booking) {\n\treturn booking.id\n\t\n}",
      "className": null, // This function is global
      "keywords": ["function", "Booking", "getBookingId", "bookingUtils"],
      "documentation": "Allows to retrieve booking's id. A Booking instance is requitred."
    },
    {
      "file": "/tah/to/User.py",
      "language": "py",
      "code": "def is_admin (self):\n\treturn True if self.user.role == 'admin' else False\n}",
      "className": "User", // This function is a method of User's class
      "keywords": ["function", "user", "role", "is_admin", "User"],
      "documentation": "Checks if current user at User's is admin."
    }
  ]
  ```

## CODE FILE
Path: {{ source }}
```{{ language }}
{{ page_content }}
``` 