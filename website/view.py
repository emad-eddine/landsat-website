from flask import Blueprint, render_template


home = Blueprint("home",__name__)
login = Blueprint("login",__name__)
signup = Blueprint("signup",__name__)
heat = Blueprint("heat",__name__)
error = Blueprint("error",__name__)

@home.route("/")
def goHome():
    return render_template("index.html")


@login.route("/login")
def goLogin():
    return render_template("login.html")

@signup.route("/signup")
def goSignup():
    return render_template("signup.html")


@heat.route("/heat")
def goHeat():
    return render_template("heat.html")



def page_not_found(e):
  return render_template('error.html'), 404
