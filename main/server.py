import json
from flask import Flask, send_file, request, redirect, render_template, jsonify, make_response
import mysql.connector
import io
import qrcode

app = Flask(__name__)
login_username = ''
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="patanahi",
    database="postdb"
)
cursor = db.cursor()
@app.route('/qrreader', methods=['GET'])
def qrreader():
    weight = request.args.get('weight')
    cost = request.args.get('cost')
    id = request.args.get('id')
    date = request.args.get('date')
    username = request.args.get('username')
    return render_template("reader.html", weight=weight, cost=cost, id=id, username=username, date=date)

@app.route('/pay', methods=['POST'])
def pay():
    if(login_username):
        weight = request.json['weight']

        sql = "SELECT * FROM Stamps"
        cursor.execute(sql)
        values = cursor.fetchone()
        if(calculate_cost(weight)<=values[1]):
            sql = "INSERT INTO Sale (username, weight, price) VALUES (%s, %s, %s)"
            values = (login_username, weight, calculate_cost(weight))
            cursor.execute(sql, values)
            db.commit()

            id = cursor.lastrowid
            sql = "Select datetime from Sale where id = %s"
            values = (id,)
            cursor.execute(sql, values)
            date = cursor.fetchone()[0]

            img_file = io.BytesIO()
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
            qr.add_data(f"https://674f-72-255-51-110.ngrok-free.app/qrreader?weight={weight}&cost={calculate_cost(weight)}&id={id}&date={date}&username={login_username}")
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(img_file, 'PNG')  # save the image to the BytesIO object

            decrement_amount(weight)

            # create a response containing the image
            response = make_response(img_file.getvalue())
            response.headers.set('Content-Type', 'image/png')
            response.headers.set('Content-Disposition', 'attachment', filename='qrcode.png')
            return response
        else:
            return jsonify({"error": "Sorry Dude but I am short of stamps right now."}), 400
    else:
        return jsonify({"error": "Not logged in."}), 401

@app.route('/')
def homepage():
    return render_template('homepage.html')

@app.route('/createUser', methods=['GET'])
def createUser():
    return render_template('createUser.html')

@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html')

@app.route('/update', methods=['POST'])
def handle_update():
    print(request.json)
    amount = request.json['amount']
    sql = "SELECT * FROM Stamps"
    cursor.execute(sql)
    values = cursor.fetchone()

    prev_amount = values[1]
    remaining = amount + prev_amount

    sql = "UPDATE stamps SET amount = %s WHERE amount = %s"
    values = (remaining, prev_amount)
    cursor.execute(sql, values)
    db.commit()

    return ''

@app.route('/edit', methods=['POST'])
def handle_edit():
    ppunit = request.json['ppunit']
    sql = "SELECT * FROM Stamps"
    cursor.execute(sql)
    values = cursor.fetchone()

    prev_ppunit = values[0]
    remaining = ppunit

    sql = "UPDATE stamps SET ppunit = %s WHERE ppunit = %s"
    values = (remaining, prev_ppunit)
    cursor.execute(sql, values)
    db.commit()

    return ''

@app.route('/createUser', methods=['POST'])
def handle_createUser():
    username = request.json['username']
    email = request.json['email']
    password = request.json['password']

    sql = "INSERT INTO user (username, email, password, role) VALUES (%s, %s, %s, %s)"
    values = (username, email, password, "0")
    cursor.execute(sql, values)
    db.commit()

    return ''
    
@app.route('/login', methods=['POST'])
def handle_login():
    username = request.form['username']
    password = request.form['password']

    sql = "SELECT * FROM user WHERE username=%s and password=%s"
    values = (username, password)
    cursor.execute(sql, values)
    user = cursor.fetchone()

    if user:
        global login_username 
        login_username = username

        if user[3]:
            sql = "SELECT * FROM Sale"
            cursor.execute(sql)
            sales = cursor.fetchall()
            sql = "SELECT * FROM Stamps"
            cursor.execute(sql)
            stamps = cursor.fetchall()
            
            print(sales)
            return render_template('admin.html', sales=sales, stamps=stamps)
        else: 
            return render_template('user.html')
    else:
        print('Error---------------------------------------------------------------------------------------')

@app.route('/calculate-cost', methods=['POST'])
def handle_calculate_cost():
    weight = request.json['weight']
    cost = calculate_cost(weight)
    return jsonify({'cost': cost})

def calculate_cost(weight):
    sql = "SELECT * FROM Stamps"
    cursor.execute(sql)
    values = cursor.fetchone()

    cost = weight * values[0] 
    return cost

def decrement_amount(weight):
    cost = calculate_cost(weight)
    sql = "SELECT * FROM Stamps"
    cursor.execute(sql)
    values = cursor.fetchone()

    amount = values[1]
    remaining = amount - cost

    sql = "UPDATE stamps SET amount = %s WHERE amount = %s"
    values = (remaining, amount)
    cursor.execute(sql, values)
    db.commit()

@app.route('/logout', methods=['GET'])
def logout():
    login_username=''
    return render_template('homepage.html')

@app.route('/form', methods=['GET'])
def form():
    return render_template('form.html')

@app.route('/submit', methods=['POST'])
def submit():

    billID = request.form['billID']
    billType = request.form['billType']
    amount = request.form['amount']
    customerName = request.form['customerName']
    date = request.form['date']
    cursor = db.cursor()
    sql = "INSERT INTO Bills (BillID, BillType, Amount, CustomerName, Date) VALUES (%s, %s, %s, %s, %s)"

    values = (billID, billType, amount, customerName, date)
    cursor.execute(sql, values)

    db.commit()

    cursor.close()

    return "Form submitted successfully!"

@app.route('/selectDate', methods=['POST'])
def selectDate():
    Sdate = request.form['Sdate']
    Edate = request.form['Edate']
    sql = "SELECT * FROM Bills WHERE Date BETWEEN %s AND %s"
    cursor.execute(sql, (Sdate, Edate))
    bills = cursor.fetchall()

    sql = "SELECT * FROM Sale"
    cursor.execute(sql)
    sales = cursor.fetchall()
    sql = "SELECT * FROM Stamps"
    cursor.execute(sql)
    stamps = cursor.fetchall()
    return render_template('admin.html', bills=bills, stamps=stamps, sales=sales)

if __name__ == '__main__':
    app.run(debug=True)
