from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import logging

logger = logging.getLogger('family_logger')
logger.setLevel(logging.INFO)
logging.getLogger().handlers = []
file_handler = logging.FileHandler('family_additions.log')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////var/data/familles.db'

db = SQLAlchemy(app)

logins = {"comitedesfetes": "vieillevigne"}


class Famille(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(80), nullable=False)
    nb_personnes = db.Column(db.Integer, nullable=False)
    enfants_moins_12_ans = db.Column(db.Integer, nullable=True)
    prix = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return f'<Famille {self.nom}>'


def create_database():
    with app.app_context():
        db.create_all()


create_database()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" not in session:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)

    return decorated_function


@app.route('/login', methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in logins and logins[username] == password:
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            error = "Identifiants incorrects"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    normal_price = 18
    child_price = 12
    total_revenue = 0

    if request.method == "POST":
        nom_famille = request.form.get("nom_famille")
        nb_personnes = int(request.form.get("nb_personnes"))
        enfants_moins_12_ans = request.form.get("enfants_moins_12_ans")
        enfants_moins_12_ans = int(enfants_moins_12_ans) if enfants_moins_12_ans != "" else None
        prix = (
                           nb_personnes - enfants_moins_12_ans) * normal_price + enfants_moins_12_ans * child_price if enfants_moins_12_ans is not None else nb_personnes * normal_price
        famille = Famille(nom=nom_famille, nb_personnes=nb_personnes, enfants_moins_12_ans=enfants_moins_12_ans,
                          prix=prix)
        db.session.add(famille)
        db.session.commit()
        logger.info(
            f'Family added: {famille.nom}, {famille.nb_personnes} people, {famille.enfants_moins_12_ans if famille.enfants_moins_12_ans is not None else "No"} children under 12')

    familles = Famille.query.all()
    total_personnes = sum([f.nb_personnes for f in familles])

    for famille in familles:
        if famille.enfants_moins_12_ans:
            total_revenue += (
                                         famille.nb_personnes - famille.enfants_moins_12_ans) * normal_price + famille.enfants_moins_12_ans * child_price
        else:
            total_revenue += famille.nb_personnes * normal_price

    return render_template("index.html", familles=familles, total_personnes=total_personnes,
                           total_revenue=total_revenue, prix=normal_price, prix_enfant=child_price)


@app.route("/reset", methods=["POST"])
@login_required
def reset():
    db.session.query(Famille).delete()
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/delete/<id>", methods=["POST"])
@login_required
def delete(id):
    famille = Famille.query.get(id)
    if famille:
        db.session.delete(famille)
        db.session.commit()
    return redirect(url_for("index"))


@app.route("/imprimer")
@login_required
def imprimer():
    familles = Famille.query.all()
    total_personnes = sum([famille.nb_personnes for famille in familles])
    total_revenue = sum([famille.prix for famille in familles])
    return render_template("imprimer.html", familles=familles, total_personnes=total_personnes,
                           total_revenue=total_revenue)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', debug=True)
