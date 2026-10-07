from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)
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
    "webp",
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
        "CDMM",
    ],
    "Men's Hostel": [
        "A", "B", "C", "D", "E", "F", "G", "H", "I", "J",
        "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
    ],
    "Women's Hostel": [
        "A", "B", "C", "D", "E", "F", "G", "H", "I", "J",
    ],
    "Food Courts": [
        "Gazebo",
        "Food Mall",
        "DC",
    ],
    "Central Library": [
        "Central Library",
    ],
    "Sports Complex": [
        "Sports Complex",
    ],
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
    "Wallets",
]


# =========================
# HELPER FUNCTIONS
# =========================

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def normalize_answer(answer):
    return answer.strip().lower()


def get_claim_table_columns(connection):
    return {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(claims)"
        ).fetchall()
    }


# =========================
# HOME PAGE
# =========================

@app.route("/")
def home():
    return render_template("index.html")


# =========================
# FINDER LOGIN
# =========================

@app.route("/finder")
def finder():
    if "finder_id" in session:
        return redirect(url_for("finder_dashboard"))

    return render_template("finder_login.html")


@app.route("/finder/login", methods=["POST"])
def finder_login():
    finder_id = request.form.get("finder_id", "").strip()

    if not finder_id:
        flash("Please enter your registration ID.", "error")
        return redirect(url_for("finder"))

    session["finder_id"] = finder_id
    return redirect(url_for("finder_dashboard"))


@app.route("/finder/dashboard")
def finder_dashboard():
    finder_id = session.get("finder_id")

    if not finder_id:
        return redirect(url_for("finder"))

    connection = get_connection()

    items = connection.execute(
        """
        SELECT *
        FROM items
        WHERE finder_id = ?
        ORDER BY id DESC
        """,
        (finder_id,),
    ).fetchall()

    connection.close()

    return render_template(
        "finder.html",
        locations=LOCATION_OPTIONS,
        items=ITEM_OPTIONS,
        finder_id=finder_id,
        posted_items=items,
    )


@app.route("/finder/logout")
def finder_logout():
    session.pop("finder_id", None)
    return redirect(url_for("finder"))


# =========================
# POST A FOUND ITEM
# =========================

@app.route("/post", methods=["POST"])
def post_item():
    finder_id = session.get("finder_id")

    if not finder_id:
        flash("Please log in as a Finder first.", "error")
        return redirect(url_for("finder"))

    location_type = request.form.get("location_type", "").strip()
    location = request.form.get("location", "").strip()
    item = request.form.get("item", "").strip()
    description = request.form.get("description", "").strip()
    picture = request.files.get("picture")

    # Read up to three verification question and answer pairs.
    verification_questions = []

    for i in range(1, 4):
        question = request.form.get(f"question_{i}", "").strip()
        answer = request.form.get(f"answer_{i}", "").strip()

        if not question and not answer:
            continue

        if question and not answer:
            flash(
                f"Please provide an answer for verification question {i}.",
                "error",
            )
            return redirect(url_for("finder_dashboard"))

        if answer and not question:
            flash(
                f"Please provide a question for verification answer {i}.",
                "error",
            )
            return redirect(url_for("finder_dashboard"))

        verification_questions.append(
            (question, normalize_answer(answer))
        )

    if location_type not in LOCATION_OPTIONS:
        flash("Please select a valid location.", "error")
        return redirect(url_for("finder_dashboard"))

    if location not in LOCATION_OPTIONS[location_type]:
        flash("Please select a valid specific location.", "error")
        return redirect(url_for("finder_dashboard"))

    if item not in ITEM_OPTIONS:
        flash("Please select a valid item.", "error")
        return redirect(url_for("finder_dashboard"))

    if not description:
        flash("Please enter a description.", "error")
        return redirect(url_for("finder_dashboard"))

    connection = get_connection()

    # Ensure the Finder exists in the users table.
    connection.execute(
        """
        INSERT OR IGNORE INTO users (registration_id)
        VALUES (?)
        """,
        (finder_id,),
    )

    picture_filename = None

    if picture and picture.filename:
        if not allowed_file(picture.filename):
            connection.close()
            flash(
                "Please upload a PNG, JPG, JPEG, or WEBP image.",
                "error",
            )
            return redirect(url_for("finder_dashboard"))

        picture_filename = secure_filename(picture.filename)
        picture.save(UPLOAD_FOLDER / picture_filename)

    cursor = connection.execute(
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
            "unclaimed",
        ),
    )

    item_id = cursor.lastrowid

    for question, answer in verification_questions:
        connection.execute(
            """
            INSERT INTO verification_questions (
                item_id,
                question,
                answer
            )
            VALUES (?, ?, ?)
            """,
            (item_id, question, answer),
        )

    connection.commit()
    connection.close()

    flash("Your found item has been posted successfully!", "success")
    return redirect(url_for("finder_dashboard"))


# =========================
# LOOKER PAGE AND LOGIN
# =========================

@app.route("/looker", methods=["GET", "POST"])
def looker():
    if request.method == "POST":
        looker_id = request.form.get("looker_id", "").strip()

        if not looker_id:
            flash("Please enter your registration ID.", "error")
        else:
            connection = get_connection()
            connection.execute(
                """
                INSERT OR IGNORE INTO users (registration_id)
                VALUES (?)
                """,
                (looker_id,),
            )
            connection.commit()
            connection.close()

            session["looker_id"] = looker_id
            return redirect(url_for("looker"))

    looker_id = session.get("looker_id")

    if not looker_id:
        return render_template("looker_login.html")

    connection = get_connection()

    items = connection.execute(
        """
        SELECT id, item, location_type, location, description, picture
        FROM items
        WHERE status = 'unclaimed'
        ORDER BY id DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "looker.html",
        looker_id=looker_id,
        items=items
    )


@app.route("/looker/logout")
def looker_logout():
    session.pop("looker_id", None)
    return redirect(url_for("looker"))


# =========================
# LOAD VERIFICATION QUESTIONS
# =========================

@app.route("/looker/item/<int:item_id>/questions", methods=["GET"])
def looker_item_questions(item_id):
    if not session.get("looker_id"):
        return jsonify({"message": "Please sign in again."}), 401

    connection = get_connection()

    item = connection.execute(
        """
        SELECT id
        FROM items
        WHERE id = ? AND status = 'unclaimed'
        """,
        (item_id,),
    ).fetchone()

    if item is None:
        connection.close()
        return jsonify({"message": "This item is no longer available."}), 404

    questions = connection.execute(
        """
        SELECT question
        FROM verification_questions
        WHERE item_id = ?
        ORDER BY id
        """,
        (item_id,),
    ).fetchall()

    connection.close()

    # The Looker receives the questions, never the stored answers.
    return jsonify({
        "questions": [row["question"] for row in questions]
    })


# =========================
# SUBMIT A CLAIM
# =========================

@app.route("/looker/claim/<int:item_id>", methods=["POST"])
def submit_looker_claim(item_id):
    looker_id = session.get("looker_id")

    if not looker_id:
        return jsonify({"message": "Please sign in again."}), 401

    payload = request.get_json(silent=True) or {}
    answers = payload.get("answers")

    if (
        not isinstance(answers, list)
        or any(not isinstance(answer, str) for answer in answers)
    ):
        return jsonify({
            "message": "Please answer each verification question."
        }), 400

    connection = get_connection()

    item = connection.execute(
        """
        SELECT id
        FROM items
        WHERE id = ? AND status = 'unclaimed'
        """,
        (item_id,),
    ).fetchone()

    if item is None:
        connection.close()
        return jsonify({"message": "This item is no longer available."}), 404

    questions = connection.execute(
        """
        SELECT answer
        FROM verification_questions
        WHERE item_id = ?
        ORDER BY id
        """,
        (item_id,),
    ).fetchall()

    if len(answers) != len(questions):
        connection.close()
        return jsonify({
            "message": "Please answer each verification question."
        }), 400

    for submitted_answer, question in zip(answers, questions):
        if normalize_answer(submitted_answer) != normalize_answer(question["answer"]):
            connection.close()
            return jsonify({
                "message": "Wrong answer. Please try again."
            }), 422

    claim_columns = get_claim_table_columns(connection)

    if "looker_id" in claim_columns:
        existing_claim = connection.execute(
            """
            SELECT id
            FROM claims
            WHERE item_id = ?
              AND looker_id = ?
              AND status = 'pending'
            """,
            (item_id, looker_id),
        ).fetchone()
    elif "looker" in claim_columns:
        existing_claim = connection.execute(
            """
            SELECT id
            FROM claims
            WHERE item_id = ?
              AND looker = ?
              AND status = 'pending'
            """,
            (item_id, looker_id),
        ).fetchone()
    else:
        connection.close()
        return jsonify({
            "message": "The claims table is missing its Looker ID column."
        }), 500

    if existing_claim:
        connection.close()
        return jsonify({
            "message": "You already have a pending claim for this item."
        }), 409

    if "looker_id" in claim_columns and "looker" in claim_columns:
        connection.execute(
            """
            INSERT INTO claims (item_id, looker, looker_id, status)
            VALUES (?, ?, ?, 'pending')
            """,
            (item_id, looker_id, looker_id),
        )
    elif "looker_id" in claim_columns:
        connection.execute(
            """
            INSERT INTO claims (item_id, looker_id, status)
            VALUES (?, ?, 'pending')
            """,
            (item_id, looker_id),
        )
    else:
        connection.execute(
            """
            INSERT INTO claims (item_id, looker, status)
            VALUES (?, ?, 'pending')
            """,
            (item_id, looker_id),
        )

    connection.commit()
    connection.close()

    return jsonify({
        "message": "Your claim has been submitted for Finder review."
    }), 201


# =========================
# FINDER CLAIMS PAGE
# =========================

@app.route("/finder/claims")
def finder_claims():
    finder_id = session.get("finder_id")

    if not finder_id:
        return redirect(url_for("finder"))

    connection = get_connection()
    claim_columns = get_claim_table_columns(connection)

    if "looker_id" in claim_columns:
        looker_column = "looker_id"
    elif "looker" in claim_columns:
        looker_column = "looker"
    else:
        connection.close()
        flash("The claims table is missing its Looker ID column.", "error")
        return redirect(url_for("finder_dashboard"))

    claims = connection.execute(
        f"""
        SELECT
            c.id AS claim_id,
            c.status AS claim_status,
            c.{looker_column} AS looker_id,
            i.id AS item_id,
            i.item,
            i.location_type,
            i.location,
            i.description,
            i.picture
        FROM claims AS c
        JOIN items AS i ON i.id = c.item_id
        WHERE i.finder_id = ?
        ORDER BY
            CASE WHEN c.status = 'pending' THEN 0 ELSE 1 END,
            c.id DESC
        """,
        (finder_id,)
    ).fetchall()

    connection.close()

    return render_template(
        "finder_claims.html",
        claims=claims,
        finder_id=finder_id
    )


# =========================
# APPROVE OR REJECT A CLAIM
# =========================

@app.route(
    "/finder/claims/<int:claim_id>/<decision>",
    methods=["POST"]
)
def update_finder_claim(claim_id, decision):
    finder_id = session.get("finder_id")

    if not finder_id:
        return redirect(url_for("finder"))

    if decision not in {"approve", "reject"}:
        flash("Invalid claim action.", "error")
        return redirect(url_for("finder_claims"))

    connection = get_connection()

    claim = connection.execute(
        """
        SELECT
            c.id,
            c.item_id,
            c.status AS claim_status,
            i.status AS item_status
        FROM claims AS c
        JOIN items AS i ON i.id = c.item_id
        WHERE c.id = ? AND i.finder_id = ?
        """,
        (claim_id, finder_id)
    ).fetchone()

    if claim is None:
        connection.close()
        flash("That claim was not found.", "error")
        return redirect(url_for("finder_claims"))

    if claim["claim_status"] != "pending":
        connection.close()
        flash("That claim has already been reviewed.", "error")
        return redirect(url_for("finder_claims"))

    if decision == "approve":
        if claim["item_status"] != "unclaimed":
            connection.close()
            flash("This item is no longer available.", "error")
            return redirect(url_for("finder_claims"))

        connection.execute(
            "UPDATE claims SET status = 'approved' WHERE id = ?",
            (claim_id,)
        )

        # Close any other pending claims on this item.
        connection.execute(
            """
            UPDATE claims
            SET status = 'rejected'
            WHERE item_id = ?
              AND id != ?
              AND status = 'pending'
            """,
            (claim["item_id"], claim_id)
        )

        connection.execute(
            "UPDATE items SET status = 'claimed' WHERE id = ?",
            (claim["item_id"],)
        )

        flash("Claim approved. The item is now marked as claimed.", "success")

    else:
        connection.execute(
            "UPDATE claims SET status = 'rejected' WHERE id = ?",
            (claim_id,)
        )

        flash("Claim rejected. The item remains available.", "success")

    connection.commit()
    connection.close()

    return redirect(url_for("finder_claims"))


# =========================
# EDIT A POSTED ITEM
# =========================

@app.route("/finder/item/<int:item_id>/edit", methods=["GET", "POST"])
def edit_item(item_id):
    finder_id = session.get("finder_id")

    if not finder_id:
        return redirect(url_for("finder"))

    connection = get_connection()

    item = connection.execute(
        """
        SELECT *
        FROM items
        WHERE id = ? AND finder_id = ?
        """,
        (item_id, finder_id)
    ).fetchone()

    if item is None:
        connection.close()
        flash("Item not found.", "error")
        return redirect(url_for("finder_dashboard"))

    if request.method == "GET":
        saved_questions = connection.execute(
            """
            SELECT question, answer
            FROM verification_questions
            WHERE item_id = ?
            ORDER BY id
            """,
            (item_id,)
        ).fetchall()

        question_values = [
            {
                "question": row["question"],
                "answer": row["answer"]
            }
            for row in saved_questions
        ]

        while len(question_values) < 3:
            question_values.append({
                "question": "",
                "answer": ""
            })

        connection.close()

        return render_template(
            "edit_item.html",
            item=item,
            locations=LOCATION_OPTIONS,
            item_options=ITEM_OPTIONS,
            questions=question_values
        )

    location_type = request.form.get("location_type", "").strip()
    location = request.form.get("location", "").strip()
    item_name = request.form.get("item", "").strip()
    description = request.form.get("description", "").strip()
    picture = request.files.get("picture")
    remove_picture = request.form.get("remove_picture") == "on"

    verification_questions = []

    for i in range(1, 4):
        question = request.form.get(f"question_{i}", "").strip()
        answer = request.form.get(f"answer_{i}", "").strip()

        if not question and not answer:
            continue

        if question and not answer:
            connection.close()
            flash(f"Please provide an answer for question {i}.", "error")
            return redirect(url_for("edit_item", item_id=item_id))

        if answer and not question:
            connection.close()
            flash(f"Please provide question {i}.", "error")
            return redirect(url_for("edit_item", item_id=item_id))

        verification_questions.append(
            (question, normalize_answer(answer))
        )

    if location_type not in LOCATION_OPTIONS:
        connection.close()
        flash("Please select a valid location.", "error")
        return redirect(url_for("edit_item", item_id=item_id))

    if location not in LOCATION_OPTIONS[location_type]:
        connection.close()
        flash("Please select a valid specific location.", "error")
        return redirect(url_for("edit_item", item_id=item_id))

    if item_name not in ITEM_OPTIONS:
        connection.close()
        flash("Please select a valid item.", "error")
        return redirect(url_for("edit_item", item_id=item_id))

    if not description:
        connection.close()
        flash("Please enter a description.", "error")
        return redirect(url_for("edit_item", item_id=item_id))

    picture_filename = None if remove_picture else item["picture"]

    if picture and picture.filename:
        if not allowed_file(picture.filename):
            connection.close()
            flash(
                "Please upload a PNG, JPG, JPEG, or WEBP image.",
                "error"
            )
            return redirect(url_for("edit_item", item_id=item_id))

        picture_filename = secure_filename(picture.filename)
        picture.save(UPLOAD_FOLDER / picture_filename)

    connection.execute(
        """
        UPDATE items
        SET location_type = ?,
            location = ?,
            item = ?,
            description = ?,
            picture = ?
        WHERE id = ? AND finder_id = ?
        """,
        (
            location_type,
            location,
            item_name,
            description,
            picture_filename,
            item_id,
            finder_id
        )
    )

    # Replace the item's previous verification questions.
    connection.execute(
        "DELETE FROM verification_questions WHERE item_id = ?",
        (item_id,)
    )

    for question, answer in verification_questions:
        connection.execute(
            """
            INSERT INTO verification_questions (item_id, question, answer)
            VALUES (?, ?, ?)
            """,
            (item_id, question, answer)
        )

    connection.commit()
    connection.close()

    flash("Item information updated successfully.", "success")
    return redirect(url_for("finder_dashboard"))

# =========================
# CLAIM CHAT HELPERS AND ROUTES
# =========================

def get_claim_looker_column(connection):
    columns = get_claim_table_columns(connection)

    if "looker_id" in columns:
        return "looker_id"

    if "looker" in columns:
        return "looker"

    return None


def get_chat_claim(connection, claim_id, role, user_id):
    looker_column = get_claim_looker_column(connection)

    if looker_column is None:
        return None

    if role == "finder":
        access_condition = "i.finder_id = ?"
    elif role == "looker":
        access_condition = f"c.{looker_column} = ?"
    else:
        return None

    return connection.execute(
        f"""
        SELECT
            c.id AS claim_id,
            c.status AS claim_status,
            c.{looker_column} AS looker_id,
            i.id AS item_id,
            i.finder_id,
            i.item,
            i.location_type,
            i.location,
            i.description
        FROM claims AS c
        JOIN items AS i ON i.id = c.item_id
        WHERE c.id = ?
          AND {access_condition}
        """,
        (claim_id, user_id),
    ).fetchone()


@app.route("/looker/claims")
def looker_claims():
    looker_id = session.get("looker_id")

    if not looker_id:
        return redirect(url_for("looker"))

    connection = get_connection()
    looker_column = get_claim_looker_column(connection)

    if looker_column is None:
        connection.close()
        flash("The claims table is missing its Looker ID column.", "error")
        return redirect(url_for("looker"))

    claims = connection.execute(
        f"""
        SELECT
            c.id AS claim_id,
            c.status AS claim_status,
            i.id AS item_id,
            i.finder_id,
            i.item,
            i.location_type,
            i.location,
            i.description
        FROM claims AS c
        JOIN items AS i ON i.id = c.item_id
        WHERE c.{looker_column} = ?
        ORDER BY c.id DESC
        """,
        (looker_id,),
    ).fetchall()

    connection.close()

    return render_template(
        "looker_claims.html",
        claims=claims,
        looker_id=looker_id,
    )


def render_claim_chat_page(claim_id, role, user_id):
    connection = get_connection()
    claim = get_chat_claim(connection, claim_id, role, user_id)
    connection.close()

    if claim is None:
        flash("That claim was not found for your account.", "error")

        if role == "finder":
            return redirect(url_for("finder_claims"))

        return redirect(url_for("looker_claims"))

    if role == "finder":
        other_role = "Looker"
        other_user_id = claim["looker_id"]
        back_url = url_for("finder_claims")
        logout_url = url_for("finder_logout")
    else:
        other_role = "Finder"
        other_user_id = claim["finder_id"]
        back_url = url_for("looker_claims")
        logout_url = url_for("looker_logout")

    return render_template(
        "claim_chat.html",
        claim=claim,
        role=role,
        current_id=user_id,
        other_role=other_role,
        other_user_id=other_user_id,
        back_url=back_url,
        logout_url=logout_url,
        messages_url=url_for(
            f"{role}_claim_messages",
            claim_id=claim_id,
        ),
    )


@app.route("/finder/claims/<int:claim_id>/chat")
def finder_claim_chat(claim_id):
    finder_id = session.get("finder_id")

    if not finder_id:
        return redirect(url_for("finder"))

    return render_claim_chat_page(
        claim_id=claim_id,
        role="finder",
        user_id=finder_id,
    )


@app.route("/looker/claims/<int:claim_id>/chat")
def looker_claim_chat(claim_id):
    looker_id = session.get("looker_id")

    if not looker_id:
        return redirect(url_for("looker"))

    return render_claim_chat_page(
        claim_id=claim_id,
        role="looker",
        user_id=looker_id,
    )


def handle_claim_messages(claim_id, role, user_id):
    if not user_id:
        return jsonify({"message": "Please sign in again."}), 401

    connection = get_connection()
    claim = get_chat_claim(connection, claim_id, role, user_id)

    if claim is None:
        connection.close()
        return jsonify({"message": "Claim not found."}), 404

    if request.method == "GET":
        rows = connection.execute(
            """
            SELECT id, sender_id, sender_role, body, created_at
            FROM claim_messages
            WHERE claim_id = ?
            ORDER BY id
            """,
            (claim_id,),
        ).fetchall()

        result = {
            "messages": [dict(row) for row in rows],
            "claim_status": claim["claim_status"],
        }

        connection.close()
        return jsonify(result)

    if claim["claim_status"] != "pending":
        connection.close()
        return jsonify({
            "message": "This claim has been reviewed. The chat is read-only."
        }), 409

    payload = request.get_json(silent=True) or {}
    body = payload.get("message", "")

    if not isinstance(body, str):
        connection.close()
        return jsonify({"message": "Enter a text message."}), 400

    body = body.strip()

    if not body:
        connection.close()
        return jsonify({"message": "Enter a message before sending."}), 400

    if len(body) > 1000:
        connection.close()
        return jsonify({
            "message": "Messages must be 1000 characters or fewer."
        }), 400

    connection.execute(
        """
        INSERT INTO claim_messages (
            claim_id,
            sender_id,
            sender_role,
            body
        )
        VALUES (?, ?, ?, ?)
        """,
        (claim_id, user_id, role, body),
    )

    connection.commit()
    connection.close()

    return jsonify({"message": "Message sent."}), 201


@app.route(
    "/finder/claims/<int:claim_id>/messages",
    methods=["GET", "POST"],
)
def finder_claim_messages(claim_id):
    return handle_claim_messages(
        claim_id,
        "finder",
        session.get("finder_id"),
    )


@app.route(
    "/looker/claims/<int:claim_id>/messages",
    methods=["GET", "POST"],
)
def looker_claim_messages(claim_id):
    return handle_claim_messages(
        claim_id,
        "looker",
        session.get("looker_id"),
    )


# =========================
# RUN APPLICATION
# =========================

if __name__ == "__main__":
    app.run(debug=True)