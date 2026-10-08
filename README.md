# Lost-and-Found
This website created by a 1st year student aims to replace the messy Whatsapp groups in VIT and give students a direct way to return and/or retrieve items that have been misplaced across the campus.

The Architecture:-
1.	Python application – Everything is live and works in real time connected through the app.py file. There is no separate API server or frontend application.
2.	HTML – Flask renders the pages which use Jinja syntax to insert the data and generate links.
3.	Browser-Side JavaScript – Plain JavaScript handles the search, dropdowns etc... The chat updates in real time (with a buffer of 3 seconds)/
4.	Images – The pictures are saved in the static folder under uploads. The database stores the filename from where it is retrieved. 
5.	Sessions – Flask maintains cookies so that the app can associate later requests with particular Logins.

Browser → Flask route → SQLite query or update → Jinja page or JSON response
Some interactions use JavaScript calls and JSON responses. 

Database maintenance and ideology :-
There is a common database maintained from where information is appended, edited and deleted as per the user’s actions. The bootstrap ensures the existence of 5 tables: users, items, claims, verification questions, claim messages. 

Libraries used :-
Flask – For routes, sessions, flash messages, templates and JSON responses
Werkzeug – To maintain the uploaded files. 
sqlite3 and pathlib (in-built to python) – Database access and file paths 
Jinja2 – Flask’s template engine for the HTML templates.
HTML, CSS and JavaScript are used in the browser
Flexbox and CSS Grid for layout. The rules correspond to the classes used in the HTML templates. 

Process/Flow of the website:-
1.	Claiming Process: A finder posts an item and can add up to 3 verification questions. A looker browses unclaimed items, answers those questions and can submit a claim only if it the answers are correct. The finder can chat with the looker and approve or reject the claim. Approval marks the item claimed and rejects other pending claims to it. 
2.	Logins – As of now there is no real authentication in the login. Separate user IDs are used to keep the data separate and only show relevant information to the user. future we can link this login process to the university email id and make things more official and secure.

Hardcoded material:-
1.	Flask uses the secret key to sign its session cookie. If someone knows it then they can forge a session cookie and manipulate the functioning of the site but that can be randomized if the site is to go public.
2.	When run directly with python the website runs with Flask’s development mode i.e. an interactive error debugger and automatic reloads when the code is changed. Flask says not to expose it in the production. Any function ns in the website can be tracked in the Powersheel based terminal I’ve used during the making of this website. 
3. Nothing in the website is deliberately hardcoded.


Thanks for reading. Hope you enjoy the website. 


For any queries or suggestions, you can contact me via the following methods :-
1. Phone/Whatsapp - +91 8591125491
2. Email_id - darshil.axayshah2026@vitstudent.ac.in  or alternatively darshil460@gmail.com
