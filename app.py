from flask import Flask, render_template, request, send_file, redirect, url_for, Response
import time
import os
import requests
import csv
import io
import re
import random
from deep_translator import GoogleTranslator
from gtts import gTTS
from database import init_db, log_search, save_bookmark, delete_bookmark, clear_logs, get_history, get_all_history, get_bookmarks, get_stats
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
init_db()

AUDIO_DIR = "static/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# --- AI FEATURE: Auto-Quiz Generator ---
def generate_ai_quiz(text):
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
    quiz = []
    for sent in sentences:
        words = sent.split()
        if 8 < len(words) < 25:
            candidates = [w for w in words if len(w) > 5 and w.isalpha()]
            if candidates:
                answer = random.choice(candidates)
                question = sent.replace(answer, "________", 1)
                quiz.append({"question": question, "answer": answer})
                if len(quiz) == 3:
                    break
    return quiz

@app.route('/', methods=['GET', 'POST'])
def home():
    query, summary, title, url, error, lang = "", "", "", "", "", "en"
    image_url = ""
    quiz_data = []

    if request.method == 'POST':
        query = request.form.get('topic', '').strip()
        lang = request.form.get('language', 'en')
        
        if query:
            start_time = time.time()
            try:
                headers = {'User-Agent': 'AIResearchHub/1.0'}
                search_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={query}&limit=1&namespace=0&format=json"
                search_res = requests.get(search_url, headers=headers, timeout=8).json()
                
                if search_res and len(search_res) > 1 and search_res[1]:
                    correct_title = search_res[1][0]
                    api_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{correct_title.replace(' ', '_')}"
                    res = requests.get(api_url, headers=headers, timeout=8)
                    
                    if res.status_code == 200:
                        data = res.json()
                        title = data.get('title', correct_title)
                        raw_summary = data.get('extract', 'No summary extract available.')
                        url = data.get('content_urls', {}).get('desktop', {}).get('page', '#')
                        
                        # Fetch Image
                        image_url = data.get('thumbnail', {}).get('source', '')
                        
                        if lang != 'en':
                            try:
                                summary = GoogleTranslator(source='en', target=lang).translate(raw_summary)
                            except:
                                summary = raw_summary
                        else:
                            summary = raw_summary

                        # Generate Quiz (Only for English to keep grammar perfect)
                        if lang == 'en':
                            quiz_data = generate_ai_quiz(summary)

                        try:
                            tts = gTTS(text=summary, lang=lang, slow=False)
                            tts.save(os.path.join(AUDIO_DIR, "output.mp3"))
                        except:
                            pass

                        end_time = time.time()
                        log_search(title, lang.upper(), round((end_time - start_time) * 1000, 2))
                    else:
                        error = "Article details could not be fetched."
                else:
                    error = f"'{query}' ke liye koi result nahi mila."
            except Exception as e:
                error = "Network gateway error. Dobara koshish karein."

    return render_template('index.html', query=query, title=title, summary=summary, url=url, error=error, lang=lang, image_url=image_url, quiz_data=quiz_data)

@app.route('/bookmark', methods=['POST'])
def bookmark():
    title = request.form.get('title')
    summary = request.form.get('summary')
    url = request.form.get('url')
    if title and summary:
        save_bookmark(title, summary, url)
    return redirect(url_for('bookmarks_page'))

@app.route('/delete_bookmark/<int:bookmark_id>', methods=['POST'])
def remove_bookmark(bookmark_id):
    delete_bookmark(bookmark_id)
    return redirect(url_for('bookmarks_page'))

@app.route('/bookmarks')
def bookmarks_page():
    saved_items = get_bookmarks()
    return render_template('bookmarks.html', bookmarks=saved_items)

@app.route('/text-tools', methods=['GET', 'POST'])
def text_tools():
    text_input = ""
    metrics = None
    if request.method == 'POST':
        text_input = request.form.get('custom_text', '')
        if text_input:
            words = len(text_input.split())
            chars = len(text_input)
            reading_time = round(words / 200, 2)
            metrics = {
                "words": words,
                "chars": chars,
                "reading_time": reading_time
            }
    return render_template('text_tools.html', text_input=text_input, metrics=metrics)

@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    title = request.form.get('pdf_title', 'Knowledge Report')
    content = request.form.get('pdf_content', 'No content available.')

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, 750, f"AI Research Report: {title}")
    
    p.setFont("Helvetica", 11)
    text_object = p.beginText(50, 720)
    text_object.setLeading(15)
    for line in content.split('\n'):
        text_object.textLine(line[:90])
    
    p.drawText(text_object)
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"{title}_Report.pdf", mimetype='application/pdf')

@app.route('/export_csv')
def export_csv():
    history = get_all_history()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Target Term', 'Language', 'Latency (ms)', 'Timestamp'])
    for row in history:
        writer.writerow(row)
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=telemetry_audit_logs.csv"}
    )

@app.route('/dashboard')
def dashboard():
    stats = get_stats()
    history = get_history()
    return render_template('dashboard.html', stats=stats, history=history)

@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    message = ""
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'clear_logs':
            try:
                clear_logs()
                message = "System telemetry audit logs successfully purged."
            except:
                message = "Failed to clear logs."
    stats = get_stats()
    return render_template('admin.html', stats=stats, message=message)

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True)