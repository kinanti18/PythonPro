from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@127.0.0.1:3307/quiz'
app.config['SECRET_KEY'] = '86ae4894ba09b070b460ac4a72d9eca2d00a4dcda4363318'  # Add this line for session support
db = SQLAlchemy(app)

# Definisikan model database (sesuaikan sesuai kebutuhan)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    nickname = db.Column(db.String(50), unique=True, nullable=False)
    scores = db.relationship('QuizScore', backref='user', lazy=True)

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
@app.route('/')
def home():
    # Contoh: Tampilkan formulir input untuk mencari cuaca
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

@app.route('/quiz')
def quiz():
    # Dapatkan pertanyaan dari database (contoh: 5 pertanyaan)
    quiz_questions = QuizQuestion.query.limit(5).all()
    return render_template('quiz.html', quiz_questions=quiz_questions)

# Rute untuk papan peringkat
@app.route('/leaderboard')
def leaderboard():
    # Dapatkan skor pemain dari database (urutkan berdasarkan skor tertinggi)
    scores = QuizScore.query.order_by(QuizScore.score.desc()).all()

    return render_template('leaderboard.html', scores=scores)

# Fungsi untuk mendapatkan data cuaca dari API (gunakan API cuaca yang sesuai)
def get_weather(city):
    api_key = 'your_weather_api_key'  # Ganti dengan kunci API cuaca Anda
    base_url = 'http://api.weatherapi.com/v1/forecast.json'
    
    params = {
        'key': api_key,
        'q': city,
        'days': 3  # Ambil perkiraan cuaca untuk 3 hari
    }

    try:
        response = requests.get(base_url, params=params)
        data = response.json()

        # Proses data cuaca dan kembalikan hasil yang diperlukan
        forecast_data = []
        for day in data['forecast']['forecastday']:
            date = day['date']
            day_name = date.split('-')[2]  # Ambil nama hari dari tanggal
            temperature_day = day['day']['maxtemp_c']
            temperature_night = day['day']['mintemp_c']
            forecast_data.append({'date': date, 'day_name': day_name, 'temp_day': temperature_day, 'temp_night': temperature_night})

        return forecast_data

    except Exception as e:
        print(f"Error retrieving weather data: {e}")
        return None

# Fungsi untuk menghitung skor kuis
def calculate_score(user_answers):
    # Hitung skor berdasarkan jawaban yang benar
    correct_answers = 0
    for answer in user_answers:
        # Misalnya, asumsikan jawaban yang benar diberi nilai 1
        if answer['selected_option'] == answer['correct_option']:
            correct_answers += 1

    total_questions = len(user_answers)
    score = (correct_answers / total_questions) * 100

    return round(score, 2)

if __name__ == '__main__':
    app.run(debug=True)
