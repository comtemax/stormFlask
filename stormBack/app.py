from flask import Flask, render_template, redirect, abort, url_for, request, send_from_directory, flash, session
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import src.detection


UPLOAD_FOLDER="uploads/"
ALLOWED_EXTENSIONS = {'flv', 'mov', 'mp4', 'mp4v', 'mpeg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'
app.debug = True

@app.errorhandler(404)
def page_not_found(error):
    return render_template('page_not_found.html'), 404


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploads/<created_at>/<name>')
def download_file(created_at, name):
    return send_from_directory(app.config['UPLOAD_FOLDER'], f"{created_at}/{name}")

@app.route('/process/<created_at>/<name>',  methods=['GET', 'POST'])
def process_file(created_at, name):
    if request.method == 'POST':
        flash(f"{request.form}")
        print(f"Ready to treat the video with {request.form} params")

        detection.detection(f"uploads/{created_at}/{name}", request.form)

    return render_template('settings.html', created_at=created_at, name=name)

    # send_from_directory(app.config['UPLOAD_FOLDER'], f"{created_at}/{name}")

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user doesn't select a file, the browser submits an empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            print (f"The file [{filename}] should be accepted")
            creation_time = datetime.now().isoformat(timespec='seconds')
            print (f"The creation_time is [{creation_time}]\n")
            savefolder = os.path.join(f"{app.config['UPLOAD_FOLDER']}{creation_time}/")
            if not os.path.isdir(savefolder):
                os.makedirs(savefolder)
            file.save(f"{savefolder}{filename}")
            return redirect(url_for('process_file', name=filename, created_at=creation_time))
        elif file and not(allowed_file(file.filename)):
            flash(f"File {secure_filename(file.filename)} was rejected. File must be one of {ALLOWED_EXTENSIONS}")
        else:
            flash("No file detected")
    return render_template('upload.html')
