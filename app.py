from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename

from database import get_connection, init_db


app = Flask(__name__)

app.secret_key = "lost-and-found-secret-key"


# =========================
# DATABASE
# =========================

init_db()


# =========================
# IMAGE UPLOAD SETTINGS
# =========================

UPLOAD_FOLDER = Path("static/uploads")

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


# =========================
# LOCATION OPTIONS
# =========================

LOCATION_OPTIONS = {

    "Academic Blocks": [
        "SJT",
        "TT",
        "PRP",
        "SMV",
        "MB",
        "GDN",
        "CDMM"
    ],

    "Men's Hostel": [
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "G",
        "H",
        "I",
        "J",
        "K",
        "L",
        "M",
        "N",
        "O",
        "P",
        "Q",
        "R",
        "S",
        "T"
    ],

    "Women's Hostel": [
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "G",
        "H",
        "I",
        "J"
    ],

    "Food Courts": [
        "Gazebo",
        "Food Mall",
        "DC"
    ],

    "Central Library": [
        "Central Library"
    ],

    "Sports Complex": [
        "Sports Complex"
    ]
}


# =========================
# ITEM OPTIONS
# =========================

ITEM_OPTIONS = [
    "ID Cards",
    "Room Keys",
    "Calculators",
    "Lab Equipment",
    "Earphones",
    "Wallets"
]


# =========================
# HELPER FUNCTION
# =========================

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# =========================
# HOME PAGE
# =========================

@app.route("/")
def home():

    return render_template("index.html")


# =========================
# FINDER LOGIN PAGE
# =========================

@app.route("/finder")
def finder():

    # If a Finder is already logged in,
    # send them directly to the Finder dashboard.

    if "finder_id" in session:

        return redirect(
            url_for("finder_dashboard")
        )

    return render_template(
        "finder_login.html"
    )


# =========================
# FINDER LOGIN
# =========================

@app.route("/finder/login", methods=["POST"])
def finder_login():

    finder_id = request.form.get(
        "finder_id",
        ""
    ).strip()


    # Make sure an ID was entered

    if not finder_id:

        flash(
            "Please enter your registration ID.",
            "error"
        )

        return redirect(
            url_for("finder")
        )


    # Store the Finder's ID in the session

    session["finder_id"] = finder_id


    return redirect(
        url_for("finder_dashboard")
    )


# =========================
# FINDER DASHBOARD
# =========================

@app.route("/finder/dashboard")
def finder_dashboard():

    # Check whether someone is logged in

    finder_id = session.get("finder_id")


    if not finder_id:

        return redirect(
            url_for("finder")
        )


    # Get only this Finder's items

    connection = get_connection()

    items = connection.execute(
        """
        SELECT *
        FROM items
        WHERE finder_id = ?
        ORDER BY id DESC
        """,
        (finder_id,)
    ).fetchall()

    connection.close()


    return render_template(
        "finder.html",
        locations=LOCATION_OPTIONS,
        items=ITEM_OPTIONS,
        finder_id=finder_id,
        posted_items=items
    )


# =========================
# FINDER LOGOUT
# =========================

@app.route("/finder/logout")
def finder_logout():

    session.pop(
        "finder_id",
        None
    )

    return redirect(
        url_for("finder")
    )


# =========================
# POST FOUND ITEM
# =========================

@app.route("/post", methods=["POST"])
def post_item():

    # =========================
    # CHECK LOGIN
    # =========================

    finder_id = session.get(
        "finder_id"
    )


    if not finder_id:

        flash(
            "Please log in as a Finder first.",
            "error"
        )

        return redirect(
            url_for("finder")
        )


    # =========================
    # GET FORM DATA
    # =========================

    location_type = request.form.get(
        "location_type",
        ""
    ).strip()

    location = request.form.get(
        "location",
        ""
    ).strip()

    item = request.form.get(
        "item",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    picture = request.files.get("picture")


    # =========================
    # VALIDATE LOCATION
    # =========================

    if location_type not in LOCATION_OPTIONS:

        flash(
            "Please select a valid location.",
            "error"
        )

        return redirect(
            url_for("finder_dashboard")
        )


    if location not in LOCATION_OPTIONS[location_type]:

        flash(
            "Please select a valid specific location.",
            "error"
        )

        return redirect(
            url_for("finder_dashboard")
        )


    # =========================
    # VALIDATE ITEM
    # =========================

    if item not in ITEM_OPTIONS:

        flash(
            "Please select a valid item.",
            "error"
        )

        return redirect(
            url_for("finder_dashboard")
        )


    # =========================
    # VALIDATE DESCRIPTION
    # =========================

    if not description:

        flash(
            "Please enter a description.",
            "error"
        )

        return redirect(
            url_for("finder_dashboard")
        )


    # =========================
    # CONNECT TO DATABASE
    # =========================

    connection = get_connection()


    # =========================
    # MAKE SURE USER EXISTS
    # =========================

    connection.execute(
        """
        INSERT OR IGNORE INTO users
        (registration_id)

        VALUES (?)
        """,

        (finder_id,)
    )


    # =========================
    # SAVE IMAGE
    # =========================

    picture_filename = None


    if picture and picture.filename:

        if not allowed_file(picture.filename):

            connection.close()

            flash(
                "Please upload a PNG, JPG, JPEG, or WEBP image.",
                "error"
            )

            return redirect(
                url_for("finder_dashboard")
            )


        picture_filename = secure_filename(
            picture.filename
        )


        picture.save(
            UPLOAD_FOLDER / picture_filename
        )


    # =========================
    # SAVE ITEM
    # =========================

    connection.execute(
        """
        INSERT INTO items (

            finder_id,
            location_type,
            location,
            item,
            description,
            picture,
            status

        )

        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,

        (
            finder_id,
            location_type,
            location,
            item,
            description,
            picture_filename,
            "unclaimed"
        )
    )


    connection.commit()

    connection.close()


    # =========================
    # SUCCESS
    # =========================

    flash(
        "Your found item has been posted successfully!",
        "success"
    )


    return redirect(
        url_for("finder_dashboard")
    )


# =========================
# RUN APPLICATION
# =========================

if __name__ == "__main__":

    app.run(debug=True)