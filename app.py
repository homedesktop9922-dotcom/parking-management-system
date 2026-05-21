from flask import Flask, render_template, request, redirect, session
from models import *
from db import init_db, create_slots
import razorpay
from ai_model import predict_next_hours
from twilio.rest import Client
from datetime import datetime
import os

app = Flask(__name__)

app.secret_key = "secret"


# ---------------- TWILIO ----------------

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_VERIFY_SID = os.environ.get("TWILIO_VERIFY_SID")

twilio_client = Client(
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN
)


# ---------------- RAZORPAY ----------------

client = razorpay.Client(auth=(
    "rzp_test_SkwzMKt4mOE88d",
    "CInqh9Z4RYQWemHfCQQ37PWj"
))


# ---------------- LOGIN ----------------

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        u = request.form["username"]
        p = request.form["password"]

        if get_admin(u, p):

            session["admin"] = u

            return redirect("/admin")

        user = get_user(u, p)

        if user:

            session["user_id"] = user["id"]

            return redirect("/dashboard")

    return render_template("login.html")


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]
        mobile = request.form["mobile"]

        session["temp_user"] = {
            "username": username,
            "password": password,
            "mobile": mobile
        }

        twilio_client.verify.v2.services(
            TWILIO_VERIFY_SID
        ).verifications.create(
            to="+91" + mobile,
            channel="sms"
        )

        return redirect("/verify_otp")

    return render_template("register.html")


# ---------------- VERIFY OTP ----------------

@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():

    if request.method == "POST":

        otp = request.form["otp"]

        mobile = session["temp_user"]["mobile"]

        verification = twilio_client.verify.v2.services(
            TWILIO_VERIFY_SID
        ).verification_checks.create(
            to="+91" + mobile,
            code=otp
        )

        if verification.status == "approved":

            data = session["temp_user"]

            create_user(
                data["username"],
                data["password"],
                data["mobile"]
            )

            session.pop("temp_user")

            return redirect("/")

        else:
            return "❌ Invalid OTP"

    return render_template("verify_otp.html")


# ---------------- USER DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/")

    return render_template(
        "user_dashboard.html",
        bookings=get_user_bookings(session["user_id"])
    )


# ---------------- BOOK SLOT ----------------

@app.route("/book", methods=["GET", "POST"])
def book():

    if "user_id" not in session:
        return redirect("/")

    if request.method == "POST":

        v = request.form["vehicle"]
        m = request.form["mobile"]
        start = request.form["start"]
        end = request.form["end"]
        slot = int(request.form["slot"])

        current = datetime.now()

        start_time = datetime.fromisoformat(start)

        if start_time < current:
            return "❌ Cannot book past time"

        if not is_slot_available(slot, start, end):
            return "❌ Slot already booked"

        price = calculate_price(start, end)

        order = client.order.create({
            "amount": int(price * 100),
            "currency": "INR"
        })

        session["booking"] = {
            "vehicle": v,
            "mobile": m,
            "start": start,
            "end": end,
            "slot": slot,
            "amount": price,
            "order_id": order["id"]
        }

        return render_template(
            "payment.html",
            order_id=order["id"],
            amount=price
        )

    return render_template(
        "book_slot.html",
        slots=get_available_slots()
    )


# ---------------- VERIFY PAYMENT ----------------

@app.route("/verify_payment", methods=["POST"])
def verify_payment():

    data = request.form

    try:

        client.utility.verify_payment_signature({

            'razorpay_order_id': data['razorpay_order_id'],
            'razorpay_payment_id': data['razorpay_payment_id'],
            'razorpay_signature': data['razorpay_signature']

        })

        booking = session["booking"]

        create_booking(

            session["user_id"],
            booking["vehicle"],
            booking["mobile"],
            booking["slot"],
            booking["start"],
            booking["end"],
            data["razorpay_payment_id"],
            booking["amount"]

        )

        save_invoice(
            data["razorpay_payment_id"],
            booking["amount"],
            session["user_id"]
        )

        session.pop("booking")

        return redirect("/dashboard")

    except Exception as e:

        return str(e)


# ---------------- REFUND ----------------

@app.route("/refund/<payment_id>")
def refund(payment_id):

    try:

        refund = client.payment.refund(payment_id, {
            "amount": 100
        })

        save_refund(payment_id, 100)

        return "Refund Successful"

    except Exception as e:
        return str(e)


# ---------------- ADMIN ----------------

@app.route("/admin", methods=["GET", "POST"])
def admin():

    if "admin" not in session:
        return redirect("/")

    search = None

    if request.method == "POST":
        search = search_vehicle(request.form["search"])

    try:
        labels, values = get_daily_bookings()

    except:
        labels, values = [], []

    return render_template(

        "admin_dashboard.html",

        bookings=get_all_bookings(),

        search=search,

        total=get_total_bookings(),

        occupied=get_occupied_slots(),

        available=get_available_slots_count(),

        revenue=get_total_revenue(),

        peak=get_peak_hour(),

        labels=labels,

        values=values,

        predictions=predict_next_hours()

    )


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# ---------------- DELETE BOOKING ----------------

@app.route("/delete/<int:id>")
def delete(id):

    delete_booking(id)

    return redirect("/admin")


# ---------------- EXIT VEHICLE ----------------

@app.route("/exit/<int:id>")
def exit_vehicle_route(id):

    exit_vehicle(id)

    return redirect("/dashboard")


# ---------------- RUN ----------------

if __name__ == "__main__":

    init_db()

    create_slots(10)

    app.run(debug=True)