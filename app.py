from flask import Flask, request,render_template, redirect,session,jsonify, url_for
from flask_sqlalchemy import SQLAlchemy
import yagmail, random,string
import pickle
from sqlalchemy.exc import IntegrityError
import bcrypt
import json
from difflib import get_close_matches
from typing import List, Union


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
app.secret_key = 'secret_key'
yag = yagmail.SMTP('deepmachine748@gmail.com', 'prtndxpwmblbfemo')
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))

    def __init__(self,email,password,name):
        self.name = name
        self.email = email
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self,password):
        return bcrypt.checkpw(password.encode('utf-8'),self.password.encode('utf-8'))

with app.app_context():
    db.create_all()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/appointment')
def appointment():
    return render_template('appointment.html')
# Add this constant for OTP length
OTP_LENGTH = 6

# Function to generate OTP
def generate_otp():
    otp = ''.join(random.choices(string.digits, k=OTP_LENGTH))
    return otp

# Function to send OTP via email
def send_otp_email(email, otp):
    # Replace 'your_email' and 'your_password' with your actual email credentials
    yag = yagmail.SMTP('deepmachine748@gmail.com', 'prtndxpwmblbfemo')
    yag.send(to=email, subject='OTP Verification', contents=f'Your OTP is: {otp}')
# Route to resend OTP
@app.route('/resend_otp', methods=['POST'])
def resend_otp():
    email = request.form.get('email')
    if email:
        # Generate new OTP
        otp = generate_otp()

        # Expire the old OTP
        session.pop('otp', None)

        # Store new OTP in session
        session['otp'] = otp

        # Send new OTP via email
        send_otp_email(email, otp)

    # Redirect back to the OTP verification page
    return redirect('/verify_otp')

# Modify your registration route to include OTP verification
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Generate OTP
        otp = generate_otp()

        # Send OTP via email
        send_otp_email(email, otp)

        # Store OTP in session
        session['otp'] = otp
        session['name'] = name
        session['email'] = email
        session['password'] = password

        # Redirect to OTP verification page
        return redirect('/verify_otp')

    return render_template('register.html')

# Route for OTP verification
@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        user_otp = request.form['otp']
        stored_otp = session.get('otp')

        if user_otp == stored_otp:
            # If OTP matches, save user data to the database
            name = session.get('name')
            email = session.get('email')
            password = session.get('password')

            try:
                new_user = User(name=name, email=email, password=password)
                db.session.add(new_user)
                db.session.commit()

                # Clear session data after successful registration
                session.pop('otp')
                session.pop('name')
                session.pop('email')
                session.pop('password')

                return render_template('otp.html', success=True)
            except IntegrityError:
                # If email already exists, redirect to the email_registered page
                return render_template('/email_registered.html')

        else:
            return render_template('otp.html', error='Invalid OTP')

    return render_template('otp.html')

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session['email'] = user.email
            return redirect('/dashboard')
        else:
            return render_template('login.html',error='Invalid user')

    return render_template('login.html')

# Load the model from the file
with open('static/rf_model.pkl', 'rb') as file:
    model = pickle.load(file)


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'email' not in session:
        return redirect('/login')

    # Initialize variables to store form data
    Name = ''
    Email = ''
    phone_number = ''

    if request.method == 'POST':
        # Get user inputs from the form
        clusters = int(request.form['clusters'])
        cholesterol = int(request.form['cholesterol'])
        gluc = int(request.form['gluc'])
        smoke = int(request.form['smoke'])
        active = int(request.form['active'])
        age_group = int(request.form['age_group'])
        bmi = float(request.form['bmi'])
        map = float(request.form['map'])

        # Get Name, Email, and phone number if available
        if 'Name' in request.form:
            Name = request.form['Name']
        if 'Email' in request.form:
            Email = request.form['Email']
        if 'phone_number' in request.form:
            phone_number = request.form['phone_number']

        # Make prediction using the loaded model
        input_data = [[clusters, cholesterol, gluc, smoke, active, age_group, bmi, map]]
        prediction = model.predict(input_data)

        if 'save_button' in request.form:
            # Convert numpy.int64 to int for serialization
            prediction = int(prediction[0])  # Assuming prediction is a single value

            # Save form data and prediction to JSON
            data = {
                'clusters': clusters,
                'cholesterol': cholesterol,
                'gluc': gluc,
                'smoke': smoke,
                'active': active,
                'age_group': age_group,
                'bmi': bmi,
                'map': map,
                'prediction': prediction,
                'Name': Name,
                'Email': Email,
                'phone_number': phone_number,
            }

            # Save to a JSON file in the static folder
            with open('static/saved_data.json', 'w') as f:
                json.dump(data, f)

            # Redirect to appointment function
            return '''
                        <div style="text-align: center; margin-top: 50px;">
                            <h2 style="color: #007bff;">Data saved successfully.</h2>
                            <a href="{}" style="display: inline-block; padding: 30px 50px; background-color: #2F3645; color: white; text-decoration: none; border-radius: 7px;">Take Doctor Appointment</a>
                        </div>
                        '''.format(url_for('appointment'))

        # Render the dashboard template with the prediction result and form data
        return render_template('dashboard.html', prediction=prediction, Name=Name, Email=Email, phone_number=phone_number)

    # Render the dashboard template initially
    return render_template('dashboard.html', Name=Name, Email=Email, phone_number=phone_number)


@app.route('/send_appointment_request', methods=['POST'])
def send_appointment_request():
    data = request.json
    doctor_email = data.get('email')

    # Attach saved_data.json file
    attachment_path = 'static/saved_data.json'
    with open(attachment_path, 'r') as f:
        data = json.load(f)

    # Email content
    contents = 'Patient data and appointment request attached.'
    try:
        yag.send(to=doctor_email, subject='Appointment Request', contents=contents, attachments=attachment_path)
        return jsonify({'message': 'Appointment request sent successfully to the doctor.'})
    except Exception as e:
        return jsonify({'message': f'Failed to send appointment request. Error: {str(e)}'}), 500


def load_knowledge_base(file_path: str) -> dict:
    with open(file_path, 'r') as file:
        data: dict = json.load(file)
    return data


def save_knowledge_base(file_path: str, data: dict):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=2)


def find_best_match(user_question: str, questions: List[str]) -> Union[str, None]:
    matches: List[str] = get_close_matches(user_question, questions, n=1, cutoff=0.6)
    return matches[0] if matches else None


def get_answer_for_question(question: str, knowledge_base: dict) -> Union[str, None]:
    for intent in knowledge_base['intents']:
        if question in intent['patterns']:
            return intent['responses'][0]  # Return the first response
    return None


@app.route('/chat_bot', methods=['GET', 'POST'])
def chat_bot():
    if request.method == 'POST':
        user_input = request.form['user_input']
        knowledge_base = load_knowledge_base('static/knowledge_base.json')
        best_match = find_best_match(user_input, [pattern for intent in knowledge_base["intents"] for pattern in intent["patterns"]])
        if best_match:
            answer = get_answer_for_question(best_match, knowledge_base)
            return jsonify({'reply': answer})
        else:
            return jsonify({'reply': 'I dont know the answer.'})
    return render_template('chatbot.html')


@app.route('/logout')
def logout():
    session.pop('email',None)
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)
