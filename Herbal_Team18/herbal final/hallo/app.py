from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, flash
from groq import Groq 
import mysql.connector  
import os
import base64
import re
import requests
from PIL import Image
import io

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # Required for flash messages

client = Groq(api_key="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")

app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images')

# Plant.id API key
PLANT_ID_API_KEY = "XrrOGdmMZ9NcRCN5Wtn253bVjI2rZfQsGRYMgbV6KoqJY4UkCf"

def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='flaskuser',
        password='flask123',
        database='herbal_db'
    )

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/chat')
def chatbot():
    return render_template('chatbot_page.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
    results = []
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        search_query = request.form['search']
        sql = """
            SELECT d.name, d.medicinal_plants, d.natural_excipients, di.image_path
            FROM drug d
            LEFT JOIN drugimg di ON d.drug_id = di.drug_id
            WHERE d.name LIKE %s
        """
        cursor.execute(sql, (f"%{search_query}%",))
    else:
        sql = """
            SELECT d.name, d.medicinal_plants, d.natural_excipients, di.image_path
            FROM drug d
            LEFT JOIN drugimg di ON d.drug_id = di.drug_id
        """
        cursor.execute(sql)

    rows = cursor.fetchall()
    for row in rows:
        name, plants, excipients, image_path = row
        results.append({
            'name': name,
            'plants': plants,
            'excipients': excipients,
            'image_path': image_path
        })

    cursor.close()
    conn.close()
    return render_template('search.html', results=results)

@app.route('/static/<path:filename>')
def serve_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/chat", methods=["POST"])
def chat_message():
    user_msg = request.json["message"]
    tablet_name = user_msg.strip().capitalize()

    messages = [
        {"role": "system", "content": "You are a helpful herbal guide."},
        {"role": "user", "content": user_msg}
    ]

    try:
        response_llm = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=messages
        )
        raw_reply = response_llm.choices[0].message.content.strip()
        formatted_reply = re.sub(r'- ', '🔸 ', raw_reply).replace('\n', '<br>')
        response = f"<b>Learn:</b><br>{formatted_reply}<br><hr>"

    except Exception as e:
        response = f"Sorry, LLaMA response failed. Error: {str(e)}"
        return jsonify({"reply": response})

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM HerbalAlternatives WHERE tablet_name LIKE %s", (f"%{tablet_name}%",))
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if result:
        image_base64 = base64.b64encode(result["image"]).decode("utf-8")
        db_info = (
            f"<b>📦 Tablet Name:</b> {result['tablet_name']}<br>"
            f"<b>🌿 Herbal Alternatives:</b> {result['herbal_alternatives']}<br>"
            f"<b>🍃 Natural Excipients:</b> {result['natural_excipients']}<br><br>"
            f"<img src='data:image/jpeg;base64,{image_base64}' width='200'>"
        )
        response += f"<b>📚 Additional Database Info:</b><br>{db_info}"

    return jsonify({"reply": response})

@app.route('/map')
def herbal_map():
    return render_template('herbal_map.html')

@app.route('/identify')
def identify():
    return render_template('identify.html')

@app.route('/identify-herb', methods=['POST'])
def identify_herb():
    try:
        # Get the image data from the request
        image_data = request.json.get('image')
        
        # Process base64 image data for Plant.id API
        if isinstance(image_data, str) and image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        
        # Call Plant.id API with the user's API key
        response = requests.post(
            "https://api.plant.id/v2/identify",
            json={
                "images": [image_data],
                "modifiers": ["crops_fast", "similar_images"],
                "plant_details": ["common_names", "url", "wiki_description", "taxonomy", "synonyms"]
            },
            headers={
                "Content-Type": "application/json",
                "Api-Key": PLANT_ID_API_KEY
            }
        )
        
        # Parse API response
        result = response.json()
        
        # Check if we got valid results
        if result and "suggestions" in result and len(result["suggestions"]) > 0:
            # Get the top match
            top_match = result["suggestions"][0]
            herb_name = top_match["plant_name"]
            confidence = top_match["probability"]
            
            # Additional plant details from Plant.id
            plant_details = top_match.get("plant_details", {})
            common_names = plant_details.get("common_names", [])
            common_name = common_names[0] if common_names else herb_name
            
            # Try to find this herb in our database
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # First try exact match
            sql = """
                SELECT d.name, d.medicinal_plants, d.natural_excipients, di.image_path
                FROM drug d
                LEFT JOIN drugimg di ON d.drug_id = di.drug_id
                WHERE d.name LIKE %s
            """
            cursor.execute(sql, (f"%{common_name}%",))
            
            herb_data = cursor.fetchone()
            
            # If no match, try with scientific name
            if not herb_data:
                cursor.execute(sql, (f"%{herb_name}%",))
                herb_data = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            # Prepare response
            response_data = {
                'herbName': common_name,
                'scientificName': herb_name,
                'confidence': confidence,
                'success': True
            }
            
            # Add Plant.id details
            wiki_desc = plant_details.get("wiki_description", {}).get("value", "")
            response_data['plantDetails'] = {
                'description': wiki_desc[:300] + "..." if len(wiki_desc) > 300 else wiki_desc,
                'url': plant_details.get("url", ""),
                'taxonomy': plant_details.get("taxonomy", {})
            }
            
            # Add our database info if available
            if herb_data:
                name, plants, excipients, image_path = herb_data
                response_data['dbInfo'] = {
                    'name': name,
                    'plants': plants,
                    'excipients': excipients,
                    'image_path': image_path
                }
            
            return jsonify(response_data)
        else:
            return jsonify({
                'success': False,
                'error': 'No plant identified in the image'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/recommend', methods=['GET', 'POST'])
def recommend():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get all symptoms for the dropdown
    cursor.execute("SELECT * FROM symptoms ORDER BY symptom_name")
    symptoms = cursor.fetchall()
    
    # Store recommendations
    recommendations = []
    
    if request.method == 'POST':
        # Get selected symptoms
        selected_symptoms = request.form.getlist('symptoms')
        
        if selected_symptoms:
            # Convert to list of IDs for SQL query
            symptom_ids = ','.join(selected_symptoms)
            
            # Query for herbs that help with selected symptoms
            sql = """
            SELECT h.*, 
                   GROUP_CONCAT(s.symptom_name SEPARATOR ', ') as matched_symptoms,
                   AVG(hs.effectiveness) as avg_effectiveness
            FROM herbs h
            JOIN herb_symptom hs ON h.herb_id = hs.herb_id
            JOIN symptoms s ON hs.symptom_id = s.symptom_id
            WHERE hs.symptom_id IN (%s)
            GROUP BY h.herb_id
            ORDER BY avg_effectiveness DESC
            """ % symptom_ids
            
            cursor.execute(sql)
            recommendations = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('recommend.html', symptoms=symptoms, recommendations=recommendations)

@app.route('/seasonal-diet', methods=['GET', 'POST'])
def seasonal_diet():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Seasons for dropdown
    seasons = ['Spring', 'Summer', 'Monsoon', 'Autumn', 'Winter']

    selected_season = request.form.get('season') if request.method == 'POST' else None
    selected_type = request.form.get('diet_type') if request.method == 'POST' else None

    # Get unique diet types for dropdown
    cursor.execute("SELECT DISTINCT diet_type FROM seasonal_diet")
    diet_types = [row['diet_type'] for row in cursor.fetchall() if row['diet_type']]

    # Query for foods
    query = "SELECT * FROM seasonal_diet"
    filters = []
    params = []
    if selected_season:
        filters.append("season=%s")
        params.append(selected_season)
    if selected_type:
        filters.append("diet_type=%s")
        params.append(selected_type)
    if filters:
        query += " WHERE " + " AND ".join(filters)
    cursor.execute(query, tuple(params))
    foods = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('seasonal_diet.html', seasons=seasons, diet_types=diet_types, foods=foods,
                           selected_season=selected_season, selected_type=selected_type)

# User profile routes
@app.route('/user-profile', methods=['GET', 'POST'])
def user_profile():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        allergies = request.form.get('allergies')
        diet_preference = request.form.get('diet_preference')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if user already exists
        cursor.execute("SELECT * FROM user_profiles WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        if user:
            # Update existing user
            cursor.execute(
                "UPDATE user_profiles SET email = %s, allergies = %s, diet_preference = %s WHERE username = %s",
                (email, allergies, diet_preference, username)
            )
        else:
            # Create new user
            cursor.execute(
                "INSERT INTO user_profiles (username, email, allergies, diet_preference) VALUES (%s, %s, %s, %s)",
                (username, email, allergies, diet_preference)
            )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Redirect to patients list instead of individual patient page
        return redirect(url_for('patient_list'))
    
    return render_template('user_profile.html')

@app.route('/patients')
def patient_list():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get all patient profiles
    cursor.execute("SELECT * FROM user_profiles ORDER BY username")
    patients = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('patient_list.html', patients=patients)

# Symptom tracker route
@app.route('/symptom-tracker/<username>', methods=['GET', 'POST'])
def symptom_tracker(username):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get user id
    cursor.execute("SELECT user_id FROM user_profiles WHERE username = %s", (username,))
    user = cursor.fetchone()
    
    if not user:
        cursor.close()
        conn.close()
        return redirect(url_for('user_profile'))
    
    user_id = user['user_id']
    
    if request.method == 'POST':
        symptom_name = request.form.get('symptom_name')
        severity = request.form.get('severity')
        notes = request.form.get('notes')
        
        cursor.execute(
            "INSERT INTO user_symptoms (user_id, symptom_name, severity, date_recorded, notes) VALUES (%s, %s, %s, CURDATE(), %s)",
            (user_id, symptom_name, severity, notes)
        )
        conn.commit()
        
        # Fetch recommendations based on symptoms
        cursor.execute("""
            SELECT h.name, h.herb_usage, hs.effectiveness 
            FROM herbs h
            JOIN herb_symptom hs ON h.herb_id = hs.herb_id
            JOIN symptoms s ON hs.symptom_id = s.symptom_id
            WHERE s.symptom_name LIKE %s
            ORDER BY hs.effectiveness DESC
            LIMIT 3
        """, (f"%{symptom_name}%",))
        
        recommendations = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('recommendations.html', username=username, symptom=symptom_name, recommendations=recommendations)
    
    # Get recent symptoms for display
    cursor.execute(
        "SELECT * FROM user_symptoms WHERE user_id = %s ORDER BY date_recorded DESC LIMIT 5",
        (user_id,)
    )
    recent_symptoms = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('symptom_tracker.html', username=username, symptoms=recent_symptoms)

# Herbal journal route
@app.route('/herb-journal/<username>', methods=['GET', 'POST'])
def herb_journal(username):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get user id
    cursor.execute("SELECT user_id, allergies FROM user_profiles WHERE username = %s", (username,))
    user = cursor.fetchone()
    
    if not user:
        cursor.close()
        conn.close()
        return redirect(url_for('user_profile'))
    
    user_id = user['user_id']
    user_allergies = user['allergies']
    
    if request.method == 'POST':
        herb_name = request.form.get('herb_name')
        effectiveness = request.form.get('effectiveness')
        notes = request.form.get('notes')
        
        cursor.execute(
            "INSERT INTO herb_journal (user_id, herb_name, date_used, effectiveness, notes) VALUES (%s, %s, CURDATE(), %s, %s)",
            (user_id, herb_name, effectiveness, notes)
        )
        conn.commit()
    
    # Get herb journal entries
    cursor.execute(
        "SELECT * FROM herb_journal WHERE user_id = %s ORDER BY date_used DESC",
        (user_id,)
    )
    journal_entries = cursor.fetchall()
    
    # Get herbs from the database for dropdown
    cursor.execute("SELECT name, benefits, herb_usage FROM herbs")
    herbs = cursor.fetchall()
    
    # Filter herbs based on user allergies
    safe_herbs = herbs
    if user_allergies:
        allergies_list = [a.strip().lower() for a in user_allergies.split(',')]
        safe_herbs = [h for h in herbs if not any(a in h['name'].lower() for a in allergies_list)]
    
    cursor.close()
    conn.close()
    
    return render_template('herb_journal.html', username=username, journal=journal_entries, herbs=safe_herbs)

# Add a health dashboard to see overview
@app.route('/health-dashboard/<username>')
def health_dashboard(username):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get user id
    cursor.execute("SELECT * FROM user_profiles WHERE username = %s", (username,))
    user = cursor.fetchone()
    
    if not user:
        cursor.close()
        conn.close()
        return redirect(url_for('user_profile'))
    
    user_id = user['user_id']
    
    # Get recent symptoms
    cursor.execute(
        "SELECT * FROM user_symptoms WHERE user_id = %s ORDER BY date_recorded DESC LIMIT 5",
        (user_id,)
    )
    recent_symptoms = cursor.fetchall()
    
    # Get effective herbs
    cursor.execute(
        "SELECT herb_name, AVG(effectiveness) as avg_effectiveness FROM herb_journal WHERE user_id = %s GROUP BY herb_name ORDER BY avg_effectiveness DESC LIMIT 3",
        (user_id,)
    )
    effective_herbs = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('health_dashboard.html', username=username, user=user, symptoms=recent_symptoms, herbs=effective_herbs)

@app.route('/delete-patient/<int:user_id>', methods=['POST'])
def delete_patient(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # First delete related records in user_symptoms and herb_journal tables
        cursor.execute("DELETE FROM user_symptoms WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM herb_journal WHERE user_id = %s", (user_id,))
        
        # Then delete the user profile
        cursor.execute("DELETE FROM user_profiles WHERE user_id = %s", (user_id,))
        
        conn.commit()
        
        # Flash a success message
        flash("Patient successfully deleted", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting patient: {str(e)}", "error")
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('patient_list'))

if __name__ == '__main__':
    app.run(debug=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
