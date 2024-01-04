from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@127.0.0.1:3307/quiz'
app.config['SECRET_KEY'] = '86ae4894ba09b070b460ac4a72d9eca2d00a4dcda4363318'  # Add this line for session support
db = SQLAlchemy(app)

bcrypt = Bcrypt(app)

# Definisikan model database (sesuaikan sesuai kebutuhan)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    nickname = db.Column(db.String(50), unique=True, nullable=False)
    scores = db.relationship('QuizScore', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

class QuizQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.String(255), nullable=False)
    option1 = db.Column(db.String(100), nullable=False)
    option2 = db.Column(db.String(100), nullable=False)
    option3 = db.Column(db.String(100), nullable=False)
    option4 = db.Column(db.String(100), nullable=False)
    correct_option = db.Column(db.Integer, nullable=False)

class QuizScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Use app.app_context() to create tables within the application context
with app.app_context():
    db.create_all()

# Rute untuk halaman beranda
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # Handle the form submission here
        city = request.form['city']
        weather_data = get_weather(city)
        
        # Render the template with the weather data
        return render_template('home.html', weather_data=weather_data)

    # For GET requests, render the home template without weather data
    return render_template('home.html')


# Rute untuk halaman registrasi
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        nickname = request.form['nickname']

        # Periksa apakah username dan nickname sudah digunakan
        existing_user = User.query.filter_by(username=username).first()
        existing_nickname = User.query.filter_by(nickname=nickname).first()

        if existing_user or existing_nickname:
            flash('Username or nickname already taken. Please choose a different one.', 'danger')
        else:
            # Tambahkan pengguna baru ke database
            new_user = User(username=username, password=password, nickname=nickname)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful. You can now log in.', 'success')
            return redirect(url_for('login'))
   
        # Tambahkan pengguna baru ke database dengan password ter-hash
        new_user = User(username=username, nickname=nickname)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful. You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# Rute untuk halaman login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Periksa apakah username dan password cocok
        user = User.query.filter_by(username=username, password=password).first()

        if user:
            # Set session untuk menandai pengguna yang sudah login
            session['user_id'] = user.id
            flash('Login successful. Welcome, {}!'.format(user.nickname), 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    # Check if the user is logged in
    if 'user_id' in session:
        # Clear the user session (logout)
        session.pop('user_id', None)
        flash('Logout successful. Goodbye!', 'success')
    else:
        flash('You are not logged in.', 'warning')

    # Redirect to the home page or any desired location after logout
    return redirect(url_for('home'))

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    # Dapatkan pertanyaan dari database (contoh: 5 pertanyaan)
    quiz_questions = QuizQuestion.query.limit(5).all()
    
    # Check if there are no quiz questions available
    if not quiz_questions:
        flash('No quiz questions available.', 'warning')
        return redirect(url_for('home'))

    if request.method == 'POST':
        # Handle form submission
        user_answers = {}
        for question in quiz_questions:
            user_answer = request.form.get(str(question.id))
            user_answers[question.id] = int(user_answer) if user_answer is not None else None

        # Logic to process quiz answers and calculate the result
        result = calculate_score(user_answers)

        # Save the quiz score to the database
        save_quiz_score(result['score'])

        return render_template('quiz_result.html', result=result)

    return render_template('quiz.html', quiz_questions=quiz_questions)

def save_quiz_score(score):
    # Check if the user is logged in
    if 'user_id' in session:
        user_id = session['user_id']
        # Create a new QuizScore record and save it to the database
        quiz_score = QuizScore(score=score, user_id=user_id)
        db.session.add(quiz_score)
        db.session.commit()
        
# Rute untuk papan peringkat
@app.route('/leaderboard')
def leaderboard():
    # Dapatkan skor pemain dari database (urutkan berdasarkan skor tertinggi)
    scores = QuizScore.query.order_by(QuizScore.score.desc()).all()

    # Pass an enumerated list to the template
    enumerated_scores = list(enumerate(scores, start=1))

    return render_template('leaderboard.html', scores=enumerated_scores)


# Fungsi untuk mendapatkan data cuaca dari API (gunakan API cuaca yang sesuai)
@app.route('/home', methods=['GET'])
def get_weather(city):
    api_key = 'a53825824b4bd2f349cb4e154bba443c'  # Ganti dengan kunci API cuaca Anda
    base_url = f"http://api.openweathermap.org/data/2.5/forecast?id={city}&appid={api_key}"
    
    params = {
        'q': city,
        'appid': api_key,
        'cnt': 3  # Ambil perkiraan cuaca untuk 3 hari
    }

    try:
        response = requests.get(base_url, params=params)
        data = response.json()

        # Proses data cuaca dan kembalikan hasil yang diperlukan
        forecast_data = []
        for day in data.get('list', []):
            date = day.get('dt_txt', '')
            day_name = date.split()[0]  # Ambil nama hari dari tanggal
            temperature_day = day['main']['temp_max']
            temperature_night = day['main']['temp_min']
            forecast_data.append({'date': date, 'day_name': day_name, 'temp_day': temperature_day, 'temp_night': temperature_night})

        return forecast_data

    except Exception as e:
        print(f"Error retrieving weather data: {e}")
        return None

# Fungsi untuk menghitung skor kuis
def calculate_score(user_answers):
    # Hitung skor berdasarkan jawaban yang benar
    correct_answers = 0
    correct_options = {}

    for question_id, selected_option in user_answers.items():
        question = QuizQuestion.query.get(question_id)

        if question and selected_option is not None:
            correct_option = question.correct_option
            correct_options[question_id] = correct_option

            if selected_option == correct_option:
                correct_answers += 1

    total_questions = len(user_answers)
    score = (correct_answers / total_questions) * 100

    return {'score': round(score, 2), 'correct_options': correct_options}

if __name__ == '__main__':
    app.run(debug=True)